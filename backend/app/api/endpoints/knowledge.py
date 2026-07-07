from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.models.article import Article
from app.models.knowledge_node import KnowledgeNode
from app.models.knowledge_edge import KnowledgeEdge
from app.schemas.article import ArticleResponse

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/nodes")
async def get_nodes(type: str | None = None, db: AsyncSession = Depends(get_db)):
    """
    获取知识图谱节点列表（技术概念）
    - type: 过滤节点类型（concept/model/framework/paper），不传则返回全部
    - 返回每个节点的 id、名称、类型、关联文章数
    """
    stmt = select(KnowledgeNode).order_by(KnowledgeNode.type, KnowledgeNode.name)
    if type:
        stmt = stmt.where(KnowledgeNode.type == type)
    nodes = (await db.execute(stmt)).scalars().all()
    return [{"id": n.id, "name": n.name, "type": n.type,
             "article_count": len(n.article_ids or [])} for n in nodes]


@router.get("/nodes/{node_id}/articles", response_model=list[ArticleResponse])
async def get_node_articles(node_id: int, db: AsyncSession = Depends(get_db)):
    """获取与指定概念节点关联的所有文章列表（按发布时间降序），用于概念浏览器右侧面板"""
    node = await db.get(KnowledgeNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")
    ids = node.article_ids or []
    if not ids:
        return []
    articles = (await db.execute(
        select(Article).where(Article.id.in_(ids)).order_by(Article.published_at.desc())
    )).scalars().all()
    return [ArticleResponse.model_validate(a) for a in articles]


@router.get("/graph")
async def get_graph(db: AsyncSession = Depends(get_db)):
    """
    获取完整知识图谱数据（ECharts 力导向图格式）
    - nodes: 节点列表，value=关联文章数（用于控制节点大小）
    - edges: 关系边列表，strength=共现强度（用于控制连线粗细）
    """
    nodes = (await db.execute(select(KnowledgeNode))).scalars().all()
    edges = (await db.execute(select(KnowledgeEdge))).scalars().all()
    return {
        "nodes": [{"id": n.id, "name": n.name, "type": n.type,
                   "value": len(n.article_ids or [])} for n in nodes],
        "edges": [{"source": e.from_node_id, "target": e.to_node_id,
                   "strength": e.strength} for e in edges],
    }


@router.post("/extract")
async def trigger_extract(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """
    手动触发知识实体提取（从已 AI 处理的文章中提取技术概念并建图）
    - limit: 每次最多处理的文章数，默认 50
    - 返回：processed（处理文章数）、nodes_added（新增节点数）
    """
    from app.services.knowledge.graph_updater import update_graph_batch
    return await update_graph_batch(db, limit)
