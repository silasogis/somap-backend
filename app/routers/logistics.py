from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import sys
import json
import datetime

from app.dependencies import get_db
from app.models.logistics import LogisticsRoute, LogisticsRouteStop

router = APIRouter(prefix="/api/v1/logistics", tags=["Logistics"])

# Coordenadas padrão para fallback em Curitiba caso não sejam especificadas
DEFAULT_ORIGIN_COORDS = [-49.285192, -25.442423]

# Mapeamento fallback de geocodificação para testes
DEFAULT_FALLBACK_COORDS = [
    [-49.2785, -25.4520],  # Água Verde
    [-49.2930, -25.4715],  # Portão
    [-49.2955, -25.4350]   # Bigorrilho
]

async def _query_nominatim_urls(search_query: str) -> Optional[List[float]]:
    """Consulta a lista de URLs do Nominatim para um determinado texto de busca."""
    urls = [
        "https://nominatim.somaping.online/search",
        "http://nominatim_server:8080/search",
        "http://localhost:8088/search",
        "https://nominatim.openstreetmap.org/search"
    ]
    
    print(f"[GEOCODE] Buscando termo: '{search_query}'", file=sys.stderr)
    
    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {"User-Agent": "somap-logistics-agent/1.0"}
                params = {
                    "q": search_query,
                    "format": "json",
                    "limit": 1
                }
                response = await client.get(url, params=params, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        lon = float(data[0]["lon"])
                        lat = float(data[0]["lat"])
                        coords = [lon, lat]
                        print(f"[GEOCODE] Sucesso via {url}: {coords}", file=sys.stderr)
                        return coords
        except Exception as e:
            print(f"[GEOCODE] Falha/Timeout em {url}: {str(e)}", file=sys.stderr)
            continue
    return None

async def geocode_address(address: str) -> Optional[List[float]]:
    """
    Tenta geocodificar o endereço de texto de forma inteligente:
    1. Tenta buscar o texto exatamente como enviado pela requisição.
    2. Se falhar, tenta anexar sufixos regionais caso não possua termos de município.
    """
    if not address or len(address.strip()) < 5:
        print(f"[GEOCODE] Endereço muito curto ou vazio: '{address}'", file=sys.stderr)
        return None
        
    # Tentativa 1: Exatamente como escrito na requisição
    coords = await _query_nominatim_urls(address)
    if coords:
        return coords
        
    # Tentativa 2: Caso a primeira busca falhe e não haja menção a outra cidade no texto,
    # tenta anexar "Curitiba, PR, Brasil" para filtrar localmente.
    cities = ["curitiba", "campo largo", "araucaria", "pinhais", "colombo", "sao jose", "são josé"]
    if not any(city in address.lower() for city in cities):
        search_query = f"{address}, Curitiba, PR, Brasil"
        print(f"[GEOCODE] Tentativa 2 com sufixo regional para Curitiba...", file=sys.stderr)
        coords = await _query_nominatim_urls(search_query)
        if coords:
            return coords
            
    print(f"[GEOCODE] Falha total. Não foi possível geocodificar '{address}'.", file=sys.stderr)
    return None

@router.post("/trigger")
async def trigger_logistics_route(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint de orquestração logística para roteirização e despacho com múltiplas paradas.
    Geocodifica os endereços textuais e executa o cálculo de rotas no pgRouting
    retornando distância real em quilômetros, tempo estimado e gerando link para navegação.
    """
    try:
        print(f"\n📥 [LOGISTICS TRIGGER] Nova requisição de roteirização recebida.", file=sys.stderr)
        driver_data = payload.get("driver") or {}
        driver_name = str(driver_data.get("name") or "Motorista")
        
        origin_hq = payload.get("origin_hq") or {}
        hq_coords = origin_hq.get("coords") or DEFAULT_ORIGIN_COORDS
        hq_name = origin_hq.get("name") or "Ponto de Origem / Sede"
        hq_address = origin_hq.get("address") or "Endereço de Origem"
        
        pickups = payload.get("pickups") or []
        route_points = [hq_coords]
        warnings = []
        resolved_details = []
        
        for idx, p in enumerate(pickups):
            address_str = p.get("address") or ""
            item_name = p.get("item") or "Item"
            
            # Tentar geocodificar o texto do endereço recebido
            geocoded_coords = await geocode_address(address_str)
            
            if geocoded_coords:
                route_points.append(geocoded_coords)
                resolved_details.append(f"{item_name}: {geocoded_coords} (Geocodificado)")
            else:
                # Usa coordenadas reais de fallback caso falhe
                fallback = DEFAULT_FALLBACK_COORDS[idx % len(DEFAULT_FALLBACK_COORDS)]
                route_points.append(fallback)
                warning_msg = f"Endereço '{address_str}' não localizado. Usando fallback: {fallback}"
                warnings.append(warning_msg)
                resolved_details.append(f"{item_name}: {fallback} (Fallback)")
                print(f"[LOGISTICS TRIGGER] {warning_msg}", file=sys.stderr)
                
        route_points.append(hq_coords)
        
        # Calcular distância acumulada (km) e tempo (horas) leg-a-leg usando a tabela sul_2po_4pgr
        total_distance_km = 0.0
        total_time_hours = 0.0
        leg_geometries = []
        
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
                coalesce(sum(edge.km), 0.0) as distance_km,
                coalesce(max(rt.agg_cost), 0.0) as time_hours,
                ST_AsGeoJSON(ST_LineMerge(ST_Union(edge.geom_way)))::json as geometry
            FROM pgr_dijkstra(
                FORMAT('SELECT id, source, target, cost, reverse_cost FROM sul_2po_4pgr 
                        WHERE geom_way && ST_Expand(ST_MakeLine(ST_SetSRID(ST_MakePoint(%L, %L), 4326), ST_SetSRID(ST_MakePoint(%L, %L), 4326)), 0.25)',
                       :start_lng, :start_lat, :end_lng, :end_lat),
                (SELECT id FROM start_node),
                (SELECT id FROM end_node),
                true
            ) as rt
            JOIN sul_2po_4pgr as edge ON rt.edge = edge.id;
        """)
        
        for i in range(len(route_points) - 1):
            start = route_points[i]
            end = route_points[i+1]
            
            result = await db.execute(query, {
                "start_lng": start[0],
                "start_lat": start[1],
                "end_lng": end[0],
                "end_lat": end[1]
            })
            
            row = result.one()
            total_distance_km += float(row.distance_km)
            total_time_hours += float(row.time_hours)
            if row.geometry:
                leg_geometries.append(row.geometry)

        # Converter tempo para minutos
        total_time_minutes = int(round(total_time_hours * 60))
        if total_time_minutes == 0 and total_distance_km > 0:
            total_time_minutes = int(round(total_distance_km * 1.5)) # Fallback seguro (1.5 min por km)

        # Gerar URL do Google Maps com os waypoints
        path_str = "/".join([f"{c[1]},{c[0]}" for c in route_points])
        gmaps_url = f"https://www.google.com/maps/dir/{path_str}"
        
        # Consolidação da Geometria da Rota em uma MultiLineString
        multiline_coords = []
        for geom in leg_geometries:
            if not geom:
                continue
            g_type = geom.get("type")
            coords = geom.get("coordinates")
            if g_type == "LineString":
                multiline_coords.append(coords)
            elif g_type == "MultiLineString":
                multiline_coords.extend(coords)
                
        route_geom_geojson = None
        if multiline_coords:
            route_geom_geojson = {
                "type": "MultiLineString",
                "coordinates": multiline_coords
            }

        # Parse da Data da Rota
        route_date_str = payload.get("date") or datetime.date.today().isoformat()
        try:
            route_date = datetime.date.fromisoformat(route_date_str)
        except Exception:
            route_date = datetime.date.today()

        # Persistir no banco de dados
        new_route = LogisticsRoute(
            route_date=route_date,
            driver_name=driver_name,
            driver_phone=driver_data.get("phone"),
            vehicle=driver_data.get("vehicle"),
            total_distance_km=round(total_distance_km, 2),
            total_duration_minutes=total_time_minutes,
            google_maps_url=gmaps_url,
            geom_route=func.ST_GeomFromGeoJSON(json.dumps(route_geom_geojson)) if route_geom_geojson else None
        )
        db.add(new_route)
        await db.flush() # Obter ID autogerado da rota

        stops_to_create = []

        # Parada 1: Origem
        stops_to_create.append(LogisticsRouteStop(
            route_id=new_route.id,
            stop_order=1,
            stop_type="origin",
            item_name=None,
            donor_name=None,
            address=hq_address,
            geom_stop=func.ST_SetSRID(func.ST_MakePoint(hq_coords[0], hq_coords[1]), 4326)
        ))

        # Paradas de Coleta / Entrega
        for idx, p in enumerate(pickups):
            coords = route_points[idx + 1]
            stops_to_create.append(LogisticsRouteStop(
                route_id=new_route.id,
                stop_order=idx + 2,
                stop_type="pickup",
                item_name=p.get("item"),
                donor_name=p.get("donor"),
                address=p.get("address") or "",
                geom_stop=func.ST_SetSRID(func.ST_MakePoint(coords[0], coords[1]), 4326)
            ))

        # Parada Final: Retorno à Origem
        stops_to_create.append(LogisticsRouteStop(
            route_id=new_route.id,
            stop_order=len(pickups) + 2,
            stop_type="return",
            item_name=None,
            donor_name=None,
            address=hq_name,
            geom_stop=func.ST_SetSRID(func.ST_MakePoint(hq_coords[0], hq_coords[1]), 4326)
        ))

        db.add_all(stops_to_create)
        await db.commit()

        print(f"📊 [LOGISTICS TRIGGER] Rota e {len(stops_to_create)} paradas salvas no banco. Distância: {total_distance_km:.2f} km | Tempo: {total_time_minutes} min. GMaps: {gmaps_url}\n", file=sys.stderr)
        
        return {
            "success": True,
            "message": "Rota logística calculada e salva com sucesso no banco de dados!",
            "total_cost": round(total_distance_km, 2),
            "total_cost_label": f"{round(total_distance_km, 1)} km",
            "estimated_time": f"~{total_time_minutes} minutos",
            "google_maps_url": gmaps_url,
            "driver_name": driver_name,
            "warnings": warnings,
            "resolved_details": resolved_details
        }
    except Exception as e:
        print(f"❌ [LOGISTICS TRIGGER] Erro interno: {str(e)}", file=sys.stderr)
        return {
            "success": False,
            "message": f"Erro interno no processamento: {str(e)}"
        }
