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

async def seed():
    async with AsyncSessionLocal() as session:
        session.add(Workspace(
            id="ws-sul", name="Sul e Sudeste", slug="sul-sudeste",
            description="Dados para região Sul e Sudeste do Brasil"
        ))
        
        session.add(User(
            id="user-admin", name="Administrador", email="admin@somap.local",
            hashed_password=hash_password("somap@2025"), role=UserRole.admin
        ))
        for data in LAYERS_SEED:
            session.add(Layer(**data, workspace_id="ws-sul"))
        await session.commit()
    print("Seed concluído e banco populado.")

if __name__ == "__main__":
    asyncio.run(seed())
