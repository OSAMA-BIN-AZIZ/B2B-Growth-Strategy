from app.models import DraftFromTopicRequest, MetricIn, TopicRequest
from app.services.formatter import markdown_to_wechat_html
from app.services.topic_engine import generate_topics
from app.services.writing_engine import generate_markdown, generate_meta, generate_outline
from app.storage import (
    get_draft,
    get_publish_job,
    get_publish_job_by_idempotency,
    init_db,
    insert_audit_log,
    insert_draft,
    insert_llm_log,
    insert_metric,
    insert_publish_job,
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


def test_topic_and_draft_flow() -> None:
    init_db()
    req = TopicRequest(
        target_customer="工厂老板",
        industry="机械制造",
        service="B2B独立站增长",
        article_goal="引导咨询",
        historical_reference=["网站有流量但无询盘"],
        use_openai=False,
    )
    topic = generate_topics(req)[0]
    draft_req = DraftFromTopicRequest(topic=topic, use_openai=False)

    outline = generate_outline(draft_req.topic)
    markdown = generate_markdown(draft_req.topic, outline)
    html = markdown_to_wechat_html(markdown)
    meta = generate_meta(draft_req.topic)

    draft_id = insert_draft(
        {
            "topic_title": draft_req.topic.title,
            "outline": outline,
            "markdown": markdown,
            "html": html,
            **meta,
        }
    )
    saved = get_draft(draft_id)

    assert saved is not None
    assert saved["topic_title"] == topic.title
    assert "<article" in saved["html"]
    assert saved["wechat_summary"]


def test_metrics_audit_llm_and_retry_queue() -> None:
    init_db()
    metrics = [
        MetricIn(
            topic_title="询盘提质SOP",
            pain_point="有流量但询盘质量差",
            target_customer="外贸负责人",
            industry="机械",
            growth_stage="有流量没询盘",
            views=1200,
            likes=42,
            shares=16,
            inquiries=7,
        ),
        MetricIn(
            topic_title="独立站转化诊断",
            pain_point="网站有访问但无转化",
            target_customer="外贸负责人",
            industry="机械",
            growth_stage="有流量没询盘",
            views=980,
            likes=30,
            shares=10,
            inquiries=6,
        ),
    ]
    for m in metrics:
        insert_metric(m.model_dump())

    summary = list_metric_summary()
    assert len(summary) >= 2
    recs = list_topic_recommendations(top_n=2)
    assert len(recs) == 2
    seg = list_segmented_topic_recommendations(top_n=2, target_customer="外贸负责人", industry="机械")
    assert len(seg) >= 1

    boost_map = topic_feedback_boost()
    assert "网站有访问但无转化" in boost_map

    audit_id = insert_audit_log({"draft_id": 1, "action": "reviewed", "actor": "alice", "note": "looks good"})
    logs = list_audit_logs(limit=5)
    assert logs[0]["id"] == audit_id

    llm_id = insert_llm_log({"model": "gpt-4.1-mini", "operation": "topic_generation", "latency_ms": 20, "success": True})
    llm_logs = list_llm_logs(limit=5)
    assert llm_logs[0]["id"] == llm_id

    job_id = insert_publish_job(
        {
            "draft_id": 1,
            "channel": "wechat_draft",
            "status": "failed",
            "message": "credential missing",
            "max_retries": 3,
            "idempotency_key": "k1",
        }
    )

    all_jobs = list_publish_jobs(limit=5)
    assert any(job["id"] == job_id for job in all_jobs)

    pending = list_retryable_publish_jobs(limit=5)
    assert any(job["id"] == job_id for job in pending)

    dup = get_publish_job_by_idempotency("wechat_draft", "k1")
    assert dup is not None
    assert dup["id"] == job_id

    mark_retry_scheduled(job_id, delay_minutes=1, message="retry later")
    job = get_publish_job(job_id)
    assert job is not None
    assert job["retry_count"] == 1

    update_publish_job(job_id, "failed", None, "still failed")
    job2 = get_publish_job(job_id)
    assert job2 is not None
    assert job2["status"] == "failed"
