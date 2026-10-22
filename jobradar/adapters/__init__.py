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


def fetch_all(sources_cfg: dict):
    """遍历启用的信源抓取岗位。

    返回 (jobs, errors)：
    - jobs: 所有成功信源的岗位列表
    - errors: 失败信源的错误清单 [{name, error}]，供主流程在邮件/日志中如实上报
    """
    jobs, errors = [], []
    for src in sources_cfg.get("sources", []):
        if not src.get("enabled", True):
            continue
        name = src.get("name", src.get("adapter", "unknown"))
        adapter = get_adapter(src.get("adapter", ""))
        if adapter is None:
            errors.append({"name": name, "error": "adapter not registered"})
            continue
        try:
            got = adapter(src).fetch()
            jobs.extend(got)
            print(f"[info] source {name}: {len(got)} jobs")
        except Exception as e:  # noqa: BLE001
            print(f"[warn] source {name} failed: {e}")
            errors.append({"name": name, "error": str(e)})
    return jobs, errors


# 导入各适配器以完成注册
from . import generic  # noqa: E402,F401
from . import iguopin  # noqa: E402,F401
