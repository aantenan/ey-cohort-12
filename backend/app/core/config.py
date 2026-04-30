from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration: environment, Entra, Redis, Azure, and integration keys."""

    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="EY Cohort 12 API")
    environment: str = Field(default="local")
    debug: bool = Field(default=False)

    api_v1_prefix: str = Field(default="/api/v1")
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)

    cors_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:4200",
            "http://127.0.0.1:4200",
        ],
        description="Allowed CORS origins (Angular dev server on 4200 by default).",
    )

    # Microsoft Entra ID (Azure AD) — JWT validation
    entra_tenant_id: str = Field(
        default="",
        description="Directory (tenant) ID; JWKS and issuer are derived when set.",
    )
    entra_audience: str = Field(
        default="",
        description="Application (client) ID or custom API URI used as `aud` claim.",
    )
    entra_issuer: str = Field(
        default="",
        description="Override token `iss` (default: https://login.microsoftonline.com/{tenant}/v2.0)",
    )

    auth_disabled: bool = Field(
        default=True,
        description=(
            "If true, skip JWT validation and use a synthetic local user. "
            "Set AUTH_DISABLED=false in production."
        ),
    )

    # Data (sync URL for Alembic; async for runtime — same SQLite file in dev)
    database_url_sync: str = Field(
        default="sqlite:///./local.db",
        description="Synchronous DB URL for Alembic migrations.",
    )
    database_url: str = Field(
        default="sqlite+aiosqlite:///./local.db",
        description="Async SQLAlchemy URL for the API runtime.",
    )

    # Redis (set empty to skip connection — tests / no local Redis)
    redis_url: str = Field(
        default="redis://127.0.0.1:6379/0",
        description="Async redis URL; leave empty to disable Redis and the WebSocket pub/sub bridge.",
    )

    # Azure Service Bus
    azure_service_bus_connection_string: str = Field(
        default="",
        description="Connection string for publishing to queues/topics; empty disables sends.",
    )

    # API keys: Key Vault (cloud) or local env
    key_vault_url: str = Field(
        default="",
        description="Azure Key Vault URL; when set, integration keys are loaded via managed identity.",
    )
    key_vault_ivr_secret_name: str = Field(default="integration-ivr-api-key")
    key_vault_chatbot_secret_name: str = Field(default="integration-chatbot-api-key")
    # Local / fallback JSON map: {"ivr":"<hex>","chatbot":"<hex>"}
    integration_api_keys_json: str = Field(default="", alias="INTEGRATION_API_KEYS_JSON")

    # Rate limits (slowapi)
    rate_limit_default: str = Field(default="100/minute")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        parts = [o.strip() for o in str(v).split(",")]
        return [o for o in parts if o]

    @property
    def jwks_url(self) -> str:
        if not self.entra_tenant_id:
            return ""
        return (
            f"https://login.microsoftonline.com/{self.entra_tenant_id}/discovery/v2.0/keys"
        )

    @property
    def expected_issuer(self) -> str:
        if self.entra_issuer:
            return self.entra_issuer.rstrip("/")
        if not self.entra_tenant_id:
            return ""
        return f"https://login.microsoftonline.com/{self.entra_tenant_id}/v2.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
