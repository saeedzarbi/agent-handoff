from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = "handoff-spec-v2"


class FileAction(StrEnum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNKNOWN = "unknown"


class FileChange(BaseModel):
    path: str
    action: FileAction = FileAction.UNKNOWN
    summary: str = ""


class ToolExecution(BaseModel):
    name: str
    status: str = ""
    outcome: str = ""
    timestamp: str | None = None


class UsageMetadata(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    total_cost: float | None = None
    currency: str = "USD"


class SessionTimestamps(BaseModel):
    started_at: str | None = None
    ended_at: str | None = None


class HandoffSpec(BaseModel):
    """Normalized task extracted from a source agent session."""

    schema_version: str = SCHEMA_VERSION
    title: str = "Agent handoff"
    objective: str
    context: str = ""
    constraints: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    files_touched: list[str] = Field(default_factory=list)
    file_changes: list[FileChange] = Field(default_factory=list)
    tool_executions: list[ToolExecution] = Field(default_factory=list)
    prior_summary: str = ""
    source_agent: str = ""
    notes: str = ""
    usage: UsageMetadata | None = None
    timestamps: SessionTimestamps | None = None

    @model_validator(mode="after")
    def sync_legacy_file_list(self) -> HandoffSpec:
        if self.file_changes:
            paths = sorted({fc.path for fc in self.file_changes if fc.path})
            if paths:
                merged = list(dict.fromkeys([*self.files_touched, *paths]))
                object.__setattr__(self, "files_touched", merged)
        elif self.files_touched and not self.file_changes:
            object.__setattr__(
                self,
                "file_changes",
                [FileChange(path=p, action=FileAction.UNKNOWN) for p in self.files_touched],
            )
        return self
