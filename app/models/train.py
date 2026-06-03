from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Train(TimestampMixin, Base):
    __tablename__ = "trains"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    origin_station_code: Mapped[str] = mapped_column(String(12), nullable=False)
    destination_station_code: Mapped[str] = mapped_column(String(12), nullable=False)
    service_days: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    route_segments = relationship(
        "RouteSegment",
        back_populates="train",
        cascade="all, delete-orphan",
        order_by="RouteSegment.sequence",
    )

