from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.compat import BaseModel, Field


class ArticleIn(BaseModel):
    title: str
    subtitle: str | None = None
    body: str
    published_at: datetime | None = None
    views: int = 0
    likes: int = 0
    shares: int = 0
    lead_effect: str | None = None
    target_customer: str
    topic: str
    pain_point: str
    product_relation: str | None = None
    has_inquiry: bool = False


class ArticleOut(ArticleIn):
    id: int
    created_at: datetime


class TopicRequest(BaseModel):
    target_customer: str
    industry: str
    service: str
    article_goal: str
    growth_stage: str = "有流量没询盘"
    historical_reference: list[str] = Field(default_factory=list)


class TopicCard(BaseModel):
    title: str
    subtitle: str
    target_reader: str
    pain_point: str
    buyer_intent: Literal["学习型", "对比型", "找服务商型", "准备付费型"]
    angle: list[str]
    conversion_goal: str
    recommended_cta: str
    score: float


class TopicBatchResponse(BaseModel):
    topics: list[TopicCard]


class DraftFromTopicRequest(BaseModel):
    topic: TopicCard
    style_template: Literal[
        "professional_consulting",
        "boss_decision",
        "case_breakdown",
        "checklist_tool",
        "industry_report",
    ] = "professional_consulting"


class DraftOut(BaseModel):
    id: int
    topic_title: str
    outline: list[str]
    markdown: str
    html: str
    wechat_title: str
    wechat_summary: str
    cover_copy: str
    created_at: datetime
