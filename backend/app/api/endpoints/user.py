from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import PRESET_INTERESTS
from app.db.deps import get_db
from app.schemas.user import PresetSourceOut, UserSourcesIn, UserInterestsIn
from app.services.preset_sources import PRESET_SOURCES
from app.services.user_service import get_or_create_user, sync_sources

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/preset-sources", response_model=list[PresetSourceOut])
async def get_preset_sources():
    """获取系统内置的所有预设资讯来源列表（12个，含中英文来源），供用户勾选启用"""
    return [PresetSourceOut(**{k: getattr(s, k) for k in PresetSourceOut.model_fields}) for s in PRESET_SOURCES]


@router.get("/sources")
async def get_user_sources(db: AsyncSession = Depends(get_db)):
    """获取当前用户已启用的来源 key 列表，用于来源管理页展示勾选状态"""
    user = await get_or_create_user(db)
    keys = user.preferences.get("enabled_keys") or user.preferences.get("enabled_sources", [])
    return {"enabled_keys": keys}


@router.put("/sources")
async def update_user_sources(body: UserSourcesIn, db: AsyncSession = Depends(get_db)):
    """
    保存用户勾选的来源，并同步到 sources 表：
    - 勾选的来源：upsert（不存在则新增，已有则设 is_active=True）
    - 未勾选的来源：设 is_active=False（保留历史数据）
    """
    user = await get_or_create_user(db)
    prefs = dict(user.preferences)
    prefs["enabled_keys"] = body.enabled_keys
    user.preferences = prefs
    await sync_sources(db, body.enabled_keys)
    await db.commit()
    return {"enabled_keys": body.enabled_keys, "synced": len(PRESET_SOURCES)}


@router.get("/interests/preset")
async def get_preset_interests():
    """获取系统预设的18个技术领域兴趣标签列表，供用户选择"""
    return {"interests": PRESET_INTERESTS}


@router.get("/interests")
async def get_user_interests(db: AsyncSession = Depends(get_db)):
    """获取当前用户已选的兴趣标签列表，用于 AI 评分和简报个性化"""
    user = await get_or_create_user(db)
    return {"interests": user.preferences.get("interests", [])}


@router.put("/interests")
async def update_user_interests(body: UserInterestsIn, db: AsyncSession = Depends(get_db)):
    """保存用户兴趣标签（覆盖更新），影响文章匹配度评分和每日简报内容"""
    user = await get_or_create_user(db)
    prefs = dict(user.preferences)
    prefs["interests"] = body.interests
    user.preferences = prefs
    await db.commit()
    return {"interests": body.interests}
