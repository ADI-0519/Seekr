from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_profile import UserProfile
from app.models.user_settings import UserSettings


class UserProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(
        self,
        uid: str,
        email: str | None,
        display_name: str | None,
        photo_url: str | None,
        provider: str | None,
    ) -> UserProfile:
        now = datetime.now(timezone.utc)
        upsert_stmt = (
            insert(UserProfile)
            .values(
                uid=uid,
                email=email,
                display_name=display_name,
                photo_url=photo_url,
                provider=provider,
                last_login_at=now,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=[UserProfile.uid],
                set_={
                    "email": email,
                    "display_name": display_name,
                    "photo_url": photo_url,
                    "provider": provider,
                    "last_login_at": now,
                    "updated_at": now,
                },
            )
            .returning(UserProfile)
        )
        result = await self.db.execute(upsert_stmt)
        return result.scalar_one()


class UserSettingsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, uid: str) -> UserSettings:
        # Seed defaults on first access, then read back the persisted row.
        insert_stmt = (
            insert(UserSettings)
            .values(uid=uid)
            .on_conflict_do_nothing(index_elements=[UserSettings.uid])
        )
        await self.db.execute(insert_stmt)

        stmt = select(UserSettings).where(UserSettings.uid == uid)
        return (await self.db.execute(stmt)).scalar_one()

    async def update(
        self,
        uid: str,
        *,
        theme_mode: str,
        background_mode: str,
        card_style: str,
        video_animation: int,
        autoplay_next: bool,
        pause_on_leave: bool,
        volume_default: float,
        muted_default: bool,
        preferred_language: str,
        timezone: str | None,
    ) -> UserSettings:
        settings = await self.get_or_create(uid)
        settings.theme_mode = theme_mode
        settings.background_mode = background_mode
        settings.card_style = card_style
        settings.video_animation = video_animation
        settings.autoplay_next = autoplay_next
        settings.pause_on_leave = pause_on_leave
        settings.volume_default = volume_default
        settings.muted_default = muted_default
        settings.preferred_language = preferred_language
        settings.timezone = timezone
        await self.db.flush()
        return settings
