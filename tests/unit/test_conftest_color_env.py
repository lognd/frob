"""T-1586 regression coverage: `tests/conftest.py`'s autouse
`_neutralize_inherited_color_env` fixture must strip `FORCE_COLOR`/
`NO_COLOR` from THIS process's own environment before every test -- so a
real `frob` CLI subprocess spawned here (which inherits `os.environ` by
default) never sees a color-forcing var leaked in from the developer's
ambient shell, no matter what that shell exported.

Reproduces the exact 2026-08 incident: a shell exporting `FORCE_COLOR=3`
(Claude Code and several CI images do) made 5 `tests/system/**` tests fail
purely from the ambient environment, embedding ANSI escapes in CLI output
those tests asserted was plain -- while the identical commit passed on a
shell without it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_ESC = "\x1b["


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


# frob:waive WIRE001 reason="a private per-file fixture helper used only by this \
# file's own three test methods below -- there is no production caller to wire it to \
# by design, it exists solely to seed a throwaway git/pyproject project this file's \
# CLI-subprocess tests run frob ticket commands against" permanent="true"
def _make_ticket_project(tmp_path: Path) -> Path:
    """A minimal git-tracked frob project with one filed ticket, cheap
    enough to build per-test -- `frob ticket list` is this file's chosen
    CLI surface because it visibly colors its output under `FORCE_COLOR`
    (unlike e.g. `frob --version`, which never touches the color path)."""
    _git("init", "-q", cwd=tmp_path)
    _git(
        "-c",
        "user.email=t@example.com",
        "-c",
        "user.name=t",
        "commit",
        "--allow-empty",
        "-q",
        "-m",
        "init",
        cwd=tmp_path,
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "colorproj"\nversion = "0.1.0"\n'
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "frob",
            "ticket",
            "new",
            "--title",
            "x",
            "--kind",
            "bug",
            "--scope",
            "a/**",
            "--body",
            "b",
            "--path",
            str(tmp_path),
            "--no-commit",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return tmp_path


class TestConftestColorEnvIsolation:
    """The autouse fixture must isolate a spawned CLI subprocess from an
    inherited `FORCE_COLOR`/`NO_COLOR`, per T-1586."""

    def test_force_color_and_no_color_are_absent_from_this_process_env(self) -> None:
        """Direct proof the autouse fixture ran before THIS test: neither
        var is present in `os.environ`, regardless of what the invoking
        shell exported -- the precondition every other test in this class
        relies on."""
        assert "FORCE_COLOR" not in os.environ
        assert "NO_COLOR" not in os.environ

    def test_spawned_cli_produces_escape_free_output_despite_ambient_shell(
        self, tmp_path: Path
    ) -> None:
        """A `frob ticket list` subprocess spawned with the DEFAULT
        inherited environment (no explicit `env=` override, exactly how a
        typical test-authored subprocess call works) must never contain an
        ANSI escape -- proving the fixture's cleanup of THIS process's own
        `os.environ` is what keeps a spawned child clean, not an accident
        of some other suppression."""
        project = _make_ticket_project(tmp_path)
        result = subprocess.run(
            [sys.executable, "-m", "frob", "ticket", "list", "--path", str(project)],
            cwd=project,
            capture_output=True,
            text=True,
        )
        out = result.stdout + result.stderr
        assert _ESC not in out, out
        assert "T-0001" in out

    def test_explicit_force_color_in_child_env_still_colors(
        self, tmp_path: Path
    ) -> None:
        """Counter-proof: passing `FORCE_COLOR` explicitly via a child's
        OWN `env=` (not inherited, deliberately set) still produces ANSI
        -- confirming the previous test's clean output is caused by the
        fixture's env cleanup, not by `frob ticket list` being incapable
        of coloring its output at all."""
        project = _make_ticket_project(tmp_path)
        child_env = {**os.environ, "FORCE_COLOR": "1"}
        result = subprocess.run(
            [sys.executable, "-m", "frob", "ticket", "list", "--path", str(project)],
            cwd=project,
            capture_output=True,
            text=True,
            env=child_env,
        )
        out = result.stdout + result.stderr
        assert _ESC in out, out
