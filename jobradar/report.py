# -*- coding: utf-8 -*-
"""jobradar.report: 日报/周报文本生成 + GitHub Pages 工作台页面"""
from __future__ import annotations

import json
import os
from datetime import datetime


def _job_line(it: dict) -> str:
    return (
        f"- [{it.get('score', '')}] {it.get('company', '')} | {it.get('title', '')} | "
        f"{it.get('location', '')} | {it.get('salary', '') or '面议'} | "
        f"截止: {it.get('deadline') or '长期有效'} | {it.get('url', '')}"
    )


def build_daily_md(items: list, soon: list) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# 求职日报 {today}", ""]
    if soon:
        lines.append("## ⏰ 即将截止（3 天内）")
        lines += [_job_line(j) for j in soon]
        lines.append("")
    lines.append("## 📮 今日推荐")
    if items:
        lines += [_job_line(it) for it in items]
    else:
        lines.append("> 今日暂无符合条件的新岗位")
    return "\n".join(lines)


def build_weekly_md(week_items: list) -> str:
    monday = datetime.now()
    lines = [f"# 求职周报（{monday:%Y-%m-%d} 所在周）", ""]
    if week_items:
        lines += [_job_line(it) for it in week_items]
    else:
        lines.append("> 本周暂无数据")
    return "\n".join(lines)


def write_state_files(data_dir: str, all_jobs: list, applied: list = None) -> None:
    """写入运行状态文件，供 Pages 与 Issue 回写使用"""
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "latest.json"), "w", encoding="utf-8") as f:
        json.dump({"updated_at": datetime.now().isoformat(timespec="seconds"),
                   "jobs": all_jobs}, f, ensure_ascii=False, indent=2)
    with open(os.path.join(data_dir, "applied.json"), "w", encoding="utf-8") as f:
        json.dump(applied or [], f, ensure_ascii=False, indent=2)


def build_index_html(latest: dict, applied: list = None) -> str:
    """生成 GitHub Pages 工作台单页"""
    jobs = latest.get("jobs", [])
    updated = latest.get("updated_at", "")
    rows = "".join(
        f"<tr><td>{j.get('score', '')}</td><td>{j.get('company', '')}</td>"
        f"<td>{j.get('title', '')}</td><td>{j.get('location', '')}</td>"
        f"<td>{j.get('salary', '') or '面议'}</td><td>{j.get('deadline') or '长期有效'}</td>"
        f"<td><a href='{j.get('url', '#')}' target='_blank'>投递</a></td></tr>"
        for j in jobs
    )
    applied_rows = "".join(
        f"<tr><td>{a.get('company', '')}</td><td>{a.get('title', '')}</td>"
        f"<td>{a.get('status', '')}</td><td>{a.get('updated_at', '')}</td></tr>"
        for a in (applied or [])
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>求职雷达工作台</title>
<style>
body{{font-family:system-ui,-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;margin:24px;color:#1f2328}}
h1{{font-size:1.4em}} table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{border:1px solid #d0d7de;padding:6px 10px;text-align:left}}
th{{background:#f6f8fa}} tr:nth-child(even){{background:#fafbfc}}
.badge{{display:inline-block;background:#0969da;color:#fff;border-radius:12px;padding:2px 10px;font-size:12px;margin-left:8px}}
</style>
</head>
<body>
<h1>🎯 求职雷达工作台 <span class="badge">更新 {updated}</span></h1>
<h2>今日岗位池（{len(jobs)}）</h2>
<table>
<tr><th>评分</th><th>公司</th><th>岗位</th><th>地点</th><th>薪资</th><th>截止</th><th>链接</th></tr>
{rows}
</table>
<h2>投递状态跟踪</h2>
<table>
<tr><th>公司</th><th>岗位</th><th>状态</th><th>更新时间</th></tr>
{applied_rows}
</table>
<p style="color:#57606a">由 GitHub Actions 每日自动更新 · 广西科技大学 27 届仪器自动化求职雷达</p>
</body>
</html>"""


def write_pages(data_dir: str, latest: dict, applied: list = None) -> str:
    os.makedirs(data_dir, exist_ok=True)
    html = build_index_html(latest, applied)
    path = os.path.join(data_dir, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
