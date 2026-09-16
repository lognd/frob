"""T-4493 regression: SUPPRESS001's ty-diagnostic correlation must not
double-join a checker-reported path onto a nested worktree root.

`ty`/`mypy` are invoked without a `cwd=` override (`frob.check._python.
_run_ty_one`), so a relative diagnostic path they report is relative to
whatever directory the frob process itself is running from -- typically
the outer repo root, not the nested worktree `root` a per-ticket `frob
check --path <worktree>` actually checks. `_suppress._relativize` used to
treat any relative path as already root-relative and return it verbatim;
`_suppress001_correlate` then joined it onto `root` a second time,
producing an unreadable doubled path (`.../t-x/.claude/worktrees/t-x/...`)
and silently zeroing SUPPRESS001 inside every worktree check.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._suppress import (
    _relativize,
    _suppress001_correlate,
    suppression_dialects,
)
from tests.test_gates_suppress import _write

pytestmark = pytest.mark.timeout(30)


class TestRelativizeUnderNestedWorktreeRoot:
    """`_relativize` against a `root` nested under the real process cwd --
    the exact shape `frob check --path .claude/worktrees/<x>` produces."""

    def test_cwd_relative_diagnostic_path_is_not_doubled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """BUG002 repro (fails at the parent commit): `ty` reports a path
        relative to the outer repo (the process cwd), e.g.
        `.claude/worktrees/x/tests/mod.py`, while SUPPRESS001 checks
        against the nested worktree `root =
        <outer>/.claude/worktrees/x`. The parent's `_relativize` returns
        that cwd-relative string UNCHANGED, and the caller then joins it
        onto `root` again -- `root / rel` resolves to a path that does
        not exist (the worktree name appears twice) and the file cannot
        be read. The fixed `_relativize` must resolve the diagnostic
        path against cwd exactly once and return the path relative to
        `root` (`tests/mod.py`), which DOES exist and IS readable."""
        monkeypatch.chdir(tmp_path)
        nested_root = tmp_path / ".claude" / "worktrees" / "x"
        _write(nested_root, "tests/mod.py", "x = 1\n")

        cwd_relative = ".claude/worktrees/x/tests/mod.py"
        rel = _relativize(cwd_relative, nested_root)

        assert rel == "tests/mod.py"
        # The doubled join this ticket names must not exist on disk --
        # confirms the fix reads the real file, not a phantom path.
        doubled = nested_root / cwd_relative
        assert not doubled.exists()
        assert (nested_root / rel).exists()

    def test_correlate_reads_the_real_file_under_nested_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End-to-end: `_relativize` (as `_ty_diagnostics` itself calls it
        on every raw diagnostic before handing anything to
        `_suppress001_correlate`) turns a cwd-relative `ty` path into the
        root-relative one `_suppress001_correlate` can actually read --
        the old double-join made that read fail (an OSError, warned and
        swallowed), so nothing ever fired inside a worktree check."""
        monkeypatch.chdir(tmp_path)
        nested_root = tmp_path / ".claude" / "worktrees" / "x"
        _write(nested_root, "tests/mod.py", "x = y  # type: ignore[name-defined]\n")

        dialects = suppression_dialects()
        cwd_relative = ".claude/worktrees/x/tests/mod.py"
        rel = _relativize(cwd_relative, nested_root)
        assert rel is not None
        oracle_diagnostics = {"ty": [(rel, 1, "unresolved-reference")]}

        violations = _suppress001_correlate(nested_root, dialects, oracle_diagnostics)

        assert len(violations) == 1
        assert violations[0].rule == "SUPPRESS001"
        assert violations[0].file == rel
        assert violations[0].line == 1
