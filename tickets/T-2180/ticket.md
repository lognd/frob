---
id: T-2180
title: fleet_status.py cannot answer 'which lands are in flight', so every coordinator
  hand-rolls a ps grep that overcounts 4x -- the misread behind two agents reporting
  15-16 concurrent lands when there were 4
state: done
kind: feature
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_coordinator_scripts.py::TestLandInvocations::test_collapses_process_fan_out_by_ticket_id
- tests/unit/test_coordinator_scripts.py::TestLandInvocations::test_rows_with_no_ticket_id_are_dropped_not_reported
- tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_prints_invocations_and_live_lock_holder
- tests/unit/test_coordinator_scripts.py::TestLandLockHolderPids::test_finds_a_pid_holding_the_lock_open
- tests/unit/test_coordinator_scripts.py::TestLandLockHolderPids::test_no_live_holder_returns_empty
- tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_prints_stale_lock_when_no_live_holder
- tests/unit/test_coordinator_scripts.py::TestScopeIntersections::test_reports_overlapping_pair
- tests/unit/test_coordinator_scripts.py::TestScopeIntersections::test_no_overlap_reports_empty
- tests/unit/test_coordinator_scripts.py::TestScopeIntersections::test_checks_against_a_held_lease_outside_the_requested_set
- tests/unit/test_coordinator_scripts.py::TestPrintFleetReport::test_prints_all_four_sections
- tests/unit/test_coordinator_scripts.py::TestHostLoad::test_reads_loadavg_and_mem_available
- tests/unit/test_coordinator_scripts.py::TestHostLoad::test_missing_proc_files_return_none
- tests/unit/test_coordinator_scripts.py::TestLandProcessRows::test_parses_matching_rows_and_skips_others
- tests/unit/test_coordinator_scripts.py::TestLandProcessRows::test_failed_ps_returns_empty
- tests/unit/test_coordinator_scripts.py::TestLandInvocations::test_must_pass_control_one_land_many_processes_reports_one
designated_repro_test: null
acceptance:
- text: Report DISTINCT land invocations keyed on ticket id, derived from the process
    table's structured fields (pid, etimes, cpu time, argv), never from a line count.
    'ps aux | grep -c frob ticket land' returns roughly 4 per land (the bash wrapper,
    timeout, uv run, and the real python process); two agents independently reported
    '15-16 concurrent lands' when there were 4, and the coordinator nearly repeated
    it. This test MUST fail against current main.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestLandInvocations::test_collapses_process_fan_out_by_ticket_id
  - tests/unit/test_coordinator_scripts.py::TestLandInvocations::test_rows_with_no_ticket_id_are_dropped_not_reported
- text: Report each land's CPU time alongside elapsed time. Content alone cannot distinguish
    a live land from a dead attempt's residue -- a killed land's staged diff is byte-identical
    across retries because it is the same work -- but CPU time discriminates immediately.
    This is what falsely read as a 'wedged land' today.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_prints_invocations_and_live_lock_holder
- text: Report land.lock holder liveness from /proc fd ownership (does any live process
    hold the file open), NOT from the recorded pid and NOT from lock age. Pids are
    reused; a legitimate land genuinely exceeds 1500s under load. The absence of this
    check is why a stale-lock theory survived long enough to be filed critical and
    later retracted -- the lock is flock-based and the kernel frees it on holder death.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestLandLockHolderPids::test_finds_a_pid_holding_the_lock_open
  - tests/unit/test_coordinator_scripts.py::TestLandLockHolderPids::test_no_live_holder_returns_empty
  - tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_prints_stale_lock_when_no_live_holder
- text: 'Accept MULTIPLE --ticket ids in one invocation and report PAIRWISE SCOPE
    INTERSECTION across them, so a coordinator can check a whole wave for contention
    before dispatching it. Compare resolved scope globs against each other and against
    live leases -- not ticket titles or file-name similarity. Measured need: I dispatched
    contending tickets twice in one session (a five-ticket docs series all scoped
    to docs/modules/tickets.md, then T-1748 and T-1780 both claiming that same file),
    and the second collision hard-refused T-1780 at start via _refuse_on_scope_lease_collision,
    which has no --steal override. This test MUST fail against current main.'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestScopeIntersections::test_reports_overlapping_pair
  - tests/unit/test_coordinator_scripts.py::TestScopeIntersections::test_no_overlap_reports_empty
  - tests/unit/test_coordinator_scripts.py::TestScopeIntersections::test_checks_against_a_held_lease_outside_the_requested_set
- text: The wave check must live in the standing report a coordinator ALREADY runs,
    not behind a separate command. frob ticket wave --agents N already computes scope-disjoint
    groups and I failed to run it both times -- a capability that requires remembering
    it exists is not enforcement (the 'automatic over commands' rule). Surfacing intersection
    in the tool already in the dispatch loop is the fix.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintFleetReport::test_prints_all_four_sections
