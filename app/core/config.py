from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # mysql+pymysql://usuario:clave@host:3306/edutrack  (en AWS: endpoint de RDS)
    # Por defecto SQLite para correr rápido en local sin MySQL.
    database_url: str = "sqlite:///./edutrack.db"
    jwt_secret: str = "cambia-esto-en-produccion"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 480  # 8 horas de sesión (TB4, HU01)
    ml_service_url: str = "http://localhost:8001"
    cors_origins: str = "http://localhost:5173"
    seed_default_password: str = ""

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
