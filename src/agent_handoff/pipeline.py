from __future__ import annotations

from pathlib import Path

from agent_handoff.emitters import EMITTERS
from agent_handoff.models import HandoffSpec
from agent_handoff.parsers import PARSERS
from agent_handoff.parsers.codex import is_codex_rollout
from agent_handoff.parsers.opencode import is_opencode_export


def detect_format(path: Path, raw: str) -> str | None:
    if is_opencode_export(path, raw):
        return "opencode"
    if is_codex_rollout(path, raw):
        return "codex"
    stripped = raw.lstrip()
    if stripped.startswith("#") or "handoff" in path.name.lower():
        return "generic"
    return None


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


def convert_file(
    source: str,
    target: str,
    input_path: Path,
    *,
    auto_detect: bool = True,
) -> str:
    raw = input_path.read_text(encoding="utf-8")
    if source == "auto":
        if not auto_detect:
            raise ValueError("Pass --from or enable auto detection.")
        detected = detect_format(input_path, raw)
        if not detected:
            raise ValueError("Could not detect source format; pass --from explicitly.")
        source = "cline" if detected == "generic" else detected
    spec = parse_source(source, raw, input_path)
    return emit_target(target, spec)
