# -*- coding: utf-8 -*-
"""jobradar.notify: 邮件推送（仅 QQ SMTP）+ 截止提醒"""
from __future__ import annotations

import os
import smtplib
from datetime import datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _env(name: str, cfg: dict, key: str) -> str:
    env_key = cfg.get(key) or key.upper()
    return os.environ.get(env_key, "")


def build_daily_html(items: list, pages_url: str = "") -> str:
    rows = []
    for it in items:
        score = it.get("score", "")
        rows.append(
            "<tr>"
            f"<td>{score}</td>"
            f"<td>{it.get('company', '')}</td>"
            f"<td>{it.get('title', '')}</td>"
            f"<td>{it.get('location', '')}</td>"
            f"<td>{it.get('salary', '')}</td>"
            f"<td>{it.get('deadline', '长期有效')}</td>"
            f"<td><a href='{it.get('url', '#')}'>投递</a></td>"
            "</tr>"
        )
    link = f"<p><a href='{pages_url}'>网页版工作台</a></p>" if pages_url else ""
    return f"""
    <h3>今日推荐岗位（{datetime.now():%Y-%m-%d}）</h3>
    <table border='1' cellpadding='6' style='border-collapse:collapse'>
    <tr><th>评分</th><th>公司</th><th>岗位</th><th>地点</th><th>薪资</th><th>截止</th><th>链接</th></tr>
    {''.join(rows)}
    </table>{link}"""


def build_deadline_html(soon: list) -> str:
    rows = "".join(
        f"<li>{j.get('company', '')} - {j.get('title', '')} "
        f"（截止 {j.get('deadline', '')}）<a href='{j.get('url', '#')}'>去投递</a></li>"
        for j in soon
    )
    return f"<h3>⏰ 即将截止提醒（3 天内）</h3><ul>{rows}</ul>"


def send_email(subject: str, html: str) -> bool:
    cfg_all = None  # 延迟导入避免循环
    from jobradar.core import load_notify_config
    cfg = (load_notify_config() or {}).get("notify", {}).get("email", {})
    user = _env("QQ_MAIL_USER", cfg, "from_user_env")
    code = _env("QQ_MAIL_AUTH_CODE", cfg, "auth_code_env")
    to = _env("MAIL_TO", cfg, "to_env")
    cc = _env("MAIL_CC", cfg, "cc_env")
    if not (user and code and to):
        raise RuntimeError("缺少邮箱 Secrets：QQ_MAIL_USER / QQ_MAIL_AUTH_CODE / MAIL_TO")

    prefix = cfg.get("subject_prefix", "")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(f"{prefix}{subject}", "utf-8")
    msg["From"] = user
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg.attach(MIMEText(html, "html", "utf-8"))

    receivers = [to] + ([cc] if cc else [])
    host = cfg.get("smtp_host", "smtp.qq.com")
    port = int(cfg.get("smtp_port", 465))
    if cfg.get("use_ssl", True):
        server = smtplib.SMTP_SSL(host, port, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        server.starttls()
    try:
        server.login(user, code)
        server.sendmail(user, receivers, msg.as_string())
    finally:
        server.quit()
    return True
