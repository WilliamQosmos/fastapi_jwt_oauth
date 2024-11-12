import secrets
import warnings
from typing import Literal, Self

from pydantic import (
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from social_core.backends.github import GithubOAuth2
from social_core.backends.google import GoogleOAuth2

from fastapi_oauth2.claims import Claims
from fastapi_oauth2.client import OAuth2Client
from fastapi_oauth2.config import OAuth2Config


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")
    BASE_PATH_PREFIX: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    PROJECT_NAME: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = ""

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0
    REDIS_TTL: int = 60 * 60

    OAUTH2_GITHUB_CLIENT_ID: str | None = None
    OAUTH2_GITHUB_CLIENT_SECRET: str | None = None
    OAUTH2_GOOGLE_CLIENT_ID: str | None = None
    OAUTH2_GOOGLE_CLIENT_SECRET: str | None = None

    OAUTH2_CLIENTS: list[str] = []

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @computed_field
    @property
    def oauth2_config(self) -> OAuth2Config:
        if not self.OAUTH2_GITHUB_CLIENT_ID or not self.OAUTH2_GITHUB_CLIENT_SECRET:
            warnings.warn("No GitHub OAuth2 credentials found. Skipping OAuth2 configuration.")
            return OAuth2Config()
        if not self.OAUTH2_GOOGLE_CLIENT_ID or not self.OAUTH2_GOOGLE_CLIENT_SECRET:
            warnings.warn("No Google OAuth2 credentials found. Skipping OAuth2 configuration.")
            return OAuth2Config()
        config = OAuth2Config(
            enable_ssr=False if self.ENVIRONMENT == "local" or self.ENVIRONMENT == "staging" else True,
            allow_http=True,
            jwt_secret=self.SECRET_KEY,
            jwt_expires=self.ACCESS_TOKEN_EXPIRE_MINUTES,
            jwt_algorithm="HS256",
            clients=[
                OAuth2Client(
                    backend=GithubOAuth2,
                    client_id=self.OAUTH2_GITHUB_CLIENT_ID,
                    client_secret=self.OAUTH2_GITHUB_CLIENT_SECRET,
                    scope=["user:email"],
                    claims=Claims(
                        picture="avatar_url",
                        identity=lambda user: f"{user.provider}:{user.id}",
                    ),
                ),
                OAuth2Client(
                    backend=GoogleOAuth2,
                    client_id=self.OAUTH2_GOOGLE_CLIENT_ID,
                    client_secret=self.OAUTH2_GOOGLE_CLIENT_SECRET,
                    scope=["openid", "profile", "email"],
                    claims=Claims(
                        identity=lambda user: f"{user.provider}:{user.sub}",
                    ),
                ),
            ]
        )
        return config

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", ' "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        return self


def get_settings():
    return Settings()


settings = get_settings()
