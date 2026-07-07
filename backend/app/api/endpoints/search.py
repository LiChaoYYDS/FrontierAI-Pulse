import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.models.article import Article
from app.schemas.article import ArticleResponse, ArticlePage

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/", response_model=ArticlePage)
async def search_articles(
        q: str = Query("", description="搜索关键词"),
        tags: list[str] = Query([]),
        source_id: int | None = Query(None),
        date_from: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
        date_to: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        db: AsyncSession = Depends(get_db)
):
    """
    全文搜索文章（分页+多维过滤）
    - q: 在标题、摘要、正文中做不区分大小写的模糊搜索（ILIKE）
    - tags: 按标签过滤（必须包含所有指定标签）
    - source_id: 按来源过滤
    - date_from / date_to: 按发布日期范围过滤（YYYY-MM-DD）
    """
    stmt = select(Article).order_by(Article.published_at.desc())
    count_stmt = select(func.count(Article.id))

    if q:
        like = f"%{q}%"
        condition = or_(
            Article.title.ilike(like),
            Article.summary.ilike(like),
            Article.content.ilike(like),
        )
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    if tags:
        stmt = stmt.where(Article.tags.contains(tags))
        count_stmt = count_stmt.where(Article.tags.contains(tags))
    if source_id:
        stmt = stmt.where(Article.source_id == source_id)
        count_stmt = count_stmt.where(Article.source_id == source_id)
    if date_from:
        stmt = stmt.where(Article.published_at >= date_from)
        count_stmt = count_stmt.where(Article.published_at >= date_from)
    if date_to:
        stmt = stmt.where(Article.published_at <= date_to + " 23:59:59")
        count_stmt = count_stmt.where(Article.published_at <= date_to + " 23:59:59")

    total = (await db.execute(count_stmt)).scalar() or 0
    articles = (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return ArticlePage(
        total=total, page=page, page_size=page_size,
        items=[ArticleResponse.model_validate(a) for a in articles],
        total_pages=math.ceil(total / page_size) if total > 0 else 0
    )


@router.get("/suggest")
async def search_suggest(q: str = Query("", min_length=1), db: AsyncSession = Depends(get_db)):
    """搜索建议：根据输入关键词返回最多10个匹配的标签名，供前端自动补全"""
    result = await db.execute(text(
        "SELECT DISTINCT tag FROM (SELECT unnest(tags) AS tag FROM articles WHERE tags IS NOT NULL) t "
        "WHERE tag ILIKE :pattern ORDER BY tag LIMIT 10"
    ), {"pattern": f"%{q}%"})
    return {"suggestions": [row[0] for row in result.all()]}
