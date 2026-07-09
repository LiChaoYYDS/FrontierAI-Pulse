from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.models.source import Source
from app.schemas.source import CustomSourceCreate, SourceActiveUpdate, SourceResponse

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("/", response_model=list[SourceResponse])
async def get_sources(db: AsyncSession = Depends(get_db)):
    """获取所有资讯来源列表（按名称排序），用于前端来源过滤下拉框"""
    result = await db.execute(select(Source).order_by(Source.name))
    return result.scalars().all()


@router.get("/all-tags", response_model=list[str])
async def get_all_tags(db: AsyncSession = Depends(get_db)):
    """获取全库所有文章中出现过的不重复标签（按字母排序），用于前端标签过滤下拉框"""
    result = await db.execute(text(
        "SELECT DISTINCT tag FROM (SELECT unnest(tags) AS tag FROM articles WHERE tags IS NOT NULL) t "
        "WHERE tag IS NOT NULL AND tag != '' ORDER BY tag"
    ))
    return [row[0] for row in result.all()]


@router.post("/custom", response_model=SourceResponse, status_code=201)
async def add_custom_source(body: CustomSourceCreate, db: AsyncSession = Depends(get_db)):
    """手动添加自定义来源（非预设），URL 唯一，添加后立即激活"""
    existing = (await db.execute(select(Source).where(Source.url == body.url))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="该来源 URL 已存在")
    source = Source(
        name=body.name,
        url=body.url,
        type=body.type,
        description=body.description,
        is_active=True,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.patch("/{source_id}", response_model=SourceResponse)
async def update_source_active(
    source_id: int, body: SourceActiveUpdate, db: AsyncSession = Depends(get_db)
):
    """切换自定义来源的启用/禁用状态"""
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")
    source.is_active = body.is_active
    await db.commit()
    return source


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    """删除自定义来源（关联文章的 source_id 自动置为 NULL）"""
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")
    await db.delete(source)
    await db.commit()


@router.post("/{source_id}/fetch")
async def trigger_fetch(source_id: int):
    """手动触发指定来源的抓取任务，立即从该来源 URL 拉取最新文章并入库"""
    from app.services.scraper.scheduler import fetch_single_source
    try:
        count = await fetch_single_source(source_id)
        return {"source_id": source_id, "new_articles": count}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
