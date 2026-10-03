from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Podemos Peru API"
    environment: str = "development"
    debug: bool = True

    database_url: str = "postgresql+psycopg://podemos:podemos@localhost:5432/podemos_peru"

    secret_key: str = "cambia-esta-clave-en-produccion"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 720

    cors_origins: str = "http://localhost:5173"

    seed_on_startup: bool = True
    admin_username: str = "admin"
    admin_password: str = "admin123"

    apisperu_token: str = ""
    apisperu_base_url: str = "https://dniruc.apisperu.com/api/v1"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
