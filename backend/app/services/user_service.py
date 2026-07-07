from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source
from app.models.user import User
from app.services.preset_sources import PRESET_SOURCES

_USER_ID = 1


async def get_or_create_user(db: AsyncSession) -> User:
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


async def sync_sources(db: AsyncSession, enabled_keys: list[str]) -> None:
    """将用户勾选的来源同步到 sources 表。先按 URL 查，找不到按名称查，都没有才插入。"""
    for preset in PRESET_SOURCES:
        result = await db.execute(select(Source).where(Source.url == preset.url))
        source = result.scalar_one_or_none()

        if source is None:
            result2 = await db.execute(select(Source).where(Source.name == preset.name))
            source = result2.scalar_one_or_none()
            if source:
                source.url = preset.url  # URL 有变化时同步更新

        enabled = preset.key in enabled_keys

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
