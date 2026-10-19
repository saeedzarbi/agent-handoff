from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from agent_handoff.detection import SessionFormatError, detect_session_format
from agent_handoff.pipeline import convert_file, load_spec
from agent_handoff.registry import SUPPORTED_AGENTS

app = typer.Typer(
    name="agent-handoff",
    help="Convert one coding agent's session into another agent's task spec.",
    no_args_is_help=True,
)
console = Console()


def _handle_format_error(exc: SessionFormatError) -> None:
    console.print(f"[red]Error:[/red] {exc}")
    raise typer.Exit(1) from exc


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

    try:
        result = convert_file(
            src,
            dst,
            input_path,
            auto_detect=not no_detect,
        )
    except SessionFormatError as exc:
        _handle_format_error(exc)

    if output:
        output.write_text(result, encoding="utf-8")
        console.print(f"[green]Wrote[/green] {output}")
    else:
        console.print(result)


@app.command()
def detect(
    input_path: Path = typer.Option(..., "--input", "-i", exists=True, readable=True),
    json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
) -> None:
    """Identify session file format, version, and structural signature."""
    raw = input_path.read_text(encoding="utf-8")
    result = detect_session_format(input_path, raw)
    if json_out:
        console.print(result.model_dump_json(indent=2))
    else:
        if not result.recognized:
            console.print("format: unknown")
            console.print(f"signature: {result.signature or 'none'}")
            console.print("message: This format is not recognized.")
            raise typer.Exit(1)
        console.print(f"format: {result.kind.value}")
        console.print(f"parser: {result.parser_agent}")
        console.print(f"version: {result.version or 'n/a'}")
        console.print(f"signature: {result.signature}")
        console.print(f"confidence: {result.confidence:.2f}")
    if not result.recognized:
        raise typer.Exit(1)


@app.command()
def inspect(
    from_agent: str = typer.Option("auto", "--from", "-f", help="Source agent or 'auto'"),
    input_path: Path = typer.Option(..., "--input", "-i", exists=True, readable=True),
    no_detect: bool = typer.Option(False, "--no-detect", help="Skip auto source detection"),
) -> None:
    """Parse a session and print the normalized HandoffSpec JSON."""
    src = from_agent.lower()
    if src != "auto" and src not in SUPPORTED_AGENTS:
        raise typer.BadParameter(f"Unknown source. Choose: auto, {', '.join(SUPPORTED_AGENTS)}")
    try:
        spec = load_spec(src, input_path, auto_detect=not no_detect)
    except SessionFormatError as exc:
        _handle_format_error(exc)
    console.print(spec.model_dump_json(indent=2))


@app.command("formats")
def list_formats() -> None:
    """List supported agent identifiers."""
    for name in SUPPORTED_AGENTS:
        console.print(name)


if __name__ == "__main__":
    app()
