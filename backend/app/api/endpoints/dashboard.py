from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.services.stats.reader_stats import get_summary
from app.services.llm.weekly_report import generate_weekly_report
from app.services.user_service import get_or_create_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """
    获取仪表盘概览统计数据（6项指标）：
    - total_articles: 总文章数
    - today_new: 今日新增
    - read_count: 已读文章数
    - favorite_count: 收藏文章数
    - active_sources: 活跃来源数
    - avg_score: 平均兴趣匹配度
    """
    return await get_summary(db)


@router.get("/weekly-report")
async def get_weekly_report(db: AsyncSession = Depends(get_db)):
    """
    生成 AI 周报（Markdown 格式），按用户兴趣个性化：
    - 本周阅读概况 + 热点趋势 + 兴趣相关分析 + 学习建议 + 下周关注
    - 附本周精选文章列表（含匹配度）
    """
    user = await get_or_create_user(db)
    interests = user.preferences.get("interests", [])
    content = await generate_weekly_report(db, interests)
    return {"content": content}
