"""Preregistration freeze machinery.

The scientific constitution rule ``objective_and_estimand_locked_before_confirmatory_analysis``
and step 1 of the Pilot 1 protocol both require that the objective, estimand, search concepts and
date windows are fixed *before* the corpus is seen. Without machinery to freeze a specification
that rule is unenforceable: a specification held only in memory can be silently edited after the
data comes back, and nobody downstream can tell the difference between a genuine prediction and a
post-hoc rationalisation.

This module supplies the missing lock:

* :class:`PreregisteredSpecification` — the declarative content that must be fixed.
* :func:`freeze` — canonically hashes it, stamps a timestamp, and writes a protected
  ``PREREGISTERED_SPECIFICATION`` event into the hash-chained research computation journal, so the
  freeze itself is tamper-evident and ordered relative to every other computation event.
* :func:`verify_unchanged` — recomputes the hash and, when it differs, reports *which fields*
  drifted. A bare boolean is not enough: an investigator must be told what changed, and a reviewer
  must be able to distinguish a typo in the narrative from a swapped estimand.
* :func:`analysis_is_confirmatory` — the gate. It refuses when no freeze exists, when the
  specification has drifted, and when the freeze post-dates data retrieval. Freezing after looking
  at the corpus is not preregistration, and a timestamp comparison is the only mechanical way to
  catch it.

A frozen specification carries :class:`AuthorityLevel.A1_AUTHORISED_SPECIFICATION`: it outranks
every model proposal and analysis artefact, so nothing produced downstream may quietly rewrite it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator

from oslt_research.domain.enums import AuthorityLevel
from oslt_research.domain.models import ScopeContext, utc_now
from oslt_research.evidence.journal import JournalEntry, ResearchComputationJournal
from oslt_research.evidence.provenance import canonical_json_hash

# The journal event type. It is one of the PROTECTED_TYPES in governance.authority, so mutating a
# frozen specification requires A2+ authority or explicit human authorisation.
PREREGISTRATION_EVENT_TYPE = "PREREGISTERED_SPECIFICATION"

# Object type used when a frozen specification is routed through the authority gate.
PREREGISTRATION_OBJECT_TYPE = "PREREGISTERED_SPECIFICATION"

# The authority a frozen specification asserts once locked.
PREREGISTRATION_AUTHORITY = AuthorityLevel.A1_AUTHORISED_SPECIFICATION

# --- Refusal reason codes -------------------------------------------------------------------
# Structured codes rather than prose, following the AdmissionDecision pattern in provenance.py:
# a gate that returns free text cannot be tested, counted or audited.
REASON_NO_FREEZE = "NO_PREREGISTRATION_FREEZE"
REASON_SPECIFICATION_DRIFT = "SPECIFICATION_DRIFT_AFTER_FREEZE"
REASON_FREEZE_POSTDATES_RETRIEVAL = "FREEZE_POSTDATES_DATA_RETRIEVAL"
REASON_SPECIFICATION_ID_MISMATCH = "SPECIFICATION_ID_MISMATCH"
REASON_JOURNAL_CHAIN_BROKEN = "JOURNAL_CHAIN_BROKEN"


class PreregistrationError(RuntimeError):
    """Raised when a preregistration operation is structurally impossible."""


class DateWindow(BaseModel):
    """A closed publication/observation window declared in advance.

    Dates are ISO-8601 strings rather than ``date`` objects because the upstream connector layer
    (``HarvestQuery.from_date`` / ``to_date``) speaks strings, and the frozen record must hash the
    same value that is actually sent to the sources.
    """

    model_config = ConfigDict(extra="forbid")

    window_id: str = Field(min_length=1)
    from_date: str = Field(min_length=1)
    to_date: str = Field(min_length=1)
    applies_to: str = Field(default="all_sources", min_length=1)


class SearchConcept(BaseModel):
    """One preregistered search concept and the exact terms that operationalise it."""

    model_config = ConfigDict(extra="forbid")

    concept_id: str = Field(min_length=1)
    concept: str = Field(min_length=1)
    query_terms: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class SelectionRule(BaseModel):
    """An inclusion or exclusion criterion, stated so a third party could apply it unaided."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1)
    rule_type: str = Field(min_length=1)
    description: str = Field(min_length=1)

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, value: str) -> str:
        normalised = value.strip().upper()
        if normalised not in {"INCLUSION", "EXCLUSION"}:
            raise ValueError("rule_type must be INCLUSION or EXCLUSION")
        return normalised


