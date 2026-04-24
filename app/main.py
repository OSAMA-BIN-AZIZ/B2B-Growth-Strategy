from __future__ import annotations

from pathlib import Path

from app.compat import FastAPI, HTTPException
from app.models import (
    ArticleIn,
    ArticleOut,
    AuditLogOut,
    DraftFromTopicRequest,
    DraftOut,
    LLMLogOut,
    MetricIn,
    MetricSummary,
    PublishAuditIn,
    PublishDraftRequest,
    PublishJobOut,
    RetryResult,
    TopicBatchResponse,
    TopicRecommendation,
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
    get_publish_job_by_idempotency,
    init_db,
    insert_article,
    insert_audit_log,
    insert_draft,
    insert_metric,
    insert_publish_job,
    list_articles,
    list_audit_logs,
    list_llm_logs,
    list_metric_summary,
    list_publish_jobs,
    list_retryable_publish_jobs,
    list_segmented_topic_recommendations,
    list_topic_recommendations,
    mark_retry_scheduled,
    topic_feedback_boost,
    update_publish_job,
)

app = FastAPI(title="B2B 内容增长操作系统 MVP", version="0.4.0")


@app.on_event("startup")
def _startup() -> None:
    init_db()


def _attempt_wechat_publish(job_id: int, draft: dict) -> tuple[bool, str | None, str]:
    try:
        media_id = WeChatDraftService().create_draft(
            title=draft["wechat_title"],
            content_html=draft["html"],
            digest=draft["wechat_summary"],
        )
        update_publish_job(job_id, "success", media_id, "draft created")
        insert_audit_log({"draft_id": draft["id"], "action": "published", "actor": "system", "note": "wechat draft created"})
        return True, media_id, "draft created"
    except Exception as exc:
        update_publish_job(job_id, "failed", None, str(exc))
        return False, None, str(exc)


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


@app.get("/api/metrics/topic-recommendations", response_model=list[TopicRecommendation])
def metric_topic_recommendations(top_n: int = 5) -> list[TopicRecommendation]:
    rows = list_topic_recommendations(top_n=top_n)
    return [TopicRecommendation(**row) for row in rows]


@app.get("/api/metrics/topic-recommendations/segmented", response_model=list[TopicRecommendation])
def metric_topic_recommendations_segmented(
    top_n: int = 5,
    target_customer: str | None = None,
    industry: str | None = None,
    growth_stage: str | None = None,
) -> list[TopicRecommendation]:
    rows = list_segmented_topic_recommendations(
        top_n=top_n, target_customer=target_customer, industry=industry, growth_stage=growth_stage
    )
    return [TopicRecommendation(**row) for row in rows]


@app.post("/api/publish/review", response_model=AuditLogOut)
def publish_review(payload: PublishAuditIn) -> AuditLogOut:
    log_id = insert_audit_log(payload.model_dump())
    rows = list_audit_logs(limit=1)
    if not rows:
        raise HTTPException(status_code=500, detail="Audit log save failed")
    return AuditLogOut(id=log_id, **rows[0])


@app.get("/api/publish/review-logs", response_model=list[AuditLogOut])
def publish_review_logs(limit: int = 50) -> list[AuditLogOut]:
    return [AuditLogOut(**row) for row in list_audit_logs(limit=limit)]


@app.get("/api/llm/logs", response_model=list[LLMLogOut])
def get_llm_logs(limit: int = 50) -> list[LLMLogOut]:
    return [LLMLogOut(**row) for row in list_llm_logs(limit=limit)]




@app.get("/api/publish/jobs", response_model=list[PublishJobOut])
def list_publish_jobs_api(limit: int = 50) -> list[PublishJobOut]:
    return [PublishJobOut(**row) for row in list_publish_jobs(limit=limit)]


@app.get("/admin")
def admin_dashboard() -> str:
    template = Path("app/templates/admin_dashboard.html")
    if not template.exists():
        raise HTTPException(status_code=404, detail="dashboard not found")
    return template.read_text(encoding="utf-8")


@app.post("/api/publish/wechat/draft", response_model=PublishJobOut)
def publish_to_wechat_draft(payload: PublishDraftRequest) -> PublishJobOut:
    draft = get_draft(payload.draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    idempotency_key = payload.idempotency_key or f"wechat_draft:{payload.draft_id}"
    existing = get_publish_job_by_idempotency("wechat_draft", idempotency_key)
    if existing:
        return PublishJobOut(**existing)

    job_id = insert_publish_job(
        {
            "draft_id": payload.draft_id,
            "channel": "wechat_draft",
            "status": "pending",
            "message": "queued",
            "idempotency_key": idempotency_key,
            "max_retries": payload.max_retries,
        }
    )
    insert_audit_log({"draft_id": payload.draft_id, "action": "reviewed", "actor": "system", "note": "queued to wechat draft"})

    _attempt_wechat_publish(job_id, draft)

    job = get_publish_job(job_id)
    if not job:
        raise HTTPException(status_code=500, detail="Publish job not found")
    return PublishJobOut(**job)


@app.post("/api/publish/wechat/retry", response_model=RetryResult)
def retry_failed_publish_jobs(limit: int = 20, delay_minutes: int = 10) -> RetryResult:
    jobs = list_retryable_publish_jobs(limit=limit)
    scanned = len(jobs)
    retried = succeeded = failed = 0

    for job in jobs:
        draft = get_draft(job["draft_id"])
        if not draft:
            update_publish_job(job["id"], "failed", None, "draft missing")
            failed += 1
            retried += 1
            continue

        ok, _, err = _attempt_wechat_publish(job["id"], draft)
        retried += 1
        if ok:
            succeeded += 1
        else:
            failed += 1
            mark_retry_scheduled(job["id"], delay_minutes=delay_minutes, message=err)

    return RetryResult(scanned=scanned, retried=retried, succeeded=succeeded, failed=failed)
