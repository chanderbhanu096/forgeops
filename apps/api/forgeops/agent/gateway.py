"""
Model Gateway — provider-independent LLM interface with cost tracking,
fallback routing and structured tool calling.
"""
from __future__ import annotations

import time
from typing import Any

import structlog
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from forgeops.config import get_settings

log = structlog.get_logger(__name__)

# ── Cost table (USD per 1k tokens) ───────────────────────────────────────────
# Update periodically. Used for budget tracking only — not invoicing.
_COST_PER_1K: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 0.0025, "output": 0.010},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
}


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = _COST_PER_1K.get(model, {"input": 0.003, "output": 0.015})
    return (prompt_tokens / 1000) * rates["input"] + (completion_tokens / 1000) * rates["output"]


# ── Gateway ───────────────────────────────────────────────────────────────────


class ModelGateway:
    """
    Wraps OpenAI and Anthropic. Tries the primary model; falls back to
    the secondary provider on rate-limit or server errors.

    All calls return a uniform ModelResponse so callers are decoupled from
    the underlying provider.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self._openai = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value()
        )
        _anthropic_key = settings.anthropic_api_key.get_secret_value()
        self._anthropic: AsyncAnthropic | None = (
            AsyncAnthropic(api_key=_anthropic_key) if _anthropic_key else None
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
        _handler: str = "unknown",
    ) -> "ModelResponse":
        model = model or self._settings.primary_model
        t0 = time.monotonic()

        try:
            response = await self._openai_chat(
                messages=messages,
                model=model,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
            latency_ms = int((time.monotonic() - t0) * 1000)
            log.debug("model_call", model=model, latency_ms=latency_ms, cost_usd=response.cost_usd)
            self._emit_trace(response, latency_ms, _handler)
            return response

        except Exception as primary_err:
            if self._anthropic is None:
                raise

            log.warning(
                "primary_model_failed_fallback",
                model=model,
                error=str(primary_err),
                fallback=self._settings.fallback_model,
            )
            response = await self._anthropic_chat(
                messages=messages,
                model=self._settings.fallback_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            latency_ms = int((time.monotonic() - t0) * 1000)
            self._emit_trace(response, latency_ms, _handler)
            return response

    def _emit_trace(self, response: "ModelResponse", latency_ms: int, handler: str) -> None:
        """Fire-and-forget Langfuse trace. Never raises."""
        try:
            from forgeops.observability import get_langfuse
            get_langfuse().trace_model_call(
                mission_id="gateway",
                model=response.model,
                provider=response.provider,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                cost_usd=response.cost_usd,
                latency_ms=latency_ms,
                handler_name=handler,
            )
        except Exception:
            pass

    async def fast_chat(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> "ModelResponse":
        """Use the fast/cheap model for classification and routing tasks."""
        return await self.chat(messages, model=self._settings.fast_model, **kwargs)

    # ── OpenAI ────────────────────────────────────────────────────────────────

    async def _openai_chat(
        self,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None,
        tool_choice: str | None,
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any] | None,
    ) -> "ModelResponse":
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice
        if response_format:
            kwargs["response_format"] = response_format

        completion = await self._openai.chat.completions.create(**kwargs)
        choice = completion.choices[0]
        usage = completion.usage

        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        cost = _estimate_cost(model, prompt_tokens, completion_tokens)

        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
                for tc in choice.message.tool_calls
            ]

        return ModelResponse(
            content=choice.message.content or "",
            tool_calls=tool_calls,
            model=model,
            provider="openai",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            finish_reason=choice.finish_reason or "stop",
        )

    # ── Anthropic ─────────────────────────────────────────────────────────────

    async def _anthropic_chat(
        self,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> "ModelResponse":
        assert self._anthropic is not None

        # Convert OpenAI message format to Anthropic format
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        system_text = "\n\n".join(system_parts) if system_parts else None
        anthropic_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m["role"] != "system"
        ]

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_text:
            kwargs["system"] = system_text

        completion = await self._anthropic.messages.create(**kwargs)
        content = "".join(
            block.text for block in completion.content if hasattr(block, "text")
        )
        usage = completion.usage
        cost = _estimate_cost(model, usage.input_tokens, usage.output_tokens)

        return ModelResponse(
            content=content,
            tool_calls=None,
            model=model,
            provider="anthropic",
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            cost_usd=cost,
            finish_reason=completion.stop_reason or "stop",
        )


# ── Response DTO ──────────────────────────────────────────────────────────────


class ModelResponse:
    __slots__ = (
        "content",
        "tool_calls",
        "model",
        "provider",
        "prompt_tokens",
        "completion_tokens",
        "cost_usd",
        "finish_reason",
    )

    def __init__(
        self,
        content: str,
        tool_calls: list[dict[str, Any]] | None,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        finish_reason: str,
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls
        self.model = model
        self.provider = provider
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.cost_usd = cost_usd
        self.finish_reason = finish_reason

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)

    def first_tool_call(self) -> dict[str, Any] | None:
        return self.tool_calls[0] if self.tool_calls else None

    def __repr__(self) -> str:
        return (
            f"ModelResponse(model={self.model!r}, provider={self.provider!r}, "
            f"cost_usd={self.cost_usd:.4f}, tokens={self.prompt_tokens}+{self.completion_tokens})"
        )
