from __future__ import annotations

from pathlib import Path

from agent_handoff.detection import (
    FormatDetection,
    SessionFormatError,
    detect_session_format,
    detection_to_legacy_id,
    resolve_parser_agent,
)
from agent_handoff.emitters import EMITTERS
from agent_handoff.models import HandoffSpec
from agent_handoff.parsers import PARSERS


def detect_format(path: Path, raw: str) -> str | None:
    """Legacy helper: returns opencode | codex | generic | None."""
    return detection_to_legacy_id(detect_session_format(path, raw))


def parse_source(source: str, raw: str, path: Path | None = None) -> HandoffSpec:
    path = path or Path("session")
    parser = PARSERS.get(source)
    if not parser:
        raise ValueError(f"Unsupported source agent: {source}")
    spec = parser(raw)
    spec.source_agent = source
    return spec


def emit_target(target: str, spec: HandoffSpec) -> str:
    emitter = EMITTERS.get(target)
    if not emitter:
        raise ValueError(f"Unsupported target agent: {target}")
    return emitter(spec)


def load_spec(
    source: str,
    input_path: Path,
    *,
    auto_detect: bool = True,
) -> HandoffSpec:
    raw = input_path.read_text(encoding="utf-8")
    parser_agent, _det = resolve_parser_agent(
        input_path, raw, source, auto_detect=auto_detect
    )
    return parse_source(parser_agent, raw, input_path)


def convert_file(
    source: str,
    target: str,
    input_path: Path,
    *,
    auto_detect: bool = True,
) -> str:
    raw = input_path.read_text(encoding="utf-8")
    parser_agent, _det = resolve_parser_agent(
        input_path, raw, source, auto_detect=auto_detect
    )
    spec = parse_source(parser_agent, raw, input_path)
    return emit_target(target, spec)


__all__ = [
    "FormatDetection",
    "SessionFormatError",
    "convert_file",
    "detect_format",
    "detect_session_format",
    "load_spec",
    "parse_source",
]
