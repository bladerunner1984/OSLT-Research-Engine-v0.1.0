from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from oslt_research.domain.enums import AuthorityLevel
from oslt_research.domain.models import ScopeContext
from oslt_research.evidence.journal import ResearchComputationJournal
from oslt_research.governance.authority import PROTECTED_TYPES
from oslt_research.governance.preregistration import (
    PREREGISTRATION_EVENT_TYPE,
    REASON_FREEZE_POSTDATES_RETRIEVAL,
    REASON_JOURNAL_CHAIN_BROKEN,
    REASON_NO_FREEZE,
    REASON_SPECIFICATION_DRIFT,
    REASON_SPECIFICATION_ID_MISMATCH,
    DateWindow,
    PreregisteredSpecification,
    PreregistrationError,
    SearchConcept,
    SelectionRule,
    analysis_is_confirmatory,
    find_freeze_entries,
    freeze,
    verify_unchanged,
)

FREEZE_TIME = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
RETRIEVAL_TIME = FREEZE_TIME + timedelta(days=1)


def make_spec(**overrides) -> PreregisteredSpecification:
    payload = {
        "specification_id": "SPEC-1",
        "objective": "Estimate the association between open peer review and retraction rate.",
        "proposition_ids": ["P1", "P2"],
        "scope": ScopeContext(
            construct="open peer review",
            population="indexed journals",
            period="2015-2025",
            jurisdiction="UK",
            estimand="risk difference in retraction rate",
        ),
        "search_concepts": [
            SearchConcept(
                concept_id="C1",
                concept="open peer review",
                query_terms=["open peer review", "transparent review"],
                sources=["openalex"],
            )
        ],
        "date_windows": [DateWindow(window_id="W1", from_date="2015-01-01", to_date="2025-12-31")],
        "selection_rules": [
            SelectionRule(rule_id="R1", rule_type="INCLUSION", description="Peer-reviewed"),
            SelectionRule(rule_id="R2", rule_type="EXCLUSION", description="Editorials"),
        ],
        "planned_analysis": "Random-effects meta-analysis over resolved dependency families.",
        "primary_outcome": "retraction rate per 1000 articles",
        "cohort_lexicon": ["retraction watch", "pubpeer"],
    }
    payload.update(overrides)
    return PreregisteredSpecification(**payload)


def make_journal(tmp_path) -> ResearchComputationJournal:
    return ResearchComputationJournal(tmp_path / "computation-journal.jsonl")


# --- hashing ---------------------------------------------------------------------------------


def test_freeze_produces_stable_hash():
    spec = make_spec()
    first = freeze(spec, frozen_at=FREEZE_TIME)
    second = freeze(make_spec(), frozen_at=FREEZE_TIME)
    assert first.specification_hash == second.specification_hash
    assert first.specification_hash == spec.specification_hash()
    assert len(first.specification_hash) == 64


def test_freeze_records_authority_and_timestamp():
    record = freeze(make_spec(), frozen_at=FREEZE_TIME)
    assert record.authority is AuthorityLevel.A1_AUTHORISED_SPECIFICATION
    assert record.frozen_at == FREEZE_TIME
    assert record.specification_id == "SPEC-1"


def test_freeze_rejects_naive_timestamp():
    with pytest.raises(PreregistrationError, match="timezone-aware"):
        freeze(make_spec(), frozen_at=datetime(2026, 1, 1, 9, 0))


def test_key_reordering_does_not_change_hash():
    """A dict-order shuffle must not move the hash, or drift detection could be side-stepped."""

    spec = make_spec()
    reordered_payload = dict(reversed(list(spec.model_dump().items())))
    reordered = PreregisteredSpecification(**reordered_payload)
    assert list(reordered_payload) != list(spec.model_dump())
    assert reordered.specification_hash() == spec.specification_hash()
    assert verify_unchanged(reordered, freeze(spec, frozen_at=FREEZE_TIME)).unchanged


def test_list_reordering_does_change_hash():
    """Order of preregistered concepts is itself part of the specification, so it must be bound."""

    spec = make_spec()
    shuffled = make_spec(proposition_ids=["P2", "P1"])
    assert shuffled.specification_hash() != spec.specification_hash()


# --- drift detection -------------------------------------------------------------------------


def test_verify_unchanged_true_for_untouched_specification():
    spec = make_spec()
    report = verify_unchanged(spec, freeze(spec, frozen_at=FREEZE_TIME))
    assert report.unchanged
    assert report.drifted_fields == []
    assert report.reasons == []
    assert report.frozen_hash == report.current_hash


