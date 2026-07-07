"""
语义相似度评分模块

本次优化：
  1. 兴趣短语编码改用 mode="query"，与文章 passage 向量做非对称匹配，提升对齐效果
  2. 新增 compute_interest_centroid()：多个兴趣向量取均值归一化，得到统一方向向量
  3. 新增 rescore_all_articles()：一条 SQL UPDATE 批量更新全库评分，避免把 embedding
     全量拉进 Python 内存，性能从 O(N×K) Python 循环降为单次 pgvector 运算
"""
import logging

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.embedder import embed_texts

logger = logging.getLogger("uvicorn")

# ── 进程内兴趣向量缓存 ──────────────────────────────────────────────────────────
# key: 兴趣短语原文；value: 512 维 L2 归一化向量
# 重启后失效，轻量够用；需跨进程持久化可改为 Redis
_interest_vec_cache: dict[str, list[float]] = {}


async def _get_interest_vectors(interests: list[str]) -> list[list[float]]:
    """
    批量获取用户兴趣向量，命中缓存直接返回，未缓存的调 embedder 补齐。

    使用 mode="query" 让 BGE 模型对短语加指令前缀，
    与文章存库时的 passage 编码形成非对称对，语义空间对齐更准确。
    """
    uncached = [phrase for phrase in interests if phrase not in _interest_vec_cache]

    if uncached:
        logger.info("[Scorer] 生成 %d 个兴趣向量（未命中缓存）: %s", len(uncached), uncached)
        try:
            # mode="query"：BGE 非对称指令前缀，与 passage 侧对齐
            vecs = await embed_texts(uncached, mode="query")
            for phrase, vec in zip(uncached, vecs):
                _interest_vec_cache[phrase] = vec
            logger.info("[Scorer] 缓存更新，当前共 %d 条兴趣向量", len(_interest_vec_cache))
        except Exception as e:
            logger.warning("[Scorer] 兴趣向量生成失败，将使用兜底评分: %s", e)
            return []

    return [_interest_vec_cache[phrase] for phrase in interests]


async def compute_interest_centroid(interests: list[str]) -> list[float] | None:
    """
    将多个兴趣向量合并为单一"质心"向量。

    算法：各向量取算术均值，再 L2 归一化，使结果向量仍可直接做点积相似度。
    用途：批量重评分时只需一个质心向量，无需逐条与 K 个兴趣向量比较。

    Returns:
        归一化后的质心向量；兴趣为空或 embed 失败时返回 None。
    """
    if not interests:
        return None

    interest_vecs = await _get_interest_vectors(interests)
    if not interest_vecs:
        return None

    arr = np.array(interest_vecs, dtype=np.float32)   # shape: (K, 512)
    #计算算数平均，即质心向量
    centroid = arr.mean(axis=0)                        # shape: (512,)
    #计算质心向量的 L2 范数（即长度）
    norm = np.linalg.norm(centroid)
    if norm < 1e-9:
        logger.warning("[Scorer] 质心向量接近零向量，无法归一化")
        return None
    #centroid_normalized = [0.8/0.9262, 0.4667/0.9262] ≈ [0.8638, 0.5039]
    centroid = centroid / norm                         # L2 归一化
    logger.info("[Scorer] 质心计算完成（%d 个兴趣融合）", len(interests))
    return centroid.tolist()


async def calculate_score(
    article_embedding: list[float] | None,
    user_interests: list[str],
) -> int:
    """
    基于语义相似度计算单篇文章与用户兴趣的匹配分数。

    用于 process_article()逐篇处理时：取所有兴趣向量中最大点积相似度打分。
    批量重评分（全库）请用 rescore_all_articles()，性能更优。

    Returns:
        整数分数 [0, 100]；无 embedding 或无兴趣时返回确定性兜底值 50。
    """
    if not article_embedding:
        logger.debug("[Scorer] 文章无 embedding，返回兜底分 50")
        return 50

    if not user_interests:
        logger.debug("[Scorer] 用户无兴趣配置，返回兜底分 50")
        return 50

    interest_vecs = await _get_interest_vectors(user_interests)
    if not interest_vecs:
        # embedder 失败时走兜底
        return 50

    article_vec = np.array(article_embedding, dtype=np.float32)
    # 两端均已 L2 归一化，点积 == 余弦相似度
    similarities = [
        float(np.dot(article_vec, np.array(iv, dtype=np.float32)))
        for iv in interest_vecs
    ]
    max_sim = max(similarities)

    # 余弦相似度 [-1, 1] → 分数 [0, 100]
    score = round((max_sim + 1) / 2 * 100)
    score = max(0, min(100, score))

    logger.debug(
        "[Scorer] 单篇评分完成 max_sim=%.4f score=%d（兴趣数=%d）",
        max_sim, score, len(user_interests),
    )
    return score


async def rescore_all_articles(
    db: AsyncSession,
    interests: list[str],
) -> int:
    """
    基于用户兴趣质心，一条 SQL UPDATE 批量更新全库已向量化文章的评分。

    性能对比（1 万篇 × 10 个兴趣）：
      旧方案（Python 循环）: 加载 ~20MB embedding 进内存，10 万次点积，数十秒
      本方案（SQL UPDATE） : embedding 不离开数据库，pgvector 索引加速，秒级完成

    pgvector <=> 是余弦距离（越小越相似），转换公式：
      score = ROUND((1 - cosine_distance) * 100)
      即相似度为 1.0 → 100 分，相似度为 0.0 → 50 分，相似度为 -1.0 → 0 分

    Returns:
        实际更新的文章行数；兴趣为空或质心计算失败时返回 0。
    """
    centroid = await compute_interest_centroid(interests)
    if centroid is None:
        logger.warning("[Scorer] 质心计算失败，跳过全库重评分")
        return 0

    # pgvector 接受 Python list[float] 格式，SQLAlchemy text() 绑定参数传递
    """
    (embedding <=> CAST(:vec AS vector))：这是pgvector扩展的余弦距离运算符，CAST是类型转换函数，将vec转为向量vector
    ROUND((1.0-...)*100)：用1.0减去余弦距离，得到的就是余弦相似度（范围[-1,1]），再线性放大到[-100,100]
    GREATEST(0, LEAST(100,...))类似于max(0,min(100,...))
    """
    result = await db.execute(
        text("""
            UPDATE articles
            SET importance_score = GREATEST(0, LEAST(100,
                ROUND((1.0 - (embedding <=> CAST(:vec AS vector))) * 100)
            ))
            WHERE embedding IS NOT NULL
        """),
        {"vec": str(centroid)},
    )
    await db.commit()

    updated = result.rowcount
    logger.info("[Scorer] 全库重评分完成，共更新 %d 篇文章", updated)
    return updated
