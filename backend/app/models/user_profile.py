from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


# Generate a timezone-aware UTC datetime for database timestamps
def time_utc():
    return datetime.now(timezone.utc)


# Map user account details to the user_profiles database table
class UserProfile(Base):
    __tablename__ = "user_profiles"

    uid: Mapped[str] = mapped_column(String(128), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=time_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=time_utc, onupdate=time_utc
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
