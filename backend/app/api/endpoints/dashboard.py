from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.schemas.dashboard import DashboardData
from app.services.llm.weekly_report import generate_weekly_report
from app.services.stats.reader_stats import get_dashboard_data
from app.services.user_service import get_or_create_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardData)
async def get_dashboard_summary(
    days: int = Query(30, ge=7, le=90, description="增长趋势时间窗口（7/30/90天）"),
):
    """
    获取仪表盘全量数据（六个模块一次返回，全部并行查询）：
    - 数据总览 / 内容增长趋势 / 阅读漏斗 / AI 推荐命中率 / 来源贡献排行 / 标签分布
    """
    return await get_dashboard_data(days)


@router.get("/weekly-report", response_model=None)
async def get_weekly_report(db: AsyncSession = Depends(get_db)):
    """
    生成结构化 AI 周报，按用户兴趣个性化。
    """
    from app.schemas.report import WeeklyReportData
    user = await get_or_create_user(db)
    interests = user.preferences.get("interests", [])
    return await generate_weekly_report(db, interests)
