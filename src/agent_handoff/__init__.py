"""Convert coding-agent sessions into handoff task specs for another agent."""

from agent_handoff.models import HandoffSpec
from agent_handoff.pipeline import convert_file, detect_format

__all__ = ["HandoffSpec", "convert_file", "detect_format"]
__version__ = "0.1.0"
