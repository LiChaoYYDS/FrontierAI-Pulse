from app.services.llm.provider_factory import get_provider


async def generate_insight(
    title: str,
    summary: str,
    tags: list[str],
    user_interests: list[str],
) -> str:
    """生成个人关联洞察：解释这篇文章和用户技术方向的具体关联。"""
    if not user_interests:
        return ""

    interests_str = "、".join(user_interests[:5])
    tags_str = "、".join(tags) if tags else "未知"

    provider = get_provider()
    result = await provider.complete(
        prompt=(
            f"文章：《{title}》\n"
            f"摘要：{summary}\n"
            f"标签：{tags_str}\n"
            f"用户兴趣：{interests_str}\n\n"
            "请用一段话说明这篇文章与用户技术兴趣的关联，以及对他有什么实际价值。"
        ),
        system="你是个人学习助手。直接输出洞察内容，不加标题，语气亲切具体。",
    )
    return result.content.strip()