class PreregisteredSpecification(BaseModel):
    """Everything that must be locked before a confirmatory analysis may begin.

    The cohort lexicon is part of the specification because ``StudyFamilyResolver`` uses it to
    collapse dependent studies. Choosing which named cohorts count as one family after seeing the
    corpus is a researcher degree of freedom that directly inflates apparent independence, so it is
    preregistered alongside the estimand rather than tuned during analysis.
    """

    model_config = ConfigDict(extra="forbid")

    specification_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    proposition_ids: list[str] = Field(default_factory=list)
    scope: ScopeContext
    search_concepts: list[SearchConcept] = Field(default_factory=list)
    date_windows: list[DateWindow] = Field(default_factory=list)
    selection_rules: list[SelectionRule] = Field(default_factory=list)
    planned_analysis: str = Field(min_length=1)
    primary_outcome: str = Field(min_length=1)
    cohort_lexicon: list[str] = Field(default_factory=list)
    notes: str = ""

    def canonical_payload(self) -> dict[str, Any]:
        """Return the dict that is hashed.

        ``model_dump(mode="json")`` plus ``canonical_json_hash`` (which sorts keys) makes the hash
        invariant to key ordering, so a specification cannot be made to look unchanged — or
        spuriously changed — by reordering its fields.
        """

        return self.model_dump(mode="json")

    def specification_hash(self) -> str:
        return canonical_json_hash(self.canonical_payload())


class FrozenSpecificationRecord(BaseModel):
    """The immutable receipt for a freeze.

    It deliberately stores the whole hashed payload, not just the digest: drift detection has to
    name the fields that changed, which is impossible from a digest alone.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    specification_id: str = Field(min_length=1)
    specification_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    frozen_at: datetime
    authority: AuthorityLevel = PREREGISTRATION_AUTHORITY
    frozen_payload: dict[str, Any] = Field(default_factory=dict)
    journal_sequence: int | None = None
    journal_entry_hash: str | None = None


@dataclass(frozen=True)
class FieldDrift:
    """One field-level difference between a live specification and its freeze."""

    field_path: str
    frozen_value: Any
    current_value: Any


@dataclass(frozen=True)
class DriftReport:
    """Result of :func:`verify_unchanged`.

    ``unchanged`` is the headline, but ``drifted_fields`` is the part that matters to a reviewer.
    """

    unchanged: bool
    frozen_hash: str
    current_hash: str
    drifted_fields: list[FieldDrift] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def drifted_field_paths(self) -> list[str]:
        return [item.field_path for item in self.drifted_fields]


@dataclass(frozen=True)
class ConfirmatoryDecision:
    """Structured verdict from the confirmatory-analysis gate.

    Mirrors ``AdmissionDecision`` in ``evidence/provenance.py``: a boolean plus machine-readable
    reason codes, so refusals can be surfaced, counted and tested rather than merely logged.
    """

    permitted: bool
    reasons: list[str] = field(default_factory=list)
    drift: DriftReport | None = None

    def __bool__(self) -> bool:  # pragma: no cover - convenience only
        return self.permitted


def _flatten(payload: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested dicts to dotted paths so drift can be reported per field.

    Lists are compared whole rather than element-wise: reporting ``search_concepts`` as drifted is
    honest and stable, whereas index-wise paths shift meaninglessly when an item is inserted.
    """

    if isinstance(payload, dict):
        flattened: dict[str, Any] = {}
        for key in sorted(payload):
            path = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_flatten(payload[key], path))
        return flattened
    return {prefix: payload}


def freeze(
    spec: PreregisteredSpecification,
    *,
    journal: ResearchComputationJournal | None = None,
    frozen_at: datetime | None = None,
) -> FrozenSpecificationRecord:
    """Lock ``spec`` and record the lock.

    The canonical hash is what makes the lock meaningful, and the journal append is what makes it
    checkable by someone who does not trust the caller: the entry is chained to everything already
    journalled, so a freeze cannot later be back-dated into the record without breaking the chain.
    """

    timestamp = frozen_at or utc_now()
    if timestamp.tzinfo is None:
        raise PreregistrationError("frozen_at must be timezone-aware")

    payload = spec.canonical_payload()
    digest = canonical_json_hash(payload)

    sequence: int | None = None
    entry_hash: str | None = None
    if journal is not None:
        entry = journal.append(
            PREREGISTRATION_EVENT_TYPE,
            {
                "specification_id": spec.specification_id,
                "specification_hash": digest,
                "frozen_at": timestamp.isoformat(),
                "authority": PREREGISTRATION_AUTHORITY.name,
                "objective": spec.objective,
                "estimand": spec.scope.estimand,
                "proposition_ids": list(spec.proposition_ids),
            },
        )
        sequence = entry.sequence
        entry_hash = entry.entry_hash

    return FrozenSpecificationRecord(
        specification_id=spec.specification_id,
        specification_hash=digest,
        frozen_at=timestamp,
        authority=PREREGISTRATION_AUTHORITY,
        frozen_payload=payload,
        journal_sequence=sequence,
        journal_entry_hash=entry_hash,
    )


