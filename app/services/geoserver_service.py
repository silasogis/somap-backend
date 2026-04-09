import httpx
from app.config import settings

class GeoServerService:
    def __init__(self):
        self.base_url = settings.geoserver_url
        self.auth = (settings.geoserver_admin_user, settings.geoserver_admin_password)

    def get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(auth=self.auth, base_url=self.base_url)

    async def create_workspace(self, name: str) -> bool:
        async with self.get_client() as client:
            response = await client.post("/rest/workspaces", json={"workspace": {"name": name}})
            return response.status_code in (201, 409)

    async def create_postgis_datastore(self, ws: str, db_name: str, db_user: str, db_pass: str) -> bool:
        async with self.get_client() as client:
            payload = {
                "dataStore": {
                    "name": "somap_postgis", 
                    "type": "PostGIS",
                    "connectionParameters": {
                        "entry": [
                            {"@key": "host", "$": "db"}, 
                            {"@key": "port", "$": "5432"},
                            {"@key": "database", "$": db_name},
                            {"@key": "user", "$": db_user},
                            {"@key": "passwd", "$": db_pass},
                            {"@key": "dbtype", "$": "postgis"},
                            {"@key": "schema", "$": "public"},
                            {"@key": "Expose primary keys", "$": "true"},
                        ]
                    }
                }
            }
            response = await client.post(f"/rest/workspaces/{ws}/datastores", json=payload)
            return response.status_code in (201, 409)

    async def publish_featuretype(self, ws: str, ds: str, table: str) -> bool:
        async with self.get_client() as client:
            payload = {"featureType": {"name": table, "nativeName": table}}
            response = await client.post(f"/rest/workspaces/{ws}/datastores/{ds}/featuretypes", json=payload)
            return response.status_code in (201, 409)

geoserver_service = GeoServerService()
