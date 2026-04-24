from __future__ import annotations

from app.models import TopicCard, TopicRequest

PAIN_OPTIONS = [
    "获客难，线索量不足",
    "有流量但询盘质量差",
    "网站有访问但无转化",
    "销售跟进效率低，成交周期长",
    "内容生产低效且缺乏转化导向",
]
INTENT_OPTIONS = ["学习型", "对比型", "找服务商型", "准备付费型"]
CTA_OPTIONS = [
    "回复【诊断】领取B2B网站转化检查清单",
    "添加顾问微信，获取一对一增长建议",
    "领取《外贸询盘提质SOP》模板",
    "预约30分钟增长策略诊断会",
]


def _score(index: int, req: TopicRequest) -> float:
    pain_strength = 80 - index * 2
    conversion_fit = 75 + (5 if "询盘" in req.article_goal else 0)
    keyword_value = 70 + (8 if "B2B" in req.service.upper() else 0)
    differentiation = 72 - index
    score = pain_strength * 0.3 + conversion_fit * 0.3 + keyword_value * 0.2 + differentiation * 0.2
    return round(min(99.0, score), 1)


def generate_topics(req: TopicRequest) -> list[TopicCard]:
    topics: list[TopicCard] = []
    for i in range(10):
        pain = PAIN_OPTIONS[i % len(PAIN_OPTIONS)]
        intent = INTENT_OPTIONS[i % len(INTENT_OPTIONS)]
        cta = CTA_OPTIONS[i % len(CTA_OPTIONS)]
        title = f"{req.target_customer}在{req.industry}里如何解决：{pain}？"
        subtitle = f"围绕{req.service}，从{req.growth_stage}到稳定询盘的实战路径"
        angle = [
            "先定义买家阶段与决策信号，避免内容泛流量",
            "拆解页面、案例、CTA三层转化结构",
            "给出7天可执行动作，形成可复盘闭环",
        ]
        topics.append(
            TopicCard(
                title=title,
                subtitle=subtitle,
                target_reader=req.target_customer,
                pain_point=pain,
                buyer_intent=intent,
                angle=angle,
                conversion_goal=req.article_goal,
                recommended_cta=cta,
                score=_score(i, req),
            )
        )
    return topics
