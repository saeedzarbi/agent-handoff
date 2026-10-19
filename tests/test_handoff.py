import json
from pathlib import Path

from agent_handoff.emitters.codex import emit_codex
from agent_handoff.parsers.codex import parse_codex
from agent_handoff.parsers.opencode import parse_opencode
from agent_handoff.pipeline import convert_file, detect_format

FIXTURES = Path(__file__).parent / "fixtures"


def test_detect_opencode_and_codex():
    oc = (FIXTURES / "opencode_min.json").read_text()
    cx = (FIXTURES / "codex_min.jsonl").read_text()
    assert detect_format(FIXTURES / "opencode_min.json", oc) == "opencode"
    assert detect_format(FIXTURES / "rollout-test.jsonl", cx) == "codex"


def test_opencode_to_codex_roundtrip_fields():
    (FIXTURES / "opencode_min.json").read_text()
    out = convert_file("opencode", "codex", FIXTURES / "opencode_min.json", auto_detect=False)
    data = json.loads(out)
    assert data["format"] == "agent-handoff-codex-v1"
    assert "integration test" in data["user_message"].lower()
    assert "app/views.py" in data["full_prompt_markdown"]


def test_codex_to_opencode_export_shape():
    (FIXTURES / "codex_min.jsonl").read_text()
    out = convert_file("codex", "opencode", FIXTURES / "codex_min.jsonl", auto_detect=False)
    data = json.loads(out)
    assert data["info"]["title"]
    assert data["messages"][0]["info"]["role"] == "user"
    assert "cache TTL" in data["messages"][0]["parts"][0]["text"]
    assert data["handoff_meta"]["format"] == "agent-handoff-opencode-v1"


def test_parse_opencode_extracts_files():
    spec = parse_opencode((FIXTURES / "opencode_min.json").read_text())
    assert "app/views.py" in spec.files_touched


def test_emit_codex_contains_seed():
    spec = parse_codex((FIXTURES / "codex_min.jsonl").read_text())
    payload = json.loads(emit_codex(spec))
    assert payload["suggested_rollout_seed"]["payload"]["role"] == "user"
