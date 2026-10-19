from __future__ import annotations

import re
from datetime import UTC, datetime

from agent_handoff.models import FileAction, FileChange, ToolExecution

_NOISE_LINE = re.compile(
    r"^(thinking\.\.\.|tool call|step-start|step-finish|\[\.\.\.\])$",
    re.I,
)
_QUESTION = re.compile(
    r"(?:^|\s)(?:open question|unresolved|need to decide|should we|what about)\b[^?.!]*\?",
    re.I,
)
_EXPLICIT_Q = re.compile(r"[^?\n]{8,200}\?")
_CONSTRAINT = re.compile(
    r"(?:^|\n)\s*(?:must|should not|don't|do not|never|always|only|avoid)\b[^\n]{5,120}",
    re.I,
)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def strip_noise_lines(text: str) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        if _NOISE_LINE.match(line.strip()):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def truncate(text: str, max_chars: int = 12_000) -> str:
    if len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head - 40
    return f"{text[:head]}\n\n…[truncated]…\n\n{text[-tail:]}"


def ms_to_iso(value: int | float | None) -> str | None:
    if value is None:
        return None
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return None
    if ts > 1e12:
        ts /= 1000.0
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


def infer_file_action(tool_name: str, output: str = "") -> FileAction:
    name = tool_name.lower()
    blob = f"{name} {output}".lower()
    if any(k in blob for k in ("delete", "remove", "unlink", "rm ")):
        return FileAction.DELETED
    if any(k in blob for k in ("create", "write", "new file", "touch")):
        return FileAction.CREATED
    if any(k in name for k in ("edit", "patch", "replace", "update")):
        return FileAction.MODIFIED
    return FileAction.UNKNOWN


def record_file_change(
    index: dict[str, FileChange],
    path: str,
    tool_name: str,
    output: str = "",
) -> None:
    path = path.strip()
    if not path:
        return
    action = infer_file_action(tool_name, output)
    summary = strip_noise_lines(str(output))[:300]
    existing = index.get(path)
    if existing:
        if action != FileAction.UNKNOWN:
            existing.action = action
        if summary and not existing.summary:
            existing.summary = summary
        return
    index[path] = FileChange(path=path, action=action, summary=summary)


def extract_open_questions(*text_blobs: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for blob in text_blobs:
        for pattern in (_QUESTION, _EXPLICIT_Q):
            for match in pattern.finditer(blob or ""):
                q = normalize_whitespace(match.group(0))
                if q.lower() in seen:
                    continue
                seen.add(q.lower())
                found.append(q)
    return found[:12]


def extract_conversation_constraints(*text_blobs: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for blob in text_blobs:
        for match in _CONSTRAINT.finditer(blob or ""):
            line = normalize_whitespace(match.group(0).strip(" -\n"))
            key = line.lower()
            if key in seen or len(line) < 8:
                continue
            seen.add(key)
            found.append(line)
    return found[:15]


def extract_actionable_summary(
    user_turns: list[str],
    assistant_turns: list[str],
    tool_summaries: list[str],
) -> tuple[str, str, str]:
    """Return objective, prior_summary, context from conversation slices."""
    objective = user_turns[-1] if user_turns else "Continue the previous task."
    if len(user_turns) > 1:
        earlier = "\n---\n".join(user_turns[:-1])
        context = truncate(normalize_whitespace(earlier))
    else:
        context = ""

    parts: list[str] = []
    if assistant_turns:
        parts.append("Last assistant outcome:\n" + assistant_turns[-1])
    if tool_summaries:
        parts.append("Tool activity (condensed):\n" + "\n".join(tool_summaries[-8:]))
    prior = truncate(normalize_whitespace("\n\n".join(parts)))
    return objective, prior, context


def append_tool_execution(
    executions: list[ToolExecution],
    name: str,
    status: str,
    outcome: str,
    timestamp: str | None = None,
) -> None:
    executions.append(
        ToolExecution(
            name=name,
            status=status,
            outcome=truncate(strip_noise_lines(outcome), 800),
            timestamp=timestamp,
        )
    )
