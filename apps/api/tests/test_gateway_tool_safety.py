"""Regression tests for provider tool-call safety."""
from forgeops.agent.gateway import normalize_tool_choice, sanitize_tool_calls

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
