# job-radar-gxut 🎯

面向 **广西科技大学 2027届 仪器与自动化本科** 的每日校招岗位推送系统。每天早上 07:30 自动从多个信源抓取岗位，三层去重 + 公司质量评分 + 配额选品，推送 **20 条**到邮箱，并把可筛选、可标记投递状态的工作台发布为公开网页（GitHub Pages），任何设备打开同一网址即可查看。

## 功能特性

- ✅ 每日 20 条不重复推送（三层去重：源内ID / 跨源指纹 / 历史冷却）
- ✅ 公司质量评分：上市 / 央国企 / 融资 / 专精特新 / 规模，S/A/B/C 四档
- ✅ 质量红线：<6K 否决；面议岗位需公司分≥75；产线倒班岗否决
- ✅ 广东优先加权，全国放开；制造业（设备/工艺/电气/仪控）权重上调
- ✅ 截止日当天 18:00 邮件提醒（主收件 + 抄送）
- ✅ 每周一 09:00 趋势周报
- ✅ 每条推送附可解释命中理由
- ✅ 缺口不降标准：库存不足时如实标注缺口数
- ✅ 手机端「标记已投」：无需令牌，通过 GitHub Issue 中转回写（方案B）

## 快速部署

1. **配置 Secrets**（Settings → Secrets and variables → Actions）：`QQ_MAIL_USER` / `QQ_MAIL_AUTH_CODE` / `MAIL_TO` / `MAIL_CC`
2. **开启 Pages**：Settings → Pages → Source 选 `main` 分支 `/docs` 目录
3. **首次运行**：Actions → Daily Job Push → Run workflow

## 目录结构

```
.github/workflows/   # daily.yml 每日推送；issue-writeback.yml 投递状态回写
config/              # profile.yaml 画像 / sources.yaml 信源 / company_registry.yaml 公司字典 / notify.yaml
jobradar/            # core.py 去重评分选品 / notify.py 推送 / report.py 日报周报Pages
scripts/             # run_daily.py 主流程 / process_issue.py Issue回写 / import_manual.py 手动录入
data/                # 库存池 / 去重历史 / 投递台账 / 信源健康
archive/             # 每日推送 Markdown 归档
docs/                # GitHub Pages 工作台 index.html
```

## 隐私红线

- 邮箱、授权码全部走 Secrets，仓库与日志中不可见
- 手机号不参与任何链路（微信推送通道已移除，仅邮件）
- `.gitignore` 已排除简历 PDF 与本地敏感文件

## 合规说明

仅采集公开可访问的招聘信息；遵守目标站点访问频率约束；不绕过登录、验证码或付费墙；不采集任何个人简历数据。本项目仅为技术实现，不构成求职建议；岗位信息以各官方平台为准。
