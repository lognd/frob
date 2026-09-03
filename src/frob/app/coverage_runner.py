"""CLI wiring for `frob coverage` -- the user-facing coverage refresh verb
(T-1525).

`frob.testing._coverage_refresh.native_coverage_refresh` (T-1516) and
`frob.testing._coverage_wait.run_coverage_wait` (T-1095/T-1516/T-1126)
already implement the frob-native, cross-platform coverage orchestration
this repo's `make coverage`/`make coverage-fast` targets previously
provided -- but neither had a CLI entrypoint of its own before this
module: `native_coverage_refresh` was reachable as a library call, and
`run_coverage_wait` was reachable indirectly (as the default coverage
path `frob.app.test_runner`'s own `--wait-coverage` flag drives). `frob
coverage` is that missing entrypoint: the default (no `--full`) path
reuses `run_coverage_wait`'s single-flight lock and freshness check
(`--full` bypasses both -- an explicit whole-suite request should not be
short-circuited by "another caller already made it fresh").

Whether `frob check` itself should auto-trigger this refresh for a
non-agent (human/CI) caller is a decision this ticket also had to make,
not just implement -- see `docs/modules/cli.md#frob-coverage-t-1525` for
the recorded answer (deliberately not, for every caller): running the
test suite is a side effect a static check command should not hide
inside itself, agent or not; `frob coverage` (this verb) and `frob
test --wait-coverage` (the existing, already-wired path into
`frob.app.test_runner`) are the two places a refresh is expected to run
from."""

from __future__ import annotations

from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:ticket T-1525
# frob:ticket T-1572
# frob:doc docs/modules/cli.md#frob-coverage-t-1525
# frob:tests tests/unit/test_coverage_runner.py::TestCoverageRunner.test_default_delegates_to_run_coverage_wait  # noqa: E501
# frob:tests tests/unit/test_coverage_runner.py::TestCoverageRunner.test_full_calls_native_refresh_directly  # noqa: E501
# frob:tests \
# tests/unit/test_coverage_runner.py::TestCoverageRunner.test_run_failure_exits_nonzero
# frob:tests tests/unit/test_coverage_runner.py::TestCoverageRunner.test_base_threads_through_to_run_coverage_wait  # noqa: E501
def run(cfg: AppConfig) -> None:
    """`frob coverage [--full] [--base REF]`: refresh `coverage.xml`/the
    coverage stamp via the T-1516 frob-native orchestration -- touched-set
    incremental by default (`run_coverage_wait`'s single-flight,
    freshness-checked path), or a whole-suite run when `--full` is passed
    (calls `native_coverage_refresh` directly, since an explicit
    full-refresh request should not be short-circuited by another
    caller's already-fresh result). `--base` (T-1572, the old `make
    coverage-fast BASE=<ref>` shell recipe's equivalent) overrides the
    git ref the touched-set incremental refresh diffs against (default
    HEAD) -- it has no effect with `--full`, which always runs the whole
    suite regardless of any touched-set base. Exits non-zero
    (`SystemExit`, the convention every other runner facing a hard
    failure uses) on refresh failure."""
    root = cfg.coverage_path or Path(".")

    if cfg.coverage_full:
        from frob.graph import build_graph, load_graph
        from frob.testing._coverage_refresh import native_coverage_refresh

        cache = root / ".frob" / "cache.db"
        loaded = load_graph(cache)
        if loaded.is_err:
            loaded = build_graph(root, cache)
        if loaded.is_err:
            _log.error(
                "frob coverage --full: could not build graph snapshot: %s",
                loaded.danger_err,
            )
            raise SystemExit(1)
        result = native_coverage_refresh(root, loaded.danger_ok, full=True)
        if result.is_err:
            _log.error("frob coverage --full: %s", result.danger_err.value)
            raise SystemExit(1)
        if cfg.coverage_fail_on_degraded:
            _fail_if_suite_degraded(root)
        _log.info("frob coverage --full: refresh complete")
        return

    from frob.testing._coverage_wait import run_coverage_wait

    outcome = run_coverage_wait(root, base=cfg.coverage_base or "HEAD")
    if outcome.is_err:
        _log.error("frob coverage: %s", outcome.danger_err.value)
        raise SystemExit(1)
    result = outcome.danger_ok
    if result.ran:
        _log.info("frob coverage: refreshed in %.1fs", result.duration_s)
    else:
        _log.info("frob coverage: already fresh, nothing to do")


# frob:ticket T-3748
# frob:tests tests/unit/test_coverage_runner.py::TestCoverageFailOnDegraded.test_red_suite_exits_nonzero  # noqa: E501
# frob:tests tests/unit/test_coverage_runner.py::TestCoverageFailOnDegraded.test_worker_crash_does_not_fail  # noqa: E501
# frob:tests tests/unit/test_coverage_runner.py::TestCoverageFailOnDegraded.test_green_suite_returns  # noqa: E501
# frob:tests tests/unit/test_coverage_runner.py::TestCoverageFailOnDegraded.test_missing_provenance_fails_closed  # noqa: E501
def _fail_if_suite_degraded(root: Path) -> None:
    """`SystemExit(1)` when the last `--full` run's provenance says the suite
    ran RED -- a pytest exit != 0 that was NOT an xdist worker-crash.

    A worker-crash is an ENVIRONMENT abort the refresh already recovers from
    with its serial retry (T-1672), not a real regression, so it must NOT
    fail this gate; only a genuinely red suite does. Reading fails closed:
    an unreadable provenance cannot confirm the suite passed. Lets one `frob
    coverage --full --fail-on-degraded` be CI's combined pass/fail + coverage
    run instead of a second full-suite pass (T-3748)."""
    import json

    from frob.testing._coverage_refresh import _RUN_PROVENANCE_REL

    prov_path = root / _RUN_PROVENANCE_REL
    try:
        record = json.loads(prov_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log.error(
            "frob coverage --fail-on-degraded: coverage-run provenance %s is "
            "unreadable (%s) -- cannot confirm the suite passed, failing closed",
            prov_path,
            exc,
        )
        raise SystemExit(1) from exc
    if record.get("degraded") and not record.get("worker_crash"):
        _log.error(
            "frob coverage --fail-on-degraded: the suite ran RED (pytest exit "
            "%s) -- coverage was measured against a failing suite; failing the "
            "gate (T-3748)",
            record.get("pytest_exit_code"),
        )
        raise SystemExit(1)
