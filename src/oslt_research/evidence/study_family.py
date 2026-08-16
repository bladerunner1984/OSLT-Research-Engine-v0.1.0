from __future__ import annotations

import hashlib
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


#: Titles of conference front-matter and session headers. These are *container* records:
#: they hold no study, so they can neither corroborate nor be corroborated. Clustering them
#: is actively harmful - their heuristic dedup keys degenerate to strings like
#: "abstract:unknown:2025", which would merge unrelated congresses into one "family".
CONTAINER_TITLE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*(scientific\s+)?abstracts?\b", re.I),
    re.compile(r"\bproceedings\b", re.I),
    re.compile(r"\b(oral|poster)\s+(presentations?|abstracts?|sessions?)\b", re.I),
    re.compile(r"\bconference\s+(programme|program|abstracts?)\b", re.I),
    re.compile(r"\b(annual\s+)?(congress|symposium|meeting)\b.*\babstracts?\b", re.I),
)

#: Below this many characters a record has no analysable content of its own.
CONTAINER_CONTENT_CHARS = 200

#: Basis recorded for a record that joined no family on any signal.
SINGLETON_BASIS = "SINGLETON_NO_SIGNAL"

#: Basis recorded for a conference container record held out of clustering.
CONTAINER_BASIS = "CONTAINER_RECORD_NOT_A_STUDY"


def is_container_record(item: EvidenceObject) -> bool:
    """True when the record is conference front-matter rather than a study.

    Requires both a container-shaped title and near-empty content: a real paper whose
    title happens to mention "proceedings" still carries an abstract.
    """

    if len((item.content or "").strip()) >= CONTAINER_CONTENT_CHARS:
        return False
    title = item.title or ""
    return any(pattern.search(title) for pattern in CONTAINER_TITLE_PATTERNS)


def family_key(members: Iterable[str]) -> str:
    """Derive a family key from cluster membership, never from a record identifier.

    A key that is just the DOI cannot be told apart from the dedup key, so a pipeline that
    silently stopped clustering would look identical to one that clustered and found
    nothing. Hashing the membership makes even a singleton visibly a family of one.
    """

    digest = hashlib.sha256("|".join(sorted(members)).encode("utf-8")).hexdigest()
    return f"family:{digest[:16]}"


def dedup_key_of(item: EvidenceObject) -> str:
    """The naive identifier key (DOI/PMID/heuristic) this record was harvested under.

    Kept in metadata because ``dependency_family`` is overwritten with the resolved family:
    without it, two records sharing a DOI but resolved in different batches could never be
    merged by a later corpus-wide pass.
    """

    return str(item.metadata.get("dedup_key") or item.dependency_family)


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
        # "Thompson L" and "Gillberg C." are surname-first with a trailing initial, the
        # dominant PubMed/Europe PMC form. Taking the last token as the surname there
        # produces keys like "l,t" whose collisions are between *initials*, which merged
        # unrelated papers on the author rule. Detect the trailing initial explicitly.
        if len(parts) > 1 and len(parts[-1].strip(".")) <= 2:
            surname, rest = parts[0], " ".join(parts[1:])
        else:
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
    #: family_id -> the signals that formed it, so a successor can tell a family built on a
    #: shared trial registration from the much weaker author-overlap kind.
    bases: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def family_count(self) -> int:
        return len(self.families)

    @property
    def collapse_rate(self) -> float:
        """Fraction of records absorbed into a family with another record."""

        if not self.raw_count:
            return 0.0
        return 1.0 - (self.family_count / self.raw_count)

    def size_distribution(self) -> dict[int, int]:
        """family size -> how many families have that size."""

        counts: dict[int, int] = defaultdict(int)
        for members in self.families.values():
            counts[len(members)] += 1
        return dict(sorted(counts.items()))

    def basis_counts(self) -> dict[str, int]:
        """How many families were formed on each signal (a family may have several)."""

        counts: dict[str, int] = defaultdict(int)
        for basis in self.bases.values():
            for signal in basis:
                counts[signal] += 1
        return dict(sorted(counts.items()))

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
        all_items = list(evidence)
        containers = [item for item in all_items if is_container_record(item)]
        items = [item for item in all_items if not is_container_record(item)]
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
            ("SAME_DEDUP_KEY", lambda item: {dedup_key_of(item)}),
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

        signals_by_member: dict[str, set[str]] = defaultdict(set)
        for link in links:
            signals_by_member[link.left_id].add(link.signal)
            signals_by_member[link.right_id].add(link.signal)

        families: dict[str, list[str]] = {}
        bases: dict[str, tuple[str, ...]] = {}
        for _, members in sorted(clusters.items()):
            ordered = sorted(members)
            key = family_key(ordered)
            families[key] = ordered
            found: set[str] = set()
            for member in ordered:
                found |= signals_by_member.get(member, set())
            bases[key] = tuple(sorted(found)) if found else (SINGLETON_BASIS,)

        # Container records are each their own family with the reason recorded, so they can
        # never be read as corroboration and never merge with one another.
        for item in containers:
            key = family_key([item.evidence_id])
            families[key] = [item.evidence_id]
            bases[key] = (CONTAINER_BASIS,)

        return StudyFamilyResolution(
            families=families,
            links=links,
            raw_count=len(all_items),
            signal_counts=dict(signal_counts),
            bases=bases,
        )

    def apply(self, evidence: Iterable[EvidenceObject]) -> tuple[list[EvidenceObject], StudyFamilyResolution]:
        """Return evidence with dependency_family rewritten to the resolved family."""

        items = list(evidence)
        resolution = self.resolve(items)
        mapping = resolution.family_of()
        updated: list[EvidenceObject] = []
        for item in items:
            family = mapping[item.evidence_id]
            updated.append(
                item.model_copy(
                    update={
                        "dependency_family": family,
                        "metadata": {
                            **item.metadata,
                            # Preserved so a later corpus-wide pass can still see the naive
                            # identifier this record arrived under.
                            "dedup_key": dedup_key_of(item),
                            "dependency_family_basis": list(resolution.bases[family]),
                            "dependency_family_size": len(resolution.families[family]),
                        },
                    }
                )
            )
        return updated, resolution
