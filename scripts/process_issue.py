# -*- coding: utf-8 -*-
"""scripts/process_issue.py: 解析投递状态回写 Issue，更新 docs/data/applied.json（方案 B）"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

APPLIED_PATH = "docs/data/applied.json"

# Issue 模板格式：
# ### 公司
# 汇川技术
# ### 岗位
# 仪器研发工程师
# ### 状态
# 已投递 | 已过筛 | 一面 | 二面 | offer | 挂了


def parse_issue(body: str) -> dict:
    """从 Issue 正文提取公司/岗位/状态"""
    fields = {}
    for key in ("公司", "岗位", "状态"):
        m = re.search(rf"###\s*{key}\s*\n+\s*(.+)", body)
        if m:
            fields[key] = m.group(1).strip()
    return {
        "company": fields.get("公司", ""),
        "title": fields.get("岗位", ""),
        "status": fields.get("状态", "已投递"),
    }


def load_applied() -> list:
    if os.path.exists(APPLIED_PATH):
        with open(APPLIED_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def upsert(records: list, item: dict) -> list:
    """按 公司+岗位 更新或追加"""
    for r in records:
        if r.get("company") == item["company"] and r.get("title") == item["title"]:
            r.update(item, updated_at=datetime.now().isoformat(timespec="seconds"))
            break
    else:
        item["updated_at"] = datetime.now().isoformat(timespec="seconds")
        records.append(item)
    return records


def main(issue_title: str, issue_body: str):
    if "投递" not in issue_title and "回写" not in issue_title:
        print("[skip] not a write-back issue")
        return
    item = parse_issue(issue_body or "")
    if not item["company"]:
        print("[skip] missing company field")
        return
    records = upsert(load_applied(), item)
    os.makedirs(os.path.dirname(APPLIED_PATH), exist_ok=True)
    with open(APPLIED_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"[done] applied records: {len(records)}")


if __name__ == "__main__":
    # 由 issue-writeback.yml 注入环境变量
    main(os.environ.get("ISSUE_TITLE", ""), os.environ.get("ISSUE_BODY", ""))
