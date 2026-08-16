from __future__ import annotations

import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterable

from oslt_research.domain.enums import AuthorityLevel
from oslt_research.domain.models import EvidenceObject, KernelResult, RunManifest, SynthesisOutcome
from oslt_research.governance.authority import (
    NOT_PREREGISTERED,
    AuthorityPatch,
    AuthorityRecord,
    apply_authority_patch,
)
from oslt_research.ontology.entities import InstitutionalEntity, InstitutionalRelation


def _dataclass_payload(item: object) -> dict[str, object]:
    """Serialise a frozen governance dataclass, keeping enum members as their values.

    Governance dataclasses carry StrEnum fields; ``asdict`` leaves them as enum members,
    which json refuses. Converting here rather than at every call site means a new field
    cannot be persisted as a repr string by accident.
    """

    from dataclasses import asdict, is_dataclass
    from enum import Enum

    if not is_dataclass(item):
        raise TypeError(f"NOT_A_DATACLASS: {type(item)!r}")
    payload = asdict(item)  # type: ignore[arg-type]
    return {
        key: (value.value if isinstance(value, Enum) else value)
        for key, value in payload.items()
    }


class MissingRunManifestError(RuntimeError):
    """Raised when a result is persisted for a run that has no sealed manifest.

    Manifest sealing used to be a parallel step in one pipeline that any other caller could
    simply forget - and every caller did, which is why `run_manifests` held zero rows while
    `kernel_results` and `synthesis_outcomes` named a run. Making the manifest a precondition
    of persistence means a result that cannot be traced to the run that produced it now
    fails loudly at the write instead of surviving as an untraceable row."""


