from app.models import DraftFromTopicRequest, TopicRequest
from app.services.formatter import markdown_to_wechat_html
from app.services.topic_engine import generate_topics
from app.services.writing_engine import generate_markdown, generate_meta, generate_outline
from app.storage import get_draft, init_db, insert_draft


def test_topic_and_draft_flow() -> None:
    init_db()
    req = TopicRequest(
        target_customer="工厂老板",
        industry="机械制造",
        service="B2B独立站增长",
        article_goal="引导咨询",
        historical_reference=["网站有流量但无询盘"],
    )
    topic = generate_topics(req)[0]
    draft_req = DraftFromTopicRequest(topic=topic)

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
