from app.services.llm.provider_factory import get_provider

# 预定义的技术领域标签集合，限制 LLM 输出范围
_PRESET_TAGS = (
    "LLM,RAG,AI Agent,多模态,计算机视觉,强化学习,微调,向量数据库,"
    "前端,后端,云原生,DevOps,数据库,安全,区块链,量化金融,"
    "开源项目,论文,工具,教程,行业动态"
)


async def extract_tags(content: str, title: str = "") -> list[str]:
    """从文章内容中提取3-6个技术标签，返回列表。"""
    if not content and not title:
        return []

    text = f"标题：{title}\n\n{content[:2000]}" if title else content[:2000]
    provider = get_provider()
    result = await provider.complete(
        prompt=(
            f"从以下文章中提取3-6个技术标签，只从候选标签中选择，用英文逗号分隔，不要其他文字。\n"
            f"候选标签：{_PRESET_TAGS}\n\n"
            f"文章：{text}"
        ),
        system="你是技术标签提取助手。只输出标签，用英文逗号分隔，不加解释。",
    )
    raw = result.content.strip()
    return [t.strip() for t in raw.split(",") if t.strip()][:6]
