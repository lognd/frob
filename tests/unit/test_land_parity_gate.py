"""LANDPARITY001/LANDPARITY002 gate tests (T-3456): `frob.gates.
_land_parity.land_parity_doc_test_gate`/`land_parity_long_function_gate`
over a real git checkout -- the actual acceptance criterion this ticket
exists to satisfy is that `frob check --ticket <id>` (which this gate
plugs into) now reports the SAME finding `frob ticket land`'s own T-2114/
T-2214 pre-land assertions already refuse on, instead of 0 errors."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.gates._land_parity import (
    land_parity_doc_test_gate,
    land_parity_long_function_gate,
)


# frob:waive DUP001 reason="same established real-git-fixture idiom this test module \
# family repeats (tests/test_ticket_work_and_land_finish.py's own _run/_git_init/ \
# _commit_all carry the identical DUP001 waiver already, citing the same real, \
# independent shared-conftest cleanup outside any one ticket's own scope)"
def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A `main`-branch checkout with one committed baseline file --
    MUST be on branch `main` itself, matching `working_diff(root,
    "main")`'s own merge-base-against-self shape every existing land-time
    pre-land-assertion test in `tests/test_ticket_work_and_land_finish.py`
    already relies on (a ticket's real worktree branches off `main`, but
    these gate functions only need an uncommitted change against SOME
    `main`-reachable merge-base, and diffing `main` against itself,
    working tree included, is the cheapest fixture shape that gives
    that)."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    _commit_all(main_repo, "init")
    return main_repo


class TestLandParityDocTestGate:
    """LANDPARITY001: `frob check`-visible mirror of T-2114's own
    pre-land assertion (`_assert_new_public_symbols_have_doc_and_test_
    edge_pre_land`)."""

    # frob:tests tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate.test_new_public_symbol_missing_both_directives_fires  # noqa: E501
    def test_new_public_symbol_missing_both_directives_fires(self, repo: Path) -> None:
        """MUST-FIRE fixture (T-3456's own acceptance, T-3302's original
        MUST-FIRE): a new public symbol with no `frob:doc`/`frob:tests`
        directive above it must be reported by `land_parity_doc_test_
        gate` -- this MUST FAIL if the gate is not wired (no rule id at
        all, per this ticket's own CONFIRMED premise)."""
        new_file = repo / "src" / "undocumented.py"
        new_file.write_text("def brand_new_public_function():\n    return 1\n")
        _run(["git", "add", "-A"], repo)

        violations = land_parity_doc_test_gate(repo)
        assert len(violations) == 1
        assert violations[0].rule == "LANDPARITY001"
        assert violations[0].file == "src/undocumented.py"
        assert "brand_new_public_function" in violations[0].message

    # frob:tests tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate.test_new_public_symbol_with_both_directives_is_quiet  # noqa: E501
    def test_new_public_symbol_with_both_directives_is_quiet(self, repo: Path) -> None:
        """Must-still-pass control: both directives present -> no
        finding, mirroring T-2114's own `test_a_new_public_symbol_with_
        both_edges_does_not_refuse`."""
        new_file = repo / "src" / "documented.py"
        new_file.write_text(
            "# frob:doc docs/modules/example.md#brand-new-public-function\n"
            "# frob:tests tests/test_example.py::test_brand_new_public_function\n"
            "def brand_new_public_function():\n"
            "    return 1\n"
        )
        _run(["git", "add", "-A"], repo)

        assert land_parity_doc_test_gate(repo) == ()

    # frob:tests tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate.test_no_diff_is_quiet  # noqa: E501
    def test_no_diff_is_quiet(self, repo: Path) -> None:
        """Must-still-pass control: a clean checkout with no working-tree
        diff against `main` reports nothing (fail-open on an empty diff,
        never a crash)."""
        assert land_parity_doc_test_gate(repo) == ()


class TestLandParityLongFunctionGate:
    """LANDPARITY002: `frob check`-visible mirror of T-2214's own
    diff-scoped ARCH001 pre-land assertion (`_assert_diff_does_not_
    worsen_long_functions_pre_land`)."""

    # frob:tests tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate.test_new_over_threshold_function_fires  # noqa: E501
    def test_new_over_threshold_function_fires(self, repo: Path) -> None:
        """MUST-FIRE fixture: a brand-new function whose body crosses
        ARCH001's long-AND-complex threshold must be reported --
        mirrors T-2214's own `test_a_new_over_threshold_function_
        refuses_the_land` MUST-FIRE shape."""
        lines = ["def brand_new_giant_function():"]
        for i in range(140):
            lines.append(f"    if x == {i}:")
            lines.append(f"        y = {i}")
        (repo / "src" / "giant.py").write_text("\n".join(lines) + "\n")
        _run(["git", "add", "-A"], repo)

        violations = land_parity_long_function_gate(repo)
        assert len(violations) == 1
        assert violations[0].rule == "LANDPARITY002"
        assert violations[0].file == "src/giant.py"
        assert "brand_new_giant_function" in violations[0].message

    # frob:tests tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate.test_pre_existing_over_threshold_function_merely_touched_is_quiet  # noqa: E501
    def test_pre_existing_over_threshold_function_merely_touched_is_quiet(
        self, repo: Path
    ) -> None:
        """Must-still-pass control (T-2214's own acceptance criterion): a
        function ALREADY over threshold before this diff, merely
        touched, must NOT be blamed on this diff -- mirrors T-2214's own
        `test_a_pre_existing_over_threshold_function_merely_touched_does_
        not_refuse`."""
        lines = ["def already_giant_function():"]
        for i in range(140):
            lines.append(f"    if x == {i}:")
            lines.append(f"        y = {i}")
        content = "\n".join(lines) + "\n"
        (repo / "src" / "already_giant.py").write_text(content)
        _commit_all(repo, "add already-giant function")

        # Touch it (a trailing no-op comment), still over threshold, but
        # NOT newly so.
        (repo / "src" / "already_giant.py").write_text(content + "# touched\n")
        _run(["git", "add", "-A"], repo)

        assert land_parity_long_function_gate(repo) == ()

    # frob:tests tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate.test_no_diff_is_quiet  # noqa: E501
    def test_no_diff_is_quiet(self, repo: Path) -> None:
        """Must-still-pass control: a clean checkout with no working-tree
        diff against `main` reports nothing."""
        assert land_parity_long_function_gate(repo) == ()
