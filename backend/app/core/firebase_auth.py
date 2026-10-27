import json
import logging
from functools import lru_cache
from typing import Annotated, Any, cast

import firebase_admin
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, credentials

from app.core.config import get_settings

log = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


def build_firebase_credential():
    settings = get_settings()

    if settings.firebase_service_account_json:
        info = json.loads(settings.firebase_service_account_json)
        return credentials.Certificate(info)

    if (
        settings.firebase_project_id
        and settings.firebase_client_email
        and settings.firebase_private_key
    ):
        return credentials.Certificate(
            {
                "type": "service_account",
                "project_id": settings.firebase_project_id,
                "client_email": settings.firebase_client_email,
                "private_key": settings.firebase_private_key.get_secret_value().replace(
                    "\\n", "\n"
                ),
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )

    # ApplicationDefault won't work on Railway, so fail loudly instead of initialising fb with credentials that never resolve
    raise ValueError(
        "No Firebase credentials configured. "
        "Set FIREBASE_SERVICE_ACCOUNT_JSON or "
        "FIREBASE_PROJECT_ID + FIREBASE_CLIENT_EMAIL + FIREBASE_PRIVATE_KEY."
    )


@lru_cache
def get_firebase_app():
    settings = get_settings()

    if not settings.firebase_auth_enabled:
        return None

    if firebase_admin._apps:
        return firebase_admin.get_app()

    app_options: dict[str, Any] = {}
    if settings.firebase_project_id:
        app_options["projectId"] = settings.firebase_project_id

    return firebase_admin.initialize_app(build_firebase_credential(), app_options or None)


async def require_firebase_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.firebase_auth_enabled:
        return None

    token = credentials.credentials if credentials else request.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header or token query parameter",
        )

    try:
        get_firebase_app()
        user = cast(
            dict[str, Any],
            auth.verify_id_token(token, clock_skew_seconds=60),
        )
        request.state.firebase_user = user
        return user
    except Exception as exc:
        log.warning(
            "Firebase token verification failed: %s: %s",
            type(exc).__name__,
            str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase token",
        ) from exc


async def get_authenticated_user(
    request: Request,
    user: dict[str, Any] | None = Depends(require_firebase_user),
) -> dict[str, Any] | None:
    authenticated_user = getattr(request.state, "firebase_user", None) or user
    if authenticated_user:
        return authenticated_user

    settings = get_settings()
    if not settings.firebase_auth_enabled:
        return None

    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authenticated user context",
        )
    return authenticated_user


FirebaseUser = Annotated[dict[str, Any] | None, Depends(get_authenticated_user)]
