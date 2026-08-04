"""LLM provider catalog exposed to the Mission Control UI."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from forgeops.config import get_settings

router = APIRouter()


class ModelProvider(BaseModel):
    id: str
    label: str
    configured: bool
    models: list[str]
    default_model: str
    supports_custom_model: bool = True
    configuration_hint: str


class ModelCatalog(BaseModel):
    providers: list[ModelProvider]
    default_provider: str
    default_model: str


def _models(raw: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in raw.split(","):
        model = value.strip()
        if model and model not in seen:
            seen.add(model)
            result.append(model)
    return result


def _has_secret(value: object) -> bool:
    getter = getattr(value, "get_secret_value", None)
    return bool(getter and str(getter()).strip())


@router.get("", response_model=ModelCatalog)
async def list_model_providers() -> ModelCatalog:
    """Return provider availability and editable model suggestions."""
    settings = get_settings()

    providers = [
        ModelProvider(
            id="demo",
            label="Demo simulator",
            configured=True,
            models=["forgeops-demo"],
            default_model="forgeops-demo",
            supports_custom_model=False,
            configuration_hint="No API key required. Simulates the workflow only.",
        ),
        ModelProvider(
            id="openai",
            label="OpenAI",
            configured=_has_secret(settings.openai_api_key),
            models=_models(settings.openai_models),
            default_model=_models(settings.openai_models)[0]
            if _models(settings.openai_models)
            else "",
            configuration_hint="Set OPENAI_API_KEY on the API server.",
        ),
        ModelProvider(
            id="anthropic",
            label="Anthropic / Claude",
            configured=_has_secret(settings.anthropic_api_key),
            models=_models(settings.anthropic_models),
            default_model=_models(settings.anthropic_models)[0]
            if _models(settings.anthropic_models)
            else "",
            configuration_hint="Set ANTHROPIC_API_KEY on the API server.",
        ),
        ModelProvider(
            id="groq",
            label="Groq",
            configured=_has_secret(settings.groq_api_key),
            models=_models(settings.groq_models),
            default_model=_models(settings.groq_models)[0]
            if _models(settings.groq_models)
            else "",
            configuration_hint="Set GROQ_API_KEY on the API server.",
        ),
        ModelProvider(
            id="openrouter",
            label="OpenRouter",
            configured=_has_secret(settings.openrouter_api_key),
            models=_models(settings.openrouter_models),
            default_model=_models(settings.openrouter_models)[0]
            if _models(settings.openrouter_models)
            else "",
            configuration_hint="Set OPENROUTER_API_KEY on the API server.",
        ),
        ModelProvider(
            id="ollama",
            label="Ollama",
            configured=bool(settings.ollama_base_url.strip()),
            models=_models(settings.ollama_models),
            default_model=_models(settings.ollama_models)[0]
            if _models(settings.ollama_models)
            else "",
            configuration_hint=(
                "Set OLLAMA_BASE_URL, for example http://host.docker.internal:11434/v1."
            ),
        ),
        ModelProvider(
            id="custom",
            label=settings.custom_openai_name,
            configured=bool(settings.custom_openai_base_url.strip()),
            models=_models(settings.custom_openai_models),
            default_model=_models(settings.custom_openai_models)[0]
            if _models(settings.custom_openai_models)
            else "",
            configuration_hint=(
                "Set CUSTOM_OPENAI_BASE_URL and, when required, CUSTOM_OPENAI_API_KEY."
            ),
        ),
    ]

    configured_ids = {provider.id for provider in providers if provider.configured}
    default_provider = settings.default_llm_provider.strip().lower()
    if default_provider not in configured_ids:
        default_provider = "demo"

    default_entry = next(provider for provider in providers if provider.id == default_provider)
    default_model = settings.default_llm_model.strip()
    if not default_model or (
        default_entry.models and default_model not in default_entry.models
    ):
        default_model = default_entry.default_model

    return ModelCatalog(
        providers=providers,
        default_provider=default_provider,
        default_model=default_model,
    )
