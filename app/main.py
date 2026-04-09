from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

from app.routers import auth_router, workspaces_router, layers_router

app = FastAPI(title="SOMAP API")

# Usamos um 'if o.strip()' extra como boa prática para evitar parse de commas vazias.
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(workspaces_router)
app.include_router(layers_router)

@app.get("/health")
async def health():
    """Usado pelo tunnel_start.sh para confirmar que a API está pronta."""
    return {"status": "ok"}
