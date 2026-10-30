# -*- coding: utf-8 -*-
"""jobradar.queue: 待推池（pending queue）——支持每天多次推送且每批互不重复

设计借鉴招聘平台的「候选池 + 批次消费」模式：
- 每次运行先把新发现的岗位评分后放入待推池（state/queue.json）
- 每次推送按分数 + 多样性规则从池中取出 batch_size 条（一次性消费，出池即标记已推）
- 池中剩余岗位保留给下一次推送，因此早/中/晚三批天然互不重复
- 已推送指纹另存 state/seen_keys.txt，保证历史岗位永不重复出现
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta


def load_queue(path: str) -> list:
    """读取待推池，返回 items 列表（按 score 降序）"""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (ValueError, OSError):
        return []
    items = data.get("items") or []
    items.sort(key=lambda x: -int(x.get("score", 0)))
    return items


def save_queue(path: str, items: list) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(items),
        "items": items,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)


def queued_keys(items: list) -> set:
    return {it.get("dedup_key") for it in items if it.get("dedup_key")}


def take_batch(items: list, size: int, max_same_company: int = 2,
               max_same_city: int = 5) -> tuple:
    """从池中取一批：按分数优先，同时限制同公司/同城重复

    返回 (batch, remaining)。抽走的条目不再回到池中，保证三批互不重复。
    """
    batch, remaining = [], []
    comp_cnt, city_cnt = {}, {}
    for it in items:
        if len(batch) >= size:
            remaining.append(it)
            continue
        comp = (it.get("company") or "").strip()
        city = (it.get("location") or "").strip()
        if comp and comp_cnt.get(comp, 0) >= max_same_company:
            remaining.append(it)
            continue
        if city and city_cnt.get(city, 0) >= max_same_city:
            remaining.append(it)
            continue
        batch.append(it)
        if comp:
            comp_cnt[comp] = comp_cnt.get(comp, 0) + 1
        if city:
            city_cnt[city] = city_cnt.get(city, 0) + 1
    return batch, remaining


def push_into_pool(pool: list, new_items: list, seen: set, cap: int = 600) -> list:
    """把新岗位并入池，跳过已在 seen / 已在池中的条目，并限制池规模"""
    have = queued_keys(pool)
    merged = list(pool)
    for it in new_items:
        k = it.get("dedup_key")
        if not k or k in seen or k in have:
            continue
        merged.append(it)
        have.add(k)
    merged.sort(key=lambda x: -int(x.get("score", 0)))
    return merged[:cap]


def slot_label(now: datetime = None) -> str:
    """按北京时间（UTC+8）判断当前推送时段标签

    GitHub Actions runner 默认 UTC 时区：北京 07:30 = UTC 23:30，
    若不换算会被误标为「晚间」，因此这里显式做 +8 小时换算。
    """
    now = now or (datetime.utcnow() + timedelta(hours=8))
    h = now.hour
    if 5 <= h < 11:
        return "早间"
    if 11 <= h < 16:
        return "午间"
    return "晚间"
