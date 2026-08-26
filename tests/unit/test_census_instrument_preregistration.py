from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from oslt_research.governance.preregistration import (
    REASON_FREEZE_POSTDATES_RETRIEVAL,
    FrozenSpecificationRecord,
    analysis_is_confirmatory,
    verify_unchanged,
)
from studies.census_instrument_sensitivity.preregistration_v1 import SPECIFICATION


ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "studies" / "census_instrument_sensitivity"
EXPECTED_HASH = "7800ff83f3bad2cf3ca9b7358a5e21faffc12cee9e9d36ebf3a488ef8af1967c"


def frozen_record() -> FrozenSpecificationRecord:
    return FrozenSpecificationRecord.model_validate_json(
        (STUDY / "frozen_specification.json").read_text(encoding="utf-8")
    )


def test_committed_census_specification_matches_freeze_receipt() -> None:
    record = frozen_record()
    drift = verify_unchanged(SPECIFICATION, record)

    assert SPECIFICATION.specification_hash() == EXPECTED_HASH
    assert record.specification_hash == EXPECTED_HASH
    assert drift.unchanged
    assert not drift.drifted_fields


def test_specification_addresses_only_registered_propositions() -> None:
    with (ROOT / "registries" / "hypotheses.csv").open(encoding="utf-8-sig") as handle:
        registered = {row["proposition_id"] for row in csv.DictReader(handle)}

    assert SPECIFICATION.proposition_ids == ["AS10", "MX10", "IR07"]
    assert set(SPECIFICATION.proposition_ids) <= registered


def test_pre_freeze_harvest_is_not_confirmatory() -> None:
    decision = analysis_is_confirmatory(
        SPECIFICATION,
        frozen_record(),
        data_retrieved_at=datetime(2026, 8, 16, tzinfo=timezone.utc),
    )

    assert not decision.permitted
    assert REASON_FREEZE_POSTDATES_RETRIEVAL in decision.reasons


def test_post_freeze_retrieval_can_pass_the_temporal_gate() -> None:
    decision = analysis_is_confirmatory(
        SPECIFICATION,
        frozen_record(),
        data_retrieved_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
    )

    assert decision.permitted
    assert not decision.reasons

