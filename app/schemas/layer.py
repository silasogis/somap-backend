from pydantic import BaseModel, ConfigDict
from humps import camelize
from typing import Optional

class LayerUpdateSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=camelize,
        populate_by_name=True,
        from_attributes=True,
    )
    name: Optional[str] = None
    visible: Optional[bool] = None
    opacity: Optional[float] = None
    z_index: Optional[int] = None
    style: Optional[dict] = None
    source: Optional[dict] = None
    bbox: Optional[list[float]] = None
    attribution: Optional[str] = None

class LayerConfigResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=camelize,
        populate_by_name=True,
        from_attributes=True,
    )
    id: str
    name: str
    workspace_id: str
    type: str 
    visible: bool
    opacity: float
    z_index: int
    style: dict | None = None
    source: dict
    bbox: list[float] | None = None
    attribution: str | None = None
