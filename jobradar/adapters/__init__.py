# -*- coding: utf-8 -*-
"""jobradar.adapters: 信源适配器注册表"""
from __future__ import annotations

ADAPTERS = {}


def register(name: str):
    def deco(cls):
        ADAPTERS[name] = cls
        return cls
    return deco


def get_adapter(name: str):
    return ADAPTERS.get(name)


def fetch_all(sources_cfg: dict) -> list:
    """遍历启用的信源并抓取岗位列表，单个信源失败不影响整体"""
    jobs = []
    for src in sources_cfg.get("sources", []):
        if not src.get("enabled", True):
            continue
        adapter = get_adapter(src.get("adapter", ""))
        if adapter is None:
            continue
        try:
            jobs.extend(adapter(src).fetch())
        except Exception as e:  # noqa: BLE001
            print(f"[warn] source {src.get('name')} failed: {e}")
    return jobs


# 导入各适配器以完成注册
from . import generic  # noqa: E402,F401  通用 HTTP 适配器（九业/国聘/国聘/国资等占位）
