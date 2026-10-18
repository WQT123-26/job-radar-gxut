# -*- coding: utf-8 -*-
"""scripts/import_manual.py: 手动线索录入 CLI —— 将临时看到的岗位导入今日池"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jobradar.core import dedup_key, load_seen_keys, append_seen_keys

MANUAL_DIR = "data/manual_feeds"


def main():
    p = argparse.ArgumentParser(description="导入手动求职线索")
    p.add_argument("--company", required=True, help="公司名")
    p.add_argument("--title", required=True, help="岗位名")
    p.add_argument("--location", default="广东", help="工作地点")
    p.add_argument("--salary", default="", help="薪资文本，如 8-12K")
    p.add_argument("--deadline", default="", help="截止日期 YYYY-MM-DD")
    p.add_argument("--url", default="", help="投递链接")
    p.add_argument("--source", default="manual", help="来源标记")
    args = p.parse_args()

    job = {
        "company": args.company,
        "title": args.title,
        "location": args.location,
        "salary": args.salary,
        "deadline": args.deadline,
        "url": args.url,
        "source": args.source,
    }
    job["dedup_key"] = dedup_key(job)

    os.makedirs(MANUAL_DIR, exist_ok=True)
    path = os.path.join(MANUAL_DIR, "jobs.jsonl")
    # 查重：seen 中已存在则跳过
    seen = load_seen_keys(os.path.join("state", "seen_keys.txt"))
    if job["dedup_key"] in seen:
        print("[skip] already imported")
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(job, ensure_ascii=False) + "\n")
    append_seen_keys(os.path.join("state", "seen_keys.txt"), [job["dedup_key"]])
    print(f"[done] imported: {args.company} - {args.title} -> {path}")


if __name__ == "__main__":
    main()
