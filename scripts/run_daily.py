# -*- coding: utf-8 -*-
"""scripts/run_daily.py: 每日主流程 —— 抓取 → 去重 → 评分 → 选品 → 邮件/Pages

守门规则（v2）：
- 当日推荐为 0 条时不发送邮件（避免无意义空列表推送），仅在日志与 Pages 数据中如实记录
- 信源抓取失败会收集到 errors 清单，有岗位时随邮件如实标注，无岗位时写入 Pages 数据
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jobradar import adapters
from jobradar.core import (
    append_seen_keys,
    deadline_soon,
    dedup_key,
    load_seen_keys,
    load_sources,
    load_profile,
    load_registry,
    load_notify_config,
    select_daily,
)
from jobradar import report
from jobradar.notify import build_daily_html, build_deadline_html, send_email

STATE_DIR = "state"
PAGES_DIR = "docs/data"


def main():
    os.makedirs(STATE_DIR, exist_ok=True)
    seen_path = os.path.join(STATE_DIR, "seen_keys.txt")

    profile = load_profile()
    registry = load_registry()
    sources_cfg = load_sources()
    notify_cfg = load_notify_config()

    # 1. 抓取所有信源（返回 jobs + 失败清单）
    raw_jobs, source_errors = adapters.fetch_all(sources_cfg)
    print(f"[info] fetched {len(raw_jobs)} raw jobs, {len(source_errors)} sources failed")

    # 2. 去重（与历史 seen 对比）
    seen = load_seen_keys(seen_path)
    fresh, all_keys = [], []
    for j in raw_jobs:
        k = dedup_key(j)
        all_keys.append(k)
        if k not in seen:
            j["dedup_key"] = k
            fresh.append(j)
    print(f"[info] {len(fresh)} new jobs after dedup")

    # 3. 评分 + 按配额选品
    quota = notify_cfg.get("quota", {"S": 6, "A": 8, "B": 4, "C": 2})
    daily_items = select_daily(fresh, quota, profile, registry)
    soon = deadline_soon(raw_jobs, days=3)
    print(f"[info] selected {len(daily_items)} daily items, {len(soon)} deadline-soon")

    # 4. 写 Pages 数据（无论有无岗位，工作台如实展示）
    os.makedirs(PAGES_DIR, exist_ok=True)
    latest = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "jobs": daily_items,
        "source_errors": source_errors,
        "raw_count": len(raw_jobs),
        "fresh_count": len(fresh),
    }
    with open(os.path.join(PAGES_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(latest, f, ensure_ascii=False, indent=2)
    pages_url = profile.get("pages_url", "")
    report.write_pages("docs", latest)

    # 5. 空列表守门：无推荐岗位时不发邮件
    if not daily_items:
        print("[warn] no jobs today — email SKIPPED (empty-list guard)")
        print(f"[warn] source errors: {json.dumps(source_errors, ensure_ascii=False)}")
        append_seen_keys(seen_path, [j["dedup_key"] for j in fresh])
        print("[done] daily run complete (no email)")
        return

    # 6. 邮件推送（含失败信源如实标注）
    email_cfg = notify_cfg.get("notify", {})
    if email_cfg.get("email", {}).get("enabled", False):
        try:
            html = build_daily_html(daily_items, pages_url)
            if soon and email_cfg.get("reminder", {}).get("deadline_alert", {}).get("enabled"):
                html += build_deadline_html(soon)
            if source_errors:
                err_rows = "".join(f"<li>{e['name']}: {e['error']}</li>" for e in source_errors)
                html += f"<hr><p style='color:#888'>⚠️ 今日失败信源（如实上报）：</p><ul>{err_rows}</ul>"
            send_email(f"日报 {len(daily_items)} 个新岗位", html)
            print("[info] email sent")
        except Exception as e:  # noqa: BLE001
            print(f"[warn] email failed: {e}")

    # 7. 记录已推送
    append_seen_keys(seen_path, [j["dedup_key"] for j in fresh])
    print("[done] daily run complete")


if __name__ == "__main__":
    main()
