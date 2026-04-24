# B2B Content Growth OS (MVP)

面向 **B2B 增长策略公众号** 的内容生产闭环系统（Python实现）。

## MVP 范围

当前版本已打通以下闭环：

1. 历史文章导入（内容资产库）
2. 选题生成（10个选题卡 + 评分）
3. 根据选题生成草稿（大纲 + Markdown正文 + 微信兼容HTML）
4. 草稿持久化与预览读取

> 设计原则：选题来自买家需求，文章服务询盘转化，草稿发布前人工审核。

## 技术栈

- Python 3.10 / 3.11 / 3.13 / 3.14
- FastAPI
- SQLite（本地部署零依赖）
- Pytest

## 目录结构

```text
app/
  main.py                     # API入口
  models.py                   # Pydantic模型
  storage.py                  # SQLite存储
  services/
    topic_engine.py           # 选题引擎（评分公式）
    writing_engine.py         # 写作引擎（大纲+正文+元信息）
    formatter.py              # 微信HTML排版转换
  templates/wechat/           # 微信模板目录（预留）
prompts/                      # 提示词模板目录
tests/
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

### 健康检查

- `GET /health`

### 文章库

- `POST /api/articles/import` 导入历史文章
- `GET /api/articles` 查询历史文章

### 选题库

- `POST /api/topics/generate`

请求示例：

```json
{
  "target_customer": "外贸负责人",
  "industry": "工业设备",
  "service": "B2B独立站增长",
  "article_goal": "提升询盘转化",
  "growth_stage": "有流量没询盘",
  "historical_reference": ["流量上涨但线索下降"]
}
```

### 草稿生成与预览

- `POST /api/drafts/from-topic` 根据选题卡生成草稿
- `GET /api/drafts/{draft_id}` 获取草稿详情

## 测试

```bash
pytest
```

## 后续迭代建议

- 接入 PostgreSQL（生产环境）
- 接入 OpenAI API（把规则引擎升级为模型推理）
- 接入微信草稿箱 API（先草稿、后人工发布）
- 新增 metrics 复盘与下一轮选题反馈
