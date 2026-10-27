from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings


def get_rate_limit_key(request) -> str:
    # Prefer per-user limits when auth is available so shared IPs do not collide.
    user = getattr(request.state, "firebase_user", None)
    if user and user.get("uid"):
        return f"uid:{user['uid']}"
    return get_remote_address(request)


settings = get_settings()
limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri=settings.rate_limit_storage_uri,
)
