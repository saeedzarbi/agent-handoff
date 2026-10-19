from __future__ import annotations

from collections.abc import Callable

from agent_handoff.models import HandoffSpec

Parser = Callable[[str], HandoffSpec]
Emitter = Callable[[HandoffSpec], str]

SUPPORTED_AGENTS = ("opencode", "codex", "openhands", "cline", "goose")
