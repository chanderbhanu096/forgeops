"""
Provider-independent LLM gateway with mission-scoped model routing.

Supported providers:
- OpenAI
- Anthropic
- Groq (OpenAI-compatible)
- OpenRouter (OpenAI-compatible)
- Ollama (OpenAI-compatible endpoint)
- Any custom OpenAI-compatible endpoint
"""
from __future__ import annotations

import json
import time
from typing import Any

import structlog
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from forgeops.agent.model_selection import get_model_selection
from forgeops.config import get_settings

log = structlog.get_logger(__name__)

# Approximate prices used only for mission budget estimates. Unknown models use
# a conservative fallback and should not be treated as provider billing data.
_COST_PER_1K: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 0.0025, "output": 0.010},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4.1-mini": {"input": 0.0004, "output": 0.0016},
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "claude-opus-4-20250514": {"input": 0.015, "output": 0.075},
}


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = _COST_PER_1K.get(model, {"input": 0.003, "output": 0.015})
    return (prompt_tokens / 1000) * rates["input"] + (
        completion_tokens / 1000
    ) * rates["output"]


class ModelGateway:
    """Route model calls to the provider selected for the current mission."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._openai_clients: dict[str, AsyncOpenAI] = {}
        self._anthropic_client: AsyncAnthropic | None = None

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
    ) -> ModelResponse:
        selection = get_model_selection()
        provider = (
            selection.provider
            if selection is not None
            else self._settings.default_llm_provider
        ).strip().lower()
        resolved_model = model or (
            selection.model
            if selection is not None
            else self._settings.default_llm_model
        )

        if provider == "demo":
            raise RuntimeError(
                "The demo provider does not perform model calls. "
                "Select a configured LLM provider for real execution."
            )

        t0 = time.monotonic()
        if provider == "anthropic":
            response = await self._anthropic_chat(
                messages=messages,
                model=resolved_model,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            response = await self._openai_compatible_chat(
                provider=provider,
                messages=messages,
                model=resolved_model,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )

        latency_ms = int((time.monotonic() - t0) * 1000)
        log.debug(
            "model_call",
            provider=provider,
            model=resolved_model,
            latency_ms=latency_ms,
            cost_usd=response.cost_usd,
        )
        self._emit_trace(response, latency_ms, _handler)
        return response

    async def fast_chat(
        self,
        messages: list[dict[str, Any]],
        **kwargs: object,
    ) -> ModelResponse:
        """Use the mission-selected model, including for classification tasks."""
        selection = get_model_selection()
        if selection is not None:
            return await self.chat(messages, **kwargs)
        return await self.chat(messages, model=self._settings.fast_model, **kwargs)

    def _get_openai_client(self, provider: str) -> AsyncOpenAI:
        cached = self._openai_clients.get(provider)
        if cached is not None:
            return cached

        settings = self._settings
        base_url: str | None = None
        api_key = ""
        default_headers: dict[str, str] | None = None

        if provider == "openai":
            api_key = settings.openai_api_key.get_secret_value().strip()
        elif provider == "groq":
            api_key = settings.groq_api_key.get_secret_value().strip()
            base_url = settings.groq_base_url
        elif provider == "openrouter":
            api_key = settings.openrouter_api_key.get_secret_value().strip()
            base_url = settings.openrouter_base_url
            default_headers = {
                "HTTP-Referer": "https://github.com/chanderbhanu096/forgeops",
                "X-Title": "ForgeOps AI",
            }
        elif provider == "ollama":
            base_url = settings.ollama_base_url.strip()
            api_key = "ollama"
            if not base_url:
                raise RuntimeError(
                    "OLLAMA_BASE_URL is not configured for the Ollama provider."
                )
        elif provider == "custom":
            base_url = settings.custom_openai_base_url.strip()
            api_key = settings.custom_openai_api_key.get_secret_value().strip()
            if not base_url:
                raise RuntimeError(
                    "CUSTOM_OPENAI_BASE_URL is not configured for the custom provider."
                )
            # Some local OpenAI-compatible servers do not require authentication.
            api_key = api_key or "not-required"
        else:
            raise RuntimeError(f"Unsupported LLM provider: {provider}")

        if not api_key:
            env_name = {
                "openai": "OPENAI_API_KEY",
                "groq": "GROQ_API_KEY",
                "openrouter": "OPENROUTER_API_KEY",
            }.get(provider, "API key")
            raise RuntimeError(f"{env_name} is not configured.")

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url.rstrip("/")
        if default_headers:
            client_kwargs["default_headers"] = default_headers

        client = AsyncOpenAI(**client_kwargs)
        self._openai_clients[provider] = client
        return client

    def _get_anthropic_client(self) -> AsyncAnthropic:
        if self._anthropic_client is not None:
            return self._anthropic_client

        api_key = self._settings.anthropic_api_key.get_secret_value().strip()
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

        self._anthropic_client = AsyncAnthropic(api_key=api_key)
        return self._anthropic_client

    async def _openai_compatible_chat(
        self,
        provider: str,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None,
        tool_choice: str | None,
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any] | None,
    ) -> ModelResponse:
        client = self._get_openai_client(provider)
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

        completion = await client.chat.completions.create(**kwargs)
        choice = completion.choices[0]
        usage = completion.usage

        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        cost = _estimate_cost(model, prompt_tokens, completion_tokens)

        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = [
                {
                    "id": call.id,
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                }
                for call in choice.message.tool_calls
            ]

        return ModelResponse(
            content=choice.message.content or "",
            tool_calls=tool_calls,
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            finish_reason=choice.finish_reason or "stop",
        )

    async def _anthropic_chat(
        self,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None,
        tool_choice: str | None,
        temperature: float,
        max_tokens: int,
    ) -> ModelResponse:
        client = self._get_anthropic_client()
        system_parts = [str(m["content"]) for m in messages if m["role"] == "system"]
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
        if tools:
            kwargs["tools"] = [
                {
                    "name": tool["function"]["name"],
                    "description": tool["function"].get("description", ""),
                    "input_schema": tool["function"].get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                }
                for tool in tools
                if tool.get("type") == "function" and "function" in tool
            ]
        if tool_choice:
            if tool_choice == "required":
                kwargs["tool_choice"] = {"type": "any"}
            elif tool_choice == "auto":
                kwargs["tool_choice"] = {"type": "auto"}

        completion = await client.messages.create(**kwargs)
        content_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for block in completion.content:
            block_type = getattr(block, "type", "")
            if block_type == "text" and hasattr(block, "text"):
                content_parts.append(block.text)
            elif block_type == "tool_use":
                tool_calls.append(
                    {
                        "id": str(getattr(block, "id", "")),
                        "name": str(getattr(block, "name", "")),
                        "arguments": json.dumps(getattr(block, "input", {})),
                    }
                )

        usage = completion.usage
        cost = _estimate_cost(model, usage.input_tokens, usage.output_tokens)
        return ModelResponse(
            content="".join(content_parts),
            tool_calls=tool_calls or None,
            model=model,
            provider="anthropic",
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            cost_usd=cost,
            finish_reason=completion.stop_reason or "stop",
        )

    def _emit_trace(self, response: ModelResponse, latency_ms: int, handler: str) -> None:
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
