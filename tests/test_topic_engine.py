from app.models import TopicRequest
from app.services.topic_engine import generate_topics


def test_generate_topics_returns_10_cards() -> None:
    req = TopicRequest(
        target_customer="外贸负责人",
        industry="工业设备",
        service="B2B内容增长",
        article_goal="提升询盘转化",
    )
    topics = generate_topics(req)
    assert len(topics) == 10
    assert topics[0].score >= topics[-1].score
