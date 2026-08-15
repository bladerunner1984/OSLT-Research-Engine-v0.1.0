from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ContinuityError(RuntimeError):
    """Raised when a handoff silently drops unresolved research state."""


class ResearchState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_version: str
    active_task_id: str
    unresolved_issue_ids: set[str] = Field(default_factory=set)
    contradiction_ids: set[str] = Field(default_factory=set)
    rejected_path_ids: set[str] = Field(default_factory=set)
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    must_read_refs: set[str] = Field(default_factory=set)


class ContinuityHandoff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_state_version: str
    to_state_version: str
    active_task_id: str
    unresolved_issue_ids: set[str] = Field(default_factory=set)
    contradiction_ids: set[str] = Field(default_factory=set)
    rejected_path_ids: set[str] = Field(default_factory=set)
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    must_read_refs: set[str] = Field(default_factory=set)


def validate_handoff(state: ResearchState, handoff: ContinuityHandoff) -> None:
    failures: list[str] = []
    if handoff.from_state_version != state.state_version:
        failures.append("STALE_STATE_VERSION")
    if not handoff.active_task_id:
        failures.append("RESUME_TASK_AMBIGUOUS")
    if not state.unresolved_issue_ids.issubset(handoff.unresolved_issue_ids):
        failures.append("OPEN_ISSUE_DROPPED")
    if not state.contradiction_ids.issubset(handoff.contradiction_ids):
        failures.append("CONTRADICTION_DROPPED")
    if not state.rejected_path_ids.issubset(handoff.rejected_path_ids):
        failures.append("REJECTED_PATH_DROPPED")
    if not state.must_read_refs.issubset(handoff.must_read_refs):
        failures.append("MUST_READ_REFERENCE_DROPPED")

    for name, digest in state.artifact_hashes.items():
        if handoff.artifact_hashes.get(name) != digest:
            failures.append(f"ARTIFACT_HASH_DRIFT:{name}")

    if failures:
        raise ContinuityError(";".join(failures))
