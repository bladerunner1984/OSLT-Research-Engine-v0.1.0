from __future__ import annotations

import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterable

from oslt_research.domain.models import EvidenceObject, KernelResult, RunManifest, SynthesisOutcome


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
