from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.firebase_auth import get_authenticated_user
from app.crud.video import VideoService
from app.db.session import get_db
from app.services.storage import StorageService

router = APIRouter(prefix="/media", tags=["media"])


def get_storage() -> StorageService:
    return StorageService()


@router.get("/{key:path}")
async def proxy_media(
    key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
    storage: StorageService = Depends(get_storage),
):
    owner_uid = (current_user or {}).get("uid")
    if not owner_uid:
        raise HTTPException(status_code=401, detail="Unauthorized")

    safe_key = storage.sanitize_key(key)
    if not safe_key or not await VideoService(db).owns_storage_key(safe_key, str(owner_uid)):
        raise HTTPException(status_code=404, detail="File not found")

    range_header = request.headers.get("Range")

    try:
        body, content_type, content_length, content_range = storage.get_object_stream(
            safe_key, range_header=range_header
        )
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")

    status_code = 206 if content_range else 200
    headers = {"Accept-Ranges": "bytes", "Cache-Control": "private, max-age=3600"}
    if content_length is not None:
        headers["Content-Length"] = str(content_length)
    if content_range:
        headers["Content-Range"] = content_range

    return StreamingResponse(
        body.iter_chunks(),
        status_code=status_code,
        media_type=content_type,
        headers=headers,
    )
