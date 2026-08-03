"""T-1395 regression lock: daemon/CLI-entry modules must stay attributed.

T-1395 tracked `src/frob/serve/**` and `src/frob/__main__.py` reading
exactly 0.0% coverage in a full `make coverage` run even after T-1235's
subprocess-rc fix landed -- the daemon and CLI-entry process classes were
not inheriting `COVERAGE_PROCESS_START` the way pytest-spawned subprocess
tests do. T-1433 (closed 2026-08-03, independent of this ticket)
root-caused the real underlying defect as xdist worker OOM-kills at
COVERAGE_WORKERS=4 corrupting the run, not an attribution-mechanism bug in
either of this file's own scoped modules; dropping the default worker
count to 2 produced the first clean, non-wedged completion. The committed
`frob-coverage.lock.json` from that clean run (commit 5ffa0159, stamped
2026-08-03) shows every module this ticket named now reading real,
non-zero coverage -- this test locks that fact down so a REGRESSION back
to the 0.0% daemon/CLI-entry attribution failure is caught by a fast unit
test instead of only being noticed the next time someone reads the raw
lock by hand.
"""

from __future__ import annotations

import json
from pathlib import Path

#: T-1395: repo root, two levels up from this test file
#: (tests/unit/test_coverage_attribution_lock_t1395.py -> repo root).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

#: T-1395's own named acceptance-criteria modules -- serve/** (daemon) and
#: __main__.py (CLI entry) -- plus serve/_leases.py, named at 0.0% in the
#: ticket body alongside serve/_socketd.py.
_T1395_NAMED_MODULES = (
    "src/frob/serve/_socketd.py",
    "src/frob/serve/_leases.py",
    "src/frob/__main__.py",
)


def _load_committed_lock() -> dict[str, float]:
    """`module_line` mapping from the committed `frob-coverage.lock.json`.

    Reads the repo-root lock directly (the same file `write_coverage_lock`/
    `load_coverage_lock` in `frob.gates._coverage` produce and consume) --
    a small, self-contained fixture-free check that this specific ticket's
    named modules stay attributed, without depending on a fresh
    `coverage.xml` this repo does not keep around (playbook section 6d).
    """
    lock_path = _REPO_ROOT / "frob-coverage.lock.json"
    data = json.loads(lock_path.read_text())
    return data["module_line"]


# frob:ticket T-1395
class TestCoverageAttributionLockStaysNonZero:
    """Regression lock: T-1395's named daemon/CLI-entry modules stay attributed."""

    def test_t1395_named_modules_are_nonzero_in_committed_lock(self) -> None:
        """serve/_socketd.py, serve/_leases.py, __main__.py must not regress to 0.0%."""
        module_line = _load_committed_lock()
        for module in _T1395_NAMED_MODULES:
            assert module in module_line, f"{module} missing from committed lock"
            assert module_line[module] > 0.0, (
                f"{module} regressed to the T-1395 zero-coverage failure mode "
                f"(module_line[{module}] = {module_line[module]})"
            )

    def test_no_module_reads_exactly_zero_in_committed_lock(self) -> None:
        """No module in the committed lock should sit at exactly 0.0% coverage.

        A module pinned at exactly 0.0% is the fingerprint of the whole
        process class this ticket (and its sibling T-1235) tracked -- a
        module that is genuinely never exercised is rare in a repo this
        size and would normally be excluded or dead-code-flagged rather
        than silently sitting at zero in a committed full-run lock.
        """
        module_line = _load_committed_lock()
        zero_modules = sorted(m for m, pct in module_line.items() if pct == 0.0)
        assert zero_modules == [], (
            f"{len(zero_modules)} module(s) read exactly 0.0% in the "
            f"committed lock: {zero_modules}"
        )
