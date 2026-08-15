from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from oslt_research.evidence.provenance import sha256_bytes
from oslt_research.pipelines.registries import registry_summary


# Directories that are gitignored build/environment artefacts rather than repository
# payload. The secret-filename gate exists to stop credentials entering the repository,
# and nothing under these paths can enter it, so scanning them only yields false
# positives (e.g. certifi ships cacert.pem inside .venv, which the Makefile install
# target creates in the repository root).
EXCLUDED_SCAN_DIRECTORIES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        ".tox",
        ".nox",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "htmlcov",
        "dist",
        "build",
    }
)


def _is_scannable(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    return not any(
        part in EXCLUDED_SCAN_DIRECTORIES or part.endswith(".egg-info")
        for part in relative.parts
    )


@dataclass(frozen=True)
class PreflightFinding:
    code: str
    severity: str
    message: str
    path: str | None = None


@dataclass(frozen=True)
class PreflightReport:
    root: str
    findings: list[PreflightFinding]

    @property
    def passed(self) -> bool:
        return not any(item.severity == "FAIL" for item in self.findings)

    def as_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "passed": self.passed,
            "findings": [item.__dict__ for item in self.findings],
        }


def _is_git_ignored(path: Path, root: Path) -> bool:
    """True when git would refuse to track this path.

    The secret gate exists to stop credentials entering the repository. A gitignored file
    cannot enter it, so flagging one is a false positive - the same reasoning that removed
    .venv from the scan. It matters here because the project ships a .env.example and
    gitignores .env, so following its own documented setup used to fail its own gate.

    Fails closed: if git cannot answer, the file is treated as scannable.
    """

    try:
        result = subprocess.run(
            ["git", "check-ignore", "--quiet", str(path)],
            cwd=str(root),
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _check_identity(root: Path) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return [PreflightFinding("NOT_OSLT_REPOSITORY", "FAIL", "pyproject.toml missing")]
    text = pyproject.read_text(encoding="utf-8")
    if 'name = "oslt-research-engine"' not in text:
        findings.append(
            PreflightFinding(
                "WRONG_REPOSITORY_IDENTITY",
                "FAIL",
                "pyproject does not identify oslt-research-engine",
                str(pyproject),
            )
        )
    return findings


def _check_registries(root: Path) -> list[PreflightFinding]:
    summary = registry_summary(root / "registries")
    return [
        PreflightFinding("REGISTRY_INVALID", "FAIL", failure, "registries")
        for failure in summary.failures
    ]


def _check_reference_manifest(root: Path) -> list[PreflightFinding]:
    manifest_path = root / "docs/reference/v2.4-rc1/MANIFEST.sha256.json"
    if not manifest_path.exists():
        return [
            PreflightFinding(
                "REFERENCE_MANIFEST_MISSING",
                "FAIL",
                "immutable v2.4 lineage manifest is absent",
                str(manifest_path),
            )
        ]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [PreflightFinding("REFERENCE_MANIFEST_INVALID", "FAIL", str(exc), str(manifest_path))]

    findings: list[PreflightFinding] = []
    base = manifest_path.parent
    for entry in manifest.get("files", []):
        relative = entry["path"]
        if relative == manifest_path.name:
            continue
        path = base / relative
        if not path.exists():
            findings.append(
                PreflightFinding("REFERENCE_FILE_MISSING", "FAIL", relative, str(path))
            )
            continue
        digest = sha256_bytes(path.read_bytes())
        if digest != entry["sha256"]:
            findings.append(
                PreflightFinding("REFERENCE_HASH_DRIFT", "FAIL", relative, str(path))
            )
    return findings


def _check_data_boundaries(root: Path) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []
    allowed = {".gitkeep", "README.md"}
    for store in ["open", "licensed", "participant", "tre"]:
        folder = root / "data" / store
        if not folder.exists():
            findings.append(
                PreflightFinding("DATA_BOUNDARY_FOLDER_MISSING", "FAIL", store, str(folder))
            )
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.name not in allowed:
                findings.append(
                    PreflightFinding(
                        "RAW_DATA_PRESENT_IN_REPOSITORY",
                        "FAIL",
                        f"Unexpected file in {store} boundary",
                        str(path),
                    )
                )
    return findings


def _check_secret_filenames(root: Path) -> list[PreflightFinding]:
    patterns = [
        re.compile(r"(^|[._-])credentials?([._-]|$)", re.I),
        re.compile(r"(^|[._-])tokens?([._-]|$)", re.I),
        re.compile(r"private[_-]?key", re.I),
        re.compile(r"\.pem$", re.I),
        re.compile(r"\.key$", re.I),
    ]
    findings: list[PreflightFinding] = []
    for path in root.rglob("*"):
        if not path.is_file() or not _is_scannable(path, root):
            continue
        if path.name == ".env.example":
            continue
        if path.name.startswith(".env"):
            if _is_git_ignored(path, root):
                continue
            findings.append(PreflightFinding("ENV_FILE_PRESENT", "FAIL", path.name, str(path)))
        elif any(pattern.search(path.name) for pattern in patterns):
            findings.append(
                PreflightFinding("CREDENTIAL_LIKE_FILENAME", "FAIL", path.name, str(path))
            )
    return findings


def _check_ai_boundary(root: Path) -> list[PreflightFinding]:
    forbidden = [
        re.compile(r"\bfrom\s+openai\b"),
        re.compile(r"\bimport\s+openai\b"),
        re.compile(r"\bfrom\s+anthropic\b"),
        re.compile(r"\bimport\s+anthropic\b"),
        re.compile(r"\bOpenAI\s*\("),
        re.compile(r"\bAnthropic\s*\("),
    ]
    findings: list[PreflightFinding] = []
    source_root = root / "src/oslt_research"
    permitted = source_root / "ai/gateway.py"
    for path in source_root.rglob("*.py"):
        if path == permitted:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            if pattern.search(text):
                findings.append(
                    PreflightFinding(
                        "DIRECT_MODEL_PROVIDER_CALL",
                        "FAIL",
                        f"Provider access must route through {permitted.relative_to(root)}",
                        str(path),
                    )
                )
                break
    return findings


def run_preflight(root: str | Path) -> PreflightReport:
    resolved = Path(root).resolve()
    findings: list[PreflightFinding] = []
    for check in [
        _check_identity,
        _check_registries,
        _check_reference_manifest,
        _check_data_boundaries,
        _check_secret_filenames,
        _check_ai_boundary,
    ]:
        findings.extend(check(resolved))
    if not findings:
        findings.append(PreflightFinding("PREFLIGHT_PASS", "INFO", "All mandatory gates passed"))
    return PreflightReport(root=str(resolved), findings=findings)
