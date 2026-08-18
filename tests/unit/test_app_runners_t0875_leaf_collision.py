"""Direct-call coverage for `clean_runner.run`, `registry_runner.run`, and
`fmt_runner.run` (T-0875): these three share the leaf name `run` with an
unrelated Rust test whose name happens to end in `_run`, so the TEST001
naming-convention fallback credits all three off that single coincidental
match (TEST014, docs/audits/gates-quality.md). Real dedicated calls here
disambiguate the credit onto the actual behavior.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.clean_runner import run as clean_run
from frob.app.config import AppConfig
from frob.app.fmt_runner import run as fmt_run
from frob.app.registry_runner import run as registry_run


def _git(root: Path, *args: str) -> None:
    """Run a `git` subcommand quietly against `root`, raising on failure."""
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """A minimal initialized-and-committed git repo (`clean_runner.run` needs
    to resolve its root against a real repo, unlike the other two runners)."""
    root = tmp_path / "proj"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "src.py").write_text("x = 1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


# frob:tests tests/unit/test_app_runners_t0875_leaf_collision.py::TestCleanRunnerRun.test_dry_run_reports_nothing_to_clean  # noqa: E501
# frob:ticket T-0875


class TestCleanRunnerRun:
    """`clean_runner.run` dry-run/execute wiring over an empty tree."""

    def test_dry_run_reports_nothing_to_clean(self, git_repo, capsys):
        """A clean repo dry-run prints the `nothing to clean` message."""
        cfg = AppConfig(clean_path=git_repo, clean_yes=False, clean_json=False)
        clean_run(cfg)
        out = capsys.readouterr().out
        assert "nothing to clean" in out

    def test_json_mode_prints_report_json(self, git_repo, capsys):
        """`--json` prints the `CleanReport` as JSON via the logger, not the renderer."""
        cfg = AppConfig(clean_path=git_repo, clean_yes=False, clean_json=True)
        clean_run(cfg)
        out = capsys.readouterr().out
        assert "nothing to clean" not in out


# frob:tests tests/unit/test_app_runners_t0875_leaf_collision.py::TestRegistryRunnerRun.test_missing_registry_dir_logs_and_returns  # noqa: E501
# frob:ticket T-0875


class TestRegistryRunnerRun:
    """`registry_runner.run` audit wiring when the registry dir is absent."""

    def test_missing_registry_dir_logs_and_returns(self, tmp_path, caplog):
        """A nonexistent `--registry-path` logs an info line and returns cleanly."""
        cfg = AppConfig(registry_path=tmp_path / "does-not-exist", registry_json=False)
        registry_run(cfg)
        assert "does not exist" in caplog.text

    # frob:ticket T-2454
    def test_sync_gate_rules_logs_the_full_generated_rule_id_set(
        self, tmp_path, caplog
    ):
        # frob:tests \
        # tests/unit/test_app_runners_t0875_leaf_collision.py::TestRegistryRunnerRun.te\
        # st_sync_gate_rules_logs_the_full_generated_rule_id_set
        """T-2454 acceptance[2]: `--sync-gate-rules` logs the FULL live
        registered rule-id set (hand literal unioned with a fresh
        `generated_gate_rule_ids` scan) as the one-place, generated
        answer to "what is the complete list of registered rule ids" --
        obtainable without reading `_KNOWN_GATE_RULES`'s source text by
        hand."""
        import logging

        registry_dir = tmp_path / "docs" / "design" / "registry"
        registry_dir.mkdir(parents=True)
        (registry_dir / "check-coverage.yaml").write_text("entries: []\n")
        cfg = AppConfig(registry_path=registry_dir, registry_sync_gate_rules=True)
        with caplog.at_level(logging.INFO):
            registry_run(cfg)
        [line] = [
            r.message
            for r in caplog.records
            if "live registered rule id(s)" in r.message
        ]
        assert "COV001" in line


# frob:tests tests/unit/test_app_runners_t0875_leaf_collision.py::TestFmtRunnerRun.test_check_mode_reports_all_canonical_on_empty_tree  # noqa: E501
# frob:ticket T-0875


class TestFmtRunnerRun:
    """`fmt_runner.run` `--check` wiring over an empty tree."""

    def test_check_mode_reports_all_canonical_on_empty_tree(self, tmp_path, capsys):
        """`--check` over an empty tree finds nothing to rewrite and exits cleanly."""
        cfg = AppConfig(fmt_path=tmp_path, fmt_check=True, fmt_json=False)
        fmt_run(cfg)
        out = capsys.readouterr().out
        assert "already canonical" in out
