"""Coverage for `frob.app.claude_runner` (T-1808): `frob claude sync
[--check]` and the automatic startup drift warning.

Builds a throwaway repo layout (`.claude/hooks/sync-claude-config.py` plus
one managed source file) and a throwaway `$HOME/.claude` so tests never
touch the real operator home directory. The acceptance shape required by
the dispatch: a divergence test that FAILS before a sync ("--check"
reports it and `drift_warning` warns), then an in-sync state that is
clean (no false positive) after syncing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from frob.app import claude_runner
from frob.app.config import AppConfig

_HOOK_SOURCE = '''"""Sync git-tracked Claude config from this repo out to `~/.claude/`."""

import argparse
import shutil
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_HOME_CLAUDE = Path.home() / ".claude"

MANAGED: list[tuple[str, str]] = [
    (".claude/hooks/widget.py", "hooks/widget.py"),
]

_BANNER = "# GENERATED COPY -- DO NOT EDIT.\\n"


def _rendered(source_rel, dest):
    source = _REPO / source_rel
    if not source.exists():
        return None
    return _BANNER + source.read_text(encoding="utf-8")


def home_claude_missing():
    """T-3600: mirrors the real script's own public predicate."""
    return not _HOME_CLAUDE.exists()


def plan():
    actions = []
    missing = []
    for source_rel, dest_rel in MANAGED:
        dest = _HOME_CLAUDE / dest_rel
        want = _rendered(source_rel, dest)
        if want is None:
            missing.append(source_rel)
            continue
        have = dest.read_text(encoding="utf-8") if dest.exists() else None
        if have == want:
            continue
        state = "absent" if have is None else "differs"
        actions.append((f"{dest_rel} ({state} vs {source_rel})", dest, want))
    return actions, missing