def verify_unchanged(
    spec: PreregisteredSpecification,
    frozen_record: FrozenSpecificationRecord,
) -> DriftReport:
    """Report whether ``spec`` still matches ``frozen_record``, and if not, what moved.

    Hash comparison decides the verdict (key reordering therefore cannot hide a change or fake
    one); the flattened payload diff supplies the human-readable detail.
    """

    current_payload = spec.canonical_payload()
    current_hash = canonical_json_hash(current_payload)

    reasons: list[str] = []
    if spec.specification_id != frozen_record.specification_id:
        reasons.append(REASON_SPECIFICATION_ID_MISMATCH)

    if current_hash == frozen_record.specification_hash and not reasons:
        return DriftReport(
            unchanged=True,
            frozen_hash=frozen_record.specification_hash,
            current_hash=current_hash,
        )

    frozen_flat = _flatten(frozen_record.frozen_payload)
    current_flat = _flatten(current_payload)
    sentinel = object()
    drifted: list[FieldDrift] = []
    for path in sorted(set(frozen_flat) | set(current_flat)):
        frozen_value = frozen_flat.get(path, sentinel)
        current_value = current_flat.get(path, sentinel)
        if frozen_value == current_value:
            continue
        drifted.append(
            FieldDrift(
                field_path=path,
                frozen_value=None if frozen_value is sentinel else frozen_value,
                current_value=None if current_value is sentinel else current_value,
            )
        )

    if drifted and REASON_SPECIFICATION_DRIFT not in reasons:
        reasons.append(REASON_SPECIFICATION_DRIFT)

    return DriftReport(
        unchanged=False,
        frozen_hash=frozen_record.specification_hash,
        current_hash=current_hash,
        drifted_fields=drifted,
        reasons=reasons,
    )


def analysis_is_confirmatory(
    spec: PreregisteredSpecification,
    frozen_record: FrozenSpecificationRecord | None,
    *,
    data_retrieved_at: datetime | Sequence[datetime] | None = None,
    journal: ResearchComputationJournal | None = None,
) -> ConfirmatoryDecision:
    """Decide whether confirmatory analysis may proceed under ``frozen_record``.

    Three independent ways to fail, each a real failure mode of preregistration in practice:

    1. ``NO_PREREGISTRATION_FREEZE`` — nothing was ever locked, so there is no prediction to test
       and any result is exploratory by definition.
    2. ``SPECIFICATION_DRIFT_AFTER_FREEZE`` — something was locked but the live specification no
       longer matches it. The drift report names the fields.
    3. ``FREEZE_POSTDATES_DATA_RETRIEVAL`` — the corpus was retrieved before the specification was
       frozen. Freezing after looking is not preregistration, however sincere the intent, so the
       earliest retrieval timestamp is compared against the freeze.

    ``journal``, when supplied, is additionally chain-verified: a freeze recorded in a tampered
    journal is not evidence of anything.
    """

    reasons: list[str] = []
    drift: DriftReport | None = None

    if frozen_record is None:
        return ConfirmatoryDecision(permitted=False, reasons=[REASON_NO_FREEZE])

    drift = verify_unchanged(spec, frozen_record)
    if not drift.unchanged:
        reasons.extend(drift.reasons or [REASON_SPECIFICATION_DRIFT])

    retrieval_times = _normalise_retrieval_times(data_retrieved_at)
    if retrieval_times:
        earliest = min(retrieval_times)
        if frozen_record.frozen_at > earliest:
            reasons.append(REASON_FREEZE_POSTDATES_RETRIEVAL)

    if journal is not None and not journal.verify():
        reasons.append(REASON_JOURNAL_CHAIN_BROKEN)

    return ConfirmatoryDecision(permitted=not reasons, reasons=reasons, drift=drift)


def _normalise_retrieval_times(
    data_retrieved_at: datetime | Sequence[datetime] | None,
) -> list[datetime]:
    """Coerce retrieval timestamps to an aware-UTC list.

    Naive timestamps are treated as UTC rather than rejected: connector metadata is not always
    tz-stamped, and silently skipping the ordering check would be worse than assuming UTC.
    """

    if data_retrieved_at is None:
        return []
    candidates = (
        [data_retrieved_at] if isinstance(data_retrieved_at, datetime) else list(data_retrieved_at)
    )
    return [
        moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)
        for moment in candidates
    ]


def find_freeze_entries(
    journal: ResearchComputationJournal,
    specification_id: str | None = None,
) -> list[JournalEntry]:
    """Return the freeze events in ``journal``, optionally for one specification.

    Used to answer "was this ever actually preregistered?" from the journal alone, without
    trusting an in-memory record handed over by the caller.
    """

    return [
        entry
        for entry in journal.entries()
        if entry.event_type == PREREGISTRATION_EVENT_TYPE
        and (
            specification_id is None
            or entry.payload.get("specification_id") == specification_id
        )
    ]
