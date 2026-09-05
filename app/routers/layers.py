from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.dependencies import get_db, get_current_user, require_role
from app.models.user import User, UserRole
from app.models.layer import Layer, LayerType
from app.models.workspace import user_workspace_association
from app.schemas.layer import LayerConfigResponse, LayerUpdateSchema
from app.services.layer_service import layer_service

router = APIRouter(prefix="/api/layers", tags=["Layers"])

async def verify_workspace_access(db: AsyncSession, user: User, workspace_id: str):
    if user.role == UserRole.admin:
        return
    stmt = select(1).select_from(user_workspace_association).where(
        user_workspace_association.c.user_id == user.id,
        user_workspace_association.c.workspace_id == workspace_id
    )
    result = await db.execute(stmt)
    if not result.scalar():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a este workspace"
        )

@router.get("", response_model=list[LayerConfigResponse])
async def get_layers(
    workspace_id: str = Query(..., alias="workspaceId"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await verify_workspace_access(db, current_user, workspace_id)
    layers = await layer_service.get_by_workspace(db, workspace_id)
    return layers

@router.get("/{layer_id}/data")
async def get_layer_data(
    layer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    layer = await layer_service.get_by_id(db, layer_id)
    await verify_workspace_access(db, current_user, layer.workspace_id)
    
    if layer.type != LayerType.geojson:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    
    feature_collection = await layer_service.get_layer_geojson(db, layer_id)
    return feature_collection

@router.patch("/{layer_id}", response_model=LayerConfigResponse)
async def update_layer(
    layer_id: str,
    payload: LayerUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.editor))
):
    layer = await layer_service.get_by_id(db, layer_id)
    await verify_workspace_access(db, current_user, layer.workspace_id)
    
    updated_layer = await layer_service.update_layer(db, layer_id, payload)
    return updated_layer

