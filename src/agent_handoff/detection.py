from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class SessionFormatKind(StrEnum):
    OPENCODE_EXPORT = "opencode_export"
    CODEX_ROLLOUT = "codex_rollout"
    GENERIC_MARKDOWN = "generic_markdown"
    GENERIC_CHAT_JSON = "generic_chat_json"
    UNKNOWN = "unknown"


class FormatDetection(BaseModel):
    """Result of inspecting a session file before parsing."""

    kind: SessionFormatKind
    parser_agent: str = Field(
        description="CLI/parser key: opencode, codex, or cline (generic markdown/chat)"
    )
    version: str | None = None
    signature: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    details: dict[str, str | int | bool] = Field(default_factory=dict)

    @property
    def recognized(self) -> bool:
        return self.kind != SessionFormatKind.UNKNOWN


class SessionFormatError(Exception):
    """Input file does not match a known agent session format."""

    def __init__(self, message: str, detection: FormatDetection | None = None) -> None:
        super().__init__(message)
        self.detection = detection


def detect_session_format(path: Path, raw: str) -> FormatDetection:
    stripped = raw.strip()
    if not stripped:
        return FormatDetection(
            kind=SessionFormatKind.UNKNOWN,
            parser_agent="",
            signature="empty",
            confidence=0.0,
        )

    oc = _probe_opencode(stripped)
    if oc.recognized:
        return oc

    cx = _probe_codex(path, stripped)
    if cx.recognized:
        return cx

    chat = _probe_generic_chat_json(stripped)
    if chat.recognized:
        return chat

    md = _probe_generic_markdown(stripped, path)
    if md.recognized:
        return md

    return FormatDetection(
        kind=SessionFormatKind.UNKNOWN,
        parser_agent="",
        signature="no_matching_structure",
        confidence=0.0,
        details={"path_suffix": path.suffix},
    )


def ensure_format_matches(
    declared_agent: str,
    path: Path,
    raw: str,
    detection: FormatDetection,
) -> None:
    """Verify explicit --from matches detected structure."""
    expected = _parser_to_kind(declared_agent)
    if detection.kind == SessionFormatKind.UNKNOWN:
        raise SessionFormatError(
            "This format is not recognized. "
            "Expected a supported agent export (OpenCode JSON, Codex JSONL, "
            "markdown handoff, or chat JSON).",
            detection,
        )
    if expected is None:
        return
    if detection.kind != expected and not (
        declared_agent == "cline"
        and detection.kind
        in (SessionFormatKind.GENERIC_MARKDOWN, SessionFormatKind.GENERIC_CHAT_JSON)
    ):
        raise SessionFormatError(
            f"File does not match --from {declared_agent}: detected {detection.kind.value} "
            f"({detection.signature}).",
            detection,
        )


def resolve_parser_agent(
    path: Path,
    raw: str,
    source: str,
    *,
    auto_detect: bool,
) -> tuple[str, FormatDetection]:
    detection = detect_session_format(path, raw)
    if source == "auto":
        if not detection.recognized:
            raise SessionFormatError(
                "This format is not recognized. "
                "Pass --from explicitly if you use a custom layout, or fix the input file.",
                detection,
            )
        return detection.parser_agent, detection

    ensure_format_matches(source, path, raw, detection)
    return source, detection


def _parser_to_kind(agent: str) -> SessionFormatKind | None:
    return {
        "opencode": SessionFormatKind.OPENCODE_EXPORT,
        "codex": SessionFormatKind.CODEX_ROLLOUT,
        "cline": SessionFormatKind.GENERIC_MARKDOWN,
        "openhands": SessionFormatKind.GENERIC_MARKDOWN,
        "goose": SessionFormatKind.GENERIC_MARKDOWN,
    }.get(agent)


def _probe_opencode(stripped: str) -> FormatDetection:
    if not stripped.startswith("{"):
        return _unknown()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return _unknown()
    if not isinstance(data, dict):
        return _unknown()
    info = data.get("info")
    messages = data.get("messages")
    if not isinstance(info, dict) or not isinstance(messages, list):
        return _unknown()
    if not messages:
        return FormatDetection(
            kind=SessionFormatKind.OPENCODE_EXPORT,
            parser_agent="opencode",
            version="export-v1-empty",
            signature="info+messages",
            confidence=0.7,
            details={"message_count": 0},
        )
    first = messages[0]
    if not isinstance(first, dict) or "parts" not in first:
        return _unknown()
    version = "export-v1"
    for msg in messages:
        for part in msg.get("parts") or []:
            if isinstance(part, dict) and part.get("type") == "tool":
                version = "export-v1-tools"
            if isinstance(part, dict) and part.get("id"):
                version = "export-v1.2+"
                break
    return FormatDetection(
        kind=SessionFormatKind.OPENCODE_EXPORT,
        parser_agent="opencode",
        version=version,
        signature="info+messages+parts",
        confidence=0.95,
        details={"message_count": len(messages)},
    )


