from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.schemas.report import WeeklyReportData
from app.services.llm.weekly_report import generate_weekly_report
from app.services.stats.reader_stats import get_summary
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


@router.get("/weekly-report", response_model=WeeklyReportData)
async def get_weekly_report(db: AsyncSession = Depends(get_db)):
    """
    生成结构化 AI 周报，按用户兴趣个性化：
    - 周报概览（文章数 / 阅读时长 / 知识点数）
    - 本周热点 Top 5（带趋势方向 + AI 一句话描述）
    - 精选文章 5-8 篇（标题 + 摘要 + 标签 + 阅读时长）
    - AI 洞见摘录（来自 article.insight 字段）
    - 个性化行动建议 3 条
    - 下周关注方向 3 条
    - 阅读趋势 & 兴趣分布（图表数据）
    """
    user = await get_or_create_user(db)
    interests = user.preferences.get("interests", [])
    return await generate_weekly_report(db, interests)
