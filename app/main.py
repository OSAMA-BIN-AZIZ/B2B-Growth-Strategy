from __future__ import annotations

from app.compat import FastAPI, HTTPException
from app.models import (
    ArticleIn,
    ArticleOut,
    DraftFromTopicRequest,
    DraftOut,
    MetricIn,
    MetricSummary,
    PublishDraftRequest,
    PublishJobOut,
    TopicBatchResponse,
    TopicRequest,
)
from app.services.formatter import markdown_to_wechat_html
from app.services.llm import generate_markdown_via_openai, generate_topics_via_openai
from app.services.topic_engine import generate_topics
from app.services.wechat import WeChatDraftService
from app.services.writing_engine import generate_markdown, generate_meta, generate_outline
from app.storage import (
    get_draft,
    get_publish_job,
    init_db,
    insert_article,
    insert_draft,
    insert_metric,
    insert_publish_job,
    list_articles,
    list_metric_summary,
    topic_feedback_boost,
    update_publish_job,
)

app = FastAPI(title="B2B 内容增长操作系统 MVP", version="0.2.0")


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/articles/import", response_model=ArticleOut)
def import_article(payload: ArticleIn) -> ArticleOut:
    data = payload.model_dump(mode="json")
    new_id = insert_article(data)
    created = list_articles()[0]
    return ArticleOut(id=new_id, **created)


@app.get("/api/articles", response_model=list[ArticleOut])
def fetch_articles() -> list[ArticleOut]:
    return [ArticleOut(**item) for item in list_articles()]


@app.post("/api/topics/generate", response_model=TopicBatchResponse)
def topic_generate(req: TopicRequest) -> TopicBatchResponse:
    if req.use_openai:
        try:
            return generate_topics_via_openai(req)
        except Exception:
            pass

    topics = generate_topics(req, feedback_boost=topic_feedback_boost())
    return TopicBatchResponse(topics=topics, source="rule")


@app.post("/api/drafts/from-topic", response_model=DraftOut)
def draft_from_topic(req: DraftFromTopicRequest) -> DraftOut:
    outline = generate_outline(req.topic)
    markdown = ""

    if req.use_openai:
        try:
            markdown = generate_markdown_via_openai(req.topic)
        except Exception:
            markdown = ""

    if not markdown:
        markdown = generate_markdown(req.topic, outline)

    html = markdown_to_wechat_html(markdown)
    meta = generate_meta(req.topic)

    draft_id = insert_draft(
        {
            "topic_title": req.topic.title,
            "outline": outline,
            "markdown": markdown,
            "html": html,
            **meta,
        }
    )
    item = get_draft(draft_id)
    if not item:
        raise HTTPException(status_code=500, detail="Failed to save draft")

    return DraftOut(id=draft_id, **item)


@app.get("/api/drafts/{draft_id}", response_model=DraftOut)
def fetch_draft(draft_id: int) -> DraftOut:
    item = get_draft(draft_id)
    if not item:
        raise HTTPException(status_code=404, detail="Draft not found")
    return DraftOut(id=draft_id, **item)


@app.post("/api/metrics", response_model=dict)
def add_metric(payload: MetricIn) -> dict:
    metric_id = insert_metric(payload.model_dump())
    return {"id": metric_id, "status": "saved"}


@app.get("/api/metrics/summary", response_model=list[MetricSummary])
def metrics_summary() -> list[MetricSummary]:
    return [MetricSummary(**row) for row in list_metric_summary()]


@app.post("/api/publish/wechat/draft", response_model=PublishJobOut)
def publish_to_wechat_draft(payload: PublishDraftRequest) -> PublishJobOut:
    draft = get_draft(payload.draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    job_id = insert_publish_job(
        {
            "draft_id": payload.draft_id,
            "channel": "wechat_draft",
            "status": "pending",
            "message": "queued",
        }
    )

    try:
        media_id = WeChatDraftService().create_draft(
            title=draft["wechat_title"],
            content_html=draft["html"],
            digest=draft["wechat_summary"],
        )
        update_publish_job(job_id, "success", media_id, "draft created")
    except Exception as exc:
        update_publish_job(job_id, "failed", None, str(exc))

    job = get_publish_job(job_id)
    if not job:
        raise HTTPException(status_code=500, detail="Publish job not found")
    return PublishJobOut(**job)