def _probe_codex(path: Path, stripped: str) -> FormatDetection:
    lines = [ln.strip() for ln in stripped.splitlines() if ln.strip()]
    if not lines:
        return _unknown()
    session_meta = 0
    response_items = 0
    turn_context = 0
    has_ordinal = False
    history_mode = ""
    for line in lines[:200]:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            if path.suffix == ".jsonl" or "rollout" in path.name:
                return FormatDetection(
                    kind=SessionFormatKind.UNKNOWN,
                    parser_agent="",
                    signature="invalid_jsonl_line",
                    confidence=0.0,
                )
            return _unknown()
        if not isinstance(row, dict) or "type" not in row:
            continue
        if row.get("ordinal") is not None:
            has_ordinal = True
        rtype = row.get("type")
        if rtype == "session_meta":
            session_meta += 1
            payload = row.get("payload") or {}
            if isinstance(payload, dict):
                history_mode = str(payload.get("history_mode") or "")
        elif rtype == "response_item":
            response_items += 1
        elif rtype == "turn_context":
            turn_context += 1

    if session_meta == 0 and response_items == 0:
        if path.suffix == ".jsonl" and turn_context > 0:
            pass
        else:
            return _unknown()

    if response_items == 0 and session_meta == 0:
        return _unknown()

    version = "rollout-v1"
    if has_ordinal:
        version = "rollout-paginated"
    if history_mode:
        version = f"rollout-{history_mode.lower()}"

    confidence = 0.9 if session_meta and response_items else 0.75
    return FormatDetection(
        kind=SessionFormatKind.CODEX_ROLLOUT,
        parser_agent="codex",
        version=version,
        signature="session_meta+response_item",
        confidence=confidence,
        details={
            "session_meta_lines": session_meta,
            "response_item_lines": response_items,
            "line_count": len(lines),
        },
    )


def _probe_generic_chat_json(stripped: str) -> FormatDetection:
    if not stripped.startswith("{") and not stripped.startswith("["):
        return _unknown()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return _unknown()
    messages: list | None = None
    if isinstance(data, dict) and isinstance(data.get("messages"), list):
        messages = data["messages"]
        signature = "object.messages[]"
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        if "role" in data[0] and ("content" in data[0] or "text" in data[0]):
            messages = data
            signature = "array[{role,content}]"
    if messages is None:
        return _unknown()
    if messages and not isinstance(messages[0], dict):
        return _unknown()
    if data if isinstance(data, dict) else messages:
        first = messages[0] if messages else {}
        if isinstance(first, dict) and "parts" in first and "info" in first:
            return _unknown()
    return FormatDetection(
        kind=SessionFormatKind.GENERIC_CHAT_JSON,
        parser_agent="cline",
        version="chat-json-v1",
        signature=signature,
        confidence=0.8,
        details={"message_count": len(messages)},
    )


def _probe_generic_markdown(stripped: str, path: Path) -> FormatDetection:
    if stripped.startswith("{") or stripped.startswith("["):
        return _unknown()
    head = stripped[:2000].lower()
    markers = (
        stripped.startswith("#"),
        "## objective" in head,
        "## context" in head,
        "handoff" in path.name.lower(),
    )
    if not any(markers):
        return _unknown()
    return FormatDetection(
        kind=SessionFormatKind.GENERIC_MARKDOWN,
        parser_agent="cline",
        version="markdown-v1",
        signature="markdown_handoff",
        confidence=0.75 if markers[0] else 0.6,
    )


def _unknown() -> FormatDetection:
    return FormatDetection(
        kind=SessionFormatKind.UNKNOWN,
        parser_agent="",
        signature="",
        confidence=0.0,
    )


def detection_to_legacy_id(detection: FormatDetection) -> str | None:
    """Map detection to legacy detect_format() string ids."""
    if not detection.recognized:
        return None
    if detection.kind == SessionFormatKind.OPENCODE_EXPORT:
        return "opencode"
    if detection.kind == SessionFormatKind.CODEX_ROLLOUT:
        return "codex"
    if detection.kind in (
        SessionFormatKind.GENERIC_MARKDOWN,
        SessionFormatKind.GENERIC_CHAT_JSON,
    ):
        return "generic"
    return None
