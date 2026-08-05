"""Provider-independent LLM gateway with safe mission-scoped tool calling."""
from __future__ import annotations

import json
import time
from typing import Any

import structlog
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI, BadRequestError

from forgeops.agent.model_selection import get_model_selection
from forgeops.config import get_settings

log = structlog.get_logger(__name__)

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


def normalize_tool_choice(
    tools: list[dict[str, Any]] | None,
    tool_choice: str | None,
) -> str | None:
    """Return a provider-safe tool choice.

    A tool-enabled request must never send ``none``. Some OpenAI-compatible
    providers reject that combination after the model emits a tool call.
    """
    if not tools:
        return None
    normalized = (tool_choice or "auto").strip().lower()
    if normalized in {"", "none"}:
        return "auto"
    if normalized not in {"auto", "required"}:
        log.warning("unsupported_tool_choice", value=normalized)
        return "auto"
    return normalized


def _tool_specs(tools: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    for tool in tools or []:
        function = tool.get("function")
        if tool.get("type") != "function" or not isinstance(function, dict):
            continue
        name = function.get("name")
        if isinstance(name, str) and name:
            specs[name] = function
    return specs


def sanitize_tool_calls(
    calls: list[dict[str, Any]] | None,
    tools: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    """Drop malformed calls before they reach a tool executor."""
    if not calls:
        return None
    specs = _tool_specs(tools)
    safe: list[dict[str, Any]] = []
    for call in calls:
        name = str(call.get("name", "")).strip()
        raw_arguments = call.get("arguments", "{}")
        try:
            arguments = (
                json.loads(raw_arguments)
                if isinstance(raw_arguments, str)
                else raw_arguments
            )
        except (TypeError, json.JSONDecodeError):
            log.warning("invalid_tool_arguments_json", tool=name)
            continue
        if not name or not isinstance(arguments, dict):
            log.warning("invalid_tool_call_shape", tool=name)
            continue

        function = specs.get(name, {})
        parameters = function.get("parameters", {})
        required = parameters.get("required", []) if isinstance(parameters, dict) else []
        missing = [
            key
            for key in required
            if key not in arguments
            or arguments[key] is None
            or (isinstance(arguments[key], str) and not arguments[key].strip())
        ]
        if missing:
            log.warning("tool_call_missing_required_arguments", tool=name, missing=missing)
            continue

        safe.append(
            {
                "id": str(call.get("id", "")),
                "name": name,
                "arguments": json.dumps(arguments, separators=(",", ":")),
            }
        )
    return safe or None


def _is_tool_choice_conflict(exc: BadRequestError) -> bool:
    message = str(exc).lower()
    return "tool choice is none" in message or (
        "tool_choice" in message and "tool" in message and "none" in message
    )


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

        safe_choice = normalize_tool_choice(tools, tool_choice)
        t0 = time.monotonic()
        if provider == "anthropic":
            response = await self._anthropic_chat(
                messages=messages,
                model=resolved_model,
                tools=tools,
                tool_choice=safe_choice,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            response = await self._openai_compatible_chat(
                provider=provider,
                messages=messages,
                model=resolved_model,
                tools=tools,
                tool_choice=safe_choice,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )

        response.tool_calls = sanitize_tool_calls(response.tool_calls, tools)
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
                raise RuntimeError("OLLAMA_BASE_URL is not configured.")
        elif provider == "custom":
            base_url = settings.custom_openai_base_url.strip()
            api_key = settings.custom_openai_api_key.get_secret_value().strip()
            if not base_url:
                raise RuntimeError("CUSTOM_OPENAI_BASE_URL is not configured.")
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
            kwargs["tool_choice"] = tool_choice or "auto"
        if response_format:
            kwargs["response_format"] = response_format

        try:
            completion = await client.chat.completions.create(**kwargs)
        except BadRequestError as exc:
            if not tools or not _is_tool_choice_conflict(exc):
                raise
            log.warning("tool_choice_conflict_recovered", provider=provider, model=model)
            kwargs["tool_choice"] = "auto"
            completion = await client.chat.completions.create(**kwargs)

        choice = completion.choices[0]
        usage = completion.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        calls = None
        if choice.message.tool_calls:
            calls = [
                {
                    "id": call.id,
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                }
                for call in choice.message.tool_calls
            ]
        return ModelResponse(
            content=choice.message.content or "",
            tool_calls=calls,
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=_estimate_cost(model, prompt_tokens, completion_tokens),
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
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [m for m in messages if m["role"] != "system"],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_parts:
            kwargs["system"] = "\n\n".join(system_parts)
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
            kwargs["tool_choice"] = {
                "type": "any" if tool_choice == "required" else "auto"
            }
        completion = await client.messages.create(**kwargs)
        content_parts: list[str] = []
        calls: list[dict[str, Any]] = []
        for block in completion.content:
            block_type = getattr(block, "type", "")
            if block_type == "text" and hasattr(block, "text"):
                content_parts.append(block.text)
            elif block_type == "tool_use":
                calls.append(
                    {
                        "id": str(getattr(block, "id", "")),
                        "name": str(getattr(block, "name", "")),
                        "arguments": json.dumps(getattr(block, "input", {})),
                    }
                )
        usage = completion.usage
        return ModelResponse(
            content="".join(content_parts),
            tool_calls=calls or None,
            model=model,
            provider="anthropic",
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            cost_usd=_estimate_cost(model, usage.input_tokens, usage.output_tokens),
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
