## Done report

Added `src/frob/testing/_coverage_refresh.py` (T-1516): `native_coverage_refresh`,
a frob-native, pure-Python replacement for the COMMON path `make coverage`/
`make coverage-fast`'s shell recipe covers -- decides cold-start-full vs.
touched-set-incremental vs. nothing-to-do (reusing T-0484's
`python_coverage_targets`), spawns `pytest`/`coverage` via `subprocess`
directly (no `Makefile`/shell dependency, identical on Linux/macOS/
Windows -- T-1205 acceptance[3]), and always finishes by calling
`frob.gates._coverage.stamp_coverage` (deferred import, same cycle
avoidance as T-1517's wiring).

Wired `frob.testing._coverage_wait.run_coverage_wait`'s `command`
parameter to default to `None` (was `("make", "coverage-fast")`) --
`None` now routes through `native_coverage_refresh` in-process instead of
spawning `make`. This is real auto-wiring, not just a new function nobody
calls: `run_coverage_wait()`'s one production call site
(`src/frob/app/test_runner.py:301`, out of this ticket's scope, untouched)
gets the native path automatically because the DEFAULT changed, no
call-site edit required -- T-1205 acceptance[4]'s "no user-invoked
refresh verb" for that call path. Existing/explicit `command=(...)`
callers (every pre-existing test, plus any future caller that wants the
Makefile recipe's own resilience) are unaffected -- verified by re-running
`tests/test_app.py::TestRunCoverageWait` and
`tests/test_coverage_wait_shared.py` unchanged and green.

Deliberately deferred, disclosed rather than silently dropped (both in
`native_coverage_refresh`'s own module docstring and in
`docs/modules/gates.md`'s new "Coverage as managed derived state"
section):

- The Makefile recipe's xdist-crash serial-rerun recovery and
  configurable rerun-deadline knobs are NOT re-derived in Python here --
  real, already-hardened resilience against a specific parallel-run flake
  class that deserves its own dedicated ticket rather than a rushed port
  in this diff. `make coverage`/`make coverage-fast` themselves are
  UNCHANGED and still the right choice when that resilience is needed.
- T-1205 acceptance[3]'s "`make coverage` becomes a thin optional
  wrapper" is NOT done -- the Makefile itself was not touched to delegate
  into `native_coverage_refresh`; only `run_coverage_wait`'s own default
  was rewired. Filed as residue below.
- T-1205 acceptance[0]/[4]'s "auto-wired into any command whose gates
  need coverage" is intentionally NOT extended into `frob check` itself.
  Every dispatched worktree agent runs with `FROB_AGENT=1`
  (`docs/guides/agent-playbook.md` section 3b), and that section's whole
  contract depends on `frob check` staying bounded under a foreground
  timeout -- auto-spawning a coverage refresh (even touched-set-scoped)
  from inside every `frob check` call would reintroduce the exact
  auto-background stall class section 3b exists to prevent. Documented
  explicitly in `docs/modules/gates.md` so this is read as a deliberate
  safety boundary, not an oversight.

design/frob.strata: `frob:ticket T-1516` on both `core` and `testsuite`
nodes; `interface=` attrs for `CoverageRefreshError`, `native_coverage_
refresh`, `TestNativeCoverageRefresh`, `TestRunCoverageWaitNativeDefault`;
`src/frob/testing/_coverage_refresh.py` added to the `core` node's `exec`
`may ... via` list (the effects scanner flagged its `subprocess.
CompletedProcess` type reference). `frob check --only sys --ticket
T-1516` went from 5 errors to 0. `frob check --only coverage --only test
--only sys --only archgate --ticket T-1516` is 0 errors, 91 warnings, 211
waived (all pre-existing, unrelated to this ticket's diff).

docs/modules/gates.md: new "Coverage as managed derived state
(T-1205/T-1516/T-1517)" section documenting both tickets together (they
compose: T-1517's cache is what lets T-1516's incremental path read as
non-deflated) and explicitly naming what is and is not done.

Residue filed as follow-up drafts (real ids after the ledger renumber
that happens at land -- see `tickets.md` for the current draft blocks):
- T-draft-2187db71: port the Makefile recipe's xdist-crash-recovery/
  rerun-deadline resilience into `native_coverage_refresh` or an
  equivalent native path.
- T-draft-b655badc: rewrite `make coverage`/`make coverage-fast` to call
  into `native_coverage_refresh` for their own common-path work (T-1205
  acceptance[3]'s "thin wrapper" half).

### Changed
```
## Done report

Added `src/frob/testing/_coverage_cache.py` (T-1517): a persisted, per-file
content-hash keyed coverage cache at `.frob/coverage-file-cache.json`,
mirroring `frob.graph.cache`'s content-hash cache-invalidation pattern
(T-1464's `parsed_artifacts` table is the closest sibling, but this is a
single small JSON document, not a sqlite table -- coverage percentages are
a handful of small floats per file, not whole parsed-file payloads).

Three public functions: `load_file_cache` (read, `{}` on cold start),
`fill_from_cache` (backfill a freshly loaded `CoverageData.module_line`
for every file this run did NOT itself measure but whose current content
hash still matches the cache -- never overwrites data the run actually
measured), `update_file_cache` (persist every measured file's
`(content_hash, line_pct)`, merged with the existing cache so an
untouched file's entry survives a narrower run).

Wired into `frob.gates._coverage.stamp_coverage` (via
`_filtered_coverage_or_deflated`): the cache fill runs on every stamp,
BEFORE the T-1180/T-1435/T-1236 deflation/provenance/canary checks, so a
touched-set `--cov-append` run's narrower `coverage.xml` -- which
structurally cannot re-measure files it did not execute -- reads as "not
deflated" for files whose content genuinely has not changed, instead of
those files silently vanishing from `module_line` or forcing a full-suite
run just to keep the join fraction up. `update_file_cache` runs after a
successful `write_coverage_lock` so the cache always reflects the
freshest per-file numbers for the next stamp, incremental or full. Both
calls are deferred (function-local) imports from `frob.gates._coverage`
into `frob.testing._coverage_cache` -- `frob.testing`'s package `__init__`
already imports `_coverage_wait`, which imports `frob.gates._coverage`
(`load_stamp`) at module level, so a module-level import the other
direction would close a real import cycle during `frob.gates` package
init; verified by re-running the fresh-collection pytest suite after
adding the deferred-import fix (no ImportError).

This directly implements T-1205 acceptance[2] ("GIVEN an unchanged file
THEN its coverage is never recomputed: per-file coverage keyed by content
hash, full-suite runs reserved for cold start or explicit --full") for the
CACHING half; T-1516 (sequenced after this ticket) is the native
orchestration command that decides WHEN to run full vs. touched-set and
is what "full-suite runs reserved for cold start" ultimately depends on
end-to-end -- this ticket supplies the persistence layer that makes an
incremental run's coverage.xml honest once that orchestration exists.

design/frob.strata: added `frob:ticket T-1517` to both the `core` and
`testsuite` nodes (COV002), three new `interface=` attrs on `core`
(`fill_from_cache`, `load_file_cache`, `update_file_cache`), one on
`testsuite` (`TestCoverageFileCache`), and
`src/frob/testing/_coverage_cache.py` to both the `fs.read`/`fs.write`
`may ... via` lists (SELFAUDIT SYS100/SYS104) -- `frob check --only sys`
went from 6 errors to 0 after these.

No code outside `src/frob/testing/**`, `src/frob/gates/_coverage.py`,
`tests/test_coverage.py`, and `design/frob.strata` (the implicit
sweep-obligation surface every ticket touching public symbols/capability
effects must update) was touched.

### Changed

### Changed

### Changed
```
 design/frob.strata                    | 859 +++++++++++++++++-----------------
 docs/modules/gates.md                 |  66 +++
 docs/modules/testing.md               |  69 +++
 src/frob/gates/_coverage.py           |  29 ++
 src/frob/testing/__init__.py          |  14 +
 src/frob/testing/_coverage_cache.py   | 191 ++++++++
 src/frob/testing/_coverage_refresh.py | 292 ++++++++++++
 src/frob/testing/_coverage_wait.py    | 163 ++++---
 tests/test_coverage.py                | 248 +++++++++-
 tickets.md                            | 402 +++++++++++++++-
 10 files changed, 1839 insertions(+), 494 deletions(-)
```

### Evidence
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_incremental_run_uses_touched_set_targets` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_nothing_touched_only_restamps` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_pytest_failure_is_err` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestRunCoverageWaitNativeDefault::test_default_command_none_calls_native_refresh` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 693 warning(s), 781 waived
- error-findings: PRE001@tickets/T-1516
