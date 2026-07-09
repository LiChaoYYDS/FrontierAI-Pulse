"""
浏览历史 API

端点：
  GET    /api/history          — 获取阅读历史（最近30天，分页+标题关键词过滤）
  DELETE /api/history/{id}     — 删除单条历史记录（清空该文章的 is_read 和 read_at）
  DELETE /api/history/all      — 清空全部历史记录
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.models.article import Article
from app.schemas.article import ArticleResponse, ArticlePage

router = APIRouter(prefix="/api/history", tags=["history"])

_HISTORY_DAYS = 30  # 历史记录最长保留天数


@router.get("", response_model=ArticlePage)
async def get_history(
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q:         str = Query("", description="按标题关键词过滤"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取阅读历史列表（最近30天内，按 read_at 倒序）。
    - page / page_size: 分页参数
    - q: 按文章标题模糊搜索（可选）
    """
    since = datetime.now(timezone.utc) - timedelta(days=_HISTORY_DAYS)

    base = (
        select(Article)
        .where(Article.is_read == True, Article.read_at >= since)
    )
    count_base = (
        select(func.count(Article.id))
        .where(Article.is_read == True, Article.read_at >= since)
    )

    if q:
        like = f"%{q}%"
        base       = base.where(Article.title.ilike(like))
        count_base = count_base.where(Article.title.ilike(like))

    total = (await db.execute(count_base)).scalar() or 0
    articles = (
        await db.execute(
            base.order_by(Article.read_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
        )
    ).scalars().all()

    import math
    return ArticlePage(
        total=total,
        page=page,
        page_size=page_size,
        items=[ArticleResponse.model_validate(a) for a in articles],
        total_pages=math.ceil(total / page_size) if total else 0,
    )


@router.delete("/all", status_code=204)
async def clear_all_history(db: AsyncSession = Depends(get_db)):
    """清空全部阅读历史：将最近30天内所有已读文章的 is_read 和 read_at 重置。"""
    since = datetime.now(timezone.utc) - timedelta(days=_HISTORY_DAYS)
    articles = (
        await db.execute(
            select(Article).where(Article.is_read == True, Article.read_at >= since)
        )
    ).scalars().all()
    for a in articles:
        a.is_read = False
        a.read_at = None
    await db.commit()


@router.delete("/{article_id}", status_code=204)
async def delete_history_item(article_id: int, db: AsyncSession = Depends(get_db)):
    """删除单条历史记录：将该文章标记为未读并清空 read_at。"""
    from fastapi import HTTPException
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    article.is_read = False
    article.read_at = None
    await db.commit()
