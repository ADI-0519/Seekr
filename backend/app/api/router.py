from fastapi import APIRouter

from app.api.jobs import router as jobs_router
from app.api.media import router as media_router
from app.api.profile import router as profile_router
from app.api.videos import router as videos_router

api_router = APIRouter()

api_router.include_router(videos_router)
api_router.include_router(jobs_router)
api_router.include_router(profile_router)
api_router.include_router(media_router)
