from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Schema for the API response returned when a new background processing task starts
class JobTriggerResponse(BaseModel):
    video_id: int
    task_id: str
    message: str


# Schema representing the detailed state and progress of an ongoing or completed job
class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    task_id: str | None = None
    status: str
    current_stage: str | None = None
    transcription_stage: str | None = None
    slides_stage: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


# Schema for the API response returned when a background task is actively aborted
class JobCancelResponse(BaseModel):
    video_id: int
    task_id: str
    status: str
    message: str