def _materialize(dest, want):
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(want, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    actions, missing = plan()
    for source_rel in missing:
        print(f"MISSING canonical source: {source_rel}", file=sys.stderr)
    if args.check:
        if actions or missing:
            return 1
        return 0
    for _entry, dest, want in actions:
        _materialize(dest, want)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
'''


# frob:waive WIRE001 reason="a private per-file pytest fixture used only by this \
# module's own test functions, the standard fixture shape (T-1024 precedent, e.g. \
# tests/unit/conftest.py's own identical waiver) -- there is no production caller to \
# wire it to by design" permanent="true"
@pytest.fixture
def _repo_and_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway repo with one managed file, and a throwaway `$HOME` so
    the sync module's `Path.home() / ".claude"` never touches the real
    operator home directory."""
    repo = tmp_path / "repo"
    hooks = repo / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "sync-claude-config.py").write_text(_HOOK_SOURCE, encoding="utf-8")
    (hooks / "widget.py").write_text("print('widget')\n", encoding="utf-8")

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: home)

    monkeypatch.chdir(repo)
    return repo


def _cfg(**overrides: object) -> AppConfig:
    """Minimal `AppConfig` for a `frob claude sync` invocation."""
    base: dict[str, Any] = {
        "subcommand": "claude",
        "claude_command": "sync",
        "claude_check": False,
        "color": "never",
        "no_color": True,
    }
    base.update(overrides)
    return AppConfig(**base)


class TestDriftReport:
    # frob:tests \
    # tests/unit/test_claude_runner.py::TestDriftReport.test_reports_drifted_and_missing
    def test_reports_drifted_and_missing(self, _repo_and_home: Path) -> None:
        report = claude_runner.drift_report(_repo_and_home)
        assert report is not None
        drifted, missing = report
        assert drifted == ["hooks/widget.py (absent vs .claude/hooks/widget.py)"]
        assert missing == []

    def test_none_for_repo_with_no_managed_config(self, tmp_path: Path) -> None:
        bare = tmp_path / "bare2"
        bare.mkdir()
        assert claude_runner.drift_report(bare) is None


class TestHomeClaudeMissing:
    """T-3600: `claude_runner.home_claude_missing` -- the adapter half of
    the "fresh machine, no ~/.claude yet" vs "present but drifted"
    discriminator `check_runner._claude_config_drift_result` needs."""

    # frob:tests \
    # tests/unit/test_claude_runner.py::TestHomeClaudeMissing.test_true_when_home_claud\
    # e_absent
    def test_true_when_home_claude_absent(self, _repo_and_home: Path) -> None:
        """`_repo_and_home`'s own `$HOME` fixture never creates
        `~/.claude` -- exactly the fresh-machine shape this predicate
        exists to detect."""
        assert claude_runner.home_claude_missing(_repo_and_home) is True

    # frob:tests \
    # tests/unit/test_claude_runner.py::TestHomeClaudeMissing.test_false_when_home_clau\
    # de_present
    def test_false_when_home_claude_present(self, _repo_and_home: Path) -> None:
        (Path.home() / ".claude").mkdir(parents=True, exist_ok=True)
        assert claude_runner.home_claude_missing(_repo_and_home) is False

    # frob:tests \
    # tests/unit/test_claude_runner.py::TestHomeClaudeMissing.test_none_for_repo_with_n\
    # o_managed_config
    def test_none_for_repo_with_no_managed_config(self, tmp_path: Path) -> None:
        bare = tmp_path / "bare3"
        bare.mkdir()
        assert claude_runner.home_claude_missing(bare) is None


class TestDriftWarning:
    # frob:tests \
    # tests/unit/test_claude_runner.py::TestDriftWarning.test_warns_when_managed_file_d\
    # iffers
    def test_warns_when_managed_file_differs(self, _repo_and_home: Path) -> None:
        """No `~/.claude/hooks/widget.py` at all yet -- this MUST report
        drift before any sync runs (the required pre-fix failing state)."""
        warning = claude_runner.drift_warning(_repo_and_home)
        assert warning is not None
        assert "DRIFT" in warning
        assert "frob claude sync" in warning

    # frob:tests \
    # tests/unit/test_claude_runner.py::TestDriftWarning.test_none_when_in_sync
    def test_none_when_in_sync(self, _repo_and_home: Path) -> None:
        """After a real sync, the same check must report clean -- no false
        positive on an in-sync tree."""
        claude_runner.run(_cfg(claude_check=False))
        assert claude_runner.drift_warning(_repo_and_home) is None

    def test_none_when_repo_has_no_managed_config(self, tmp_path: Path) -> None:
        """A repo that never had `.claude/hooks/sync-claude-config.py` is a
        no-op, not a false positive."""
        empty_repo = tmp_path / "bare"
        empty_repo.mkdir()
        assert claude_runner.drift_warning(empty_repo) is None


class TestRun:
    # frob:tests \
    # tests/unit/test_claude_runner.py::TestRun.test_check_mode_exits_1_on_drift
    def test_check_mode_exits_1_on_drift(self, _repo_and_home: Path) -> None:
        with pytest.raises(SystemExit) as exc_info:
            claude_runner.run(_cfg(claude_check=True))
        assert exc_info.value.code == 1
        assert not (_repo_and_home.parent / "home" / ".claude" / "hooks").exists()

    # frob:tests \
    # tests/unit/test_claude_runner.py::TestRun.test_sync_writes_managed_files
    def test_sync_writes_managed_files(self, _repo_and_home: Path) -> None:
        claude_runner.run(_cfg(claude_check=False))
        dest = Path.home() / ".claude" / "hooks" / "widget.py"
        assert dest.exists()
        assert "GENERATED COPY" in dest.read_text(encoding="utf-8")

        # A second --check run, now in sync, must NOT exit(1).
        claude_runner.run(_cfg(claude_check=True))

    def test_run_rejects_unknown_action(self, _repo_and_home: Path) -> None:
        with pytest.raises(SystemExit) as exc_info:
            claude_runner.run(_cfg(claude_command="frobnicate"))
        assert exc_info.value.code == 1
