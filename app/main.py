from __future__ import annotations

from app.compat import FastAPI, HTTPException

from app.models import (
    ArticleIn,
    ArticleOut,
    DraftFromTopicRequest,
    DraftOut,
    TopicBatchResponse,
    TopicRequest,
)
from app.services.formatter import markdown_to_wechat_html
from app.services.topic_engine import generate_topics
from app.services.writing_engine import generate_markdown, generate_meta, generate_outline
from app.storage import get_draft, init_db, insert_article, insert_draft, list_articles

app = FastAPI(title="B2B 内容增长操作系统 MVP", version="0.1.0")


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
    return TopicBatchResponse(topics=generate_topics(req))


@app.post("/api/drafts/from-topic", response_model=DraftOut)
def draft_from_topic(req: DraftFromTopicRequest) -> DraftOut:
    outline = generate_outline(req.topic)
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
