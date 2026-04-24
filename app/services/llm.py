from __future__ import annotations

import json
from pathlib import Path
from urllib import request

from app.config import settings
from app.models import TopicBatchResponse, TopicCard, TopicRequest

OPENAI_URL = "https://api.openai.com/v1/responses"


def _call_openai(prompt: str) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    payload = {
        "model": settings.openai_model,
        "input": prompt,
        "text": {"format": {"type": "text"}},
    }
    req = request.Request(
        OPENAI_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.openai_api_key}",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if "output_text" in data:
        return data["output_text"]

    # minimal fallback parser for nested responses format
    text_parts: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                text_parts.append(content.get("text", ""))
    return "\n".join(text_parts).strip()


def _load_prompt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def generate_topics_via_openai(req: TopicRequest) -> TopicBatchResponse:
    tpl = _load_prompt("prompts/topic_generation.txt")
    prompt = (
        f"{tpl}\n\n"
        f"目标客户: {req.target_customer}\n"
        f"行业: {req.industry}\n"
        f"服务: {req.service}\n"
        f"文章目标: {req.article_goal}\n"
        f"增长阶段: {req.growth_stage}\n"
        f"历史参考: {'; '.join(req.historical_reference)}\n\n"
        "请只返回 JSON，格式为: {\"topics\": [{...TopicCard字段...}]}."
    )
    raw = _call_openai(prompt)
    parsed = json.loads(raw)
    topics = [TopicCard(**item) for item in parsed["topics"]][:10]
    return TopicBatchResponse(topics=topics, source="openai")


def generate_markdown_via_openai(topic: TopicCard) -> str:
    tpl = _load_prompt("prompts/article_writing.txt")
    prompt = (
        f"{tpl}\n\n"
        f"选题: {topic.title}\n"
        f"副标题: {topic.subtitle}\n"
        f"目标读者: {topic.target_reader}\n"
        f"核心痛点: {topic.pain_point}\n"
        f"转化目标: {topic.conversion_goal}\n"
        f"CTA: {topic.recommended_cta}\n"
    )
    return _call_openai(prompt)
