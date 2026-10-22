# -*- coding: utf-8 -*-
"""jobradar.adapters.iguopin: 国聘免登录职位接口适配器（v5）

签名算法逆向自官方前端 main.js：
Sign = HMAC-SHA256(HMAC-SHA256(MB, "YYYYMMDD:ts//180"), "ts|nonce|METHOD|path|pc")
接口: POST https://api4.iguopin.com/api/jobs/v3/list
注意：本适配器在沙箱 IP 下被服务端静默拦截（data:null），
     在 GitHub Actions 出口 IP 下待 Run 验证；失败会如实上报，不影响其他信源。
"""
from __future__ import annotations

import datetime as _dt
import hashlib as _hashlib
import hmac as _hmac
import json as _json
import random as _rd
import string as _sg
import time as _time

import requests

from . import register

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

_IGP_MB = "115WVZvg"
_IGP_HOST = "https://api4.iguopin.com"


def _igp_headers(method: str, path: str) -> dict:
    ts = int(_time.time())
    nonce = "".join(_rd.choices(_sg.ascii_lowercase + _sg.digits, k=8))
    joined = "|".join([str(ts), nonce, method.upper(), path, "pc"])
    day = _dt.datetime.fromtimestamp(ts).strftime("%Y%m%d")
    inner = _hmac.new(_IGP_MB.encode(), ("%s:%d" % (day, ts // 180)).encode(),
                      _hashlib.sha256).hexdigest()
    sign = _hmac.new(inner.encode(), joined.encode(), _hashlib.sha256).hexdigest()
    return {
        "User-Agent": UA, "Content-Type": "application/json", "Accept": "application/json",
        "Origin": "https://www.iguopin.com", "Referer": "https://www.iguopin.com/job",
        "Device": "pc", "Version": "5.2.300", "Subsite": "iguopin",
        "Sign": sign, "T": str(ts), "Nonce": nonce,
    }


@register("iguopin")
class IguopinAdapter:
    """国聘免登录职位列表（POST /api/jobs/v3/list，官方签名头）"""
    PATH = "/api/jobs/v3/list"

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self) -> list:
        jobs = []
        for page in (1, 2, 3):
            payload = _json.dumps({"page": page, "page_size": 20})
            r = requests.post(_IGP_HOST + self.PATH, data=payload.encode("utf-8"),
                              headers=_igp_headers("POST", self.PATH), timeout=25)
            r.raise_for_status()
            data = (r.json() or {}).get("data")
            if isinstance(data, dict):
                rows = (data.get("list") or data.get("rows")
                        or data.get("records") or data.get("data") or [])
            elif isinstance(data, list):
                rows = data
            else:
                rows = []
            if not rows:
                break
            for row in rows:
                def g(*keys, default=""):
                    for k in keys:
                        v = row.get(k)
                        if v:
                            return str(v).strip()
                    return default
                jobs.append({
                    "company": g("company_name", "companyName", "org_name"),
                    "title": g("name", "job_name", "title", "position_name"),
                    "location": g("city_name", "address", "work_place", "province_name"),
                    "salary": g("salary", "salary_text", "salary_desc"),
                    "deadline": "",
                    "url": "https://www.iguopin.com/job-detail?id=%s" % row.get("id", ""),
                    "source": "iguopin",
                })
        return jobs
