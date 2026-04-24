# B2B Content Growth OS (MVP)

面向 **B2B 增长策略公众号** 的内容生产闭环系统（Python实现）。

## 当前能力（一次性补齐）

1. 历史文章导入（内容资产库）
2. 选题生成（规则引擎 + OpenAI可选）
3. 草稿生成（大纲/正文/微信HTML）
4. 微信草稿箱投递（幂等键 + 自动重试）
5. Metrics 复盘 + Top N 推荐 + 分层推荐（客户/行业/阶段）
6. 发布审核日志（review/approve/reject/publish）
7. LLM 调用日志（模型、操作、时延、成功率、错误）
8. SQLite 本地 / PostgreSQL 生产切换
9. Docker + Cron + Windows 计划任务 + Systemd

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -e .[dev]
uvicorn app.main:app --reload
```

## 关键 API

- `POST /api/topics/generate`
- `POST /api/drafts/from-topic`
- `POST /api/metrics`
- `GET /api/metrics/summary`
- `GET /api/metrics/topic-recommendations?top_n=5`
- `GET /api/metrics/topic-recommendations/segmented?target_customer=...&industry=...&growth_stage=...`
- `POST /api/publish/review`
- `GET /api/publish/review-logs?limit=50`
- `POST /api/publish/wechat/draft`
- `POST /api/publish/wechat/retry`
- `GET /api/llm/logs?limit=50`

## 调度

- CLI 单次：`python -m app.workers.retry_worker --limit 20 --delay-minutes 10`
- Linux cron：`bash scripts/setup_cron.sh /path/to/repo /path/to/python /path/to/logfile`
- Windows 计划任务：`powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows_task.ps1 ...`
- Linux systemd：`sudo bash scripts/install_systemd_retry_worker.sh /opt/b2b-growth /opt/b2b-growth/.venv/bin/python`

## 环境变量

```bash
DATABASE_URL=sqlite:///data/b2b_growth.db
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
WECHAT_APPID=
WECHAT_APPSECRET=
```