def test_field_drift_is_detected_and_named():
    record = freeze(make_spec(), frozen_at=FREEZE_TIME)
    drifted = make_spec(primary_outcome="retraction count")
    report = verify_unchanged(drifted, record)

    assert not report.unchanged
    assert report.drifted_field_paths == ["primary_outcome"]
    assert report.reasons == [REASON_SPECIFICATION_DRIFT]
    change = report.drifted_fields[0]
    assert change.frozen_value == "retraction rate per 1000 articles"
    assert change.current_value == "retraction count"


def test_nested_estimand_drift_is_named_with_dotted_path():
    record = freeze(make_spec(), frozen_at=FREEZE_TIME)
    swapped_estimand = make_spec(
        scope=ScopeContext(
            construct="open peer review",
            population="indexed journals",
            period="2015-2025",
            jurisdiction="UK",
            estimand="odds ratio for retraction",
        )
    )
    report = verify_unchanged(swapped_estimand, record)
    assert report.drifted_field_paths == ["scope.estimand"]


def test_multiple_field_drifts_are_all_reported():
    record = freeze(make_spec(), frozen_at=FREEZE_TIME)
    drifted = make_spec(
        objective="A different objective entirely.",
        cohort_lexicon=["retraction watch"],
    )
    report = verify_unchanged(drifted, record)
    assert report.drifted_field_paths == ["cohort_lexicon", "objective"]


def test_cohort_lexicon_drift_is_detected():
    """The lexicon drives dependency-family collapse, so tuning it post hoc must be visible."""

    record = freeze(make_spec(), frozen_at=FREEZE_TIME)
    widened = make_spec(cohort_lexicon=["retraction watch", "pubpeer", "scopus"])
    report = verify_unchanged(widened, record)
    assert not report.unchanged
    assert "cohort_lexicon" in report.drifted_field_paths


def test_specification_id_mismatch_is_reported():
    record = freeze(make_spec(), frozen_at=FREEZE_TIME)
    report = verify_unchanged(make_spec(specification_id="SPEC-2"), record)
    assert not report.unchanged
    assert REASON_SPECIFICATION_ID_MISMATCH in report.reasons
    assert "specification_id" in report.drifted_field_paths


# --- confirmatory gate -----------------------------------------------------------------------


def test_confirmatory_refused_with_no_freeze():
    decision = analysis_is_confirmatory(make_spec(), None, data_retrieved_at=RETRIEVAL_TIME)
    assert not decision.permitted
    assert decision.reasons == [REASON_NO_FREEZE]


def test_confirmatory_refused_on_drift():
    record = freeze(make_spec(), frozen_at=FREEZE_TIME)
    decision = analysis_is_confirmatory(
        make_spec(planned_analysis="Fixed-effect meta-analysis."),
        record,
        data_retrieved_at=RETRIEVAL_TIME,
    )
    assert not decision.permitted
    assert REASON_SPECIFICATION_DRIFT in decision.reasons
    assert decision.drift is not None
    assert decision.drift.drifted_field_paths == ["planned_analysis"]


def test_confirmatory_refused_when_freeze_postdates_retrieval():
    """Freezing after the corpus has been seen is not preregistration."""

    spec = make_spec()
    late_freeze = freeze(spec, frozen_at=RETRIEVAL_TIME + timedelta(hours=1))
    decision = analysis_is_confirmatory(spec, late_freeze, data_retrieved_at=RETRIEVAL_TIME)
    assert not decision.permitted
    assert decision.reasons == [REASON_FREEZE_POSTDATES_RETRIEVAL]


def test_confirmatory_uses_earliest_retrieval_timestamp():
    spec = make_spec()
    record = freeze(spec, frozen_at=FREEZE_TIME)
    early = FREEZE_TIME - timedelta(minutes=1)
    decision = analysis_is_confirmatory(
        spec, record, data_retrieved_at=[RETRIEVAL_TIME, early, RETRIEVAL_TIME]
    )
    assert not decision.permitted
    assert decision.reasons == [REASON_FREEZE_POSTDATES_RETRIEVAL]


def test_confirmatory_treats_naive_retrieval_time_as_utc():
    spec = make_spec()
    record = freeze(spec, frozen_at=FREEZE_TIME)
    naive_earlier = datetime(2026, 1, 1, 8, 0)
    decision = analysis_is_confirmatory(spec, record, data_retrieved_at=naive_earlier)
    assert not decision.permitted
    assert decision.reasons == [REASON_FREEZE_POSTDATES_RETRIEVAL]


