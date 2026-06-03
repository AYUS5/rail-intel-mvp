from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RouteSegment(TimestampMixin, Base):
    __tablename__ = "route_segments"
    __table_args__ = (
        UniqueConstraint("train_id", "sequence", name="uq_route_segments_train_sequence"),
        UniqueConstraint("train_id", "station_id", name="uq_route_segments_train_station"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    train_id: Mapped[int] = mapped_column(ForeignKey("trains.id"), index=True, nullable=False)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), index=True, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_km: Mapped[int] = mapped_column(Integer, nullable=False)
    arrival_time: Mapped[str | None] = mapped_column(String(8))
    departure_time: Mapped[str | None] = mapped_column(String(8))

    train = relationship("Train", back_populates="route_segments")
    station = relationship("Station", back_populates="route_segments")

