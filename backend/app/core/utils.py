from fastapi import HTTPException, status

from app.core.config import get_settings


def resolve_owner_uid(current_user: dict | None) -> str | None:
    uid = (current_user or {}).get("uid")
    if uid:
        return str(uid)

    settings = get_settings()
    if not settings.firebase_auth_enabled:
        return None

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authenticated user id missing from token")
