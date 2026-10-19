from __future__ import annotations

import json
from pathlib import Path

from agent_handoff.clean import extract_actionable_summary, normalize_whitespace
from agent_handoff.models import HandoffSpec


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


def parse_codex(raw: str) -> HandoffSpec:
    user_turns: list[str] = []
    assistant_turns: list[str] = []
    tool_summaries: list[str] = []
    title = "Codex handoff"
    cwd = ""

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
            args = payload.get("arguments") or payload.get("input") or ""
            tool_summaries.append(f"- {name}: {str(args)[:400]}")
        elif ptype in ("function_call_output", "custom_tool_call_output"):
            out = payload.get("output") or payload.get("content") or ""
            tool_summaries.append(f"- output: {str(out)[:400]}")

    objective, prior, context = extract_actionable_summary(
        user_turns, assistant_turns, tool_summaries
    )
    if cwd:
        context = (f"Working directory: {cwd}\n\n" + context).strip()

    return HandoffSpec(
        title=title,
        objective=objective,
        context=context,
        prior_summary=prior,
        source_agent="codex",
        constraints=[
            "Pick up from the handoff summary; verify tests before large refactors.",
        ],
    )


def is_codex_rollout(path: Path, raw: str) -> bool:
    if path.suffix == ".jsonl" or "rollout" in path.name:
        return True
    for line in raw.splitlines()[:30]:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("type") in ("session_meta", "response_item", "turn_context"):
            return True
    return False
