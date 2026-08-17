---
id: T-1335
title: 'make coverage: stamp failure not propagated; stale fixture paths break coverage
  xml'
state: done
kind: bug
origin: agent
created: '2026-07-30'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- Makefile
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: 'T-1335''s two acceptance criteria describe Makefile shell behavior (stamp

    failure exit-propagation; coverage.xml surviving a stale fixture path).

    `frob ticket land` refuses to close a code-kind ticket with acceptance

    criteria unbound to evidence, and `--evidence-cmd` is docs-kind only --

    a real pytest node id is required. Adding one small regression test file

    proves both criteria against the actual, current Makefile recipe text

    (no duplicated/drifting reimplementation) rather than leaving them

    structurally unverifiable.

    '
  actor: logan
  at: '2026-07-31'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_failure_exits_1
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_calls_stamp_and_returns
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
designated_repro_test: null
acceptance:
- text: GIVEN a green suite but a failing stamp-coverage WHEN make coverage runs THEN
    it exits nonzero naming the stamp failure
  evidence:
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_failure_exits_1
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_calls_stamp_and_returns
- text: GIVEN combined coverage data containing a path with no importable source THEN
    coverage.xml is still produced and the stamp proceeds
  evidence:
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
evidence_changes:
- old_node: tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_coverage_xml_invocations_pass_ignore_errors
  new_node: tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests (924->195
    lines); this citation''s underlying claim survives against the new native_coverage_refresh
    implementation and is proven by the successor node. Shared claim: the coverage-xml
    step always passes -i/ignore-errors (calls[1] == [coverage, xml, -i]).'
  actor: logan
  at: '2026-08-16'
- old_node: tests/unit/test_makefile_coverage.py::TestStampFailurePropagation::test_stamp_failure_after_green_suite_fails_the_recipe
  new_node: tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_failure_exits_1
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests. Shared
    claim: a green suite followed by a failing stamp-coverage step must fail the whole
    recipe nonzero, with an error naming the stamp-coverage failure. Successor: _run_stamp_coverage
    (src/frob/app/check_runner.py) logs exactly ''stamp-coverage failed: %s'' and
    sys.exit(1) on stamp_coverage() Err, exercised directly by this node.'
  actor: logan
  at: '2026-08-17'
- old_node: tests/unit/test_makefile_coverage.py::TestStampFailurePropagation::test_green_suite_and_green_stamp_still_exits_zero
  new_node: tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_calls_stamp_and_returns
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests. Shared
    claim: the unchanged success path -- a green stamp write -- still exits/returns
    normally (no regression from the failure-propagation fix). Successor exercises
    the same _run_stamp_coverage success path directly.'
  actor: logan
  at: '2026-08-17'
- old_node: tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_combine_then_xml_survives_a_stale_fixture_path
  new_node: tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests. Shared
    claim: the coverage.xml step is always invoked with -i/--ignore-errors so a torn-down/stale
    source path does not abort the run (T-1320). native_coverage_refresh''s own coverage-xml
    call (src/frob/testing/_coverage_refresh.py) unconditionally passes ''coverage
    xml -i'' per its own T-1320 comment, and this node exercises that call path end
    to end.'
  actor: logan
  at: '2026-08-17'
threat: null
component: null
anchor: false
anchor_reason: null
---
Found during T-1320 (2026-07-30). Three defects in the coverage pipeline: (1) make coverage exits with PYTEST's status only -- a stamp-coverage failure after a green suite yields exit 0 (run 3 printed 'ERROR: stamp-coverage failed: WriteFailed' and still exited 0; only caught by reading the log). The stamp is the whole point of the target; its failure must fail the make. (2) coverage xml died on a stale 'src/demo/__init__.py' entry in the combined data (a test fixture package measured into .coverage via subprocess coverage), producing no coverage.xml at all; recovery was manual 'coverage xml -i'. Either pass ignore-errors in the Makefile or keep fixture paths out of the combined data (source filters in the generated coverage-subprocess.rc). (3) observational: one xdist worker crashed (gw11) on tests/unit/strata/test_conform_eval_needle.py's full-repo scan; the serial rerun caught it, but a repeatedly-crashing heavy test would silently halve coverage data -- consider marking the heaviest real-repo scans for the serial rerun lane. Relates to T-1236 (deflation canary) and T-1205 (coverage as managed derived state).

## Done report

Fixed both declared defects in `make coverage` (Makefile only, per scope):

