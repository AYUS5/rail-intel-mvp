from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Availability(TimestampMixin, Base):
    __tablename__ = "availabilities"
    __table_args__ = (
        UniqueConstraint(
            "train_id",
            "source_station_id",
            "destination_station_id",
            "travel_date",
            "travel_class",
            name="uq_availability_lookup",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    train_id: Mapped[int] = mapped_column(ForeignKey("trains.id"), index=True, nullable=False)
    source_station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False)
    destination_station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False)
    travel_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    travel_class: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    available_count: Mapped[int | None] = mapped_column(Integer)
    rac_count: Mapped[int | None] = mapped_column(Integer)
    waitlist_count: Mapped[int | None] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(40), default="mock", nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

