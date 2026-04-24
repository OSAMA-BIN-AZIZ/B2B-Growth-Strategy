from app.models import DraftFromTopicRequest, MetricIn, TopicRequest
from app.services.formatter import markdown_to_wechat_html
from app.services.topic_engine import generate_topics
from app.services.writing_engine import generate_markdown, generate_meta, generate_outline
from app.storage import (
    get_draft,
    get_publish_job,
    init_db,
    insert_draft,
    insert_metric,
    insert_publish_job,
    list_metric_summary,
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


def test_metrics_feedback_and_publish_job() -> None:
    init_db()
    metric = MetricIn(
        topic_title="测试选题",
        pain_point="网站有访问但无转化",
        views=1000,
        likes=50,
        shares=20,
        inquiries=8,
    )
    insert_metric(metric.model_dump())
    summary = list_metric_summary()
    assert len(summary) >= 1
    assert summary[0]["feedback_boost"] > 0

    boost_map = topic_feedback_boost()
    assert "网站有访问但无转化" in boost_map

    job_id = insert_publish_job(
        {
            "draft_id": 1,
            "channel": "wechat_draft",
            "status": "pending",
            "message": "queued",
        }
    )
    update_publish_job(job_id, "failed", None, "credential missing")
    job = get_publish_job(job_id)
    assert job is not None
    assert job["status"] == "failed"
