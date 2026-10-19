"""Convert coding-agent sessions into handoff task specs for another agent."""

from agent_handoff.detection import FormatDetection, SessionFormatError, detect_session_format
from agent_handoff.models import HandoffSpec
from agent_handoff.pipeline import convert_file, detect_format

__all__ = [
    "FormatDetection",
    "HandoffSpec",
    "SessionFormatError",
    "convert_file",
    "detect_format",
    "detect_session_format",
]
__version__ = "0.1.0"
