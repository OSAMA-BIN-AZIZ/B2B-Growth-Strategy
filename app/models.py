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
    use_openai: bool = True
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
    source: Literal["rule", "openai"]


class DraftFromTopicRequest(BaseModel):
    topic: TopicCard
    use_openai: bool = True
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


class MetricIn(BaseModel):
    article_id: int | None = None
    topic_title: str
    pain_point: str
    target_customer: str | None = None
    industry: str | None = None
    growth_stage: str | None = None
    views: int = 0
    likes: int = 0
    shares: int = 0
    inquiries: int = 0


class MetricSummary(BaseModel):
    pain_point: str
    records: int
    avg_views: float
    avg_likes: float
    avg_shares: float
    avg_inquiries: float
    feedback_boost: float


class TopicRecommendation(BaseModel):
    topic_title: str
    pain_point: str
    records: int
    avg_views: float
    avg_shares: float
    avg_inquiries: float
    suggestion_score: float


class PublishDraftRequest(BaseModel):
    draft_id: int
    idempotency_key: str | None = None
    max_retries: int = 3


class PublishJobOut(BaseModel):
    id: int
    draft_id: int
    channel: str
    idempotency_key: str | None = None
    status: str
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: str | None = None
    external_id: str | None = None
    message: str | None = None
    created_at: datetime


class PublishAuditIn(BaseModel):
    draft_id: int
    action: Literal["reviewed", "approved", "rejected", "published"]
    actor: str
    note: str | None = None


class AuditLogOut(BaseModel):
    id: int
    draft_id: int
    action: str
    actor: str
    note: str | None = None
    created_at: datetime


class LLMLogOut(BaseModel):
    id: int
    model: str
    operation: str
    latency_ms: int
    success: bool
    error: str | None = None
    created_at: datetime


class RetryResult(BaseModel):
    scanned: int
    retried: int
    succeeded: int
    failed: int
