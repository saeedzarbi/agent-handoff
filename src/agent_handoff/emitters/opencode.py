from __future__ import annotations

import json
import time

from agent_handoff.emitters.shared import _task_body
from agent_handoff.models import HandoffSpec


def emit_opencode(spec: HandoffSpec) -> str:
    """Emit an OpenCode session export skeleton for a new continuation turn."""
    now = int(time.time() * 1000)
    prompt = _task_body(spec)
    payload = {
        "info": {
            "id": "ses_handoff_import",
            "title": spec.title,
            "createdAt": now,
            "updatedAt": now,
        },
        "messages": [
            {
                "info": {
                    "id": "msg_handoff_user",
                    "role": "user",
                    "time": {"created": now},
                },
                "parts": [{"type": "text", "text": prompt}],
            }
        ],
        "handoff_meta": {
            "format": "agent-handoff-opencode-v1",
            "source_agent": spec.source_agent,
        },
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
