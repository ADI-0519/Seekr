from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# Map a summary of a recently uploaded video for dashboard display
class ProfileRecentUpload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: str
    created_at: datetime
    duration: float | None = None


# Aggregate user video statistics and recent activity for the profile screen
class ProfileSummaryResponse(BaseModel):
    lecture_count: int
    ready_lecture_count: int
    processing_lecture_count: int
    failed_lecture_count: int
    total_duration_seconds: float
    recent_uploads: list[ProfileRecentUpload]


# Define the incoming payload for syncing external auth provider details
class ProfileSyncRequest(BaseModel):
    display_name: str | None = None
    photo_url: str | None = None


# Define the outgoing payload confirming the synced user profile state
class ProfileSyncResponse(BaseModel):
    uid: str
    email: str | None = None
    display_name: str | None = None
    photo_url: str | None = None
    provider: str | None = None
    last_login_at: datetime | None = None


# Define the outgoing payload for user application preferences
class UserSettingsResponse(BaseModel):
    uid: str
    theme_mode: str
    background_mode: str
    card_style: str
    video_animation: int
    autoplay_next: bool
    pause_on_leave: bool
    volume_default: float
    muted_default: bool
    preferred_language: str
    timezone: str | None = None


# Validate incoming preference updates with strict type and boundary constraints
class UserSettingsUpdateRequest(BaseModel):
    theme_mode: str = Field("light", pattern="^(light|dark)$")
    background_mode: str = Field("animated", pattern="^(animated|static)$")
    card_style: str = Field("solid", pattern="^(solid|transparent)$")
    video_animation: int = Field(1, ge=1, le=7)
    autoplay_next: bool = True
    pause_on_leave: bool = True
    volume_default: float = Field(1.0, ge=0.0, le=1.0)
    muted_default: bool = False
    preferred_language: str = Field("en", min_length=2, max_length=16)
    timezone: str | None = Field(default=None, max_length=64)
