"""Integration test for `frob mutate --json` (T-0815): the exec guard
DEBUG-logs every mutant test spawn through `guarded_subprocess_run`, and
this repo's stdout log handler is DEBUG-level by default, so an unguarded
`run_mutations` call would leak those lines into the `--json` payload.
Drives the real CLI over an on-disk target file and asserts the full
stdout parses as clean JSON.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

FROB = [sys.executable, "-m", "frob"]

_TARGET_SOURCE = "def add(a, b):\n    return a + b\n"


def _write_target(tmp_path: Path) -> Path:
    """A tiny single-mutation-point source file for `frob mutate` to chew on."""
    target = tmp_path / "target.py"
    target.write_text(_TARGET_SOURCE, encoding="utf-8")
    return target


class TestMutateRunnerJson:
    def test_json_output_is_clean(self, tmp_path: Path) -> None:
        """`frob mutate --json` stdout json.loads cleanly -- no leaked
        `guarded_subprocess_run` DEBUG spawn lines mixed into the payload."""
        # frob:tests src/frob/mutate kind="integration"
        target = _write_target(tmp_path)
        result = subprocess.run(
            FROB
            + [
                "mutate",
                "--path",
                str(tmp_path),
                "--json",
                str(target),
                "--",
                sys.executable,
                "-c",
                "raise SystemExit(1)",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert "total" in data
        assert "killed" in data
        assert "survivors" in data

    def test_human_mode_still_shows_diagnostics(self, tmp_path: Path) -> None:
        """Without `--json`, human-mode output is unaffected by the guard."""
        target = _write_target(tmp_path)
        result = subprocess.run(
            FROB
            + [
                "mutate",
                "--path",
                str(tmp_path),
                str(target),
                "--",
                sys.executable,
                "-c",
                "raise SystemExit(1)",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "mutation score" in result.stdout
