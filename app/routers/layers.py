from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.dependencies import get_db, get_current_user, require_role
from app.models.user import UserRole
from app.models.layer import Layer, LayerType
from app.schemas.layer import LayerConfigResponse, LayerUpdateSchema
from app.services.layer_service import layer_service

router = APIRouter(prefix="/api/layers", tags=["Layers"])

@router.get("", response_model=list[LayerConfigResponse])
async def get_layers(
    workspace_id: str = Query(..., alias="workspaceId"),
    db: AsyncSession = Depends(get_db),
    _ = Depends(get_current_user)
):
    layers = await layer_service.get_by_workspace(db, workspace_id)
    return layers

@router.get("/{layer_id}/data")
async def get_layer_data(
    layer_id: str,
    db: AsyncSession = Depends(get_db),
    _ = Depends(get_current_user)
):
    layer = await layer_service.get_by_id(db, layer_id)
    
    if layer.type != LayerType.geojson:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    
    feature_collection = await layer_service.get_layer_geojson(db, layer_id)
    return feature_collection

@router.patch("/{layer_id}", response_model=LayerConfigResponse)
async def update_layer(
    layer_id: str,
    payload: LayerUpdateSchema,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_role(UserRole.admin, UserRole.editor))
):
    layer = await layer_service.update_layer(db, layer_id, payload)
    return layer
