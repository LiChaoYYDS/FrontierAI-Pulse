from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.config import get_db
from app.models.source import Source
from app.models.user import User
from app.services.preset_sources import PRESET_SOURCES, PRESET_MAP, PresetSource

router = APIRouter(prefix="/api/user", tags=["user"])

_USER_ID = 1  # 个人应用固定单用户


# ── Schemas ──────────────────────────────────────────────────────────────────

class PresetSourceOut(BaseModel):
    key: str
    name: str
    url: str
    type: str
    description: str
    category: str


class UserSourcesIn(BaseModel):
    enabled_keys: list[str]  # 用户勾选的预设来源 key 列表


# ── 辅助函数 ──────────────────────────────────────────────────────────────────

async def _get_or_create_user(db: AsyncSession) -> User:
    """获取单用户，不存在则创建（默认全部来源启用）"""
    user = await db.get(User, _USER_ID)
    if not user:
        user = User(
            id=_USER_ID,
            preferences={
                "enabled_keys": [s.key for s in PRESET_SOURCES],
                "interests": [],
            },
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


# ── 端点 ──────────────────────────────────────────────────────────────────────

@router.get("/preset-sources", response_model=list[PresetSourceOut])
async def get_preset_sources():
    """获取所有预设来源列表"""
    # list_sources: list[PresetSourceOut] = []
    # for source in PRESET_SOURCES:
    #    list_sources.append(PresetSourceOut(
    #        key=source.key,
    #        name=source.name,
    #        url=source.url,
    #        type=source.type,
    #        description=source.description,
    #        category=source.category,
    #    ))
    # return list_sources
    #先外层循环取出预设来源元素，然后内层循环取出要输出的元素属性，然后赋给输出对象，model_fields获取字段列表dict[str,FieldInfo]
    return [PresetSourceOut(**{k: getattr(s, k,None) for k in PresetSourceOut.model_fields}) for s in PRESET_SOURCES]


@router.get("/sources")
async def get_user_sources(db: AsyncSession = Depends(get_db)):
    """获取用户当前启用的来源 key 列表"""
    user = await _get_or_create_user(db)
    # 兼容旧字段名 enabled_sources
    keys = user.preferences.get("enabled_keys") or user.preferences.get("enabled_sources", [])
    return {"enabled_keys": keys}


@router.put("/sources")
async def update_user_sources(body: UserSourcesIn, db: AsyncSession = Depends(get_db)):
    """
    保存用户启用的来源，并同步到 sources 表：
    - 勾选的来源 → upsert（不存在则插入，存在则设 is_active=True）
    - 未勾选的来源 → is_active=False
    """
    user = await _get_or_create_user(db)

    # 1. 更新用户偏好
    prefs = dict(user.preferences)
    prefs["enabled_keys"] = body.enabled_keys
    user.preferences = prefs

    # 2. 同步到 sources 表：先按 url 匹配，找不到再按 name 匹配，都没有才插入
    for preset in PRESET_SOURCES:
        result = await db.execute(select(Source).where(Source.url == preset.url))
        source = result.scalar_one_or_none()

        if source is None:
            # URL 变了但同名来源可能已存在，按名称查
            result2 = await db.execute(select(Source).where(Source.name == preset.name))
            source = result2.scalar_one_or_none()
            if source:
                source.url = preset.url  # 更新到最新 URL

        enabled = preset.key in body.enabled_keys

        if source:
            source.is_active = enabled
        elif enabled:
            db.add(Source(
                name=preset.name,
                url=preset.url,
                type=preset.type,
                description=preset.description,
                is_active=True,
                extra_config=preset.extra_config or None,
            ))

    await db.commit()
    return {"enabled_keys": body.enabled_keys, "synced": len(PRESET_SOURCES)}
