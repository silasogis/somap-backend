from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas.routing import RouteRequest, RouteResponse
from app.services.routing_service import routing_service

router = APIRouter(prefix="/api/v1/routes", tags=["Routing"])

@router.post("", response_model=RouteResponse)
async def calculate_route(
    request: RouteRequest,
    db: AsyncSession = Depends(get_db),
    _ = Depends(get_current_user)
):
    """
    Calculates the shortest path between two points using pgRouting.
    Expects coordinates in [longitude, latitude] format.
    """
    result = await routing_service.get_route(db, request)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message
        )
    
    return result
