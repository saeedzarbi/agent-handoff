from __future__ import annotations

from agent_handoff.models import FileAction, HandoffSpec


def _format_file_changes(spec: HandoffSpec) -> list[str]:
    lines: list[str] = []
    for fc in spec.file_changes:
        action = fc.action.value if fc.action != FileAction.UNKNOWN else "changed"
        line = f"- `{fc.path}` ({action})"
        if fc.summary:
            line += f" — {fc.summary[:200]}"
        lines.append(line)
    return lines


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
    if spec.file_changes or spec.files_touched:
        lines.append("## File changes")
        if spec.file_changes:
            lines.extend(_format_file_changes(spec))
        else:
            lines.extend([f"- `{p}`" for p in spec.files_touched])
        lines.append("")
    if spec.tool_executions:
        lines.append("## Tool history")
        for te in spec.tool_executions[-15:]:
            ts = f" ({te.timestamp})" if te.timestamp else ""
            lines.append(f"- **{te.name}** [{te.status}]{ts}: {te.outcome[:300]}")
        lines.append("")
    if spec.constraints:
        lines.extend(["## Constraints", *[f"- {c}" for c in spec.constraints], ""])
    if spec.open_questions:
        lines.extend(["## Open questions", *[f"- {q}" for q in spec.open_questions], ""])
    if spec.timestamps and (spec.timestamps.started_at or spec.timestamps.ended_at):
        lines.append("## Session timing")
        if spec.timestamps.started_at:
            lines.append(f"- Started: {spec.timestamps.started_at}")
        if spec.timestamps.ended_at:
            lines.append(f"- Last activity: {spec.timestamps.ended_at}")
        lines.append("")
    if spec.usage and any(
        v is not None
        for v in (
            spec.usage.input_tokens,
            spec.usage.output_tokens,
            spec.usage.total_cost,
        )
    ):
        lines.append("## Usage (from source log)")
        if spec.usage.input_tokens is not None:
            lines.append(f"- Input tokens: {spec.usage.input_tokens}")
        if spec.usage.output_tokens is not None:
            lines.append(f"- Output tokens: {spec.usage.output_tokens}")
        if spec.usage.total_cost is not None:
            lines.append(f"- Cost: {spec.usage.total_cost} {spec.usage.currency}")
        lines.append("")
    if spec.notes:
        lines.extend(["## Notes", spec.notes, ""])
    return "\n".join(lines).strip() + "\n"


def emit_markdown_task(spec: HandoffSpec) -> str:
    return _task_body(spec)
