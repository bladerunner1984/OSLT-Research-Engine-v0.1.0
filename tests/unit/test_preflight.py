from pathlib import Path

from oslt_research.governance.preflight import run_preflight


ROOT = Path(__file__).resolve().parents[2]


def test_repository_preflight_passes():
    report = run_preflight(ROOT)
    assert report.passed, report.as_dict()
    assert report.findings[0].code == "PREFLIGHT_PASS"
