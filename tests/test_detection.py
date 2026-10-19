import json
from pathlib import Path

import pytest

from agent_handoff.detection import (
    SessionFormatError,
    SessionFormatKind,
    detect_session_format,
    resolve_parser_agent,
)
from agent_handoff.pipeline import convert_file

FIXTURES = Path(__file__).parent / "fixtures"


def test_detect_opencode_export():
    raw = (FIXTURES / "opencode_min.json").read_text()
    d = detect_session_format(FIXTURES / "opencode_min.json", raw)
    assert d.kind == SessionFormatKind.OPENCODE_EXPORT
    assert d.parser_agent == "opencode"
    assert d.signature == "info+messages+parts"
    assert d.version and "export" in d.version


def test_detect_codex_rollout():
    raw = (FIXTURES / "codex_min.jsonl").read_text()
    d = detect_session_format(FIXTURES / "codex_min.jsonl", raw)
    assert d.kind == SessionFormatKind.CODEX_ROLLOUT
    assert d.parser_agent == "codex"
    assert "session_meta" in d.signature


def test_detect_generic_markdown():
    raw = (FIXTURES / "handoff.md").read_text()
    d = detect_session_format(FIXTURES / "handoff.md", raw)
    assert d.kind == SessionFormatKind.GENERIC_MARKDOWN
    assert d.parser_agent == "cline"


def test_detect_generic_chat_json():
    raw = (FIXTURES / "chat_min.json").read_text()
    d = detect_session_format(FIXTURES / "chat_min.json", raw)
    assert d.kind == SessionFormatKind.GENERIC_CHAT_JSON
    assert d.parser_agent == "cline"


def test_detect_unknown():
    raw = (FIXTURES / "unknown.json").read_text()
    d = detect_session_format(FIXTURES / "unknown.json", raw)
    assert d.kind == SessionFormatKind.UNKNOWN
    assert not d.recognized


def test_detect_empty_file():
    d = detect_session_format(FIXTURES / "empty.txt", "")
    assert not d.recognized


def test_auto_convert_unknown_raises():
    with pytest.raises(SessionFormatError, match="not recognized"):
        convert_file("auto", "codex", FIXTURES / "unknown.json")


def test_explicit_from_mismatch():
    with pytest.raises(SessionFormatError, match="does not match"):
        resolve_parser_agent(
            FIXTURES / "codex_min.jsonl",
            (FIXTURES / "codex_min.jsonl").read_text(),
            "opencode",
            auto_detect=True,
        )


def test_auto_resolve_parser():
    agent, det = resolve_parser_agent(
        FIXTURES / "opencode_min.json",
        (FIXTURES / "opencode_min.json").read_text(),
        "auto",
        auto_detect=True,
    )
    assert agent == "opencode"
    assert det.kind == SessionFormatKind.OPENCODE_EXPORT


def test_convert_auto_still_works():
    out = convert_file("auto", "codex", FIXTURES / "opencode_min.json")
    data = json.loads(out)
    assert data["format"] == "agent-handoff-codex-v1"
