from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.firebase_auth import get_authenticated_user
from app.core.utils import resolve_owner_uid
from app.crud.profile import UserProfileService, UserSettingsService
from app.crud.video import VideoService
from app.db.session import get_db
from app.schemas.profile import (
    ProfileSummaryResponse,
    ProfileSyncRequest,
    ProfileSyncResponse,
    UserSettingsResponse,
    UserSettingsUpdateRequest,
)

router = APIRouter(prefix="/profile", tags=["profile"])


def require_uid(current_user: dict | None) -> str:
    uid = (current_user or {}).get("uid")
    if not uid:
        raise HTTPException(401, "Authenticated user id missing from token")
    return str(uid)


@router.get("/me", response_model=ProfileSummaryResponse)
async def get_my_profile_summary(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    return await VideoService(db).get_profile_summary(owner_uid=owner_uid)


@router.put("/me", response_model=ProfileSyncResponse)
async def upsert_my_profile(
    payload: ProfileSyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    uid = (current_user or {}).get("uid")
    if not uid:
        raise HTTPException(401, "Authenticated user id missing from token")

    email = (current_user or {}).get("email")
    provider = ((current_user or {}).get("firebase") or {}).get("sign_in_provider")

    profile = await UserProfileService(db).upsert(
        uid=str(uid),
        email=str(email) if email else None,
        display_name=payload.display_name,
        photo_url=payload.photo_url,
        provider=str(provider) if provider else None,
    )

    return ProfileSyncResponse(
        uid=profile.uid,
        email=profile.email,
        display_name=profile.display_name,
        photo_url=profile.photo_url,
        provider=profile.provider,
        last_login_at=profile.last_login_at,
    )


@router.get("/settings", response_model=UserSettingsResponse)
async def get_my_settings(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    uid = require_uid(current_user)
    settings = await UserSettingsService(db).get_or_create(uid)
    return UserSettingsResponse(
        uid=settings.uid,
        theme_mode=settings.theme_mode,
        background_mode=settings.background_mode,
        card_style=settings.card_style,
        video_animation=settings.video_animation,
        autoplay_next=settings.autoplay_next,
        pause_on_leave=settings.pause_on_leave,
        volume_default=settings.volume_default,
        muted_default=settings.muted_default,
        preferred_language=settings.preferred_language,
        timezone=settings.timezone,
    )


@router.put("/settings", response_model=UserSettingsResponse)
async def update_my_settings(
    payload: UserSettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    uid = require_uid(current_user)
    settings = await UserSettingsService(db).update(
        uid,
        theme_mode=payload.theme_mode,
        background_mode=payload.background_mode,
        card_style=payload.card_style,
        video_animation=payload.video_animation,
        autoplay_next=payload.autoplay_next,
        pause_on_leave=payload.pause_on_leave,
        volume_default=payload.volume_default,
        muted_default=payload.muted_default,
        preferred_language=payload.preferred_language,
        timezone=payload.timezone,
    )
    return UserSettingsResponse(
        uid=settings.uid,
        theme_mode=settings.theme_mode,
        background_mode=settings.background_mode,
        card_style=settings.card_style,
        video_animation=settings.video_animation,
        autoplay_next=settings.autoplay_next,
        pause_on_leave=settings.pause_on_leave,
        volume_default=settings.volume_default,
        muted_default=settings.muted_default,
        preferred_language=settings.preferred_language,
        timezone=settings.timezone,
    )
