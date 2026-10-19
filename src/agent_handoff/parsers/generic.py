from __future__ import annotations

import json

from agent_handoff.clean import extract_actionable_summary, normalize_whitespace
from agent_handoff.models import HandoffSpec


def parse_generic_summary(raw: str) -> HandoffSpec:
    """Best-effort parser for markdown summaries or chat JSON exports."""
    stripped = raw.lstrip()
    user_turns: list[str] = []
    assistant_turns: list[str] = []

    if stripped.startswith("{") or stripped.startswith("["):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and "messages" in data:
            for msg in data["messages"]:
                role = msg.get("role") or msg.get("type", "")
                content = msg.get("content") or msg.get("text") or ""
                if isinstance(content, list):
                    content = " ".join(
                        str(c.get("text", c)) if isinstance(c, dict) else str(c) for c in content
                    )
                content = normalize_whitespace(str(content))
                if not content:
                    continue
                if role == "user":
                    user_turns.append(content)
                elif role in ("assistant", "agent"):
                    assistant_turns.append(content)
        elif isinstance(data, list):
            for msg in data:
                if not isinstance(msg, dict):
                    continue
                role = msg.get("role", "")
                content = normalize_whitespace(str(msg.get("content", "")))
                if role == "user" and content:
                    user_turns.append(content)
                elif role == "assistant" and content:
                    assistant_turns.append(content)

    if not user_turns and not assistant_turns:
        body = normalize_whitespace(raw)
        user_turns = [body[:8000] if body else "Continue the task described in the handoff file."]

    objective, prior, context = extract_actionable_summary(user_turns, assistant_turns, [])
    return HandoffSpec(
        title="Agent handoff",
        objective=objective,
        context=context,
        prior_summary=prior,
        source_agent="generic",
    )
