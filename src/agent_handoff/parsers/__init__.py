from agent_handoff.parsers.codex import parse_codex
from agent_handoff.parsers.generic import parse_generic_summary
from agent_handoff.parsers.opencode import parse_opencode

PARSERS = {
    "opencode": parse_opencode,
    "codex": parse_codex,
    "openhands": parse_generic_summary,
    "cline": parse_generic_summary,
    "goose": parse_generic_summary,
}
