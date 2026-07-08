"""
RAG 后台任务：批量 Embedding 和全库重评分

将后台任务状态和执行逻辑从接口层剥离，由服务层统一管理。
接口层仅负责触发任务和查询状态，不持有业务逻辑。
"""
import logging

from app.db.config import async_session
from app.models.article import Article
from app.services.llm.scorer import rescore_all_articles
from app.services.rag.embedder import embed_articles
from sqlalchemy import select

logger = logging.getLogger("uvicorn")

# ── 任务状态（进程级，重启后清空） ─────────────────────────────────────────────
embed_job: dict = {"running": False, "done": 0, "total": 0, "error": ""}
rescore_job: dict = {"running": False, "updated": 0, "error": ""}


# ── 批量 Embedding ─────────────────────────────────────────────────────────────

async def run_embed_job() -> None:
    """
    后台任务：为所有 embedding=NULL 的文章批量生成向量并写回数据库。
    通过 FastAPI BackgroundTasks 调度，接口层调用此函数后立即返回。
    """
    embed_job.update({"running": True, "done": 0, "error": ""})
    try:
        async with async_session() as db:
            result = await db.execute(
                select(Article).where(Article.embedding.is_(None))
            )
            articles = result.scalars().all()
            embed_job["total"] = len(articles)

            if not articles:
                logger.info("[Embedder] 所有文章已有向量，无需处理")
                return

            logger.info("[Embedder] 开始批量生成向量，共 %d 篇", len(articles))
            vectors = await embed_articles(articles)
            assert len(articles) == len(vectors), (
                f"长度不匹配: articles={len(articles)}, vectors={len(vectors)}"
            )
            for article, vec in zip(articles, vectors):
                article.embedding = vec
                embed_job["done"] += 1

            await db.commit()
            logger.info("[Embedder] 向量写入完成，共 %d 篇", len(articles))

    except Exception as e:
        embed_job["error"] = str(e)
        logger.exception("[Embedder] 批量生成向量失败: %s", e)
    finally:
        embed_job["running"] = False


# ── 全库重评分 ─────────────────────────────────────────────────────────────────

async def run_rescore_job(interests: list[str]) -> None:
    """
    后台任务：基于用户兴趣质心，用一条 SQL UPDATE 更新全库已向量化文章的评分。
    不把 embedding 拉进内存，由 pgvector 在数据库侧完成向量运算。
    """
    rescore_job.update({"running": True, "updated": 0, "error": ""})
    try:
        async with async_session() as db:
            updated = await rescore_all_articles(db, interests)
            rescore_job["updated"] = updated
            logger.info("[RescoreJob] 完成，共更新 %d 篇文章评分", updated)
    except Exception as e:
        rescore_job["error"] = str(e)
        logger.exception("[RescoreJob] 重评分失败: %s", e)
    finally:
        rescore_job["running"] = False