def test_confirmatory_accumulates_multiple_refusal_reasons():
    record = freeze(make_spec(), frozen_at=RETRIEVAL_TIME + timedelta(hours=1))
    decision = analysis_is_confirmatory(
        make_spec(objective="Changed after the fact."),
        record,
        data_retrieved_at=RETRIEVAL_TIME,
    )
    assert not decision.permitted
    assert set(decision.reasons) == {
        REASON_SPECIFICATION_DRIFT,
        REASON_FREEZE_POSTDATES_RETRIEVAL,
    }


def test_confirmatory_permitted_in_clean_case():
    spec = make_spec()
    record = freeze(spec, frozen_at=FREEZE_TIME)
    decision = analysis_is_confirmatory(spec, record, data_retrieved_at=RETRIEVAL_TIME)
    assert decision.permitted
    assert decision.reasons == []
    assert bool(decision) is True


def test_confirmatory_permitted_without_retrieval_timestamps():
    spec = make_spec()
    record = freeze(spec, frozen_at=FREEZE_TIME)
    assert analysis_is_confirmatory(spec, record).permitted


# --- journal integration ---------------------------------------------------------------------


def test_freeze_writes_journal_entry_and_chain_verifies(tmp_path):
    journal = make_journal(tmp_path)
    journal.append("PILOT_ONE_STARTED", {"run_id": "R1"})
    spec = make_spec()
    record = freeze(spec, journal=journal, frozen_at=FREEZE_TIME)

    assert journal.verify()
    assert record.journal_sequence == 2
    assert record.journal_entry_hash

    entries = journal.entries()
    assert entries[1].event_type == PREREGISTRATION_EVENT_TYPE
    payload = entries[1].payload
    assert payload["specification_hash"] == record.specification_hash
    assert payload["specification_id"] == "SPEC-1"
    assert payload["frozen_at"] == FREEZE_TIME.isoformat()
    assert payload["authority"] == "A1_AUTHORISED_SPECIFICATION"
    assert payload["estimand"] == "risk difference in retraction rate"


def test_freeze_event_type_is_a_protected_authority_type():
    assert PREREGISTRATION_EVENT_TYPE in PROTECTED_TYPES


def test_find_freeze_entries_filters_by_specification(tmp_path):
    journal = make_journal(tmp_path)
    freeze(make_spec(), journal=journal, frozen_at=FREEZE_TIME)
    freeze(make_spec(specification_id="SPEC-2"), journal=journal, frozen_at=FREEZE_TIME)
    journal.append("SOURCE_HARVEST_COMPLETED", {"source": "openalex"})

    assert len(find_freeze_entries(journal)) == 2
    only = find_freeze_entries(journal, "SPEC-2")
    assert len(only) == 1
    assert only[0].payload["specification_id"] == "SPEC-2"


def test_confirmatory_refused_when_journal_chain_is_broken(tmp_path):
    journal = make_journal(tmp_path)
    spec = make_spec()
    record = freeze(spec, journal=journal, frozen_at=FREEZE_TIME)

    lines = journal.path.read_text(encoding="utf-8").splitlines()
    journal.path.write_text(lines[0].replace("SPEC-1", "SPEC-9") + "\n", encoding="utf-8")

    decision = analysis_is_confirmatory(
        spec, record, data_retrieved_at=RETRIEVAL_TIME, journal=journal
    )
    assert not decision.permitted
    assert decision.reasons == [REASON_JOURNAL_CHAIN_BROKEN]


def test_confirmatory_permitted_with_intact_journal(tmp_path):
    journal = make_journal(tmp_path)
    spec = make_spec()
    record = freeze(spec, journal=journal, frozen_at=FREEZE_TIME)
    assert analysis_is_confirmatory(
        spec, record, data_retrieved_at=RETRIEVAL_TIME, journal=journal
    ).permitted


# --- model validation ------------------------------------------------------------------------


def test_specification_forbids_extra_fields():
    with pytest.raises(Exception):
        make_spec(unexpected_field="nope")


def test_selection_rule_type_is_normalised_and_constrained():
    rule = SelectionRule(rule_id="R", rule_type="inclusion", description="d")
    assert rule.rule_type == "INCLUSION"
    with pytest.raises(Exception):
        SelectionRule(rule_id="R", rule_type="MAYBE", description="d")


def test_frozen_record_is_immutable():
    record = freeze(make_spec(), frozen_at=FREEZE_TIME)
    with pytest.raises(Exception):
        record.specification_hash = "0" * 64
