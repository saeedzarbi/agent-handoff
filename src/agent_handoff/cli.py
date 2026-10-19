from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from agent_handoff.pipeline import convert_file, detect_format
from agent_handoff.registry import SUPPORTED_AGENTS

app = typer.Typer(
    name="agent-handoff",
    help="Convert one coding agent's session into another agent's task spec.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def convert(
    from_agent: str = typer.Option(..., "--from", "-f", help="Source agent or 'auto'"),
    to_agent: str = typer.Option(..., "--to", "-t", help="Target agent"),
    input_path: Path = typer.Option(..., "--input", "-i", exists=True, readable=True),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write result to file"),
    no_detect: bool = typer.Option(False, "--no-detect", help="Skip auto source detection"),
) -> None:
    """Parse a session log and emit a handoff for the target agent."""
    src = from_agent.lower()
    dst = to_agent.lower()
    if src != "auto" and src not in SUPPORTED_AGENTS:
        raise typer.BadParameter(f"Unknown source. Choose: auto, {', '.join(SUPPORTED_AGENTS)}")
    if dst not in SUPPORTED_AGENTS:
        raise typer.BadParameter(f"Unknown target. Choose: {', '.join(SUPPORTED_AGENTS)}")

    result = convert_file(
        src,
        dst,
        input_path,
        auto_detect=not no_detect,
    )
    if output:
        output.write_text(result, encoding="utf-8")
        console.print(f"[green]Wrote[/green] {output}")
    else:
        console.print(result)


@app.command()
def detect(
    input_path: Path = typer.Option(..., "--input", "-i", exists=True, readable=True),
) -> None:
    """Guess the source agent format for a file."""
    raw = input_path.read_text(encoding="utf-8")
    fmt = detect_format(input_path, raw)
    if fmt:
        console.print(fmt)
    else:
        console.print("unknown")
        raise typer.Exit(1)


@app.command("formats")
def list_formats() -> None:
    """List supported agent identifiers."""
    for name in SUPPORTED_AGENTS:
        console.print(name)


if __name__ == "__main__":
    app()
