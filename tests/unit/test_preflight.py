from pathlib import Path

from oslt_research.governance.preflight import run_preflight


ROOT = Path(__file__).resolve().parents[2]


def test_repository_preflight_passes():
    report = run_preflight(ROOT)
    assert report.passed, report.as_dict()
    assert report.findings[0].code == "PREFLIGHT_PASS"


def test_gitignored_env_file_does_not_fail_the_gate(tmp_path):
    """The project ships .env.example and gitignores .env; following that setup
    must not break its own preflight gate."""

    from oslt_research.governance.preflight import _is_git_ignored

    root = Path(__file__).resolve().parents[2]
    assert _is_git_ignored(root / ".env", root) is True
    assert _is_git_ignored(root / "README.md", root) is False


def test_env_gate_fails_closed_where_git_cannot_answer(tmp_path):
    """Outside a git repository nothing is known to be ignored, so the file is flagged."""

    from oslt_research.governance.preflight import _is_git_ignored

    (tmp_path / "pyproject.toml").write_text('name = "oslt-research-engine"\n', encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=x\n", encoding="utf-8")
    assert _is_git_ignored(tmp_path / ".env", tmp_path) is False
    codes = [item.code for item in run_preflight(tmp_path).findings]
    assert "ENV_FILE_PRESENT" in codes
