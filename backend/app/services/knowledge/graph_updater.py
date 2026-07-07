from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.knowledge_node import KnowledgeNode
from app.services.knowledge.extractor import extract_concepts
from app.services.knowledge.graph_builder import build_edges


def _to_int_list(val) -> list[int]:
    """兼容 Python list 和 PostgreSQL 数组字符串 {1,2,3} 两种格式。"""
    if not val:
        return []
    if isinstance(val, str):
        val = val.strip('{}')
        return [int(x.strip('"').strip()) for x in val.split(',') if x.strip()] if val else []
    return [int(x) for x in val]


async def update_graph_for_article(db: AsyncSession, article_id: int) -> int:
    """为单篇文章提取概念并更新图谱，返回新增节点数。"""
    article = await db.get(Article, article_id)
    if not article:
        return 0

    concepts = await extract_concepts(article)
    added = 0

    for concept in concepts:
        result = await db.execute(
            select(KnowledgeNode).where(KnowledgeNode.name == concept["name"])
        )
        node = result.scalar_one_or_none()

        if node:
            # 追加文章 ID（去重）
            ids = list(set(_to_int_list(node.article_ids) + [article_id]))
            node.article_ids = ids
        else:
            db.add(KnowledgeNode(
                name=concept["name"],
                type=concept["type"],
                article_ids=[article_id],
            ))
            added += 1

    await db.commit()
    await build_edges(db)
    return added


async def update_graph_batch(db: AsyncSession, limit: int = 100) -> dict:
    """批量更新图谱：处理有 summary 但还没映射到图谱的文章。"""
    # 取已AI处理的文章
    from app.models.article import Article
    stmt = select(Article).where(Article.process_status == "done").limit(limit)
    articles = (await db.execute(stmt)).scalars().all()

    total_added = 0
    for article in articles:
        total_added += await update_graph_for_article(db, article.id)

    return {"processed": len(articles), "nodes_added": total_added}
