# -*- coding: utf-8 -*-
"""scripts/run_daily.py: 每日多次推送主流程（v3 待推池架构）

流程（早/中/晚三次运行完全一致，靠时间区分批次）：
1. 抓取全部信源（含失败清单）
2. 与「已推指纹 seen」+「待推池 queued」双重去重，把新岗位评分后并入待推池
3. 按 batch_size 从池中取本批岗位（同公司/同城限流），抽走即出池
4. 发邮件（本批为空则守门不发），并把本批指纹写入 seen
5. 保存 queue.json（剩余留给下一批）+ 刷新 Pages 数据

因此三批推送互不重复，且每批都能拿到足够数量。
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jobradar import adapters, report
from jobradar.core import (
    append_seen_keys,
    deadline_soon,
    dedup_key,
    load_notify_config,
    load_profile,
    load_registry,
    load_seen_keys,
    load_sources,
    score_job,
    veto,
)
from jobradar.notify import build_daily_html, build_deadline_html, send_email
from jobradar.queue import (
    load_queue,
    push_into_pool,
    save_queue,
    slot_label,
    take_batch,
)

STATE_DIR = "state"
PAGES_DIR = "docs/data"
QUEUE_PATH = os.path.join(STATE_DIR, "queue.json")
SEEN_PATH = os.path.join(STATE_DIR, "seen_keys.txt")


def main() -> int:
    os.makedirs(STATE_DIR, exist_ok=True)

    profile = load_profile()
    registry = load_registry()
    sources_cfg = load_sources()
    notify_cfg = load_notify_config()

    push_cfg = notify_cfg.get("push", {}) or {}
    batch_size = int(push_cfg.get("batch_size", 12))
    max_same_company = int(push_cfg.get("max_same_company", 2))
    max_same_city = int(push_cfg.get("max_same_city", 5))
    pool_cap = int(push_cfg.get("pool_cap", 600))

    # 1) 抓取
    raw_jobs, source_errors = adapters.fetch_all(sources_cfg)
    print(f"[info] fetched {len(raw_jobs)} raw jobs, {len(source_errors)} sources failed")

    # 2) 去重 + 评分 → 入池
    seen = load_seen_keys(SEEN_PATH)
    pool = load_queue(QUEUE_PATH)
    pool_before = len(pool)

    candidates = []
    skipped_seen = 0
    for job in raw_jobs:
        key = dedup_key(job)
        if key in seen:
            skipped_seen += 1
            continue
        if veto(job, profile):
            continue
        candidates.append({"score": score_job(job, profile, registry),
                           "dedup_key": key, **job})

    pool = push_into_pool(pool, candidates, seen, cap=pool_cap)
    print(f"[info] pool: {pool_before} -> {len(pool)} "
          f"(+{len(pool) - pool_before} new, {skipped_seen} already pushed)")

    # 3) 取本批
    batch, remaining = take_batch(pool, batch_size, max_same_company, max_same_city)
    label = slot_label()
    print(f"[info] {label} batch: {len(batch)} jobs, {len(remaining)} left in pool")

    soon = deadline_soon(raw_jobs, days=3)

    # 4) 保存队列（先落盘，确保即使发信失败也不重复推）
    save_queue(QUEUE_PATH, remaining)

    # 5) Pages 数据
    latest = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "slot": label,
        "jobs": batch,
        "pool_remaining": len(remaining),
        "source_errors": source_errors,
        "raw_count": len(raw_jobs),
        "fresh_count": len(batch),
    }
    os.makedirs(PAGES_DIR, exist_ok=True)
    with open(os.path.join(PAGES_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(latest, f, ensure_ascii=False, indent=2)
    pages_url = profile.get("pages_url", "")
    try:
        report.write_pages("docs", latest)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] pages write failed: {exc}")

    # 6) 空批次守门
    if not batch:
        print("[warn] empty batch — email SKIPPED (empty-list guard)")
        if remaining:
            print(f"[info] {len(remaining)} jobs still queued for next push")
        return 0

    # 7) 发信
    email_cfg = notify_cfg.get("notify", {}).get("email", {})
    if email_cfg.get("enabled", True):
        try:
            html = build_daily_html(batch, pages_url)
            reminder = notify_cfg.get("notify", {}).get("reminder", {})
            if soon and reminder.get("deadline_alert", {}).get("enabled"):
                html += build_deadline_html(soon)
            if source_errors:
                rows = "".join(
                    f"<li>{e['name']}: {e['error']}</li>" for e in source_errors)
                html += (f"<hr><p style='color:#888'>⚠️ 本次失败信源（如实上报）：</p>"
                         f"<ul>{rows}</ul>")
            send_email(f"{label}推送 {len(batch)} 个新岗位", html)
            print("[info] email sent")
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] email failed: {exc}")

    # 8) 记录已推（出池即永久去重）
    append_seen_keys(SEEN_PATH, [j["dedup_key"] for j in batch])
    print(f"[done] {label}推送完成：{len(batch)} 条，池内剩余 {len(remaining)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
