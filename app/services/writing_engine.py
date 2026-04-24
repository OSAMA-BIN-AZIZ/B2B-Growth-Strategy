from __future__ import annotations

from app.models import TopicCard


def generate_outline(topic: TopicCard) -> list[str]:
    return [
        f"开场：{topic.target_reader}最常见困境与机会窗口",
        f"问题拆解：为什么会出现“{topic.pain_point}”",
        "方法框架：用“需求-信任-转化”三层模型重建内容",
        "执行清单：7天内可落地动作与分工",
        f"结尾CTA：{topic.recommended_cta}",
    ]


def generate_markdown(topic: TopicCard, outline: list[str]) -> str:
    sections = "\n\n".join([f"## {part}\n\n围绕该部分输出可执行建议与业务示例。" for part in outline])
    return (
        f"# {topic.title}\n\n"
        f"> {topic.subtitle}\n\n"
        f"目标读者：{topic.target_reader}  \\n"
        f"核心痛点：{topic.pain_point}  \\n"
        f"转化目标：{topic.conversion_goal}\n\n"
        f"{sections}\n\n"
        f"---\n\n"
        f"**行动建议**：先完成一次内容漏斗体检，再按优先级迭代首屏与CTA。\n\n"
        f"**CTA**：{topic.recommended_cta}\n"
    )


def generate_meta(topic: TopicCard) -> dict:
    return {
        "wechat_title": topic.title,
        "wechat_summary": f"聚焦{topic.pain_point}，给出一套可执行的B2B增长内容方案。",
        "cover_copy": f"{topic.target_reader}必读：{topic.pain_point}",
    }
