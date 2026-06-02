from pydantic import BaseModel, Field
from typing import List, Optional
from geojson_pydantic import FeatureCollection

class RouteRequest(BaseModel):
    start_point: List[float] = Field(..., description="[longitude, latitude] of the start point")
    end_point: List[float] = Field(..., description="[longitude, latitude] of the end point")

class RouteResponse(BaseModel):
    success: bool
    data: Optional[FeatureCollection] = None
    message: Optional[str] = None
    total_cost: Optional[float] = None
