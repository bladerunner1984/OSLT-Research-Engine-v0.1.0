from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Mapping

from oslt_research.connectors.base import SourceConnector
from oslt_research.domain.models import RunManifest
from oslt_research.evidence.provenance import sha256_bytes
from oslt_research.governance.authority import NOT_PREREGISTERED
from oslt_research.settings import repository_root


#: Configuration whose content changes what a run means. Hashed individually so a diff
#: points at the file that moved rather than at the run as a whole.
CONFIG_FILES = (
    "config/constitution.yaml",
    "config/data_boundaries.yaml",
    "config/human_review.yaml",
    "config/model_policy.yaml",
)


def _file_hash(path: Path) -> str | None:
    try:
        return sha256_bytes(path.read_bytes())
    except OSError:
        return None


def repository_commit(root: Path | None = None) -> str:
    """Current commit, or a marker when it cannot be determined.

    Never silently returns an empty string: a manifest that claims no commit is a
    manifest nobody can reproduce from, and it should look wrong rather than blank.
    """

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root or repository_root()),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN_NO_GIT"
    commit = result.stdout.strip()
    return commit if result.returncode == 0 and commit else "UNKNOWN_NOT_A_REPOSITORY"


def working_tree_is_clean(root: Path | None = None) -> bool:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root or repository_root()),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and not result.stdout.strip()


def build_run_manifest(
    *,
    run_id: str,
    objective: str,
    proposition_ids: Iterable[str],
    connectors: Iterable[SourceConnector],
    corpus_hashes: Mapping[str, str] | None = None,
    registry_hashes: Mapping[str, str] | None = None,
    preregistration_ref: str,
    model_gateway: str = "DISABLED",
    root: Path | None = None,
) -> RunManifest:
    """Assemble the reproducibility manifest for a run.

    Point 8 of the claim release standard. Records the commit, the hash of every
    configuration file that governs interpretation, the connector versions that produced
    the data, and the interpreter and platform it ran on - enough for someone else to
    determine whether their re-run is the same run.

    A dirty working tree is recorded in the environment rather than raising, because the
    manifest exists to describe what happened, including when what happened was
    unreproducible.

    ``preregistration_ref`` is a required keyword with no default. It previously defaulted to
    ``None`` and no caller ever passed it, so every manifest would have claimed nothing about
    the specification it was testing while looking complete. A run that is genuinely not
    preregistered must say so with :data:`NOT_PREREGISTERED`; silence is not an option.
    """

    if not preregistration_ref:
        raise ValueError(
            "PREREGISTRATION_REF_REQUIRED: pass a specification_id or NOT_PREREGISTERED"
        )

    resolved = root or repository_root()
    configuration_hashes: dict[str, str] = {}
    for relative in CONFIG_FILES:
        digest = _file_hash(resolved / relative)
        if digest:
            configuration_hashes[relative] = digest

    constitution = configuration_hashes.get("config/constitution.yaml", "MISSING")

    return RunManifest(
        run_id=run_id,
        objective=objective,
        proposition_ids=list(proposition_ids),
        preregistration_ref=preregistration_ref,
        repository_commit=repository_commit(resolved),
        constitution_hash=constitution,
        configuration_hashes=configuration_hashes,
        registry_hashes=dict(registry_hashes or {}),
        data_or_corpus_hashes=dict(corpus_hashes or {}),
        connector_versions={
            connector.source_name: connector.connector_version for connector in connectors
        },
        model_gateway=model_gateway,
        environment={
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "working_tree_clean": str(working_tree_is_clean(resolved)).lower(),
        },
    )
