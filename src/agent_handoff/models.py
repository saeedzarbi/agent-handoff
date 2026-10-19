from __future__ import annotations

from pydantic import BaseModel, Field


class HandoffSpec(BaseModel):
    """Normalized task extracted from a source agent session."""

    title: str = "Agent handoff"
    objective: str
    context: str = ""
    constraints: list[str] = Field(default_factory=list)
    files_touched: list[str] = Field(default_factory=list)
    prior_summary: str = ""
    source_agent: str = ""
    notes: str = ""
