from sqlalchemy import Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Recommendation(TimestampMixin, Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    monitor_id: Mapped[str | None] = mapped_column(ForeignKey("user_monitors.id"), index=True)
    train_number: Mapped[str] = mapped_column(String(12), index=True, nullable=False)
    source_station_code: Mapped[str] = mapped_column(String(12), nullable=False)
    destination_station_code: Mapped[str] = mapped_column(String(12), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(String(1000), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    monitor = relationship("UserMonitor", back_populates="recommendations")

