import asyncio, os
from dotenv import load_dotenv

load_dotenv()

from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.workspace import Workspace
from app.models.layer import Layer
from app.services.auth_service import hash_password

GEO_URL = os.getenv("GEO_PUBLIC_URL", "http://localhost:8080")

LAYERS_SEED = [
    {
        "id": "osm-base", "name": "OpenStreetMap", "type": "xyz",
        "visible": True, "opacity": 1.0, "z_index": 0,
        "source": {"url": "https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png"},
        "attribution": "© OpenStreetMap contributors",
    },
    {
        "id": "ibge-municipios", "name": "Municípios — IBGE", "type": "wms",
        "visible": True, "opacity": 0.7, "z_index": 10,
        "source": {
            "url": "https://geoservicos.ibge.gov.br/geoserver/wms",
            "layers": "CCAR:BC250_Municipio_A",
            "params": {"FORMAT": "image/png", "TRANSPARENT": "TRUE"},
        },
        "attribution": "© IBGE",
    },
    {
        "id": "ibge-rodovias", "name": "Rodovias — IBGE", "type": "wms",
        "visible": False, "opacity": 1.0, "z_index": 20,
        "source": {
            "url": "https://geoservicos.ibge.gov.br/geoserver/wms",
            "layers": "CCAR:BC250_Trecho_Rodoviario_L",
            "params": {"FORMAT": "image/png", "TRANSPARENT": "TRUE"},
        },
        "attribution": "© IBGE",
    },
    {
        "id": "somap-layers", "name": "Camadas SOMAP (GeoServer)", "type": "wms",
        "visible": False, "opacity": 1.0, "z_index": 30,
        "source": {
            "url": f"{GEO_URL}/geoserver/somap/wms",
            "layers": "somap:layers",
            "params": {"FORMAT": "image/png", "TRANSPARENT": "TRUE"},
        },
        "attribution": "© SOMAP",
    },
]

LOGISTICS_LAYERS = [
    {
        "id": "osm-base-logistics", "name": "OpenStreetMap", "type": "xyz",
        "visible": True, "opacity": 1.0, "z_index": 0,
        "source": {"url": "https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png"},
        "attribution": "© OpenStreetMap contributors",
        "basemap": True
    },
    {
        "id": "logistics-routes-layer", "name": "Rotas Otimizadas", "type": "wms",
        "visible": True, "opacity": 0.9, "z_index": 10,
        "source": {
            "url": f"{GEO_URL}/geoserver/somap/wms",
            "layers": "somap:logistics_routes",
            "params": {"FORMAT": "image/png", "TRANSPARENT": "TRUE"},
        },
        "attribution": "© SOMAP Logistics",
        "basemap": False
    },
    {
        "id": "logistics-stops-layer", "name": "Pontos de Coleta/Entrega", "type": "wms",
        "visible": True, "opacity": 1.0, "z_index": 20,
        "source": {
            "url": f"{GEO_URL}/geoserver/somap/wms",
            "layers": "somap:logistics_route_stops",
            "params": {"FORMAT": "image/png", "TRANSPARENT": "TRUE"},
        },
        "attribution": "© SOMAP Logistics",
        "basemap": False
    }
]

async def seed():
    async with AsyncSessionLocal() as session:
        from sqlalchemy.future import select
        
        # 1. Verificar/Inserir Workspace ws-sul
        res_ws_sul = await session.execute(select(Workspace).where(Workspace.id == "ws-sul"))
        if not res_ws_sul.scalar_one_or_none():
            session.add(Workspace(
                id="ws-sul", name="Sul e Sudeste", slug="sul-sudeste",
                description="Dados para região Sul e Sudeste do Brasil"
            ))
            print("Workspace ws-sul cadastrado.")
            for data in LAYERS_SEED:
                session.add(Layer(**data, workspace_id="ws-sul"))
        
        # 2. Verificar/Inserir Usuário Admin
        res_user = await session.execute(select(User).where(User.id == "user-admin"))
        if not res_user.scalar_one_or_none():
            session.add(User(
                id="user-admin", name="Administrador", email="admin@somap.local",
                hashed_password=hash_password("somap@2025"), role=UserRole.admin
            ))
            print("Usuário Admin cadastrado.")

        # 3. Verificar/Inserir Workspace ws-logistics
        res_ws_logistics = await session.execute(select(Workspace).where(Workspace.id == "ws-logistics"))
        if not res_ws_logistics.scalar_one_or_none():
            session.add(Workspace(
                id="ws-logistics", name="Logística & Despacho", slug="logistica",
                description="Operação e logística de rotas"
            ))
            print("Workspace ws-logistics cadastrado.")
            
            # Adicionar as camadas de Logística
            for data in LOGISTICS_LAYERS:
                session.add(Layer(**data, workspace_id="ws-logistics"))
            print("Camadas de Logística cadastradas.")

        # 4. Verificar/Inserir Usuário cristolandia
        res_user_cristolandia = await session.execute(select(User).where(User.id == "cristolandia"))
        existing_user = res_user_cristolandia.scalar_one_or_none()
        if not existing_user:
            session.add(User(
                id="cristolandia", name="Cristolândia", email="cristolandia@somap.map",
                hashed_password=hash_password("cristolandia@2025"), role=UserRole.viewer
            ))
            print("Usuário cristolandia cadastrado.")
        else:
            existing_user.email = "cristolandia@somap.map"
            existing_user.role = UserRole.viewer
            existing_user.hashed_password = hash_password("cristolandia@2025")
            print("Usuário cristolandia atualizado para viewer com nova senha.")

        # 5. Verificar/Inserir Workspace cristolandia
        res_ws_cristolandia = await session.execute(select(Workspace).where(Workspace.id == "cristolandia"))
        if not res_ws_cristolandia.scalar_one_or_none():
            session.add(Workspace(
                id="cristolandia", name="Cristolândia", slug="cristolandia",
                description="Workspace da Cristolândia"
            ))
            print("Workspace cristolandia cadastrado.")

        await session.commit()

        # 6. Vincular usuário cristolandia ao workspace cristolandia (se ainda não vinculado)
        from app.models.workspace import user_workspace_association
        res_assoc = await session.execute(
            select(1).select_from(user_workspace_association).where(
                user_workspace_association.c.user_id == "cristolandia",
                user_workspace_association.c.workspace_id == "cristolandia"
            )
        )
        if not res_assoc.scalar():
            await session.execute(
                user_workspace_association.insert().values(
                    user_id="cristolandia",
                    workspace_id="cristolandia"
                )
            )
            await session.commit()
            print("Usuário cristolandia vinculado ao workspace cristolandia.")

    print("Seed concluído e banco populado.")

if __name__ == "__main__":
    asyncio.run(seed())

