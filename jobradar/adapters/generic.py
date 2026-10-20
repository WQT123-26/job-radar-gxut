# -*- coding: utf-8 -*-
"""jobradar.adapters.generic: 信源适配器实装版

实测结论（2026-10-20）：
- 广西科技大学就业网 /mobile.php 接口必须带 login_user_id（登录态），
  需在仓库 Secrets 配置 JIUYEB_COOKIE（浏览器登录后的完整 Cookie），否则返回空并在错误清单中标注。
- 国聘 iguopin.com、ncss.cn 为 SPA / 需登录，免登录无法抓取，保留骨架并如实标注。
"""
from __future__ import annotations

import json
import os
import re

import requests

from . import register

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) job-radar-gxut/0.2"


def _cookie_str() -> str:
    """从 Secret 注入的环境变量读取校就业网 Cookie"""
    return os.environ.get("JIUYEB_COOKIE", "").strip()


@register("gxut_jiuyeb")
class GxutJiuyebAdapter:
    """广西科技大学就业网（gxkejidx.jiuyeb.cn）

    接口形态：GET /mobile.php?m=Zhaopin&c=xiaozhao&a=list&login_user_id=<uid>&pageNo=1&pageSize=20
    login_user_id 需从登录态 Cookie/JUEYEB_COOKIE 环境变量中提取；未配置则返回空列表。
    """

    BASE = "https://gxkejidx.jiuyeb.cn"

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def _extract_login_id(self, cookie: str) -> str:
        # jiuyeb 平台登录态常见字段：login_user_id 或 slogin_user_id
        m = re.search(r"(?:s?login_user_id)=(\d+)", cookie)
        return m.group(1) if m else ""

    def fetch(self) -> list:
        cookie = _cookie_str()
        if not cookie:
            raise RuntimeError(
                "gxut_jiuyeb: 未配置 JIUYEB_COOKIE Secret，"
                "校就业网接口需登录态（login_user_id），本日该源跳过"
            )
        uid = self._extract_login_id(cookie)
        if not uid:
            raise RuntimeError("gxut_jiuyeb: JIUYEB_COOKIE 中未找到 login_user_id 字段")

        jobs = []
        session = requests.Session()
        session.headers.update({"User-Agent": UA, "Cookie": cookie, "Referer": self.BASE + "/Zhaopin/xiaozhao.html"})
        for page in (1, 2, 3):
            url = (
                f"{self.BASE}/mobile.php?m=Zhaopin&c=xiaozhao&a=list"
                f"&login_user_id={uid}&pageNo={page}&pageSize=20"
            )
            r = session.get(url, timeout=20)
            r.raise_for_status()
            payload = r.json()
            data = payload.get("data") or {}
            rows = data.get("list") or data.get("rows") or data.get("records") or []
            if not rows:
                break
            for row in rows:
                info = row.get("jobInfo") or row
                jobs.append({
                    "company": (info.get("create_name") or info.get("company_name") or "").strip(),
                    "title": (info.get("work_name") or "").strip(),
                    "location": (info.get("address") or info.get("work_place") or "").strip(),
                    "salary": (info.get("xinzi") or "面议").strip(),
                    "deadline": (info.get("endDate") or info.get("daoqishijian") or "")[:10],
                    "url": f"{self.BASE}/Zhaopin/zhiweiDetail.html?jobtype={info.get('jobtype', '')}&id={row.get('publish_id') or info.get('id', '')}",
                    "source": "gxut_jiuyeb",
                })
        return jobs


@register("iguopin")
class IguopinAdapter:
    """国聘 iguopin.com（SPA，需登录态，免登录抓取不可行——实测确认）"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        raise RuntimeError("iguopin: 站点为 SPA 且接口需登录态，暂不可抓取（如实跳过）")


@register("ncss")
class NcssAdapter:
    """国家大学生就业服务平台 ncss.cn（需学信网登录态——实测确认）"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        raise RuntimeError("ncss: 需学信网登录态，暂不可抓取（如实跳过）")


@register("sasac_hr")
class SasacAdapter:
    """国资委央企招聘专栏（站群需 JS 渲染，暂不可静态抓取）"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        raise RuntimeError("sasac_hr: 页面为 JS 渲染，暂不可静态抓取（如实跳过）")


@register("moka_batch")
class MokaBatchAdapter:
    """Moka 招聘批量适配器（各公司站点接口不一，暂未实装）"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        raise RuntimeError("moka_batch: 未实装（如实跳过）")


@register("beisen_batch")
class BeisenBatchAdapter:
    """北森招聘批量适配器（暂未实装）"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        raise RuntimeError("beisen_batch: 未实装（如实跳过）")


def http_get(url: str, timeout: int = 15) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text
