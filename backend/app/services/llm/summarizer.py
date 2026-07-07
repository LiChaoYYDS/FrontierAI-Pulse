from app.services.llm.provider_factory import get_provider


async def summarize(content: str) -> str:
    """用AI生成60-120字的中文摘要，不复制原文。"""
    if not content or len(content.strip()) < 50:
        return content.strip()

    provider = get_provider()
    result = await provider.complete(
        prompt=f"请阅读以下内容，用自己的话概括核心要点，60-120字，不要复制原文：\n\n{content[:3000]}",
        system="你是技术资讯摘要助手。只输出摘要正文，不加标题、序号或解释。",
    )
    return result.content.strip()
