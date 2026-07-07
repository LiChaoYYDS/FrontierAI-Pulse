"""
Embedding 服务：将文本转换为语义向量。

支持两种后端（通过 EMBEDDING_BACKEND 切换）：
  local — 使用本地 sentence-transformers（无需 API Key，首次运行自动下载模型）
  api   — 使用 OpenAI 兼容接口（OpenAI / 硅基流动 / Ollama 等）

本次优化：
  1. 新增 mode 参数（"query" / "passage"），支持 BGE 非对称检索指令前缀
     - mode="query"  : 加前缀 "为这个句子生成表示以用于检索相关文章："
     - mode="passage": 原文直接编码（存库文章、用户输入短语以外的场景）
  2. 新增维度校验：embed 完成后自动与 settings.EMBEDDING_DIM 对比，
     维度不符时立即抛出 RuntimeError，防止脏数据写入 Vector(N) 列
"""
import logging
from functools import lru_cache

from app.core.config import settings
from app.models.article import Article

logger = logging.getLogger("uvicorn")

_BATCH_SIZE = 32

# BGE 系列模型官方推荐的 Query 侧指令前缀
# 文档侧（passage）不加前缀，两侧不对称才能达到最优检索效果
_BGE_QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


def _build_embed_text(article: Article) -> str:
    """构建文章（passage 侧）送入 Embedding 的文本：标题 + 摘要/内容前500字。"""
    body = article.summary or (article.content[:500] if article.content else "")
    return f"{article.title}\n{body}".strip()


def _apply_query_prefix(texts: list[str], mode: str) -> list[str]:
    """
    根据 mode 决定是否在文本前添加 BGE Query 指令前缀。

    Args:
        texts: 原始文本列表
        mode : "query"   — 检索时的查询端，加指令前缀
               "passage" — 文章存库端，不加前缀（默认）

    Returns:
        处理后的文本列表（passage 侧原样返回，不修改原列表）
    """
    if mode == "query":
        prefixed = [f"{_BGE_QUERY_INSTRUCTION}{t}" for t in texts]
        logger.debug("[Embedder] mode=query，已添加 BGE 指令前缀，共 %d 条", len(texts))
        return prefixed
    return texts


def _validate_dimensions(vecs: list[list[float]], expected_dim: int) -> None:
    """
    校验返回向量的维度是否与配置一致。

    维度不符时抛出 RuntimeError，让调用方感知，避免把错误维度的向量
    写入固定维度的 Vector(N) 列导致 pgvector 报错或数据静默损坏。

    Args:
        vecs        : embed 完成后的向量列表
        expected_dim: settings.EMBEDDING_DIM 的值
    """
    if not vecs:
        return
    actual_dim = len(vecs[0])
    if actual_dim != expected_dim:
        raise RuntimeError(
            f"[Embedder] 向量维度不匹配！"
            f"期望 {expected_dim} 维（数据库 Vector({expected_dim})），"
            f"实际输出 {actual_dim} 维。\n"
            f"请检查 EMBEDDING_BACKEND / EMBEDDING_MODEL 与 EMBEDDING_DIM 的配置是否一致：\n"
            f"  local 默认模型 bge-small-zh-v1.5 → 512 维\n"
            f"  api   text-embedding-3-small     → 1536 维\n"
            f"切换后端时需同步修改 EMBEDDING_DIM 并迁移数据库列定义。"
        )
    logger.debug("[Embedder] 维度校验通过：%d 维", actual_dim)


# ── 本地后端（sentence-transformers）─────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_local_model():
    """单例本地模型（懒加载，已缓存则秒启动）。"""
    import os
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")  # 国内镜像
    from sentence_transformers import SentenceTransformer
    logger.info("[Embedder] 加载本地模型 %s …", settings.EMBEDDING_LOCAL_MODEL)
    model = SentenceTransformer(settings.EMBEDDING_LOCAL_MODEL)
    logger.info(
        "[Embedder] 本地模型加载完成，向量维度 %d",
        model.get_sentence_embedding_dimension(),
    )
    return model


async def _embed_local(texts: list[str]) -> list[list[float]]:
    """本地推理（CPU），用 asyncio.to_thread 隔离阻塞调用，避免卡死事件循环。"""
    import asyncio

    def _run():
        model = _get_local_model()
        # normalize_embeddings=True：L2 归一化，后续余弦相似度可用点积代替
        vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [v.tolist() for v in vecs]

    return await asyncio.to_thread(_run)


# ── API 后端（OpenAI 兼容）────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_api_client():
    """单例 OpenAI 兼容客户端。"""
    from openai import AsyncOpenAI
    api_key = settings.EMBEDDING_API_KEY or settings.OPENAI_API_KEY
    if not api_key:
        raise RuntimeError(
            "未配置 EMBEDDING_API_KEY，请切换为 EMBEDDING_BACKEND=local 或填写 API Key"
        )
    logger.info("[Embedder] 使用 API 后端，模型 %s", settings.EMBEDDING_MODEL)
    return AsyncOpenAI(api_key=api_key, base_url=settings.EMBEDDING_BASE_URL)


async def _embed_api(texts: list[str]) -> list[list[float]]:
    """调用 OpenAI 兼容 Embedding API。"""
    client = _get_api_client()
    resp = await client.embeddings.create(model=settings.EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]


# ── 公开接口 ──────────────────────────────────────────────────────────────────

async def embed_text(text: str, mode: str = "passage") -> list[float]:
    """
    单条文本 → 向量。

    Args:
        text: 待编码文本
        mode: "query" 加 BGE 检索指令前缀；"passage" 原文直接编码（默认）
    """
    results = await embed_texts([text], mode=mode)
    return results[0]


async def embed_texts(texts: list[str], mode: str = "passage") -> list[list[float]]:
    """
    批量文本 → 向量列表（自动选择后端，含维度校验）。

    Args:
        texts: 待编码文本列表
        mode : "query" | "passage"，控制是否添加 BGE 指令前缀
    """
    # 根据 mode 决定是否加前缀（只影响编码，不改原始列表）
    processed_texts = _apply_query_prefix(texts, mode)

    # 选择后端
    if settings.EMBEDDING_BACKEND == "local":
        vecs = await _embed_local(processed_texts)
    else:
        vecs = await _embed_api(processed_texts)

    # 维度校验：防止 backend 切换后维度不符导致写库报错
    _validate_dimensions(vecs, settings.EMBEDDING_DIM)

    return vecs


async def embed_articles(articles: list[Article]) -> list[list[float]]:
    """
    批量为文章生成 Embedding（passage 侧，不加 query 前缀）。
    自动按 BATCH_SIZE 分批，避免内存/请求过大。
    """
    if not articles:
        return []

    texts = [_build_embed_text(a) for a in articles]
    vectors: list[list[float]] = []

    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i: i + _BATCH_SIZE]
        # 文章存库侧用 passage 模式（默认）
        batch_vecs = await embed_texts(batch, mode="passage")
        vectors.extend(batch_vecs)
        logger.info(
            "[Embedder] 进度 %d/%d 篇",
            min(i + _BATCH_SIZE, len(texts)), len(texts),
        )

    return vectors
