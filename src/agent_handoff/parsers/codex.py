from __future__ import annotations

import json
import re
from pathlib import Path

from agent_handoff.clean import (
    append_tool_execution,
    extract_actionable_summary,
    extract_conversation_constraints,
    extract_open_questions,
    normalize_whitespace,
    record_file_change,
)
from agent_handoff.models import HandoffSpec, SessionTimestamps, ToolExecution

_PATH_IN_ARGS = re.compile(r'["\']?(?:/[\w./-]+|[\w./-]+\.(?:py|ts|js|md|json|yaml|yml))["\']?')


def _text_from_message_payload(payload: dict) -> tuple[str, str]:
    role = payload.get("role", "")
    chunks: list[str] = []
    for block in payload.get("content") or []:
        if not isinstance(block, dict):
            continue
        btype = block.get("type", "")
        if btype in ("input_text", "output_text", "text"):
            if block.get("text"):
                chunks.append(str(block["text"]))
        elif btype == "input_text" and block.get("input_text"):
            chunks.append(str(block["input_text"]))
    if not chunks and payload.get("text"):
        chunks.append(str(payload["text"]))
    return normalize_whitespace("\n".join(chunks)), role


def _paths_from_arguments(args: str) -> list[str]:
    return [m.group(0).strip("'\"") for m in _PATH_IN_ARGS.finditer(args)][:5]


def parse_codex(raw: str) -> HandoffSpec:
    user_turns: list[str] = []
    assistant_turns: list[str] = []
    tool_summaries: list[str] = []
    file_index: dict = {}
    tool_executions: list[ToolExecution] = []
    pending_tools: dict[str, dict] = {}
    title = "Codex handoff"
    cwd = ""
    started_at: str | None = None
    ended_at: str | None = None

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        rtype = row.get("type", "")
        payload = row.get("payload") or {}
        envelope_ts = row.get("timestamp")
        if envelope_ts:
            ended_at = str(envelope_ts)
            if not started_at:
                started_at = str(envelope_ts)

        if rtype == "session_meta":
            title = payload.get("title") or payload.get("preview") or title
            cwd = payload.get("cwd") or cwd
            continue
        if rtype != "response_item":
            continue

        ptype = payload.get("type", "")
        if ptype == "message":
            text, role = _text_from_message_payload(payload)
            if not text:
                continue
            if role == "user":
                user_turns.append(text)
            elif role == "assistant":
                assistant_turns.append(text)
        elif ptype in ("function_call", "custom_tool_call"):
            name = payload.get("name") or payload.get("tool_name") or "tool"
            args = str(payload.get("arguments") or payload.get("input") or "")
            call_id = payload.get("call_id") or payload.get("id") or name
            pending_tools[str(call_id)] = {"name": name, "args": args}
            tool_summaries.append(f"- {name}: {args[:400]}")
            for path in _paths_from_arguments(args):
                record_file_change(file_index, path, name)
            append_tool_execution(
                tool_executions,
                name,
                "invoked",
                args[:500],
                str(envelope_ts) if envelope_ts else None,
            )
        elif ptype in ("function_call_output", "custom_tool_call_output"):
            out = str(payload.get("output") or payload.get("content") or "")
            call_id = str(payload.get("call_id") or payload.get("id") or "")
            name = pending_tools.get(call_id, {}).get("name", "tool")
            tool_summaries.append(f"- {name} output: {out[:400]}")
            if tool_executions:
                tool_executions[-1].status = "completed"
                tool_executions[-1].outcome = out[:800]
            for path in _paths_from_arguments(out):
                record_file_change(file_index, path, name, out)

    objective, prior, context = extract_actionable_summary(
        user_turns, assistant_turns, tool_summaries
    )
    if cwd:
        context = (f"Working directory: {cwd}\n\n" + context).strip()

    convo = "\n".join(user_turns + assistant_turns)
    extracted = extract_conversation_constraints(convo)
    open_questions = extract_open_questions(convo)

    return HandoffSpec(
        title=title,
        objective=objective,
        context=context,
        prior_summary=prior,
        file_changes=list(file_index.values()),
        tool_executions=tool_executions,
        open_questions=open_questions,
        source_agent="codex",
        constraints=[
            *extracted,
            "Pick up from the handoff summary; verify tests before large refactors.",
        ],
        timestamps=SessionTimestamps(started_at=started_at, ended_at=ended_at),
    )


def is_codex_rollout(path: Path, raw: str) -> bool:
    from agent_handoff.detection import SessionFormatKind, detect_session_format

    return detect_session_format(path, raw).kind == SessionFormatKind.CODEX_ROLLOUT
