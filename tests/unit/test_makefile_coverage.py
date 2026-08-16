"""Regression tests for Makefile's `coverage:`/`coverage-fast:` targets.

T-2240: `coverage:` used to carry ~40 lines of its own inline shell
crash-recovery/rerun/stamp logic (subprocess-rc generation, xdist-deadline
timeout, node-down detection + full serial rerun, T-1363 never-promote-
partial-on-failure, coverage combine/xml, final `frob check
--stamp-coverage`), and this file used to test that shell logic directly
by regex-slicing it out of the live Makefile text (`_recipe_tail`/
`_MAKEFILE` slicing) and running it as a standalone script. That shell
logic is gone -- `coverage:` now delegates to `uv run frob coverage
--full`, itself a thin CLI wrapper (`src/frob/app/coverage_runner.py`)
over `frob.testing._coverage_refresh.native_coverage_refresh` (T-1516).
The equivalent behavior this file used to prove by running Makefile
shell fragments -- T-1363's never-promote-partial-data-on-failure guard,
xdist worker-crash ("node down") detection with a full-data-recovering
serial rerun, the stamp-failure-after-a-green-suite propagation, and
coverage.xml surviving a torn-down source path (`-i`/`--ignore-errors`)
-- is now proven directly against `native_coverage_refresh` in
`tests/test_coverage.py::TestNativeCoverageRefresh` /
`TestPytestOutcomeWorkerCrashRecovery` (NO DUPLICATION: this file does
not re-implement those checks against a second, Makefile-text-derived
copy of the same logic).

What remains here is Makefile-text-level: does `coverage:` actually
delegate to `frob coverage --full` (not a hand-copied reimplementation),
and the two still-live cross-target/lock-content checks that were never
about the deleted shell fragment in the first place.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.unit.conftest import _load_committed_coverage_lock

#: T-1335: repo root, resolved the same way every other Makefile-adjacent
#: test in this repo does (tests/unit/test_makefile_coverage.py -> repo
#: root is two levels up).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MAKEFILE = (_REPO_ROOT / "Makefile").read_text(encoding="utf-8")


def _recipe_body(target: str) -> str:
    """The tab-indented recipe lines directly under `target:` in the live
    Makefile text, target line included."""
    match = re.search(
        rf"^{re.escape(target)}:[^\n]*\n(?:\t.*\n)*", _MAKEFILE, re.MULTILINE
    )
    assert match is not None, f"{target}: recipe not found in Makefile"
    return match.group(0)


# frob:ticket T-2240
class TestCoverageRecipeDelegatesToFrobCoverageFull:
    """T-2240 acceptance[0]: `coverage:`'s recipe body is a single `uv run
    frob coverage --full` line, not the old ~40-line inline shell block."""

    # frob:tests tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull.test_recipe_body_is_at_most_two_non_comment_lines  # noqa: E501
    def test_recipe_body_is_at_most_two_non_comment_lines(self) -> None:
        recipe = _recipe_body("coverage")
        # Drop the `target:` line itself; count only the indented recipe
        # lines that follow it.
        lines = recipe.splitlines()[1:]
        non_comment = [line for line in lines if line.strip() and not line.strip().startswith("#")]
        assert len(non_comment) <= 2, (
            f"coverage: recipe still carries {len(non_comment)} non-comment "
            f"line(s), expected the T-2240 single-delegation shape:\n{recipe}"
        )

    # frob:tests tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull.test_recipe_calls_frob_coverage_full  # noqa: E501
    def test_recipe_calls_frob_coverage_full(self) -> None:
        recipe = _recipe_body("coverage")
        assert "uv run frob coverage --full" in recipe, recipe

    # frob:tests tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull.test_recipe_no_longer_shells_out_to_pytest_or_coverage_directly  # noqa: E501
    def test_recipe_no_longer_shells_out_to_pytest_or_coverage_directly(self) -> None:
        recipe = _recipe_body("coverage")
        assert "uv run pytest" not in recipe, recipe
        assert "uv run coverage " not in recipe, recipe

    # frob:tests tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull.test_recipe_depends_on_core_not_a_recipe_embedded_make_call  # noqa: E501
    def test_recipe_depends_on_core_not_a_recipe_embedded_make_call(self) -> None:
        """T-2098: a recipe line containing literal `$(MAKE)` executes even
        under `make -n` (dry run) -- `core` must be a prerequisite, never a
        recipe-body `$(MAKE) core` call."""
        recipe = _recipe_body("coverage")
        target_line = recipe.splitlines()[0]
        assert target_line == "coverage: core", target_line
        assert "$(MAKE)" not in recipe, recipe


class TestPreviouslyZeroModulesNowAttributeInTheCommittedLock:
    """T-1235's acceptance [2]: previously-exercised-but-zero symbols
    (excludes.py, doctor.py, serve/, __main__.py) report real coverage in
    a corrected full run, and the TEST005 count reflects it.

    This ticket's own scope has no direct pytest surface for "the next
    full `make coverage` run" -- that run is a coordinator-only step
    (docs/guides/agent-playbook.md section 6b), and its raw `coverage.xml`
    does not survive past the run that produced it (section 6d). The
    committed `frob-coverage.lock.json` (`write_coverage_lock`,
    `frob.gates._coverage`) is this repo's own durable, attestable summary
    of that same run -- reading it directly, rather than re-deriving a
    fresh (and necessarily locally-scoped, per section 6c) coverage.xml
    from this worktree, is the only way to verify this acceptance
    criterion without forcing an unverifiable claim.
    """

    #: T-1235's own named acceptance-criterion module groups.
    _NAMED_MODULES = (
        "src/frob/excludes.py",
        "src/frob/doctor.py",
        "src/frob/serve/_socketd.py",
        "src/frob/__main__.py",
    )

    def test_named_module_groups_are_nonzero_in_the_committed_lock(self) -> None:
        """excludes.py/doctor.py/serve/_socketd.py/__main__.py must not be 0.0%.

        Measured directly against `frob-coverage.lock.json` as committed
        on `main` (commit `5ffa0159`, "chore(coverage): stamp lock from
        green suite run", 2026-08-03 -- after both this ticket's own
        subprocess-rc fix and T-1433's xdist-wedge fix landed): every
        named module reads well above 0.0% (measured: excludes.py 100.0%,
        doctor.py 93.8%, serve/_socketd.py 90.7%, __main__.py 89.5%),
        versus the 0.0% each read before T-1235's fix (T-0969's 2026-07-29
        diagnosis).
        """
        module_line = _load_committed_coverage_lock()
        for module in self._NAMED_MODULES:
            assert module in module_line, f"{module} missing from committed lock"
            assert module_line[module] > 0.0, (
                f"{module} regressed to the pre-T-1235 zero-coverage "
                f"attribution failure (module_line[{module}] = "
                f"{module_line[module]})"
            )


# frob:ticket T-1469
class TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor:
    """T-1469: `coverage:`/`coverage-fast:` must run `frob ticket
    reconcile --apply` before `frob doctor` -- a stale IN_PROGRESS
    ticket hold with no live lease (`scan_stale_ticket_leases`, T-1131)
    used to make the doctor precondition abort the whole recipe before
    pytest ever ran; `reconcile --apply` auto-requeues exactly that shape
    (logging which ticket(s) it requeued) and is a no-op otherwise, so
    the precondition can no longer abort on THIS specific, mechanically
    healable condition while every other doctor-checked condition
    (missing natives, corrupt derived state, a live land.lock, venv shim
    drift) still fails the recipe hard."""

    # frob:tests tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor.test_coverage_reconciles_before_doctor  # noqa: E501
    def test_coverage_reconciles_before_doctor(self) -> None:
        recipe = _recipe_body("coverage")
        reconcile_idx = recipe.index("uv run frob ticket reconcile --apply")
        doctor_idx = recipe.index("uv run frob doctor")
        assert reconcile_idx < doctor_idx, recipe

    # frob:tests tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor.test_coverage_fast_reconciles_before_doctor  # noqa: E501
    def test_coverage_fast_reconciles_before_doctor(self) -> None:
        recipe = _recipe_body("coverage-fast")
        reconcile_idx = recipe.index("uv run frob ticket reconcile --apply")
        doctor_idx = recipe.index("uv run frob doctor")
        assert reconcile_idx < doctor_idx, recipe
