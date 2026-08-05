"""Regression tests for provider tool-call safety."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from openai import BadRequestError

from forgeops.agent.gateway import ModelGateway, normalize_tool_choice, sanitize_tool_calls

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "repo_browser.open_file",
            "description": "Read a repository file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    }
]


def test_tool_choice_none_is_upgraded_to_auto() -> None:
    assert normalize_tool_choice(TOOLS, "none") == "auto"


def test_tool_choice_defaults_to_auto_when_tools_exist() -> None:
    assert normalize_tool_choice(TOOLS, None) == "auto"


def test_tool_choice_is_removed_without_tools() -> None:
    assert normalize_tool_choice(None, "required") is None


def test_empty_required_tool_argument_is_rejected() -> None:
    calls = [
        {
            "id": "call-1",
            "name": "repo_browser.open_file",
            "arguments": '{"path":""}',
        }
    ]
    assert sanitize_tool_calls(calls, TOOLS) is None


def test_valid_tool_argument_is_normalized() -> None:
    calls = [
        {
            "id": "call-1",
            "name": "repo_browser.open_file",
            "arguments": '{"path":"README.md"}',
        }
    ]
    assert sanitize_tool_calls(calls, TOOLS) == [
        {
            "id": "call-1",
            "name": "repo_browser.open_file",
            "arguments": '{"path":"README.md"}',
        }
    ]


def test_invalid_json_tool_argument_is_rejected() -> None:
    calls = [
        {
            "id": "call-1",
            "name": "repo_browser.open_file",
            "arguments": "not-json",
        }
    ]
    assert sanitize_tool_calls(calls, TOOLS) is None


@pytest.mark.asyncio
async def test_unsolicited_tool_call_error_retries_as_content_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(400, request=request)
    conflict = BadRequestError(
        "Tool choice is none, but model called a tool",
        response=response,
        body={"error": {"message": "Tool choice is none, but model called a tool"}},
    )
    completion = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content='{"ok":true}', tool_calls=None),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=4),
    )
    create = AsyncMock(side_effect=[conflict, completion])
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    gateway = ModelGateway()
    monkeypatch.setattr(gateway, "_get_openai_client", lambda provider: fake_client)

    result = await gateway._openai_compatible_chat(
        provider="groq",
        messages=[{"role": "user", "content": "Return JSON"}],
        model="openai/gpt-oss-20b",
        tools=None,
        tool_choice=None,
        temperature=0.1,
        max_tokens=100,
        response_format={"type": "json_object"},
    )

    assert result.content == '{"ok":true}'
    assert create.await_count == 2
    retry_kwargs = create.await_args_list[1].kwargs
    assert "tools" not in retry_kwargs
    assert "tool_choice" not in retry_kwargs
    assert "Tool calling is unavailable" in retry_kwargs["messages"][0]["content"]
