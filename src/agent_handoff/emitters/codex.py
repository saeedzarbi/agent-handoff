from __future__ import annotations

import json
import time

from agent_handoff.emitters.shared import _task_body
from agent_handoff.models import HandoffSpec


def emit_codex(spec: HandoffSpec) -> str:
    """Emit a Codex-friendly handoff: JSON task envelope + embedded markdown."""
    prompt = _task_body(spec)
    envelope = {
        "format": "agent-handoff-codex-v1",
        "generated_at_ms": int(time.time() * 1000),
        "title": spec.title,
        "user_message": spec.objective,
        "full_prompt_markdown": prompt,
        "handoff_spec": spec.model_dump(mode="json"),
        "suggested_rollout_seed": {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            },
        },
    }
    return json.dumps(envelope, indent=2, ensure_ascii=False) + "\n"
