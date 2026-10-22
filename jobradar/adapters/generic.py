# -*- coding: utf-8 -*-
"""jobradar.adapters.generic: 高校就业网实抓适配器 + 种子岗位兜底（v3）

实测结论（2026-10-22，均已 curl 验证）：
- 华南师范大学 career.scnu.edu.cn 主页静态包含 /detail/online?id= 岗位条目
  （含"广东电网2027年校园招聘"等真实校招公告）→ 已实装 ✅
- 广东外语外贸大学 career.gdufs.edu.cn 主页静态包含 job-detail?id= 与
  jobs-brief-detail?id= 条目 → 已实装 ✅
- 国聘/ncss/BOSS直聘/国资小新：SPA 或需登录/违反平台协议 → 不做，如实跳过
- 岗位公告标题通常无薪资 → 交由 core.select_daily 的公司质量分规则处理（≥75 分），标注"薪资待确认"
"""
from __future__ import annotations

import re

import requests

from . import register

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HDRS = {"User-Agent": UA, "Accept": "text/html", "Accept-Language": "zh-CN,zh;q=0.9"}


def _get(url: str) -> str:
    r = requests.get(url, headers=HDRS, timeout=25, allow_redirects=True)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


@register("scnu_home")
class ScnuHomeAdapter:
    """华南师范大学就业网主页：/detail/online?id= 静态条目（已实测）"""

    URL = "https://career.scnu.edu.cn/"
    BASE = "https://career.scnu.edu.cn"

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        html = _get(self.URL)
        jobs = []
        seen = set()
        for m in re.finditer(
            r'href="(/detail/online\?id=\d+)"[^>]*title="([^"]+)"', html
        ):
            path, title = m.group(1), _clean(m.group(2))
            if path in seen or not title:
                continue
            seen.add(path)
            if not re.search(r"招聘|校招|宣讲|人才|招聘会", title):
                continue
            jobs.append({
                "company": _extract_company(title),
                "title": title,
                "location": "广东",
                "salary": "",  # 公告无薪资 → 薪资待确认，走质量分规则
                "deadline": "",
                "url": self.BASE + path,
                "source": "scnu",
            })
        return jobs


@register("gdufs_home")
class GdufsHomeAdapter:
    """广东外语外贸大学就业网主页：job-detail / jobs-brief-detail 静态条目（已实测）"""

    URL = "https://career.gdufs.edu.cn/"
    BASE = "https://career.gdufs.edu.cn"

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        html = _get(self.URL)
        jobs, seen = [], set()
        pat = re.compile(r'href="((?:job-detail|jobs-brief-detail)\?id=[^"]+)"[^>]*>')
        # 相邻文本取标题：<a href=...>标题</a>
        for m in re.finditer(
            r'href="((?:job-detail|jobs-brief-detail)\?id=[^"]+)"[^>]*>([^<]{8,80})</a>', html
        ):
            path, title = m.group(1), _clean(m.group(2))
            if path in seen or not title:
                continue
            seen.add(path)
            if not re.search(r"招聘|校招|宣讲|人才|招聘会|简章", title):
                continue
            jobs.append({
                "company": _extract_company(title),
                "title": title,
                "location": "广东",
                "salary": "",
                "deadline": "",
                "url": self.BASE + "/" + path,
                "source": "gdufs",
            })
        return jobs


def _extract_company(title: str) -> str:
    """从公告标题提取公司名：取“2026/2027届校招”或“招聘”前的主体"""
    m = re.split(r"\d{4}[-~—至]*\d{0,4}届|招聘|校招|宣讲|引进|简章|启事|公告", title)[0]
    return _clean(m) or title


@register("seed_jobs")
class SeedJobsAdapter:
    """冷启动种子岗位：预先核实的 2027 届真实校招线索（保证首封邮件非空）"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        import json
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), "data", "seed_jobs.json")
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


@register("gxut_jiuyeb")
class GxutJiuyebAdapter:
    """广西科技大学就业网（需 JIUYEB_COOKIE 登录态，未配置则如实跳过）"""

    BASE = "https://gxkejidx.jiuyeb.cn"

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        import os
        cookie = os.environ.get("JIUYEB_COOKIE", "").strip()
        if not cookie:
            raise RuntimeError("gxut_jiuyeb: 未配置 JIUYEB_COOKIE，本日该源跳过")
        m = re.search(r"(?:s?login_user_id)=(\d+)", cookie)
        if not m:
            raise RuntimeError("gxut_jiuyeb: Cookie 中未找到 login_user_id")
        uid = m.group(1)
        jobs = []
        s = requests.Session()
        s.headers.update({"User-Agent": UA, "Cookie": cookie,
                          "Referer": self.BASE + "/Zhaopin/xiaozhao.html"})
        for page in (1, 2):
            url = (f"{self.BASE}/mobile.php?m=Zhaopin&c=xiaozhao&a=list"
                   f"&login_user_id={uid}&pageNo={page}&pageSize=20")
            r = s.get(url, timeout=20)
            r.raise_for_status()
            data = (r.json().get("data") or {})
            rows = data.get("list") or data.get("rows") or data.get("records") or []
            if not rows:
                break
            for row in rows:
                info = row.get("jobInfo") or row
                jobs.append({
                    "company": (info.get("create_name") or info.get("company_name") or "").strip(),
                    "title": (info.get("work_name") or "").strip(),
                    "location": (info.get("address") or info.get("work_place") or "广西").strip(),
                    "salary": (info.get("xinzi") or "").strip(),
                    "deadline": (info.get("endDate") or "")[:10],
                    "url": f"{self.BASE}/Zhaopin/zhiweiDetail.html?jobtype={info.get('jobtype', '')}&id={row.get('publish_id') or info.get('id', '')}",
                    "source": "gxut_jiuyeb",
                })
        return jobs


def http_get(url: str, timeout: int = 15) -> str:
    return _get(url)
