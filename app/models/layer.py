from sqlalchemy import String, Float, Boolean, Integer, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from app.database import Base
from uuid import uuid4
import enum

class LayerType(str, enum.Enum):
    wms = "wms"
    wfs = "wfs"
    geojson = "geojson"
    xyz = "xyz"

class Layer(Base):
    __tablename__ = "layers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    type: Mapped[LayerType] = mapped_column(SAEnum(LayerType), nullable=False)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    opacity: Mapped[float] = mapped_column(Float, default=1.0)
    z_index: Mapped[int] = mapped_column(Integer, default=0)
    style: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source: Mapped[dict] = mapped_column(JSON, nullable=False)
    bbox: Mapped[list | None] = mapped_column(JSON, nullable=True)
    attribution: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Geometria nativa PostGIS 
    geometry: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326),
        nullable=True
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="layers")
