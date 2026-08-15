from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

from oslt_research.domain.enums import (
    ClaimTier,
    EpistemicStatus,
    FalsifierStatus,
    FindingDirection,
    ModelFamily,
)
from oslt_research.domain.models import CertaintyVector, EvidenceObject, KernelResult, ScopeContext
from oslt_research.evidence.dependency import EvidenceDependencyGraph


@dataclass(frozen=True)
class AcademicCorpusMetrics:
    raw_records: int
    admitted_records: int
    independent_families: int
    source_counts: dict[str, int]
    orientation_counts: dict[str, int]
    registrations: int
    publications: int
    linked_registration_publications: int
    corrections_or_retractions: int
    publication_rates_by_orientation: dict[str, float]

    @property
    def denominator_available(self) -> bool:
        return self.registrations > 0 and bool(self.publication_rates_by_orientation)


class AcademicKnowledgeProductionKernel:
    name = "ACADEMIC_KNOWLEDGE_PRODUCTION"

    @staticmethod
    def metrics(evidence: Iterable[EvidenceObject]) -> AcademicCorpusMetrics:
        items = list(evidence)
        admitted = [item for item in items if item.admitted]
        dependency = EvidenceDependencyGraph.summarise(admitted)
        source_counts = Counter(item.provenance.source_id for item in admitted)
        orientation_counts = Counter(
            str(item.metadata.get("orientation", "NOT_ASSESSABLE")) for item in admitted
        )

        registrations = [
            item
            for item in admitted
            if str(item.metadata.get("record_kind", "publication")).casefold() == "registration"
        ]
        publications = [
            item
            for item in admitted
            if str(item.metadata.get("record_kind", "publication")).casefold() != "registration"
        ]
        linked = sum(
            1
            for item in publications
            if item.metadata.get("registration_id") or item.metadata.get("linked_registration_id")
        )
        corrections = sum(
            1
            for item in admitted
            if item.lane.value == "CORRECTION_RETRACTION"
            or item.metadata.get("is_retracted") is True
            or bool(item.metadata.get("update_to"))
        )

        registration_groups: dict[str, list[EvidenceObject]] = defaultdict(list)
        for item in registrations:
            registration_groups[str(item.metadata.get("orientation", "NOT_ASSESSABLE"))].append(item)
        rates: dict[str, float] = {}
        for orientation, group in registration_groups.items():
            if len(group) < 5:
                continue
            published = sum(1 for item in group if item.metadata.get("published") is True)
            rates[orientation] = published / len(group)

        return AcademicCorpusMetrics(
            raw_records=len(items),
            admitted_records=len(admitted),
            independent_families=dependency.effective_independent_families,
            source_counts=dict(source_counts),
            orientation_counts=dict(orientation_counts),
            registrations=len(registrations),
            publications=len(publications),
            linked_registration_publications=linked,
            corrections_or_retractions=corrections,
            publication_rates_by_orientation=rates,
        )

    @staticmethod
    def _certainty(metrics: AcademicCorpusMetrics) -> CertaintyVector:
        admitted_ratio = metrics.admitted_records / max(1, metrics.raw_records)
        independence_ratio = metrics.independent_families / max(1, metrics.admitted_records)
        denominator = 0.70 if metrics.denominator_available else 0.20
        replication = min(0.75, 0.2 + 0.1 * max(0, len(metrics.source_counts) - 1))
        return CertaintyVector(
            statistical_precision=0.45 if metrics.admitted_records >= 100 else 0.25,
            measurement_validity=0.45,
            temporal_ordering=0.40 if metrics.denominator_available else 0.20,
            causal_identification=0.35 if metrics.denominator_available else 0.10,
            confounding_control=0.30,
            selection_bias_control=denominator,
            missing_data_robustness=0.35,
            specification_stability=0.45,
            source_independence=min(1.0, max(0.1, independence_ratio)),
            cross_method_convergence=0.30,
            replication=replication,
            transportability=0.25,
            publication_selection_control=denominator,
            provenance_completeness=admitted_ratio,
            theory_independence=0.65,
            explanatory_contribution=0.35,
        )

    def analyse(
        self,
        *,
        run_id: str,
        evidence: Iterable[EvidenceObject],
        period: str,
        jurisdiction: str = "MULTI_JURISDICTIONAL",
    ) -> list[KernelResult]:
        items = list(evidence)
        metrics = self.metrics(items)
        certainty = self._certainty(metrics)
        evidence_ids = [item.evidence_id for item in items if item.admitted]
        counter_ids = [
            item.evidence_id
            for item in items
            if item.admitted and item.lane.value in {"CONTRADICT", "RIVAL", "NULL", "BIAS_CRITIQUE"}
        ]
        families = sorted({item.dependency_family for item in items if item.admitted})
        scope = ScopeContext(
            construct="academic knowledge-production selection",
            population="registered and published research records",
            period=period,
            jurisdiction=jurisdiction,
            estimand="orientation-associated difference in publication/funding/citation pathway",
        )

        if not metrics.denominator_available:
            direction_md = FindingDirection.INCONCLUSIVE
            direction_null = FindingDirection.INCONCLUSIVE
            falsifier_md = FalsifierStatus.NOT_TESTED
            falsifier_null = FalsifierStatus.NOT_TESTED
            impacts_md = {
                ModelFamily.MULTIFACTORIAL_DEVELOPMENTAL_INSTITUTIONAL.value: 0.0,
                ModelFamily.NULL_OR_ALTERNATIVE.value: 0.0,
            }
            impacts_null = dict(impacts_md)
            conclusion = (
                "The corpus can describe publication and citation structure, but it lacks a valid "
                "registration/submission denominator and adjusted selection model. Publication bias "
                "or gatekeeping is therefore not identified."
            )
        else:
            rates = list(metrics.publication_rates_by_orientation.values())
            spread = max(rates) - min(rates) if len(rates) >= 2 else 0.0
            if spread >= 0.10:
                direction_md = FindingDirection.SUPPORTS
                direction_null = FindingDirection.WEAKENS
                falsifier_md = FalsifierStatus.NOT_TRIGGERED
                falsifier_null = FalsifierStatus.PARTIALLY_TRIGGERED
                impacts_md = {
                    ModelFamily.MULTIFACTORIAL_DEVELOPMENTAL_INSTITUTIONAL.value: min(1.0, spread),
                    ModelFamily.NULL_OR_ALTERNATIVE.value: -min(1.0, spread),
                }
                impacts_null = dict(impacts_md)
                conclusion = (
                    "Observed orientation-stratified publication rates differ in the available "
                    "registration cohort. This is an association requiring design, quality, field-size "
                    "and dependency adjustment before any direction-bias inference."
                )
            else:
                direction_md = FindingDirection.WEAKENS
                direction_null = FindingDirection.SUPPORTS
                falsifier_md = FalsifierStatus.PARTIALLY_TRIGGERED
                falsifier_null = FalsifierStatus.NOT_TRIGGERED
                impacts_md = {
                    ModelFamily.MULTIFACTORIAL_DEVELOPMENTAL_INSTITUTIONAL.value: -0.25,
                    ModelFamily.NULL_OR_ALTERNATIVE.value: 0.25,
                }
                impacts_null = dict(impacts_md)
                conclusion = (
                    "No large orientation-stratified publication-rate difference is visible in the "
                    "available registration cohort. Smaller or confounded selection effects remain possible."
                )

        common = dict(
            run_id=run_id,
            kernel_name=self.name,
            scope=scope,
            epistemic_status=EpistemicStatus.ASSOCIATION
            if metrics.denominator_available
            else EpistemicStatus.OBSERVATION,
            effect_estimate=None,
            uncertainty=(
                f"records={metrics.admitted_records}; independent_families="
                f"{metrics.independent_families}; registrations={metrics.registrations}"
            ),
            certainty=certainty,
            evidence_ids=evidence_ids,
            counterevidence_ids=counter_ids,
            dependency_families=families,
            claim_tier=ClaimTier.ASSOCIATION_ONLY
            if metrics.denominator_available
            else ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
            narrative=conclusion,
            limitations=[
                "Raw publication or citation counts are not truth measures.",
                "Automated orientation coding requires blinded human validation and error reporting.",
                "Study, cohort, dataset and author-network dependence must be collapsed.",
                "Direction-dependent selection requires an appropriate denominator and controls.",
            ],
        )
        return [
            KernelResult(
                result_id=f"KR-{run_id}-MD11",
                proposition_id="MD11",
                model_family=ModelFamily.MULTIFACTORIAL_DEVELOPMENTAL_INSTITUTIONAL,
                finding_direction=direction_md,
                falsifier_status=falsifier_md,
                model_impacts=impacts_md,
                **common,
            ),
            KernelResult(
                result_id=f"KR-{run_id}-MX14",
                proposition_id="MX14",
                model_family=ModelFamily.NULL_OR_ALTERNATIVE,
                finding_direction=direction_null,
                falsifier_status=falsifier_null,
                model_impacts=impacts_null,
                **common,
            ),
        ]
