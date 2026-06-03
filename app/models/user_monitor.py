from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class UserMonitor(TimestampMixin, Base):
    __tablename__ = "user_monitors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(80), index=True)
    train_number: Mapped[str | None] = mapped_column(String(12), index=True)
    source_station_code: Mapped[str] = mapped_column(String(12), nullable=False)
    destination_station_code: Mapped[str] = mapped_column(String(12), nullable=False)
    travel_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    travel_class: Mapped[str] = mapped_column(String(12), nullable=False)
    threshold_status: Mapped[str] = mapped_column(String(32), default="RAC", nullable=False)
    notification_target: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    recommendations = relationship("Recommendation", back_populates="monitor")

