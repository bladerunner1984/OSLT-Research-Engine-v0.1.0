import pytest

from oslt_research.governance.continuity import (
    ContinuityError,
    ContinuityHandoff,
    ResearchState,
    validate_handoff,
)


def state():
    return ResearchState(
        state_version="v1",
        active_task_id="TASK-1",
        unresolved_issue_ids={"I1"},
        contradiction_ids={"C1"},
        rejected_path_ids={"R1"},
        artifact_hashes={"a": "abc"},
        must_read_refs={"D1"},
    )


def valid_handoff():
    return ContinuityHandoff(
        from_state_version="v1",
        to_state_version="v2",
        active_task_id="TASK-1",
        unresolved_issue_ids={"I1", "I2"},
        contradiction_ids={"C1"},
        rejected_path_ids={"R1"},
        artifact_hashes={"a": "abc"},
        must_read_refs={"D1"},
    )


def test_valid_handoff_passes():
    validate_handoff(state(), valid_handoff())


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("from_state_version", "old", "STALE_STATE_VERSION"),
        ("active_task_id", "", "RESUME_TASK_AMBIGUOUS"),
        ("unresolved_issue_ids", set(), "OPEN_ISSUE_DROPPED"),
        ("contradiction_ids", set(), "CONTRADICTION_DROPPED"),
        ("rejected_path_ids", set(), "REJECTED_PATH_DROPPED"),
        ("must_read_refs", set(), "MUST_READ_REFERENCE_DROPPED"),
        ("artifact_hashes", {"a": "changed"}, "ARTIFACT_HASH_DRIFT:a"),
    ],
)
def test_handoff_failures_are_named(field, value, code):
    handoff = valid_handoff().model_copy(update={field: value})
    with pytest.raises(ContinuityError, match=code):
        validate_handoff(state(), handoff)
