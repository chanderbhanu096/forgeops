"""
OpenTelemetry + Langfuse observability setup.

Instruments:
  - FastAPI HTTP spans (opentelemetry-instrumentation-fastapi)
  - SQLAlchemy query spans
  - Every model gateway call (cost, tokens, latency, provider)
  - Every state machine transition
  - Every verifier pipeline run
  - Every MCP tool call

Langfuse receives LLM-specific traces (prompt, completion, cost).
OTLP receiver (e.g. Grafana Tempo) receives the rest.

When keys are absent the module degrades gracefully —
no tracing rather than a startup failure.
"""
from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# ── OpenTelemetry setup ───────────────────────────────────────────────────────


def setup_otel(service_name: str = "forgeops-api") -> None:
    """
    Configure OpenTelemetry SDK. No-ops gracefully if the SDK is not installed
    or OTEL_EXPORTER_OTLP_ENDPOINT is not set.
    """
    try:
        import os

        from opentelemetry import trace
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if not endpoint:
            log.info("otel_disabled", reason="OTEL_EXPORTER_OTLP_ENDPOINT not set")
            return

        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        resource = Resource(attributes={SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
        trace.set_tracer_provider(provider)
        log.info("otel_enabled", endpoint=endpoint, service=service_name)

    except ImportError:
        log.debug("otel_sdk_not_installed")
    except Exception as exc:
        log.warning("otel_setup_failed", error=str(exc))


def get_tracer(name: str) -> object:
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        return _NoopTracer()


class _NoopTracer:
    @contextmanager
    def start_as_current_span(self, name: str, **_: object) -> Generator[_NoopSpan, None, None]:
        yield _NoopSpan()


class _NoopSpan:
    def set_attribute(self, *_: object) -> None: pass
    def set_status(self, *_: object) -> None: pass
    def record_exception(self, *_: object) -> None: pass


# ── Langfuse LLM tracing ──────────────────────────────────────────────────────


class LangfuseTracer:
    """
    Wraps Langfuse SDK for LLM-specific tracing.
    Degrades to a no-op when keys are absent.
    """

    def __init__(self) -> None:
        self._client: Any = None
        self._enabled = False
        self._setup()

    def _setup(self) -> None:
        try:
            from forgeops.config import get_settings
            settings = get_settings()
            if not settings.langfuse_public_key:
                return

            from langfuse import Langfuse
            self._client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key.get_secret_value(),
                host=settings.langfuse_host,
            )
            self._enabled = True
            log.info("langfuse_enabled", host=settings.langfuse_host)
        except ImportError:
            log.debug("langfuse_not_installed")
        except Exception as exc:
            log.warning("langfuse_setup_failed", error=str(exc))

    def trace_model_call(
        self,
        mission_id: str,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        latency_ms: int,
        handler_name: str,
    ) -> None:
        if not self._enabled or not self._client:
            return
        try:
            self._client.generation(
                trace_id=mission_id,
                name=handler_name,
                model=model,
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_cost": cost_usd,
                },
                metadata={
                    "provider": provider,
                    "latency_ms": latency_ms,
                },
            )
        except Exception as exc:
            log.debug("langfuse_trace_failed", error=str(exc))

    def flush(self) -> None:
        if self._enabled and self._client:
            from contextlib import suppress
            with suppress(Exception):
                self._client.flush()


# ── Singletons ────────────────────────────────────────────────────────────────

_langfuse: LangfuseTracer | None = None


def get_langfuse() -> LangfuseTracer:
    global _langfuse
    if _langfuse is None:
        _langfuse = LangfuseTracer()
    return _langfuse


# ── Instrumentation helpers ───────────────────────────────────────────────────

_tracer = get_tracer("forgeops.agent")


def trace_state_transition(
    mission_id: str,
    from_state: str | None,
    to_state: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Emit a structured log + OTEL span for a state machine transition."""
    log.info(
        "state_transition",
        mission_id=mission_id,
        from_state=from_state,
        to_state=to_state,
        **(metadata or {}),
    )
    with _tracer.start_as_current_span("state_transition") as span:
        span.set_attribute("mission.id", mission_id)
        span.set_attribute("state.from", str(from_state))
        span.set_attribute("state.to", to_state)


def trace_tool_call(
    mission_id: str,
    server: str,
    tool: str,
    duration_ms: int,
    success: bool,
) -> None:
    """Emit a structured log + OTEL span for an MCP tool call."""
    log.info(
        "tool_call",
        mission_id=mission_id,
        server=server,
        tool=tool,
        duration_ms=duration_ms,
        success=success,
    )
    with _tracer.start_as_current_span("mcp_tool_call") as span:
        span.set_attribute("mcp.server", server)
        span.set_attribute("mcp.tool", tool)
        span.set_attribute("mcp.duration_ms", duration_ms)
        span.set_attribute("mcp.success", success)


def trace_verification(
    pipeline: str,
    passed: bool,
    critical_count: int,
    high_count: int,
    total_findings: int,
) -> None:
    """Emit a structured log + OTEL span for a verification pipeline run."""
    log.info(
        "verification_complete",
        pipeline=pipeline,
        passed=passed,
        critical=critical_count,
        high=high_count,
        total_findings=total_findings,
    )
    with _tracer.start_as_current_span("verification_pipeline") as span:
        span.set_attribute("verification.pipeline", pipeline)
        span.set_attribute("verification.passed", passed)
        span.set_attribute("verification.critical", critical_count)
        span.set_attribute("verification.high", high_count)
