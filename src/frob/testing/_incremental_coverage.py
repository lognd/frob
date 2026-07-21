"""Touched-set coverage targets (T-0484: incrementalize the coverage cycle).

`make coverage` (`frob check --stamp-coverage`'s data source) runs the WHOLE
suite under `pytest --cov` on every invocation, so TEST005/TEST006 feedback
for a one-line edit costs a full-suite wait. This module supplies the one
missing piece to make that incremental instead of daemon-side: "which
python test targets does the CURRENT touched set actually obligate,"
reusing `frob.testing.select_tests`'s existing pure selection algorithm
(the same one `frob test --base REF` already runs against) rather than a
second, independently-hand-written diff-to-tests mapping.

The intended recipe (wired into `make coverage-fast`, not a daemon):
1. `python_coverage_targets(root, snapshot, base)` -- the touched-set's
   selected python pytest targets (node ids, or `()` when nothing touched
   selects any python test).
2. Run `pytest --cov=... --cov-append --cov-report=` restricted to just
   those targets (NOT the whole suite) -- `--cov-append` preserves the
   PRIOR full run's per-file hit data for every file the touched-set run
   never re-executes (their source has not changed, so their old coverage
   data is still valid), only refreshing the touched files' own numbers.
3. `coverage combine` + `coverage xml` + `frob check --stamp-coverage`
   exactly as the full `make coverage` target already does -- the stamp
   step itself is already cheap (file hashing, no test execution); the
   suite RUN is what this shortens.

This is deliberately NOT a background daemon (the ticket's (a) option):
a daemon needs a long-lived process, IPC/socket surface, and staleness
handling of its own -- a strictly larger, separately-scoped effort not
justified when the touched-set + `--cov-append` recipe already turns a
full-suite wait into a touched-set-sized one using machinery
(`select_tests`, `working_diff`) this repo already has and already trusts
for `frob test`. See T-0484's Done report for what is explicitly deferred
(a real daemon, and non-python touched-set coverage) as follow-up-worthy
rather than silently dropped.
"""

from __future__ import annotations

from pathlib import Path

from frob.gitio import working_diff
from frob.graph import GraphSnapshot
from frob.testing._models import SelectConfig
from frob.testing._select import select_tests

_PYTHON_LANG = "python"


# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/test_coverage.py::TestPythonCoverageTargets.test_touched_source_selects_test kind="unit"  # noqa: E501
# frob:tests tests/test_coverage.py::TestPythonCoverageTargets.test_nothing_touched_returns_empty kind="unit"  # noqa: E501
# frob:tests tests/test_coverage.py::TestPythonCoverageTargets.test_bad_base_ref_returns_empty kind="unit"  # noqa: E501
def python_coverage_targets(
    root: Path, snapshot: GraphSnapshot, base: str
) -> tuple[str, ...]:
    """The touched-set's selected python pytest node ids/paths against
    `base` (same selection `frob test --base <base>` runs), for feeding a
    coverage-instrumented pytest run restricted to just what changed
    rather than the whole suite.

    Returns `()` on a diff/selection failure or when nothing touched
    selects any python test -- callers treat an empty result as "nothing
    to incrementally re-measure," not an error; the caller is expected to
    fall back to a full `make coverage` run when this is empty and no
    coverage stamp exists yet (the first run always needs the full
    baseline)."""
    diff_result = working_diff(root, base)
    if diff_result.is_err:
        return ()
    report = select_tests(snapshot, diff_result.danger_ok, SelectConfig())
    return report.selected.get(_PYTHON_LANG, ())


__all__ = ["python_coverage_targets"]
