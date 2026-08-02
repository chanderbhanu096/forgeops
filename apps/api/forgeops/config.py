"""Application settings loaded from environment variables."""
from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    development = "development"
    staging = "staging"
    production = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    # ── Runtime ───────────────────────────────────────────────────────────────
    environment: Environment = Environment.development
    log_level: str = "INFO"
    sql_echo: bool = Field(default=False, alias="SQL_ECHO")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://forgeops:forgeops_dev@localhost:5432/forgeops"
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"

    # ── LLM providers ─────────────────────────────────────────────────────────
    openai_api_key: SecretStr = Field(default=SecretStr(""))
    anthropic_api_key: SecretStr = Field(default=SecretStr(""))

    # Default model routing
    primary_model: str = "gpt-4o"
    fallback_model: str = "claude-3-5-sonnet-20241022"
    fast_model: str = "gpt-4o-mini"        # used for classification, routing

    # ── MCP ───────────────────────────────────────────────────────────────────
    mcp_secret: SecretStr = Field(default=SecretStr("forgeops_mcp_dev"))
    mcp_github_url: str = "http://mcp-github:8001"
    mcp_data_url: str = "http://mcp-data:8002"
    mcp_knowledge_url: str = "http://mcp-knowledge:8003"

    # ── GitHub ────────────────────────────────────────────────────────────────
    github_token: SecretStr = Field(default=SecretStr(""))

    # ── Observability ─────────────────────────────────────────────────────────
    langfuse_public_key: str = ""
    langfuse_secret_key: SecretStr = Field(default=SecretStr(""))
    langfuse_host: str = "https://cloud.langfuse.com"

    # ── Agent budgets (defaults) ──────────────────────────────────────────────
    default_max_steps: int = 50
    default_max_cost_usd: float = 2.0
    default_max_duration_seconds: int = 600   # 10 min

    # ── Sandbox ───────────────────────────────────────────────────────────────
    sandbox_url: str = "http://sandbox:9000"
    sandbox_max_execution_seconds: int = 30
    sandbox_max_memory_mb: int = 256


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
