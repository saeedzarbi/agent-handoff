from __future__ import annotations

from agent_handoff.models import HandoffSpec


def _task_body(spec: HandoffSpec) -> str:
    lines = [
        f"# {spec.title}",
        "",
        "## Objective",
        spec.objective,
        "",
    ]
    if spec.context:
        lines.extend(["## Context", spec.context, ""])
    if spec.prior_summary:
        lines.extend(["## Prior work", spec.prior_summary, ""])
    if spec.files_touched:
        lines.extend(["## Files", *[f"- `{f}`" for f in spec.files_touched], ""])
    if spec.constraints:
        lines.extend(["## Constraints", *[f"- {c}" for c in spec.constraints], ""])
    if spec.notes:
        lines.extend(["## Notes", spec.notes, ""])
    return "\n".join(lines).strip() + "\n"


def emit_markdown_task(spec: HandoffSpec) -> str:
    return _task_body(spec)
