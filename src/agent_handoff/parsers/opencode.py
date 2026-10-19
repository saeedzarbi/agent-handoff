from __future__ import annotations

import json
import re
from pathlib import Path

from agent_handoff.clean import (
    append_tool_execution,
    extract_actionable_summary,
    extract_conversation_constraints,
    extract_open_questions,
    ms_to_iso,
    normalize_whitespace,
    record_file_change,
    strip_noise_lines,
)
from agent_handoff.models import (
    FileChange,
    HandoffSpec,
    SessionTimestamps,
    UsageMetadata,
)

_FILE_RE = re.compile(r"(?:filePath|path|file)[\"']?\s*[:=]\s*[\"']([^\"']+)")


def parse_opencode(raw: str) -> HandoffSpec:
    data = json.loads(raw)
    if "messages" not in data:
        raise ValueError("Not an OpenCode export: missing 'messages'")

    title = (data.get("info") or {}).get("title") or "OpenCode handoff"
    info = data.get("info") or {}
    user_turns: list[str] = []
    assistant_turns: list[str] = []
    tool_summaries: list[str] = []
    file_index: dict[str, FileChange] = {}
    tool_executions: list = []
    created_times: list[int] = []
    completed_times: list[int] = []
    total_in = 0
    total_out = 0
    total_cost = 0.0
    cost_seen = False

    for msg in data["messages"]:
        minfo = msg.get("info") or {}
        role = minfo.get("role", "")
        times = minfo.get("time") or {}
        if times.get("created"):
            created_times.append(int(times["created"]))
        if times.get("completed"):
            completed_times.append(int(times["completed"]))
        tokens = minfo.get("tokens") or {}
        if tokens:
            total_in += int(tokens.get("input") or 0)
            total_out += int(tokens.get("output") or 0)
        if minfo.get("cost") is not None:
            total_cost += float(minfo["cost"])
            cost_seen = True

        parts = msg.get("parts") or []
        texts: list[str] = []
        ts_iso = ms_to_iso(times.get("created"))
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
                            record_file_change(
                                file_index, str(inp[key]), tool, str(output)
                            )
                snippet = strip_noise_lines(str(output))[:500]
                tool_summaries.append(f"- {tool} ({status}): {snippet}")
                append_tool_execution(tool_executions, tool, status, str(output), ts_iso)
                blob = json.dumps(inp) if inp else ""
                for match in _FILE_RE.finditer(blob):
                    record_file_change(file_index, match.group(1), tool, str(output))
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
    convo_text = "\n".join(user_turns + assistant_turns)
    extracted_constraints = extract_conversation_constraints(convo_text)
    open_questions = extract_open_questions(convo_text)

    usage = None
    if total_in or total_out or cost_seen:
        usage = UsageMetadata(
            input_tokens=total_in or None,
            output_tokens=total_out or None,
            total_cost=total_cost if cost_seen else None,
        )

    started = (
        ms_to_iso(min(created_times))
        if created_times
        else ms_to_iso(info.get("createdAt"))
    )
    timestamps = SessionTimestamps(
        started_at=started,
        ended_at=ms_to_iso(max(completed_times or created_times))
        if (completed_times or created_times)
        else None,
    )

    default_constraints = [
        "Continue from the summarized state; do not redo completed work unless asked.",
        "Prefer editing listed files before creating new ones.",
    ]

    return HandoffSpec(
        title=title,
        objective=objective,
        context=context,
        prior_summary=prior,
        file_changes=list(file_index.values()),
        tool_executions=tool_executions,
        open_questions=open_questions,
        constraints=[*extracted_constraints, *default_constraints],
        source_agent="opencode",
        usage=usage,
        timestamps=timestamps,
    )


def is_opencode_export(path: Path, raw: str) -> bool:
    from agent_handoff.detection import SessionFormatKind, detect_session_format

    return detect_session_format(path, raw).kind == SessionFormatKind.OPENCODE_EXPORT
