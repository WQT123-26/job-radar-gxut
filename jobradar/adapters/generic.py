# -*- coding: utf-8 -*-
"""jobradar.adapters.generic: 通用 HTTP 抓取适配器（骨架版）"""
from __future__ import annotations

import requests

from . import register


@register("gxut_jiuyeb")
class GxutJiuyebAdapter:
    """广西科技大学就业网（骨架：返回空列表，待解析规则补充）"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        # TODO: 解析 https://gxkejidx.jiuyeb.cn/Zhaopin/xiaozhao.html 校招列表
        return []


@register("iguopin")
class IguopinAdapter:
    """国聘 iguopin.com（骨架）"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        # TODO: 调用国聘公开搜索接口
        return []


@register("ncss")
class NcssAdapter:
    """国家大学生就业服务平台 ncss.cn（骨架）"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        return []


@register("sasac_hr")
class SasacAdapter:
    """国资委央企招聘专栏（骨架）"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        return []


@register("moka_batch")
class MokaBatchAdapter:
    """Moka 招聘批量适配器（按 watchlist 中 moka_slug 抓取）"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        # TODO: 遍历 sources.yaml guangdong_watchlist 中带 moka_slug 的公司
        return []


@register("beisen_batch")
class BeisenBatchAdapter:
    """北森招聘批量适配器（骨架）"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        return []


def http_get(url: str, timeout: int = 15) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (job-radar-gxut/0.1)"}
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text
