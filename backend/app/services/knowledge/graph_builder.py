from collections import Counter
from itertools import combinations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_node import KnowledgeNode
from app.models.knowledge_edge import KnowledgeEdge


async def build_edges(db: AsyncSession) -> int:
    """基于共现关系（同一文章中出现的概念）构建或加强关系边。返回新增/更新边数。"""
    nodes = (await db.execute(select(KnowledgeNode))).scalars().all()
    if len(nodes) < 2:
        return 0

    # 按文章分组节点
    article_to_nodes: dict[int, list[int]] = {}
    for node in nodes:
        for aid in (node.article_ids or []):
            article_to_nodes.setdefault(aid, []).append(node.id)

    # 统计共现次数
    pair_counts: Counter = Counter()
    for nids in article_to_nodes.values():
        for a, b in combinations(sorted(nids), 2):
            pair_counts[(a, b)] += 1

    count = 0
    for (from_id, to_id), strength in pair_counts.items():
        result = await db.execute(
            select(KnowledgeEdge).where(
                KnowledgeEdge.from_node_id == from_id,
                KnowledgeEdge.to_node_id == to_id,
                KnowledgeEdge.relation_type == "co-occurs",
            )
        )
        edge = result.scalar_one_or_none()
        if edge:
            edge.strength = float(strength)
        else:
            db.add(KnowledgeEdge(
                from_node_id=from_id,
                to_node_id=to_id,
                relation_type="co-occurs",
                strength=float(strength),
            ))
            count += 1

    await db.commit()
    return count
