from agent_handoff.emitters.codex import emit_codex
from agent_handoff.emitters.opencode import emit_opencode
from agent_handoff.emitters.shared import emit_markdown_task

EMITTERS = {
    "opencode": emit_opencode,
    "codex": emit_codex,
    "openhands": emit_markdown_task,
    "cline": emit_markdown_task,
    "goose": emit_markdown_task,
}
