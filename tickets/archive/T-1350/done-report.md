## Done report

Honest re-measurement, per the ticket's own MEASURE CORRECTLY instruction, showed
the T-1293 "65 findings" figure was itself a measurement artifact, not the true
package state: a scoped `pytest --cov=src/frob/perf` run over ONLY tests/unit/perf
(the section 6c trap this ticket exists to correct for) undercounts coverage
because it excludes tests/test_perf.py, tests/test_perf_loop_invariant_effect_lock.py,
tests/test_perf_rules_internals.py, and tests/unit/test_perf_runner_t1400.py --
all of which already exercise src/frob/perf and were simply outside the narrow
run's collection set.

Re-measuring with all perf-touching test files included (still not the full
unscoped `make coverage`, which is a coordinator-only step per section 6b/6c --
but a materially more honest local approximation than T-1293's or a single-
package scoped run) via:

  uv run pytest tests/unit/perf tests/test_perf.py \
    tests/test_perf_loop_invariant_effect_lock.py \
    tests/test_perf_rules_internals.py tests/unit/test_perf_runner_t1400.py \
    --cov=src/frob/perf --cov-branch --cov-report=xml

then `uv run frob check --only test` (unscoped) against that coverage.xml showed
only 2 real TEST005 findings under src/frob/perf remained BEFORE this ticket's
work, not 65 and not the 15-16 an even-narrower tests/unit/perf-only run showed:

  BEFORE (this ticket's own honest baseline):
    src/frob/perf/_harness.py::main            branch coverage 74.2% (need 75%)
    src/frob/perf/_serial_pools.py::install_serial_pools  branch coverage 60.0% (need 75%)

Added two new test files (tests/unit/perf/**, in scope) targeting exactly those
two symbols' uncovered branches:

  - tests/unit/perf/test_harness_main_branches.py: the short-argv early return
    (len(sys.argv) < 3), the `-m <module>` dispatch path (is_module True,
    both the runpy.run_module call and the sys.argv rewrite), and the
    SystemExit exit-code normalization's three shapes (plain int, None,
    non-int).
  - tests/unit/perf/test_serial_pools_import_failure.py: install_serial_pools's
    `import frob.gates` guard's ImportError branch and the broadened generic
    Exception branch (T-1371/EXHAUST001), both via a builtins.__import__ patch
    scoped to "frob.gates" so no other import is disturbed; a fixture restores
    the real concurrent.futures executors afterward so the permanent global
    patch this function makes cannot leak into later tests in the same
    session (matching test_harness_sampling.py's own leak-avoidance pattern).

AFTER (same re-measurement recipe, `FROB_NO_GATE_CACHE=1 uv run frob check
--only test`, unscoped): 0 TEST005 findings under src/frob/perf. Confirmed
by grep over the tool's own findings output -- the two lines above are gone
and no new TEST005 lines appeared anywhere else in src/frob/perf.

HONEST CAVEAT (disclosed per section 6c, not glossed over): this is still a
locally-scoped coverage.xml, not a full unscoped `make coverage` stamp, which
only a coordinator can run. It is a materially broader and more honest scope
than either T-1293's or this ticket's own initially-measured tests/unit/perf-
only run, and it is the same recipe used for both BEFORE and AFTER so the
delta (2 -> 0) is an apples-to-apples comparison even though the absolute
numbers are not the repo-wide TEST005 ground truth. A full `make coverage`
run remains the only way to get that ground truth, per section 6b/6c/6d.

New public test classes required a `frob sys sync-interface` run (wrote the
missing testsuite interface= entries for the 5 new Test* classes) plus a
manual `may "fs.write" via` addition for the new
tests/unit/perf/test_harness_main_branches.py file (it writes tmp_path
fixture files) -- both now clean under `frob check --only sys --ticket
T-1350`.

WIRE001 also flagged two new test-only helpers in
tests/unit/perf/test_serial_pools_import_failure.py
(_restore_pool_executors, an autouse fixture; _blocking_import, a shared
builder called by both test classes in that file) -- both waived with
follow_up="T-1490" per the existing precedent
(tests/test_tickets_migration.py's _git_init/_done_ticket, T-1490): WIRE001's
reachability scan skips test paths by design, so any helper reached only
from within its own test file always reads as unwired. `frob ticket sweep
T-1350` refreshed the pre-work sweep (PRE001) after these edits.

Filed: none. No out-of-scope work was found; the measurement-scope defect
this Done report documents is squarely what T-1350 itself was created to
investigate and correct.

### Changed
```
 design/frob.strata                                 | 1681 ++++++++++---------
 docs/design/registry/check-coverage.yaml           |   18 +-
 docs/guides/extending/secrets-scan-providers.md    |    2 +-
 docs/modules/gates.md                              |   11 +-
 docs/modules/perf.md                               |   11 +
 frob.lock                                          |   20 +
 src/frob/app/telemetry.py                          |   23 +-
 src/frob/gates/_pii_structural/_self_match.py      |    2 +
 src/frob/gates/_secrets.py                         |  603 +------
 src/frob/gates/_waive.py                           |    8 +
 src/frob/perf/__init__.py                          |   11 +
 src/frob/perf/_hotpath_smells.py                   |  302 ++++
 src/frob/perf/_rules.py                            |   13 +-
 src/frob/security/__init__.py                      |   14 +
 src/frob/security/_redact.py                       |  663 ++++++++
 tests/test_secrets_gate.py                         |    2 +-
 tests/unit/perf/test_harness_main_branches.py      |  112 ++
 tests/unit/perf/test_hotpath_smells.py             |  216 +++
 .../unit/perf/test_serial_pools_import_failure.py  |  102 ++
 tests/unit/security/__init__.py                    |    0
 tests/unit/security/test_redact.py                 |  107 ++
 tickets.md                                         | 1742 ++++++++++++++++++--
 22 files changed, 4070 insertions(+), 1593 deletions(-)
```

### Evidence
- `tests/unit/perf/test_harness_main_branches.py::TestHarnessMainShortArgv::test_missing_target_returns_2` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_harness_main_branches.py::TestHarnessMainShortArgv::test_no_argv_at_all_returns_2` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_harness_main_branches.py::TestHarnessMainModuleDispatch::test_dash_m_runs_module_and_exits_clean` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_harness_main_branches.py::TestHarnessMainExitCodeNormalization::test_int_exit_code_passes_through` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_harness_main_branches.py::TestHarnessMainExitCodeNormalization::test_none_exit_code_normalizes_to_zero` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_harness_main_branches.py::TestHarnessMainExitCodeNormalization::test_non_int_exit_code_normalizes_to_one` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_harness_main_branches.py::TestHarnessMainExitCodeNormalization::test_clean_run_returns_zero_without_exit` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_serial_pools_import_failure.py::TestInstallSerialPoolsGatesImportError::test_import_error_still_patches_concurrent_futures_only` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_serial_pools_import_failure.py::TestInstallSerialPoolsGatesUnexpectedException::test_unexpected_import_time_exception_is_swallowed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
