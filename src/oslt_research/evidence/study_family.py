from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from oslt_research.domain.models import EvidenceObject


#: Trial and review registration identifiers. Two records carrying the same registration
#: describe the same study and can never be independent evidence of anything.
REGISTRATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bNCT\d{8}\b", re.I),
    re.compile(r"\bISRCTN\d{8}\b", re.I),
    re.compile(r"\bEudraCT[- ]?\d{4}-\d{6}-\d{2}\b", re.I),
    re.compile(r"\bCRD4?2?\d{10,13}\b", re.I),
    re.compile(r"\bACTRN\d{14}\b", re.I),
    re.compile(r"\bChiCTR[-A-Z]*\d{6,10}\b", re.I),
    re.compile(r"\bDRKS\d{8}\b", re.I),
    re.compile(r"\bNTR\d{3,4}\b", re.I),
)

#: Dataset/biobank accessions that imply a shared analytic sample.
ACCESSION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bGSE\d{4,7}\b"),
    re.compile(r"\bEGA[SD]\d{11}\b"),
    re.compile(r"\bphs\d{6}\b"),
    re.compile(r"\bdoi:10\.5281/zenodo\.\d+\b", re.I),
)


def normalise_author(name: str) -> str:
    """Fold an author name to 'lastname, first-initial'.

    Deliberately coarse. Bibliographic author strings vary wildly between sources, and
    a coarse key that occasionally over-merges two authors is safer here than one that
    silently treats the same research group as independent.
    """

    cleaned = re.sub(r"[^A-Za-z\s,.-]", " ", name).strip()
    if not cleaned:
        return ""
    if "," in cleaned:
        surname, _, rest = cleaned.partition(",")
    else:
        parts = cleaned.split()
        surname, rest = parts[-1], " ".join(parts[:-1])
    surname = surname.strip().casefold()
    initial = ""
    for character in rest.strip():
        if character.isalpha():
            initial = character.casefold()
            break
    return f"{surname},{initial}" if surname else ""


@dataclass(frozen=True)
class FamilyLink:
    """One auditable reason two records were placed in the same dependency family."""

    left_id: str
    right_id: str
    signal: str
    detail: str


@dataclass(frozen=True)
class StudyFamilyResolution:
    families: dict[str, list[str]]
    links: list[FamilyLink]
    raw_count: int
    signal_counts: dict[str, int] = field(default_factory=dict)

    @property
    def family_count(self) -> int:
        return len(self.families)

    @property
    def collapse_rate(self) -> float:
        """Fraction of records absorbed into a family with another record."""

        if not self.raw_count:
            return 0.0
        return 1.0 - (self.family_count / self.raw_count)

    def family_of(self) -> dict[str, str]:
        return {
            evidence_id: family_id
            for family_id, members in self.families.items()
            for evidence_id in members
        }


