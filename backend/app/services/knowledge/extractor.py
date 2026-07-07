import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.article import Article
from app.services.llm.provider_factory import get_provider

# arXiv 分类代码正则（过滤用）
_ARXIV_CATEGORY = re.compile(r'^(cs|math|stat|eess|econ|q-bio|physics)\.[A-Z]{2}$')

# 预设类型关键词映射
_TYPE_KEYWORDS = {
    "model": ["gpt", "llama", "claude", "gemini", "bert", "t5", "mistral", "qwen", "deepseek",
              "stable diffusion", "whisper", "blip", "vit", "resnet", "transformer"],
    "framework": ["langchain", "llamaindex", "pytorch", "tensorflow", "jax", "huggingface",
                  "fastapi", "react", "vue", "vite", "docker", "kubernetes"],
    "concept": ["rag", "fine-tuning", "prompt", "embedding", "attention", "lora", "qlora",
                "inference", "quantization", "moe", "agent", "chain-of-thought", "reinforcement"],
    "paper": [],  # 通过 LLM 抽取结果中含 "paper" 关键词判断
}


def _classify(name: str) -> str:
    n = name.lower()
    for t, kws in _TYPE_KEYWORDS.items():
        if any(kw in n for kw in kws):
            return t
    return "concept"


async def extract_concepts(article: Article) -> list[dict]:
    """从文章中提取技术概念，返回 [{name, type}] 列表。"""
    text = f"{article.title}\n{(article.summary or article.content or '')[:1500]}"

    # 先用已有标签作为候选（过滤arXiv分类码）
    seed_tags = [
        t for t in (article.tags or [])
        if not _ARXIV_CATEGORY.match(t) and len(t) > 1
    ]

    try:
        provider = get_provider()
        result = await provider.complete(
            prompt=(
                f"从以下技术文章中提取3-8个实际技术概念（模型名/框架名/算法/技术方法），"
                f"不要提取arXiv分类代码（如cs.AI）、公司名或普通词汇。\n"
                f"已知标签：{', '.join(seed_tags)}\n"
                f"文章：{text}\n\n"
                "只输出概念名，英文逗号分隔，每个概念首字母大写，如：Transformer, RAG, LoRA"
            ),
            system="你是技术概念提取专家，只输出概念名列表，不加解释。",
        )
        raw = result.content.strip()
        names = [n.strip() for n in raw.split(",") if n.strip()]
    except Exception:
        names = seed_tags[:6]

    # 过滤arXiv码 + 去重
    seen = set()
    concepts = []
    for name in names:
        if _ARXIV_CATEGORY.match(name):
            continue
        key = name.lower()
        if key not in seen and 1 < len(name) < 80:
            seen.add(key)
            concepts.append({"name": name, "type": _classify(name)})

    return concepts
