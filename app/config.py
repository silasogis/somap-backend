from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    geoserver_url: str
    geoserver_admin_user: str
    geoserver_admin_password: str
    cors_origins: str
    api_public_url: str = ""
    geo_public_url: str = ""

settings = Settings()