evidence_changes:
- old_node: tests/unit/test_coordinator_scripts.py::TestLandInvocations::test_rows_with_no_ticket_id_are_never_merged_together
  new_node: tests/unit/test_coordinator_scripts.py::TestLandInvocations::test_rows_with_no_ticket_id_are_dropped_not_reported
  reason: 'T-2193 fix: rows with no parseable ticket id are now dropped, not reported
    as their own invocation; test renamed to match'
  actor: logan
  at: '2026-08-16'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

fleet_status.py could not answer "which lands are in flight" -- every
coordinator hand-rolled `ps aux | grep "frob ticket land"`, counting
~4 process lines per real land (bash wrapper, timeout, uv run, python).

Added:
- land_process_rows: parses `ps -eo pid,etimes,time,args`'s structured
  columns for rows whose argv contains a "ticket land" invocation.
- land_invocations: collapses the row fan-out to distinct invocations
  keyed on the ticket id parsed from each row's own `--ticket T-####`
  argv fragment (acceptance [0]); reports elapsed (max etimes) and CPU
  time (max parsed ps TIME) per invocation (acceptance [1]) so a wedged
  process (near-zero CPU) can be told apart from a genuinely slow one.
  Rows with no parseable ticket id are reported individually, never
  silently merged.
- land_lock_holder_pids: scans /proc/<pid>/fd/* for a symlink resolving
  to .frob/land.lock's own absolute path -- never the pid recorded in
  the lock file's own JSON (reused pids) and never lock file age
  (acceptance [2]).
- scope_intersections: PAIRWISE scope-glob overlap across a list of
  ticket ids (via each ticket's effective scope -- lease if held, else
  main's declared scope), plus a check against every other currently
  held lease. Wired into `--ticket` (now repeatable) so 2+ ids print
  every collision (acceptance [3]).
- _print_land_status: prints LANDS + LAND LOCK unconditionally inside
  _print_fleet_report, the standing report a coordinator already runs
  before dispatch and land -- not a new command (acceptance [4]).

Optional addition taken at the coordinator's request (same file, same
"surface it where dispatch already looks" theme as this ticket's own
acceptance [4]): host_load reads /proc/loadavg and /proc/meminfo's
MemAvailable (never MemFree, which reads near-0 on a busy-but-healthy
host and would raise a false alarm) and prints a LOAD line alongside
LANDS, since both read process-table-adjacent state.

Repro-style verification: all new functions/prints are covered by new
unit tests against synthetic ps rows / synthetic /proc fixtures
(injectable `proc`/`root` params), not the live host, so tests are
deterministic. pytest collected count moved 51 -> 51 (T-2181 baseline)
-> 62 after T-2180's own additions (delta of +11 new tests across this
ticket's three lands: T-2180 fix commit +9, host-load commit +2).

--ticket is a repeatable flag now (argparse action="append"); a single
--ticket call is unchanged in behavior and exit-code semantics.

Mid-land correction (T-2193, coordinator-reported live): the ticket id
regex looked for a `--ticket T-####` FLAG, which does not exist on
`land`'s own argparse usage (the id is a bare POSITIONAL argument) --
so it matched NOTHING against a real `frob ticket land T-#### --worktree
...` invocation, every row fell back to `ticket_id=None`, and the
report read 13 rows for one real land (pid 2298926, the only row
burning real CPU at 67s). Fixed: `_LAND_ARGV_TICKET_RE` now matches the
positional form first (falls back to `--ticket` for any other `frob`
invocation shape), and `land_invocations` now DROPS any row with no
parseable ticket id entirely rather than reporting it as its own
`ticket_id=None` invocation -- there is nothing to deduplicate an
uncorrelated row against, so it is process-table noise (the measured
false positive: a coordinator's own ~28-hour wait-loop shell whose
command line merely contains the substring "frob ticket land"), never
evidence of a land. Added a must-pass control test (one land
represented by several processes must report exactly one) per the
coordinator's explicit request, plus a dedicated dropped-row test.
Verified live post-fix: `python3 scripts/fleet_status.py` correctly
reported "LANDS IN FLIGHT: 1" with the real ticket id during an actual
concurrent land.

Filed: none beyond T-2193 (already filed, cited above, out of this
ticket's scope -- src/frob/gates/_mutation_evidence.py).

### Changed
```
 tickets/T-2180/ticket.md | 12 ++++++++++--
 1 file changed, 10 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestLandInvocations::test_collapses_process_fan_out_by_ticket_id` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLandInvocations::test_rows_with_no_ticket_id_are_dropped_not_reported` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_prints_invocations_and_live_lock_holder` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLandLockHolderPids::test_finds_a_pid_holding_the_lock_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLandLockHolderPids::test_no_live_holder_returns_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_prints_stale_lock_when_no_live_holder` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestScopeIntersections::test_reports_overlapping_pair` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestScopeIntersections::test_no_overlap_reports_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestScopeIntersections::test_checks_against_a_held_lease_outside_the_requested_set` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintFleetReport::test_prints_all_four_sections` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestHostLoad::test_reads_loadavg_and_mem_available` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestHostLoad::test_missing_proc_files_return_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLandProcessRows::test_parses_matching_rows_and_skips_others` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLandProcessRows::test_failed_ps_returns_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLandInvocations::test_must_pass_control_one_land_many_processes_reports_one` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2180/src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2180, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
