import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.schemas.routing import RouteRequest, RouteResponse
from geojson_pydantic import FeatureCollection, Feature

class RoutingService:
    async def get_route(self, db: AsyncSession, request: RouteRequest) -> RouteResponse:
        try:
            # Query to find the shortest path using pgRouting
            # 1. Find nearest vertices
            # 2. Run pgr_dijkstra
            # 3. Join with original table to get geometries
            
            query = text("""
                WITH start_node AS (
                    SELECT id FROM sul_2po_vertices
                    ORDER BY the_geom <-> ST_SetSRID(ST_MakePoint(:start_lng, :start_lat), 4326)
                    LIMIT 1
                ),
                end_node AS (
                    SELECT id FROM sul_2po_vertices
                    ORDER BY the_geom <-> ST_SetSRID(ST_MakePoint(:end_lng, :end_lat), 4326)
                    LIMIT 1
                )
                SELECT 
                    rt.seq, 
                    rt.node, 
                    rt.edge, 
                    rt.cost, 
                    rt.agg_cost, 
                    ST_AsGeoJSON(edge.geom_way)::json as geometry
                FROM pgr_dijkstra(
                    -- FORMAT injeta as coordenadas dinamicamente na string da subquery
                    FORMAT(
                        'SELECT id, source, target, cost, reverse_cost FROM sul_2po_4pgr 
                         WHERE geom_way && ST_Expand(ST_MakeLine(ST_SetSRID(ST_MakePoint(%L, %L), 4326), ST_SetSRID(ST_MakePoint(%L, %L), 4326)), 0.1)',
                        :start_lng, :start_lat, :end_lng, :end_lat
                    ),
                    (SELECT id FROM start_node),
                    (SELECT id FROM end_node),
                    true
                ) as rt
                JOIN sul_2po_4pgr as edge ON rt.edge = edge.id
                ORDER BY rt.seq;
            """)
            
            result = await db.execute(query, {
                "start_lng": request.start_point[0],
                "start_lat": request.start_point[1],
                "end_lng": request.end_point[0],
                "end_lat": request.end_point[1]
            })
            
            rows = result.all()
            
            if not rows:
                return RouteResponse(success=False, message="No route found between selected points.")
            
            features = []
            total_cost = 0
            
            for row in rows:
                if row.geometry:
                    feature = Feature(
                        type="Feature",
                        geometry=row.geometry,
                        properties={
                            "seq": row.seq,
                            "cost": row.cost,
                            "agg_cost": row.agg_cost
                        }
                    )
                    features.append(feature)
                    total_cost = row.agg_cost # The last row has the total agg_cost
            
            feature_collection = FeatureCollection(type="FeatureCollection", features=features)
            
            return RouteResponse(
                success=True, 
                data=feature_collection,
                total_cost=total_cost
            )
            
        except Exception as e:
            return RouteResponse(success=False, message=str(e))

routing_service = RoutingService()
