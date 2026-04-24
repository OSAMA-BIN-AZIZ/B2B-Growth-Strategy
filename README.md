# B2B Content Growth OS (MVP)

面向 **B2B 增长策略公众号** 的内容生产闭环系统（Python实现）。

## MVP 范围

当前版本已打通并扩展以下闭环：

1. 历史文章导入（内容资产库）
2. 选题生成（10个选题卡 + 评分）
3. 根据选题生成草稿（大纲 + Markdown正文 + 微信兼容HTML）
4. 草稿持久化与预览读取
5. **Metrics复盘与下一轮选题反馈加权**
6. **微信草稿箱投递（先草稿、后人工发布）**

> 设计原则：选题来自买家需求，文章服务询盘转化，草稿发布前人工审核。

## 技术栈

- Python 3.10 / 3.11 / 3.13 / 3.14
- FastAPI（缺失依赖时自动使用兼容层，便于离线测试）
- SQLite（本地）/ PostgreSQL（生产）
- OpenAI API（可选，失败自动回退规则引擎）
- Pytest

## 环境变量

```bash
# 数据库（默认SQLite）
DATABASE_URL=sqlite:///data/b2b_growth.db
# 生产示例
# DATABASE_URL=postgresql://user:password@host:5432/b2b_growth

# OpenAI（可选）
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini

# 微信草稿箱（可选）
WECHAT_APPID=
WECHAT_APPSECRET=
```

## 快速启动（本地）

### 1) 创建虚拟环境并安装依赖

#### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[dev]
```

#### Windows (PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e .[dev]
```

### 2) 启动服务

```bash
uvicorn app.main:app --reload
```

打开 `http://127.0.0.1:8000/docs` 进行接口调试。

## 核心 API

### 文章库

- `POST /api/articles/import` 导入历史文章
- `GET /api/articles` 查询历史文章

### 选题与草稿

- `POST /api/topics/generate`（`use_openai=true`时优先模型推理）
- `POST /api/drafts/from-topic`（失败自动回退规则写作）
- `GET /api/drafts/{draft_id}`

### 发布管理（微信草稿）

- `POST /api/publish/wechat/draft`

### 数据复盘

- `POST /api/metrics`
- `GET /api/metrics/summary`

## PostgreSQL 生产接入

1. 安装 `psycopg`。
2. 设置 `DATABASE_URL=postgresql://...`。
3. 启动服务时自动建表（`articles / drafts / metrics / publish_jobs`）。

## 测试

```bash
pytest
```