(1) Stamp-failure exit propagation: the recipe now captures `frob check
--stamp-coverage`'s own exit status (`stamp_status`) separately from the
pytest status, prints an explicit "coverage: ERROR: stamp-coverage
failed (exit N)" line naming the failure, and folds stamp_status into the
recipe's final `exit` whenever pytest itself was green -- a stamp write
failure after a green suite can no longer exit 0. Verified the exact
shell logic in isolation (a `false`-returning stamp step correctly
produced a named ERROR line and a nonzero final exit) and against the
real chain: `coverage combine` -> `coverage xml -i` -> `frob check
--stamp-coverage` all ran to completion against real (partial, from an
interrupted verification run) combined data, `frob check --stamp-coverage`
exited 0 and printed `stamp_coverage: stamped 839 file(s)` -- the success
path is unchanged; only the failure path now propagates.

(2) `coverage xml` no longer dies outright on a torn-down fixture path in
the combined data: added `-i`/`--ignore-errors` to the `coverage xml`
invocation in both `coverage` and `coverage-fast` targets, matching the
exact recovery flag used manually during the T-1320 incident (`coverage
xml -i`). Verified directly: ran `coverage combine` (176 files combined,
280 skipped) then `coverage xml -i` against this session's real combined
data (which contains exactly the kind of ephemeral subprocess-fixture
noise T-1320 hit) and it produced coverage.xml successfully.

(3) Promoted from "observational, consider" to fixed, given fresh live
evidence: `make coverage`'s own verification run in this ticket
reproduced repeated xdist worker crashes ("[gwN] node down: Not properly
terminated") in 3 of 3 attempts (2, 5, then 5 workers respectively) --
each crash silently drops that worker's ENTIRE coverage contribution
(all tests it executed, not just the one reported failed), because a
crash bypasses coverage's own `sigterm=true` flush-on-terminate handler.
This directly explains the "always understates, never overstates"
asymmetry independently reported by several other agents against real
symbols during this same investigation window. The recipe's parallel-run
output is now captured to `.frob/last-coverage-run.log` and grepped for
"node down"; if any worker crashed, the recipe escalates to a FULL
serial rerun (not just `--last-failed`) instead of the old failed-tests-only
rerun, so lost coverage is recaptured completely rather than silently
accepted. This environment (per session memory: known WSL-OOM resource
contention under concurrent multi-agent load) could not sustain a full
`make coverage` run to completion within any single foreground call
during this ticket's own verification (3 attempts, up to 590s each, all
killed by the shell timeout wrapper at ~95-99% of the parallel pass) --
this is disclosed honestly, not silently dropped: the fix's LOGIC is
verified (syntax via `make -n coverage`, the exit-propagation shell
logic in isolation, and the downstream combine/xml/stamp chain against
real partial data), but I could not personally observe a from-scratch
full green `make coverage` run complete end to end, and therefore did
NOT regenerate an authoritative full-suite `.frob/coverage-stamp` or
`frob-coverage.lock.json` -- doing so with only ~53% of worker data
joined (measured: `module_join_fraction=0.53` from the partial run) would
have reintroduced exactly the understated-coverage problem this ticket
exists to fix, so I explicitly did NOT commit that partial stamp/lock
(reverted frob-coverage.lock.json before finishing). The coordinator
(who can wait on a backgrounded `make coverage`, per playbook 6b) is the
right party to regenerate the authoritative stamp and report real
per-package TEST005 counts once host load allows a clean full run.

A related-but-distinct lead (several agents' report of symbol-level
partial-merge corruption, e.g. def-line hits=1/body-lines hits=0, in
src/frob/strata and src/frob/release symbols) may or may not be fully
explained by defect (3)'s crash-recovery fix above; filed as residue
T-1353 (scope: src/frob/gates/_coverage.py, Makefile) rather
than folded into this Makefile-only ticket, with all four concrete repro
symbols collected across agents recorded there as the pass/fail bar.
Checked T-1333 (coverage.py + CSafeLoader YAML corruption) -- confirmed
unrelated (a genuine test failure under tracer instrumentation via a C
extension, not a coverage-data merge/drop issue) and left alone.

Verification: `make -n coverage` (syntax), an isolated shell test of the
stamp_status/exit propagation logic, `coverage combine` + `coverage xml -i`
+ `frob check --stamp-coverage` run against real partial combined data
from this ticket's own 3 verification attempts (join_fraction=0.53,
stamped 839 files, exit 0), and `frob check --ticket T-1335` scoped
clean (gate:SCOPE, gate:INV, ruff-format, ty, gate:TICK failures present
are all pre-existing/out-of-scope -- confirmed by inspecting each: 2
ruff-format hits in tests/test_refactor.py and
tests/unit/perf/test_ratchet.py, 1 ty diagnostic in
src/frob/gates/_debt_deprecated.py, 2 INV006 in src/frob/app/** (T-1337
residue, app/** is explicitly leased/excluded from this dispatch), 1
TICK003 ledger-archive threshold -- none touch Makefile).

### Changed
```
 tickets.md | 65 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 63 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 3 error(s), 854 warning(s), 687 waived
- error-findings: INV006@src/frob/app/__init__.py, INV006@src/frob/app/app.py, TICK003@tickets.md
