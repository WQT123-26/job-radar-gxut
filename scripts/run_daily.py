# -*- coding: utf-8 -*-
"""scripts/run_daily.py: 每日主流程 —— 抓取 → 去重 → 评分 → 选品 → 邮件/Pages"""
from __future__ import annotations

import json
import os
import sys

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

    # 1. 抓取所有信源
    raw_jobs = adapters.fetch_all(sources_cfg) if hasattr(adapters, "fetch_all") else []
    print(f"[info] fetched {len(raw_jobs)} raw jobs")

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

    # 4. 写状态与 Pages 数据
    report.write_state_files(STATE_DIR, daily_items)
    os.makedirs(PAGES_DIR, exist_ok=True)
    latest = {"updated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
              "jobs": daily_items}
    with open(os.path.join(PAGES_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(latest, f, ensure_ascii=False, indent=2)
    pages_url = profile.get("pages_url", "")
    report.write_pages("docs", latest)

    # 5. 邮件推送
    email_cfg = notify_cfg.get("notify", {})
    if email_cfg.get("email", {}).get("enabled", False):
        try:
            html = build_daily_html(daily_items, pages_url)
            if soon and email_cfg.get("reminder", {}).get("deadline_alert", {}).get("enabled"):
                html += build_deadline_html(soon)
            send_email(f"日报 {len(daily_items)} 个新岗位", html)
            print("[info] email sent")
        except Exception as e:  # noqa: BLE001
            print(f"[warn] email failed: {e}")

    # 6. 记录已推送
    append_seen_keys(seen_path, [j["dedup_key"] for j in fresh])
    print("[done] daily run complete")


if __name__ == "__main__":
    main()
