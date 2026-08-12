from __future__ import annotations

import json
from pathlib import Path

from codex_monitor.sources.codex.parser import CodexEventParser


def records() -> list:
    parser = CodexEventParser("fixture")
    path = Path(__file__).parent / "fixtures" / "rollout-basic.jsonl"
    return [item for line in path.read_bytes().splitlines() if (item := parser.parse_line(line))]


def test_normalizes_session_models_prompts_tools_tokens_and_mcp() -> None:
    parsed = records()
    assert parsed[-1].session.session_id == "session-test-1"
    assert parsed[-1].session.model == "gpt-test-codex-2"
    assert [item.prompt for item in parsed if item.prompt] == ["Build a safe parser"]
    calls = [item.tool_call for item in parsed if item.tool_call]
    assert {(call.name, call.kind, call.server) for call in calls} == {
        ("exec_command", "function", None), ("read_file", "mcp", "filesystem")
    }
    usage = next(item.token_usage for item in parsed if item.token_usage)
    assert usage.cached_input_tokens == 40 and usage.context_window == 200000


def test_compaction_file_activity_and_unknown_retention() -> None:
    parsed = records()
    assert any(item.event.subtype == "compaction" for item in parsed)
    assert ("/tmp/example-project/new.py", "created", "patch_apply_end") in [
        activity for item in parsed for activity in item.file_activity
    ]
    assert parsed[-1].event.unsupported and parsed[-1].raw_unknown is not None


def test_corrupt_record_does_not_crash() -> None:
    parser = CodexEventParser("bad")
    assert parser.parse_line(b"{broken") is None


def test_reasoning_content_is_not_normalized() -> None:
    parser = CodexEventParser("reasoning")
    parser.session.session_id = "s"
    raw = {"timestamp": "now", "type": "response_item", "payload": {"type": "reasoning", "encrypted_content": "private", "summary": ["exposed"]}}
    parsed = parser.parse_line(json.dumps(raw).encode())
    assert parsed and parsed.event.data == {"summary_exposed": True}
    assert "private" not in json.dumps(parsed.event.data)


def test_visible_assistant_message_is_normalized() -> None:
    parser = CodexEventParser("assistant")
    parser.session.session_id = "s"
    raw = {"timestamp": "now", "type": "event_msg",
           "payload": {"type": "item_completed", "item": {
               "type": "AgentMessage", "phase": "final_answer",
               "content": [{"type": "text", "text": "Tests now pass."}],
           }}}
    parsed = parser.parse_line(json.dumps(raw).encode())
    assert parsed and parsed.assistant_message == "Tests now pass."
    assert parsed.event.data["phase"] == "final_answer"
