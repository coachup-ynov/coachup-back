from functools import lru_cache
from typing import Literal, Self

from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: Literal["local", "test", "staging", "production"] = "local"
    PROJECT_NAME: str = "CoachUp API"
    API_V1_PREFIX: str = "/api/v1"

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "coachup"
    POSTGRES_PASSWORD: str = "coachup"
    POSTGRES_DB: str = "coachup"

    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    # Version des CGU en vigueur : à incrémenter quand le texte change
    TERMS_VERSION: str = "2026-10"

    # Utilisé pour construire les liens envoyés par email
    FRONTEND_URL: str = "http://localhost:4200"

    CORS_ORIGINS: list[str] = ["http://localhost:4200"]

    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    EMAIL_FROM: str = "no-reply@coachup.local"

    @model_validator(mode="after")
    def check_secret_key(self) -> Self:
        if self.ENVIRONMENT in ("staging", "production") and (
            self.SECRET_KEY == "change-me" or len(self.SECRET_KEY) < 32
        ):
            raise ValueError("SECRET_KEY doit être défini (32 caractères minimum) hors local.")
        return self

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
