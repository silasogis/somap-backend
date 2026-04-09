"""
Configura o GeoServer via REST API administrativa (roda na VM, direto no localhost).
Execute após `docker compose up`:
  python scripts/geoserver_setup.py
"""
import httpx, os
from dotenv import load_dotenv

load_dotenv()

GS_URL  = "http://localhost:8080/geoserver"
GS_AUTH = (os.getenv("GEOSERVER_ADMIN_USER", "admin"),
           os.getenv("GEOSERVER_ADMIN_PASSWORD", "geoserver"))

def create_workspace(name: str):
    r = httpx.post(f"{GS_URL}/rest/workspaces", auth=GS_AUTH,
                   json={"workspace": {"name": name}})
    assert r.status_code in (201, 409), f"workspace: {r.status_code} {r.text}"

def create_postgis_datastore(ws: str):
    r = httpx.post(f"{GS_URL}/rest/workspaces/{ws}/datastores", auth=GS_AUTH,
        json={"dataStore": {"name": "somap_postgis", "type": "PostGIS",
            "connectionParameters": {"entry": [
                {"@key": "host",     "$": "db"},
                {"@key": "port",     "$": "5432"},
                {"@key": "database", "$": os.getenv("POSTGRES_DB", "somap")},
                {"@key": "user",     "$": os.getenv("POSTGRES_USER", "somap")},
                {"@key": "passwd",   "$": os.getenv("POSTGRES_PASSWORD", "somap_secret")},
                {"@key": "dbtype",   "$": "postgis"},
                {"@key": "schema",   "$": "public"},
                {"@key": "Expose primary keys", "$": "true"},
            ]}}})
    assert r.status_code in (201, 409), f"datastore: {r.status_code} {r.text}"

def publish_featuretype(ws: str, ds: str, table: str):
    r = httpx.post(
        f"{GS_URL}/rest/workspaces/{ws}/datastores/{ds}/featuretypes",
        auth=GS_AUTH, json={"featureType": {"name": table, "nativeName": table}})
    assert r.status_code in (201, 409), f"featuretype: {r.status_code} {r.text}"

if __name__ == "__main__":
    create_workspace("somap")
    create_postgis_datastore("somap")
    publish_featuretype("somap", "somap_postgis", "layers")
    print("GeoServer configurado.")
