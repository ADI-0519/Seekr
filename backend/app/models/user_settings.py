from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


# Generate current UTC timestamp for database defaults
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# Map user application preferences to the user_settings table
class UserSettings(Base):
    __tablename__ = "user_settings"

    uid: Mapped[str] = mapped_column(String(128), primary_key=True)
    theme_mode: Mapped[str] = mapped_column(String(16), default="light")
    background_mode: Mapped[str] = mapped_column(String(16), default="animated")
    card_style: Mapped[str] = mapped_column(String(16), default="solid")
    video_animation: Mapped[int] = mapped_column(default=1)
    autoplay_next: Mapped[bool] = mapped_column(Boolean, default=True)
    pause_on_leave: Mapped[bool] = mapped_column(Boolean, default=True)
    volume_default: Mapped[float] = mapped_column(Float, default=1.0)
    muted_default: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_language: Mapped[str] = mapped_column(String(16), default="en")
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )
