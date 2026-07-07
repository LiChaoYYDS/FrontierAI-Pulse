from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.services.llm.daily_brief import generate_daily_brief
from app.services.user_service import get_or_create_user

router = APIRouter(prefix="/api/brief", tags=["brief"])


@router.get("/today")
async def get_today_brief(db: AsyncSession = Depends(get_db)):
    """
    生成今日 AI 简报（Markdown 格式）
    - 根据近24小时新增文章，按用户兴趣标签分块展示
    - 每个兴趣方向单独一节：新发现 + 进展 + 趋势 + 代表文章
    - 无新文章时返回引导设置来源/兴趣的提示
    """
    user = await get_or_create_user(db)
    interests = user.preferences.get("interests", [])
    content = await generate_daily_brief(db, interests)
    return {"content": content}
