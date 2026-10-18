# -*- coding: utf-8 -*-
"""jobradar.core: 岗位去重、评分与每日选品核心逻辑"""
from __future__ import annotations

import hashlib
import os
import re
import yaml
from datetime import datetime, timedelta

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")


def load_yaml(name: str):
    path = os.path.join(CONFIG_DIR, name)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def norm_text(s: str) -> str:
    """规范化文本，用于去重指纹"""
    if not s:
        return ""
    s = re.sub(r"\s+", "", str(s))
    return s.lower()


def dedup_key(job: dict) -> str:
    """同一公司+岗位名视为重复"""
    company = norm_text(job.get("company", ""))
    title = norm_text(job.get("title", ""))
    raw = f"{company}|{title}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def load_seen_keys(state_path: str) -> set:
    if os.path.exists(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()


def append_seen_keys(state_path: str, keys) -> None:
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "a", encoding="utf-8") as f:
        for k in keys:
            f.write(k + "\n")


def parse_salary_min(text: str):
    """从薪资文本提取下限（元/月），失败返回 None"""
    if not text:
        return None
    t = str(text)
    m = re.search(r"(\d+(?:\.\d+)?)\s*[-~到]\s*(\d+(?:\.\d+)?)\s*(千|k|K|万|w|W)?", t)
    if not m:
        m2 = re.search(r"(\d+(?:\.\d+)?)\s*(千|k|K|万|w|W)", t)
        if not m2:
            return None
        lo = hi = float(m2.group(1))
        unit = m2.group(2)
    else:
        lo, hi = float(m.group(1)), float(m.group(2))
        unit = m.group(3)
    mult = {"千": 1000, "k": 1000, "K": 1000, "万": 10000, "w": 10000, "W": 10000}.get(unit, 1)
    return int(min(lo, hi) * mult)


def veto(job: dict, profile: dict) -> bool:
    """一票否决：薪资 <6K 或地点不符合"""
    sal = parse_salary_min(job.get("salary", ""))
    if sal is not None and sal < 6000:
        return True
    loc = job.get("location", "") or ""
    if profile.get("location_priority") == "广东" and loc and "广东" not in loc and "广州" not in loc \
       and "深圳" not in loc and "东莞" not in loc and "佛山" not in loc and "珠海" not in loc \
       and "惠州" not in loc and "中山" not in loc:
        return True
    return False


def company_tier(company: str, registry: dict) -> str:
    for c in registry.get("companies", []):
        names = [c.get("name", "")] + list(c.get("alias", []))
        if any(n and n in company for n in names):
            return c.get("tier", "B")
    return registry.get("defaults", {}).get("unknown_company", {}).get("tier", "B")


TIER_SCORE = {"S": 40, "A": 30, "B": 20, "C": 10}


def score_job(job: dict, profile: dict, registry: dict) -> int:
    """综合评分：tier 基础分 + 关键词匹配 - 距离截止惩罚"""
    s = TIER_SCORE.get(company_tier(job.get("company", ""), registry), 20)
    text = norm_text(job.get("title", "")) + norm_text(job.get("tags", ""))
    for kw in profile.get("keywords", []):
        if norm_text(kw) and norm_text(kw) in text:
            s += 5
    ddl = job.get("deadline")
    if ddl:
        try:
            d = datetime.strptime(str(ddl)[:10], "%Y-%m-%d")
            days = (d - datetime.now()).days
            if days <= 3:
                s += 10  # 快截止优先展示
            elif days < 0:
                s = 0
        except ValueError:
            pass
    return s


def select_daily(jobs: list, quota: dict, profile: dict, registry: dict) -> list:
    """按评分排序并按 tier 配额选取每日推荐"""
    scored = []
    for j in jobs:
        if veto(j, profile):
            continue
        scored.append((score_job(j, profile, registry), j))
    scored.sort(key=lambda x: -x[0])
    counts = {"S": 0, "A": 0, "B": 0, "C": 0}
    picked = []
    for sc, j in scored:
        t = company_tier(j.get("company", ""), registry)
        cap = int(quota.get(t, 0))
        if cap and counts[t] < cap:
            counts[t] += 1
            picked.append({"score": sc, **j})
    return picked


def deadline_soon(jobs: list, days: int = 3) -> list:
    """即将截止的岗位"""
    soon = []
    limit = datetime.now() + timedelta(days=days)
    for j in jobs:
        ddl = j.get("deadline")
        if not ddl:
            continue
        try:
            d = datetime.strptime(str(ddl)[:10], "%Y-%m-%d")
            if datetime.now() <= d <= limit:
                soon.append(j)
        except ValueError:
            pass
    soon.sort(key=lambda x: x.get("deadline", ""))
    return soon


def load_profile():
    return load_yaml("profile.yaml")


def load_registry():
    return load_yaml("company_registry.yaml")


def load_sources():
    return load_yaml("sources.yaml")


def load_notify_config():
    return load_yaml("notify.yaml")