class StudyFamilyResolver:
    """Cluster evidence into research-dependence families.

    Identifier equality (same DOI) only detects the *same paper retrieved twice*. Research
    dependence is broader: papers reporting the same trial, the same cohort, or produced by
    the same group from the same sample are not independent evidence, and triangulating
    across them manufactures confidence that does not exist.

    The cohort lexicon is deliberately a caller-supplied preregistered parameter rather than
    a built-in list. Which named cohorts dominate a literature is a study design decision
    that belongs in the frozen specification, not a guess baked into the engine.
    """

    def __init__(
        self,
        *,
        cohort_lexicon: Sequence[str] = (),
        min_shared_authors: int = 2,
        author_jaccard_threshold: float = 0.6,
    ):
        if min_shared_authors < 1:
            raise ValueError("min_shared_authors must be at least 1")
        if not 0 < author_jaccard_threshold <= 1:
            raise ValueError("author_jaccard_threshold must be in (0,1]")
        self.cohort_lexicon = tuple(
            term.casefold() for term in cohort_lexicon if term and term.strip()
        )
        self.min_shared_authors = min_shared_authors
        self.author_jaccard_threshold = author_jaccard_threshold

    # ------------------------------------------------------------------ signals

    @staticmethod
    def _searchable_text(item: EvidenceObject) -> str:
        identifiers = item.metadata.get("identifiers") or {}
        identifier_text = " ".join(str(value) for value in identifiers.values())
        return f"{item.title} {item.content} {identifier_text}"

    def registrations(self, item: EvidenceObject) -> set[str]:
        text = self._searchable_text(item)
        found: set[str] = set()
        for pattern in REGISTRATION_PATTERNS:
            found.update(match.group(0).upper().replace(" ", "") for match in pattern.finditer(text))
        return found

    def accessions(self, item: EvidenceObject) -> set[str]:
        text = self._searchable_text(item)
        found: set[str] = set()
        for pattern in ACCESSION_PATTERNS:
            found.update(match.group(0).upper() for match in pattern.finditer(text))
        return found

    def cohorts(self, item: EvidenceObject) -> set[str]:
        if not self.cohort_lexicon:
            return set()
        text = f"{item.title} {item.content}".casefold()
        return {term for term in self.cohort_lexicon if term in text}

    def authors(self, item: EvidenceObject) -> set[str]:
        raw = item.metadata.get("authors") or []
        return {key for key in (normalise_author(str(name)) for name in raw) if key}

    # ------------------------------------------------------------------ resolve

    def resolve(self, evidence: Iterable[EvidenceObject]) -> StudyFamilyResolution:
        items = list(evidence)
        parent: dict[str, str] = {item.evidence_id: item.evidence_id for item in items}
        links: list[FamilyLink] = []
        signal_counts: dict[str, int] = defaultdict(int)

        def find(node: str) -> str:
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        def union(left: str, right: str, signal: str, detail: str) -> None:
            left_root, right_root = find(left), find(right)
            if left_root == right_root:
                return
            parent[max(left_root, right_root)] = min(left_root, right_root)
            links.append(FamilyLink(left, right, signal, detail))
            signal_counts[signal] += 1

        # Exact-identity and shared-sample signals: merge on any single hit.
        for signal, extractor in (
            ("SAME_DEDUP_KEY", lambda item: {item.dependency_family}),
            ("SHARED_TRIAL_REGISTRATION", self.registrations),
            ("SHARED_DATASET_ACCESSION", self.accessions),
            ("SHARED_NAMED_COHORT", self.cohorts),
        ):
            buckets: dict[str, list[str]] = defaultdict(list)
            for item in items:
                for key in extractor(item):
                    buckets[key].append(item.evidence_id)
            for key, members in buckets.items():
                for other in members[1:]:
                    union(members[0], other, signal, key)

        # Author-network overlap: a weaker signal, so it needs both a minimum number of
        # shared authors and a high overlap ratio before it merges anything.
        author_sets = {item.evidence_id: self.authors(item) for item in items}
        by_author: dict[str, list[str]] = defaultdict(list)
        for evidence_id, names in author_sets.items():
            for name in names:
                by_author[name].append(evidence_id)

        considered: set[tuple[str, str]] = set()
        for candidates in by_author.values():
            for index, left in enumerate(candidates):
                for right in candidates[index + 1 :]:
                    pair = (left, right) if left < right else (right, left)
                    if pair in considered:
                        continue
                    considered.add(pair)
                    left_names, right_names = author_sets[left], author_sets[right]
                    shared = left_names & right_names
                    union_size = len(left_names | right_names)
                    if not union_size:
                        continue
                    jaccard = len(shared) / union_size
                    if (
                        len(shared) >= self.min_shared_authors
                        and jaccard >= self.author_jaccard_threshold
                    ):
                        union(
                            pair[0],
                            pair[1],
                            "AUTHOR_NETWORK_OVERLAP",
                            f"shared={len(shared)} jaccard={jaccard:.2f}",
                        )

        clusters: dict[str, list[str]] = defaultdict(list)
        for item in items:
            clusters[find(item.evidence_id)].append(item.evidence_id)

        families = {
            f"family:{root}": sorted(members) for root, members in sorted(clusters.items())
        }
        return StudyFamilyResolution(
            families=families,
            links=links,
            raw_count=len(items),
            signal_counts=dict(signal_counts),
        )

    def apply(self, evidence: Iterable[EvidenceObject]) -> tuple[list[EvidenceObject], StudyFamilyResolution]:
        """Return evidence with dependency_family rewritten to the resolved family."""

        items = list(evidence)
        resolution = self.resolve(items)
        mapping = resolution.family_of()
        updated = [
            item.model_copy(update={"dependency_family": mapping[item.evidence_id]})
            for item in items
        ]
        return updated, resolution
