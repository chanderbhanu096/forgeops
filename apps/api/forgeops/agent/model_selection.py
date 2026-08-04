"""Mission-scoped LLM provider and model selection."""
from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelSelection:
    provider: str
    model: str


_current_selection: ContextVar[ModelSelection | None] = ContextVar(
    "forgeops_model_selection",
    default=None,
)


def get_model_selection() -> ModelSelection | None:
    """Return the provider/model selected for the current mission task."""
    return _current_selection.get()


def set_model_selection(provider: str, model: str) -> Token[ModelSelection | None]:
    """Set provider/model for the current async context and return a reset token."""
    return _current_selection.set(ModelSelection(provider=provider, model=model))


def reset_model_selection(token: Token[ModelSelection | None]) -> None:
    """Restore the previous model selection."""
    _current_selection.reset(token)
