from __future__ import annotations

import re

_NOISE_LINE = re.compile(
    r"^(thinking\.\.\.|tool call|step-start|step-finish|\[\.\.\.\])$",
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
