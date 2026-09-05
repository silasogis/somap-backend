from sqlalchemy import String, Float, Integer, ForeignKey, Date, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from app.database import Base
from uuid import uuid4
import datetime

class LogisticsRoute(Base):
    __tablename__ = "logistics_routes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    route_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    driver_name: Mapped[str] = mapped_column(String(120), nullable=False)
    driver_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    vehicle: Mapped[str | None] = mapped_column(String(80), nullable=True)
    total_distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    total_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    google_maps_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Geometria do traçado da rota
    geom_route: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="MULTILINESTRING", srid=4326),
        nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    stops: Mapped[list["LogisticsRouteStop"]] = relationship(
        "LogisticsRouteStop", back_populates="route", cascade="all, delete-orphan"
    )

class LogisticsRouteStop(Base):
    __tablename__ = "logistics_route_stops"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    route_id: Mapped[str] = mapped_column(
        ForeignKey("logistics_routes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stop_order: Mapped[int] = mapped_column(Integer, nullable=False)
    stop_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'origin', 'pickup', 'return'
    item_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    donor_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Geometria do ponto da parada
    geom_stop: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    route: Mapped["LogisticsRoute"] = relationship("LogisticsRoute", back_populates="stops")
