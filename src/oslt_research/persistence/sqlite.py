from __future__ import annotations

import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterable

from oslt_research.domain.models import EvidenceObject, KernelResult, RunManifest, SynthesisOutcome
from oslt_research.ontology.entities import InstitutionalEntity, InstitutionalRelation


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

    def save_run(self, manifest: RunManifest) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO run_manifests(run_id, payload_json) VALUES (?, ?)
                ON CONFLICT(run_id) DO UPDATE SET payload_json=excluded.payload_json
                """,
                (manifest.run_id, manifest.model_dump_json()),
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
