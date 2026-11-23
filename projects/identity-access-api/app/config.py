from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./identity_access.db"
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "identity-access-api"
    jwt_audience: str = "identity-access-client"
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_days: int = Field(default=7, ge=1, le=30)

    @field_validator("jwt_algorithm")
    @classmethod
    def only_allow_hs256(cls, value: str) -> str:
        if value != "HS256":
            raise ValueError("This project currently supports HS256 only.")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
