## Done report

Changed:
- `src/frob/testing/_runners.py::_is_neutral_outcome` (new, private): true
  when a `RunnerOutcome` is Python + exit 5 (pytest's "collection ran,
  selected zero tests", distinct from a genuine failure).
- `src/frob/testing/_runners.py::run_selected`: no longer flips
  `TestRunReport.ok` to `False` for an outcome `_is_neutral_outcome` accepts
  -- only a real nonzero/non-5 exit still fails the run.
- `src/frob/testing/_runners.py::_PYTEST_NO_TESTS_COLLECTED` (new, private
  module constant, value 5).
- `src/frob/app/test_runner.py::_print_outcomes`: prints `[NEUTRAL]` instead
  of `[FAIL]` for an `_is_neutral_outcome` outcome (imported directly from
  `frob.testing._runners`, not re-exported -- kept off the public API
  surface so this fix does not require a version bump / CHANGELOG entry).
  Only a real `[FAIL]` still dumps the stdout/stderr tail.

Root cause: `run_selected` in `src/frob/testing/_runners.py` flipped
`TestRunReport.ok` to `False` for ANY nonzero runner exit code, including
pytest's own exit 5 ("collection succeeded, zero tests were selected") --
a case the package-fallback path (`select_tests(..., fallback="package")`)
legitimately produces when a touched file's package has no tests. That is
semantically the same "nothing to run" outcome the empty-selection branch
in `frob.app.test_runner.run` already treats as a clean pass (`if not
any(report.selected.values()): ...; return`); it was only reported as
`[FAIL]` because the package-fallback path DOES select something (the
package dir) and lets pytest itself discover there is nothing to collect.

Evidence (fresh `pytest --collect-only -q` confirmed collected; `uv run
pytest tests/test_testing.py -q` -> 40 passed):
- `tests/test_testing.py::TestRunners::test_pytest_exit_5_no_tests_collected_is_neutral_not_fail`
  -- unit-level: a fake exit-5 script through `run_selected` ->
  `report.ok is True`.
- `tests/test_testing.py::TestRunners::test_package_fallback_with_zero_tests_is_ok_end_to_end`
  -- T-0210's literal regression case: a real fixture package
  (`activities/git-heist/`-shaped) with a source edit and zero tests,
  selected via `fallback="package"`, run through the real `python -m
  pytest` runner -> genuine pytest exit 5, `report.ok is True`.
- `tests/test_testing.py::TestRunners::test_exit_code_is_data` (pre-existing,
  re-verified unchanged) -- exit 1 still flips `ok` to `False`, confirming
  genuine failures are not swallowed by this change.

Also ran `uv run frob test --base main` in this worktree end to end:
touched-set selection picked up the changed files, ran the real pytest
runner, printed `[PASS] python exit=0 3.57s`.

Filed: none -- no out-of-scope work found; `src/frob/app/test_runner.py`
was brought into scope (see the widening note above) because the fix is
not complete without its status-line branch.

Gates: `uv run frob check --ticket T-0210` clean (0 errors; 3 pre-existing
`frob-arch` abstraction-opportunity warnings unrelated to this ticket, plus
the repo's existing 27 waived violations). `uv run ruff check` and `uv run
ruff format --check` both clean under `uv run ruff` (project-pinned). Deletion-filter
land rule verified: `git diff main --diff-filter=D --stat` is empty.
`frob-core/Cargo.lock` / `strata-core/Cargo.lock` build-artifact diffs from
`make core` were reverted (out of scope, pre-existing across worktrees, not
part of this fix).
