"""T-0736: `frob scaffold apply` end-to-end -- the real CLI subprocess
installs/updates the managed boilerplate blocks in a target repo."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FROB = [sys.executable, "-m", "frob"]


# frob:ticket T-0736
def _git(*args: str, cwd: Path) -> None:
    """Run a git command in `cwd`, raising on failure -- setup helper only."""
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


# frob:ticket T-0736
class TestScaffoldApplyCli:
    """End-to-end CLI coverage for `frob scaffold apply` (T-0736)."""

    # frob:ticket T-0736
    def test_apply_reports_changes(self, tmp_path: Path) -> None:
        # frob:tests tests/system/test_cli_scaffold_apply.py::TestScaffoldApplyCli.test_apply_reports_changes  # noqa: E501
        """A fresh git repo with a `frob.toml` gets the Makefile core-shim,
        `.gitignore` entries, and worktree-lease hooks installed on the
        first run, and reports each as already current on the second."""
        _git("init", "-q", "-b", "main", cwd=tmp_path)
        _git("config", "user.email", "test@example.com", cwd=tmp_path)
        _git("config", "user.name", "Test", cwd=tmp_path)
        (tmp_path / "frob.toml").write_text("[project]\n")

        first = subprocess.run(
            FROB + ["scaffold", "apply"], cwd=tmp_path, capture_output=True, text=True
        )
        out = first.stdout + first.stderr
        assert first.returncode == 0, out
        assert "Makefile" in out
        assert ".gitignore" in out
        assert (tmp_path / "Makefile").exists()
        assert (tmp_path / ".gitignore").exists()
        assert (tmp_path / ".git" / "hooks" / "pre-commit").exists()
        assert (tmp_path / ".git" / "hooks" / "pre-merge-commit").exists()

        second = subprocess.run(
            FROB + ["scaffold", "apply"], cwd=tmp_path, capture_output=True, text=True
        )
        out2 = second.stdout + second.stderr
        assert second.returncode == 0, out2
        assert "already current" in out2
