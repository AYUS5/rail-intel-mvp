from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AvailabilitySnapshotRecord(Base):
    __tablename__ = "availability_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    train_number: Mapped[str] = mapped_column(String(12), index=True, nullable=False)
    source_station_code: Mapped[str] = mapped_column(String(12), index=True, nullable=False)
    destination_station_code: Mapped[str] = mapped_column(String(12), index=True, nullable=False)
    travel_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    travel_class: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    available_count: Mapped[int | None] = mapped_column(Integer)
    rac_count: Mapped[int | None] = mapped_column(Integer)
    waitlist_count: Mapped[int | None] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)

