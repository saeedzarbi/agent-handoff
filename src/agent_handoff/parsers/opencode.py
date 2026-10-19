from __future__ import annotations

import json
import re
from pathlib import Path

from agent_handoff.clean import extract_actionable_summary, normalize_whitespace, strip_noise_lines
from agent_handoff.models import HandoffSpec

_FILE_RE = re.compile(r"(?:filePath|path|file)[\"']?\s*[:=]\s*[\"']([^\"']+)")


def parse_opencode(raw: str) -> HandoffSpec:
    data = json.loads(raw)
    if "messages" not in data:
        raise ValueError("Not an OpenCode export: missing 'messages'")

    title = (data.get("info") or {}).get("title") or "OpenCode handoff"
    user_turns: list[str] = []
    assistant_turns: list[str] = []
    tool_summaries: list[str] = []
    files: set[str] = set()

    for msg in data["messages"]:
        role = (msg.get("info") or {}).get("role", "")
        parts = msg.get("parts") or []
        texts: list[str] = []
        for part in parts:
            ptype = part.get("type", "")
            if ptype == "text" and part.get("text"):
                texts.append(part["text"])
            elif ptype == "reasoning" and part.get("text"):
                continue
            elif ptype == "tool":
                tool = part.get("tool", "tool")
                state = part.get("state") or {}
                status = state.get("status", "")
                output = state.get("output") or ""
                inp = state.get("input") or {}
                if isinstance(inp, dict):
                    for key in ("filePath", "path", "file"):
                        if inp.get(key):
                            files.add(str(inp[key]))
                snippet = strip_noise_lines(str(output))[:500]
                tool_summaries.append(f"- {tool} ({status}): {snippet}")
                blob = json.dumps(inp) if inp else ""
                for match in _FILE_RE.finditer(blob):
                    files.add(match.group(1))
        chunk = normalize_whitespace("\n".join(texts))
        if not chunk:
            continue
        if role == "user":
            user_turns.append(chunk)
        elif role == "assistant":
            assistant_turns.append(chunk)

    objective, prior, context = extract_actionable_summary(
        user_turns, assistant_turns, tool_summaries
    )
    return HandoffSpec(
        title=title,
        objective=objective,
        context=context,
        prior_summary=prior,
        files_touched=sorted(files),
        source_agent="opencode",
        constraints=[
            "Continue from the summarized state; do not redo completed work unless asked.",
            "Prefer editing listed files before creating new ones.",
        ],
    )


def is_opencode_export(path: Path, raw: str) -> bool:
    stripped = raw.lstrip()
    if not stripped.startswith("{"):
        return False
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False
    return isinstance(data.get("messages"), list) and isinstance(data.get("info"), dict)
