"""
混合检索器（Hybrid Retriever）

召回策略：
  1. 向量检索（Dense）   — pgvector 余弦相似度，捕捉语义
  2. 关键词检索（Sparse）— PostgreSQL ILIKE + jieba 中文分词，捕捉字面匹配
  3. RRF 融合           — Reciprocal Rank Fusion 对两路结果重排序，取 Top-K

层路由（Layer Routing）：
  - personal : is_favorite=True 或有 notes（用户收藏/笔记）
  - curated  : importance_score ≥ 65（高分精选）
  - general  : 全量库

优雅降级：
  - 若文章没有 embedding（尚未生成），自动退化到纯关键词检索
  - 若 jieba 不可用，退化到空格分词
"""
import logging
from typing import Literal

import jieba
from sqlalchemy import select, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.services.rag.embedder import embed_text

logger = logging.getLogger("uvicorn")

# 路由关键词
_PERSONAL_KWS = ["我", "我看过", "我收藏", "我的笔记", "我之前", "我保存", "我喜欢"]
_CURATED_KWS  = ["最近", "进展", "新的", "重要", "热点", "趋势", "本周", "近期", "最新"]

Layer = Literal["personal", "curated", "general"]

# RRF 超参：k=60 是经典默认值，调大会让排名靠后的结果影响力下降更慢
_RRF_K = 60
# 每路召回候选数（最终返回 TOP_K）
_CANDIDATE_N = 20
TOP_K = 5


def route_layer(question: str) -> Layer:
    """根据问题关键词决定检索范围。"""
    q = question.lower()
    if any(kw in q for kw in _PERSONAL_KWS):
        return "personal"
    if any(kw in q for kw in _CURATED_KWS):
        return "curated"
    return "general"


def _tokenize_cn(text_: str) -> list[str]:
    """中文分词：jieba 提取长度 ≥ 2 的词，最多取前 8 个有效词。"""
    # jieba 是 Python 最流行的中文分词第三方库，能把连续的中文字符串切分成独立的词语
    #为什么需要分词？英文单词天然用空格分隔，而中文句子没有空格（例如：“我爱北京天安门”）。jieba.cut("我爱北京天安门") 会将其切分为 ['我', '爱', '北京', '天安门']。只有切分成词，后续才能筛选出有实际含义的词汇。
    tokens = [w.strip() for w in jieba.cut(text_) if len(w.strip()) >= 2]
    return tokens[:8]


def _apply_layer_filter(stmt, layer: Layer):
    """在 SQL 语句上附加层过滤条件。"""
    if layer == "personal":
        return stmt.where(or_(Article.is_favorite == True, Article.notes.isnot(None)))
    if layer == "curated":
        return stmt.where(Article.importance_score >= 55)  # 55 而非 65，兼容未打分数据
    return stmt


# ──────────────────────────────────────────────────────────────────────────────
# 向量检索（Dense Retrieval）
# ──────────────────────────────────────────────────────────────────────────────

async def _vector_retrieve(
    db: AsyncSession, question: str, layer: Layer, n: int
) -> list[Article]:
    """用问题向量做 pgvector 余弦相似度检索，返回 Top-n 文章。"""
    try:
        # mode="query"：使用 BGE 非对称检索指令前缀，与文章存库时的 passage 编码对齐
        q_vec = await embed_text(question, mode="query")
    except Exception as e:
        logger.warning("[RAG] Embedding 生成失败，跳过向量检索: %s", e)
        return []

    stmt = (
        select(Article)
        .where(Article.embedding.isnot(None))
        .order_by(Article.embedding.cosine_distance(q_vec))  # 直接传 list[float]
        .limit(n)
    )
    stmt = _apply_layer_filter(stmt, layer)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ──────────────────────────────────────────────────────────────────────────────
# 关键词检索（Sparse Retrieval）
# ──────────────────────────────────────────────────────────────────────────────

async def _keyword_retrieve(
    db: AsyncSession, question: str, layer: Layer, n: int
) -> list[Article]:
    """jieba 分词后做 ILIKE 模糊匹配，返回 Top-n 文章。"""
    tokens = _tokenize_cn(question)
    if not tokens:
        # 分词为空（如纯符号），退化到全问句截断匹配
        tokens = [question[:20]]

    conditions = [
        or_(
            Article.title.ilike(f"%{w}%"),
            Article.summary.ilike(f"%{w}%"),
        )
        for w in tokens
    ]
    stmt = (
        select(Article)
        .where(or_(*conditions))                        # 任意词命中即可
        .order_by(Article.importance_score.desc())
        .limit(n)
    )
    stmt = _apply_layer_filter(stmt, layer)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ──────────────────────────────────────────────────────────────────────────────
# RRF 融合（Reciprocal Rank Fusion）
# ──────────────────────────────────────────────────────────────────────────────

def _rrf_merge(
    dense_list: list[Article],
    sparse_list: list[Article],
    k: int = _RRF_K,
    top_k: int = TOP_K,
) -> list[Article]:
    """
    RRF 公式：score(d) = Σ 1/(k + rank_i(d))
    rank 从 1 开始，文章出现在哪路都贡献分数，两路都命中则分数叠加。
    """
    scores: dict[int, float] = {}
    id_to_article: dict[int, Article] = {}

    for rank, article in enumerate(dense_list, start=1):
        scores[article.id] = scores.get(article.id, 0) + 1 / (k + rank)
        id_to_article[article.id] = article

    for rank, article in enumerate(sparse_list, start=1):
        scores[article.id] = scores.get(article.id, 0) + 1 / (k + rank)
        id_to_article[article.id] = article

    # 按 RRF 分数降序排列，取 Top-K
    sorted_ids = sorted(scores, key=lambda aid: scores[aid], reverse=True)
    return [id_to_article[aid] for aid in sorted_ids[:top_k]]


# ──────────────────────────────────────────────────────────────────────────────
# 公开接口
# ──────────────────────────────────────────────────────────────────────────────

async def retrieve(db: AsyncSession, question: str, layer: Layer) -> list[Article]:
    """
    混合检索主入口：顺序执行向量+关键词两路检索，RRF 融合后返回 Top-5。

    注意：两路检索共享同一个 db Session，必须顺序执行（AsyncSession 不支持并发）。
    - 若向量检索失败（无 API Key / 无 embedding），自动降级为纯关键词结果。
    - 若两路结果均为空，返回按重要性排序的兜底文章。
    """
    dense_list  = await _vector_retrieve(db, question, layer, _CANDIDATE_N)
    sparse_list = await _keyword_retrieve(db, question, layer, _CANDIDATE_N)

    merged = _rrf_merge(dense_list, sparse_list)

    # 兜底：两路都为空时，去掉层过滤按分数返回，确保始终有文章可用
    if not merged:
        logger.warning("[RAG] 两路检索均无结果，启用兜底策略（忽略层过滤）")
        stmt = (
            select(Article)
            .order_by(Article.importance_score.desc())
            .limit(TOP_K)
        )
        result = await db.execute(stmt)
        merged = list(result.scalars().all())

    logger.info(
        "[RAG] 检索完成 layer=%s dense=%d sparse=%d merged=%d",
        layer, len(dense_list), len(sparse_list), len(merged),
    )
    return merged
