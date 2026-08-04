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
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://forgeops:forgeops_dev@localhost:5432/forgeops"
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"

    # ── LLM providers ─────────────────────────────────────────────────────────
    # Credentials always remain on the server. The UI only receives provider
    # availability and model suggestions, never secret values.
    openai_api_key: SecretStr = Field(default=SecretStr(""), alias="OPENAI_API_KEY")
    anthropic_api_key: SecretStr = Field(default=SecretStr(""), alias="ANTHROPIC_API_KEY")
    groq_api_key: SecretStr = Field(default=SecretStr(""), alias="GROQ_API_KEY")
    openrouter_api_key: SecretStr = Field(default=SecretStr(""), alias="OPENROUTER_API_KEY")

    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL"
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )
    ollama_base_url: str = Field(default="", alias="OLLAMA_BASE_URL")

    # Any service implementing OpenAI-compatible /chat/completions can be added
    # without changing ForgeOps code.
    custom_openai_name: str = Field(
        default="Custom OpenAI-compatible", alias="CUSTOM_OPENAI_NAME"
    )
    custom_openai_base_url: str = Field(default="", alias="CUSTOM_OPENAI_BASE_URL")
    custom_openai_api_key: SecretStr = Field(
        default=SecretStr(""), alias="CUSTOM_OPENAI_API_KEY"
    )

    # Defaults used when an older client creates a mission without an explicit
    # provider/model. New clients select these per mission.
    default_llm_provider: str = Field(default="demo", alias="DEFAULT_LLM_PROVIDER")
    default_llm_model: str = Field(default="forgeops-demo", alias="DEFAULT_LLM_MODEL")

    # Comma-separated suggestions shown in the UI. Users can always type a
    # different valid model ID, so provider model releases require no code change.
    openai_models: str = Field(
        default="gpt-5-mini,gpt-4.1-mini,gpt-4o-mini", alias="OPENAI_MODELS"
    )
    anthropic_models: str = Field(
        default="claude-sonnet-4-20250514,claude-opus-4-20250514",
        alias="ANTHROPIC_MODELS",
    )
    groq_models: str = Field(
        default="openai/gpt-oss-20b,openai/gpt-oss-120b",
        alias="GROQ_MODELS",
    )
    openrouter_models: str = Field(
        default="openrouter/auto", alias="OPENROUTER_MODELS"
    )
    ollama_models: str = Field(default="llama3.2,qwen2.5-coder", alias="OLLAMA_MODELS")
    custom_openai_models: str = Field(default="", alias="CUSTOM_OPENAI_MODELS")

    # Legacy defaults retained for code paths that explicitly request a fast
    # model outside a mission context.
    primary_model: str = "gpt-4o"
    fallback_model: str = "claude-sonnet-4-20250514"
    fast_model: str = "gpt-4o-mini"

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
    default_max_duration_seconds: int = 600

    # ── Sandbox ───────────────────────────────────────────────────────────────
    sandbox_url: str = "http://sandbox:9000"
    sandbox_max_execution_seconds: int = 30
    sandbox_max_memory_mb: int = 256


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
