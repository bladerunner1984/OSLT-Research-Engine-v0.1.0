from pathlib import Path

from oslt_research.domain.enums import ModelFamily
from oslt_research.pipelines.registries import load_hypotheses, registry_summary


ROOT = Path(__file__).resolve().parents[2]


def test_canonical_registry_counts_and_competing_models():
    summary = registry_summary(ROOT / "registries")
    assert summary.valid, summary.failures
    assert summary.counts["hypotheses.csv"] == 64
    assert summary.counts["variables.csv"] == 640
    hypotheses = load_hypotheses(ROOT / "registries/hypotheses.csv")
    assert {item.model_family for item in hypotheses} == set(ModelFamily)
    assert all(item.prediction and item.falsifier for item in hypotheses)


def test_registry_count_drift_fails(tmp_path):
    root = tmp_path / "registries"
    root.mkdir()
    for name in ["hypotheses.csv", "variables.csv", "sources.csv", "methods.csv", "workstreams.csv"]:
        (root / name).write_text("a\n1\n", encoding="utf-8")
    summary = registry_summary(root)
    assert not summary.valid
    assert any("REGISTRY_COUNT_DRIFT" in failure for failure in summary.failures)
