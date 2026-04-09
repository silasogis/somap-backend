import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.layer import Layer, LayerType
from app.schemas.layer import LayerUpdateSchema

class LayerService:
    async def get_by_workspace(self, db: AsyncSession, workspace_id: str):
        stmt = select(Layer).where(Layer.workspace_id == workspace_id).order_by(Layer.z_index)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, db: AsyncSession, layer_id: str):
        stmt = select(Layer).where(Layer.id == layer_id)
        result = await db.execute(stmt)
        layer = result.scalar_one_or_none()
        
        if not layer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camada não encontrada")
        return layer

    async def update_layer(self, db: AsyncSession, layer_id: str, payload: LayerUpdateSchema) -> Layer:
        layer = await self.get_by_id(db, layer_id)
        update_data = payload.model_dump(exclude_unset=True, by_alias=False)
        
        for key, value in update_data.items():
            setattr(layer, key, value)
            
        await db.commit()
        await db.refresh(layer)
        return layer

    async def get_layer_geojson(self, db: AsyncSession, layer_id: str) -> dict:
        stmt = select(
            Layer,
            func.ST_AsGeoJSON(Layer.geometry).label("geojson")
        ).where(Layer.id == layer_id)
        
        result = await db.execute(stmt)
        row = result.one_or_none()
        
        if not row or not row.Layer:
            raise HTTPException(status_code=404, detail="Camada não encontrada")
        
        layer = row.Layer
        
        if layer.type != LayerType.geojson or not row.geojson:
            return {"type": "FeatureCollection", "features": []}
        
        geometry = json.loads(row.geojson)
        
        feature = {
            "type": "Feature",
            "properties": {
                "id": layer.id,
                "name": layer.name,
                "workspace_id": layer.workspace_id
            },
            "geometry": geometry
        }
        
        return {
            "type": "FeatureCollection",
            "features": [feature]
        }

layer_service = LayerService()