class SQLiteStore:
    """Small deterministic persistence layer for local/public-data research runs.

    Restricted data environments should implement the same result contracts inside their approved
    environment rather than exporting raw records into this store.
    """

    def __init__(self, path: str | Path = "runtime/oslt.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @contextmanager
    def transaction(self):
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialise(self) -> None:
        with self.transaction() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS evidence_objects (
                    evidence_id TEXT PRIMARY KEY,
                    dependency_family TEXT NOT NULL,
                    lane TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    admitted INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS run_manifests (
                    run_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS authority_records (
                    object_id TEXT NOT NULL,
                    object_type TEXT NOT NULL,
                    authority INTEGER NOT NULL,
                    value_json TEXT NOT NULL,
                    PRIMARY KEY (object_id, object_type)
                );

                CREATE TABLE IF NOT EXISTS kernel_results (
                    result_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    proposition_id TEXT NOT NULL,
                    kernel_name TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_kernel_results_run
                    ON kernel_results(run_id);
                CREATE INDEX IF NOT EXISTS idx_kernel_results_proposition
                    ON kernel_results(proposition_id);

                CREATE TABLE IF NOT EXISTS synthesis_outcomes (
                    synthesis_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS institutional_entities (
                    entity_id TEXT PRIMARY KEY,
                    canonical_name TEXT NOT NULL,
                    system_domain TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    dependency_family TEXT NOT NULL,
                    admitted INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_entities_family
                    ON institutional_entities(dependency_family);

                CREATE TABLE IF NOT EXISTS institutional_relations (
                    relation_id TEXT PRIMARY KEY,
                    source_entity_id TEXT NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    valid_from TEXT,
                    dependency_family TEXT NOT NULL,
                    admitted INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_relations_family
                    ON institutional_relations(dependency_family);
                CREATE INDEX IF NOT EXISTS idx_relations_endpoints
                    ON institutional_relations(source_entity_id, target_entity_id);
                """
            )

    def save_evidence(self, evidence: EvidenceObject) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO evidence_objects(
                    evidence_id, dependency_family, lane, source_id, admitted, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(evidence_id) DO UPDATE SET
                    dependency_family=excluded.dependency_family,
                    lane=excluded.lane,
                    source_id=excluded.source_id,
                    admitted=excluded.admitted,
                    payload_json=excluded.payload_json
                """,
                (
                    evidence.evidence_id,
                    evidence.dependency_family,
                    evidence.lane.value,
                    evidence.provenance.source_id,
                    int(evidence.admitted),
                    evidence.model_dump_json(),
                ),
            )

    def save_evidence_many(self, evidence: Iterable[EvidenceObject]) -> None:
        for item in evidence:
            self.save_evidence(item)

    def list_evidence(self, *, admitted_only: bool = False) -> list[EvidenceObject]:
        query = "SELECT payload_json FROM evidence_objects"
        params: tuple[object, ...] = ()
        if admitted_only:
            query += " WHERE admitted = ?"
            params = (1,)
        query += " ORDER BY evidence_id"
        with closing(self.connect()) as connection:
            rows = connection.execute(query, params).fetchall()
        return [EvidenceObject.model_validate_json(row["payload_json"]) for row in rows]

    # ----------------------------------------------------------- authority lattice

    _AUTHORITY_DDL = """
        CREATE TABLE IF NOT EXISTS authority_records (
            object_id TEXT NOT NULL,
            object_type TEXT NOT NULL,
            authority INTEGER NOT NULL,
            value_json TEXT NOT NULL,
            PRIMARY KEY (object_id, object_type)
        )
    """

    def get_authority(self, object_id: str, object_type: str) -> AuthorityRecord | None:
        """The authority level currently recorded for an object, or None if never claimed.

        None is not "unauthorised" - it is "no claim yet", which the lattice treats as an
        open slot. It is deliberately distinct from a recorded low authority, because the
        two demand different answers when a higher-authority actor arrives.
        """

        with closing(self.connect()) as connection:
            connection.execute(self._AUTHORITY_DDL)
            row = connection.execute(
                """
                SELECT object_id, object_type, authority, value_json
                FROM authority_records WHERE object_id = ? AND object_type = ?
                """,
                (object_id, object_type),
            ).fetchone()
        if row is None:
            return None
        return AuthorityRecord(
            object_id=row["object_id"],
            object_type=row["object_type"],
            authority=AuthorityLevel(row["authority"]),
            value=json.loads(row["value_json"]),
        )

    def apply_authority(self, patch: AuthorityPatch) -> AuthorityRecord:
        """Run one mutation through the lattice and persist the resulting authority claim.

        This is the enforcement point the lattice never had: `apply_authority_patch` was a
        pure function nothing called, so no persisted object carried an authority level and
        PROTECTED_TYPES gated nothing. Routing the mutation through the store means the
        previous claim is real state that a later, lower-authority writer collides with,
        rather than an argument the caller supplies about itself.

        Raises AuthorityError (from the lattice) - deliberately not caught here, because a
        refused governance mutation must abort the write rather than downgrade it.
        """

        existing = self.get_authority(patch.object_id, patch.object_type)
        record = apply_authority_patch(existing, patch)
        with self.transaction() as connection:
            connection.execute(self._AUTHORITY_DDL)
            connection.execute(
                """
                INSERT INTO authority_records(object_id, object_type, authority, value_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(object_id, object_type) DO UPDATE SET
                    authority=excluded.authority,
                    value_json=excluded.value_json
                """,
                (
                    record.object_id,
                    record.object_type,
                    int(record.authority),
                    json.dumps(record.value, sort_keys=True, default=str),
                ),
            )
        return record

    # ------------------------------------------------------------------- run manifests

    def save_run(
        self,
        manifest: RunManifest,
        *,
        authority: AuthorityLevel,
        explicit_human_authorisation: bool = False,
    ) -> None:
        """Seal a run manifest, through the authority lattice.

        `authority` is required with no default: the authority under which a run was sealed
        is precisely the fact that must not be guessed, and any default here would be a
        governance value invented by the persistence layer.

        A manifest that binds a run to a frozen preregistration is a PREREGISTERED_SPECIFICATION
        mutation and therefore protected: an A3 pipeline computation cannot declare its own run
        confirmatory without explicit human authorisation. A manifest that records
        NOT_PREREGISTERED claims nothing and is not protected, but its authority is still
        recorded, so a later lower-authority writer cannot silently overwrite a sealed run.
        """

        object_type = (
            "PREREGISTERED_SPECIFICATION"
            if manifest.preregistration_ref not in (None, NOT_PREREGISTERED)
            else "RUN_MANIFEST"
        )
        self.apply_authority(
            AuthorityPatch(
                object_id=manifest.run_id,
                object_type=object_type,
                proposer_authority=authority,
                value={
                    "preregistration_ref": manifest.preregistration_ref,
                    "repository_commit": manifest.repository_commit,
                    "constitution_hash": manifest.constitution_hash,
                },
                explicit_human_authorisation=explicit_human_authorisation,
            )
        )
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO run_manifests(run_id, payload_json) VALUES (?, ?)
                ON CONFLICT(run_id) DO UPDATE SET payload_json=excluded.payload_json
                """,
                (manifest.run_id, manifest.model_dump_json()),
            )

    def require_run_manifest(self, run_id: str) -> None:
        """Fail closed unless `run_id` names a sealed manifest.

        Called before any result is written. Reproducibility that depends on the caller
        remembering a second step is not a control; this makes it one.
        """

        if self.get_run(run_id) is None:
            raise MissingRunManifestError(
                f"NO_RUN_MANIFEST_SEALED_FOR_RUN: {run_id!r}. Seal it with "
                "save_run(build_run_manifest(...)) before persisting any result for this run."
            )

    def get_run(self, run_id: str) -> RunManifest | None:
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT payload_json FROM run_manifests WHERE run_id = ?", (run_id,)
            ).fetchone()
        return RunManifest.model_validate_json(row["payload_json"]) if row else None


    # ------------------------------------------------------------ ontology layer

    def save_entity(self, entity: InstitutionalEntity) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO institutional_entities (
                    entity_id, canonical_name, system_domain, jurisdiction,
                    dependency_family, admitted, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_id) DO UPDATE SET
                    canonical_name=excluded.canonical_name,
                    system_domain=excluded.system_domain,
                    jurisdiction=excluded.jurisdiction,
                    dependency_family=excluded.dependency_family,
                    admitted=excluded.admitted,
                    payload_json=excluded.payload_json
                """,
                (
                    entity.entity_id,
                    entity.canonical_name,
                    entity.system_domain.value,
                    entity.jurisdiction,
                    entity.dependency_family,
                    int(entity.admitted),
                    entity.model_dump_json(),
                ),
            )

    def save_entities(self, entities: Iterable[InstitutionalEntity]) -> None:
        for entity in entities:
            self.save_entity(entity)

    def list_entities(self, *, admitted_only: bool = False) -> list[InstitutionalEntity]:
        query = "SELECT payload_json FROM institutional_entities"
        if admitted_only:
            query += " WHERE admitted = 1"
        with closing(self.connect()) as connection:
            rows = connection.execute(query).fetchall()
        return [InstitutionalEntity.model_validate_json(row["payload_json"]) for row in rows]

    def save_relation(self, relation: InstitutionalRelation) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO institutional_relations (
                    relation_id, source_entity_id, target_entity_id, relation_type,
                    valid_from, dependency_family, admitted, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(relation_id) DO UPDATE SET
                    source_entity_id=excluded.source_entity_id,
                    target_entity_id=excluded.target_entity_id,
                    relation_type=excluded.relation_type,
                    valid_from=excluded.valid_from,
                    dependency_family=excluded.dependency_family,
                    admitted=excluded.admitted,
                    payload_json=excluded.payload_json
                """,
                (
                    relation.relation_id,
                    relation.source_entity_id,
                    relation.target_entity_id,
                    relation.relation_type.value,
                    relation.valid_from.isoformat() if relation.valid_from else None,
                    relation.dependency_family,
                    int(relation.admitted),
                    relation.model_dump_json(),
                ),
            )

    def save_relations(self, relations: Iterable[InstitutionalRelation]) -> None:
        for relation in relations:
            self.save_relation(relation)

    def list_relations(self, *, admitted_only: bool = False) -> list[InstitutionalRelation]:
        query = "SELECT payload_json FROM institutional_relations"
        if admitted_only:
            query += " WHERE admitted = 1"
        with closing(self.connect()) as connection:
            rows = connection.execute(query).fetchall()
        return [InstitutionalRelation.model_validate_json(row["payload_json"]) for row in rows]

    def save_kernel_result(self, result: KernelResult) -> None:
        self.require_run_manifest(result.run_id)
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO kernel_results(
                    result_id, run_id, proposition_id, kernel_name, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(result_id) DO UPDATE SET
                    run_id=excluded.run_id,
                    proposition_id=excluded.proposition_id,
                    kernel_name=excluded.kernel_name,
                    payload_json=excluded.payload_json
                """,
                (
                    result.result_id,
                    result.run_id,
                    result.proposition_id,
                    result.kernel_name,
                    result.model_dump_json(),
                ),
            )

    def list_kernel_results(self, run_id: str) -> list[KernelResult]:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT payload_json FROM kernel_results WHERE run_id = ? ORDER BY result_id",
                (run_id,),
            ).fetchall()
        return [KernelResult.model_validate_json(row["payload_json"]) for row in rows]

    def save_synthesis(self, outcome: SynthesisOutcome) -> None:
        self.require_run_manifest(outcome.run_id)
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO synthesis_outcomes(synthesis_id, run_id, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(synthesis_id) DO UPDATE SET
                    run_id=excluded.run_id,
                    payload_json=excluded.payload_json
                """,
                (outcome.synthesis_id, outcome.run_id, outcome.model_dump_json()),
            )

    def get_synthesis(self, synthesis_id: str) -> SynthesisOutcome | None:
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT payload_json FROM synthesis_outcomes WHERE synthesis_id = ?",
                (synthesis_id,),
            ).fetchone()
        return SynthesisOutcome.model_validate_json(row["payload_json"]) if row else None

    # ------------------------------------------------- feasibility census + design cost

    _FEASIBILITY_DDL = """
        CREATE TABLE IF NOT EXISTS feasibility_censuses (
            census_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            assessed_at TEXT NOT NULL,
            registry_digest_json TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS proposition_feasibility (
            census_id TEXT NOT NULL,
            proposition_id TEXT NOT NULL,
            model_family TEXT NOT NULL,
            reachability TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (census_id, proposition_id)
        );

        CREATE INDEX IF NOT EXISTS idx_feasibility_reachability
            ON proposition_feasibility(reachability);

        CREATE TABLE IF NOT EXISTS design_requirements (
            census_id TEXT NOT NULL,
            proposition_id TEXT NOT NULL,
            reachability TEXT NOT NULL,
            claim_tier TEXT NOT NULL,
            epistemic_status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (census_id, proposition_id)
        );
    """

    def save_feasibility_census(
        self,
        *,
        census_id: str,
        run_id: str,
        assessed_at: str,
        registry_digest: dict[str, str],
        summary: dict[str, object],
        results: Iterable[object],
        requirements: Iterable[object] = (),
    ) -> None:
        """Persist a census, its per-proposition rows and any priced designs.

        Requires a sealed run manifest, exactly as `save_kernel_result` does. The census is
        quoted as a governance fact - "16 of 64 propositions are testable" gates what the
        project attempts - and a governance fact whose code version and registry version are
        unrecorded cannot be re-derived when it is later disputed. The registry digest is
        stored too, so a disagreement can be attributed to an input change rather than argued
        about.
        """

        self.require_run_manifest(run_id)
        if not registry_digest:
            raise ValueError(
                "REGISTRY_DIGEST_REQUIRED: a census with unrecorded inputs is not reproducible"
            )

        with self.transaction() as connection:
            connection.executescript(self._FEASIBILITY_DDL)
            connection.execute(
                """
                INSERT INTO feasibility_censuses(
                    census_id, run_id, assessed_at, registry_digest_json, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(census_id) DO UPDATE SET
                    run_id=excluded.run_id,
                    assessed_at=excluded.assessed_at,
                    registry_digest_json=excluded.registry_digest_json,
                    payload_json=excluded.payload_json
                """,
                (
                    census_id,
                    run_id,
                    assessed_at,
                    json.dumps(registry_digest, sort_keys=True),
                    json.dumps(summary, sort_keys=True, default=str),
                ),
            )
            for item in results:
                connection.execute(
                    """
                    INSERT INTO proposition_feasibility(
                        census_id, proposition_id, model_family, reachability, payload_json
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(census_id, proposition_id) DO UPDATE SET
                        model_family=excluded.model_family,
                        reachability=excluded.reachability,
                        payload_json=excluded.payload_json
                    """,
                    (
                        census_id,
                        item.proposition_id,
                        item.model_family,
                        item.reachability.value,
                        json.dumps(_dataclass_payload(item), sort_keys=True, default=str),
                    ),
                )
            for requirement in requirements:
                connection.execute(
                    """
                    INSERT INTO design_requirements(
                        census_id, proposition_id, reachability, claim_tier,
                        epistemic_status, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(census_id, proposition_id) DO UPDATE SET
                        reachability=excluded.reachability,
                        claim_tier=excluded.claim_tier,
                        epistemic_status=excluded.epistemic_status,
                        payload_json=excluded.payload_json
                    """,
                    (
                        census_id,
                        requirement.proposition_id,
                        requirement.reachability.value,
                        requirement.claim_tier.value,
                        requirement.epistemic_status.value,
                        json.dumps(_dataclass_payload(requirement), sort_keys=True, default=str),
                    ),
                )

    def get_feasibility_census(self, census_id: str) -> dict[str, object] | None:
        with closing(self.connect()) as connection:
            connection.executescript(self._FEASIBILITY_DDL)
            row = connection.execute(
                """
                SELECT census_id, run_id, assessed_at, registry_digest_json, payload_json
                FROM feasibility_censuses WHERE census_id = ?
                """,
                (census_id,),
            ).fetchone()
            if row is None:
                return None
            rows = connection.execute(
                """
                SELECT payload_json FROM proposition_feasibility
                WHERE census_id = ? ORDER BY proposition_id
                """,
                (census_id,),
            ).fetchall()
        return {
            "census_id": row["census_id"],
            "run_id": row["run_id"],
            "assessed_at": row["assessed_at"],
            "registry_digest": json.loads(row["registry_digest_json"]),
            "summary": json.loads(row["payload_json"]),
            "results": [json.loads(item["payload_json"]) for item in rows],
        }

    def latest_feasibility_census_id(self) -> str | None:
        with closing(self.connect()) as connection:
            connection.executescript(self._FEASIBILITY_DDL)
            row = connection.execute(
                "SELECT census_id FROM feasibility_censuses ORDER BY assessed_at DESC LIMIT 1"
            ).fetchone()
        return row["census_id"] if row else None

    # ------------------------------------------------------------------ claim release

    _CLAIM_RELEASE_DDL = """
        CREATE TABLE IF NOT EXISTS claim_release_assessments (
            claim_ref TEXT NOT NULL,
            run_id TEXT NOT NULL,
            source_document TEXT NOT NULL,
            declared_tier TEXT,
            tier_source TEXT NOT NULL,
            released INTEGER NOT NULL,
            wording_acceptable INTEGER,
            assessed_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (claim_ref, run_id)
        );

        CREATE INDEX IF NOT EXISTS idx_claim_release_released
            ON claim_release_assessments(released);

        CREATE TABLE IF NOT EXISTS released_claims (
            claim_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            proposition_id TEXT NOT NULL,
            claim_tier TEXT NOT NULL,
            release_manifest_hash TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
    """

    def save_claim_assessment(self, assessment: object, *, run_id: str, assessed_at: str) -> None:
        """Persist one release decision - refusals included, especially refusals.

        Storing only successes would turn the release table into a list of things that
        passed, with no record that anything was ever refused or why. The refusals are the
        audit trail; a claim released later has to be visibly a change from a recorded
        refusal, rather than an absence that quietly became a presence.

        `declared_tier` is stored as SQL NULL when the source document declared none. NULL
        here means "the document never said", which is not the same as any tier value, and
        the schema keeps it not the same.
        """

        self.require_run_manifest(run_id)
        record = assessment.as_record()
        wording_acceptable = record["wording_acceptable"]
        with self.transaction() as connection:
            connection.executescript(self._CLAIM_RELEASE_DDL)
            connection.execute(
                """
                INSERT INTO claim_release_assessments(
                    claim_ref, run_id, source_document, declared_tier, tier_source,
                    released, wording_acceptable, assessed_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(claim_ref, run_id) DO UPDATE SET
                    source_document=excluded.source_document,
                    declared_tier=excluded.declared_tier,
                    tier_source=excluded.tier_source,
                    released=excluded.released,
                    wording_acceptable=excluded.wording_acceptable,
                    assessed_at=excluded.assessed_at,
                    payload_json=excluded.payload_json
                """,
                (
                    assessment.claim_ref,
                    run_id,
                    assessment.source_document,
                    record["declared_tier"],
                    assessment.tier_source,
                    int(assessment.released),
                    None if wording_acceptable is None else int(bool(wording_acceptable)),
                    assessed_at,
                    json.dumps(record, sort_keys=True, default=str),
                ),
            )
            if assessment.claim is not None:
                claim = assessment.claim
                connection.execute(
                    """
                    INSERT INTO released_claims(
                        claim_id, run_id, proposition_id, claim_tier,
                        release_manifest_hash, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(claim_id) DO UPDATE SET
                        run_id=excluded.run_id,
                        proposition_id=excluded.proposition_id,
                        claim_tier=excluded.claim_tier,
                        release_manifest_hash=excluded.release_manifest_hash,
                        payload_json=excluded.payload_json
                    """,
                    (
                        claim.claim_id,
                        run_id,
                        claim.proposition_id,
                        claim.claim_tier.value,
                        claim.release_manifest_hash,
                        claim.model_dump_json(),
                    ),
                )

    def list_claim_assessments(self, run_id: str | None = None) -> list[dict[str, object]]:
        query = "SELECT payload_json FROM claim_release_assessments"
        params: tuple[object, ...] = ()
        if run_id is not None:
            query += " WHERE run_id = ?"
            params = (run_id,)
        query += " ORDER BY claim_ref"
        with closing(self.connect()) as connection:
            connection.executescript(self._CLAIM_RELEASE_DDL)
            rows = connection.execute(query, params).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]
