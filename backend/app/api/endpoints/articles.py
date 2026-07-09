import math

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.models.article import Article
from app.models.source import Source
from app.schemas.article import ArticleResponse, ArticlePage, ArticleUpdate

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.get("/list", response_model=ArticlePage)
@router.get("/feed", response_model=ArticlePage)
async def get_articles(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        tags: list[str] = Query([]),
        source_id: int | None = Query(None),
        is_read: bool | None = Query(None),
        is_favorite: bool | None = Query(None),
        is_liked: bool | None = Query(None),
        sort_by: str = Query("score", pattern="^(time|score)$"),
        source_type: str | None = Query(None, description="仅返回该来源类型（如 github）"),
        exclude_source_type: str | None = Query(None, description="排除指定来源类型（如 github）"),
        db: AsyncSession = Depends(get_db)
):
    """
    获取文章列表（分页+过滤+排序）
    - tags: 按标签过滤（传多个值表示"包含所有这些标签"）
    - source_id: 按来源过滤
    - is_read / is_favorite / is_liked: 按阅读/收藏/点赞状态过滤
    - sort_by: time=按发布时间降序，score=按兴趣匹配度降序
    - source_type: 仅返回指定 source_type（rss/arxiv/website/github）
    - exclude_source_type: 排除指定 source_type
    """
    order = Article.importance_score.desc() if sort_by == "score" else Article.published_at.desc()
    stmt = select(Article).order_by(order)
    count_stmt = select(func.count(Article.id))

    if tags:
        stmt = stmt.where(Article.tags.contains(tags))
        count_stmt = count_stmt.where(Article.tags.contains(tags))
    if source_id:
        stmt = stmt.where(Article.source_id == source_id)
        count_stmt = count_stmt.where(Article.source_id == source_id)
    if is_read is not None:
        stmt = stmt.where(Article.is_read == is_read)
        count_stmt = count_stmt.where(Article.is_read == is_read)
    if is_favorite is not None:
        stmt = stmt.where(Article.is_favorite == is_favorite)
        count_stmt = count_stmt.where(Article.is_favorite == is_favorite)
    if is_liked is not None:
        stmt = stmt.where(Article.is_liked == is_liked)
        count_stmt = count_stmt.where(Article.is_liked == is_liked)
    if source_type == 'github':
        github_ids = select(Source.id).where(Source.url.like('%github.com%')).scalar_subquery()
        stmt       = stmt.where(Article.source_id.in_(github_ids))
        count_stmt = count_stmt.where(Article.source_id.in_(github_ids))
    elif source_type:
        stmt       = stmt.where(Article.source_type == source_type)
        count_stmt = count_stmt.where(Article.source_type == source_type)

    if exclude_source_type == 'github':
        github_ids = select(Source.id).where(Source.url.like('%github.com%')).scalar_subquery()
        stmt       = stmt.where(Article.source_id.notin_(github_ids))
        count_stmt = count_stmt.where(Article.source_id.notin_(github_ids))
    elif exclude_source_type:
        stmt       = stmt.where(Article.source_type != exclude_source_type)
        count_stmt = count_stmt.where(Article.source_type != exclude_source_type)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    articles = (await db.execute(stmt)).scalars().all()

    return ArticlePage(
        total=total, page=page, page_size=page_size,
        items=[ArticleResponse.model_validate(a) for a in articles],
        total_pages=math.ceil(total / page_size) if total > 0 else 0
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    """获取单篇文章详情（含 AI 摘要、标签、洞察等所有字段）"""
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return ArticleResponse.model_validate(article)


@router.patch("/{article_id}", response_model=ArticleResponse)
async def update_article(article_id: int, body: ArticleUpdate, db: AsyncSession = Depends(get_db)):
    """
    更新文章状态或笔记（只更新传入的字段）
    - is_read: 标记已读/未读（首次标记已读时同步写入 read_at）
    - is_favorite: 收藏/取消收藏
    - is_liked: 点赞/取消点赞
    - notes: 保存个人笔记
    """
    from datetime import datetime, timezone
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(article, field, value)

    # 首次标记已读时写入 read_at；取消已读时清空 read_at
    if body.is_read is True and article.read_at is None:
        article.read_at = datetime.now(timezone.utc)
    elif body.is_read is False:
        article.read_at = None

    await db.commit()
    return ArticleResponse.model_validate(article)


@router.delete("/{article_id}", status_code=204)
async def delete_article(article_id: int, db: AsyncSession = Depends(get_db)):
    """删除指定文章（物理删除，不可恢复）"""
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    await db.delete(article)
    await db.commit()


@router.get("/{article_id}/insight")
async def get_insight(article_id: int, db: AsyncSession = Depends(get_db)):
    """获取文章的 AI 个人关联洞察及处理状态（pending/processing/done/failed）"""
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return {"insight": article.insight, "process_status": article.process_status}


@router.post("/{article_id}/process")
async def trigger_process(article_id: int, db: AsyncSession = Depends(get_db)):
    """手动触发单篇文章的 AI 处理（摘要→标签→评分→洞察），已处理的文章会跳过"""
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    from app.services.user_service import get_or_create_user
    user = await get_or_create_user(db)
    interests = user.preferences.get("interests", [])

    from app.services.llm.tasks import process_article
    await process_article(article_id, interests)

    # 刷新后检查实际处理结果，避免 tasks 内部吞异常导致前端收到误导性的"处理完成"
    await db.refresh(article)
    if article.process_status == "failed":
        raise HTTPException(status_code=500, detail="AI 处理失败，请检查 LLM 服务配置（模型名、API Key）")

    return {"message": "处理完成", "article_id": article_id}


@router.post("/batch-process")
async def batch_process(db: AsyncSession = Depends(get_db)):
    """批量处理所有 pending/failed 状态的文章（每次最多50篇），按用户兴趣评分"""
    stmt = select(Article.id).where(
        Article.process_status.in_(["pending", "failed", None])
    ).limit(50)
    result = await db.execute(stmt)
    ids = [row[0] for row in result.all()]

    if not ids:
        return {"message": "没有需要处理的文章", "count": 0}

    from app.services.user_service import get_or_create_user
    user = await get_or_create_user(db)
    interests = user.preferences.get("interests", [])

    from app.services.llm.tasks import batch_process as do_batch
    stats = await do_batch(ids, interests)
    return {"message": "批量处理完成", **stats}
