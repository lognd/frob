---
id: T-2180
title: fleet_status.py cannot answer 'which lands are in flight', so every coordinator
  hand-rolls a ps grep that overcounts 4x -- the misread behind two agents reporting
  15-16 concurrent lands when there were 4
state: in-progress
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
- tests/unit/test_coordinator_scripts.py::TestLandInvocations::test_rows_with_no_ticket_id_are_never_merged_together
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
  - tests/unit/test_coordinator_scripts.py::TestLandInvocations::test_rows_with_no_ticket_id_are_never_merged_together
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
threat: null
component: null
anchor: false
anchor_reason: null
---
