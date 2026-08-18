---
id: T-2517
title: fleet_status reports ORPHANED FORKSERVERS 0 while 82 stale pools hold 12GB
  of swap
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- tests/unit/test_coordinator_scripts.py
- docs/guides/coordinator-scripts.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: new stale/swap-held forkserver reporting needs test coverage and its own
    frob:doc anchors alongside the existing orphaned_forkserver_count docs
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: new stale/swap-held forkserver reporting needs test coverage and its own
    frob:doc anchors alongside the existing orphaned_forkserver_count docs
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount::test_counts_old_forkserver_when_no_checks_running
- tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount::test_ignores_young_forkserver
- tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount::test_never_counts_anything_while_a_check_is_running
- tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount::test_unknown_concurrent_checks_never_counts_anything
- tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount::test_missing_proc_returns_none
- tests/unit/test_coordinator_scripts.py::TestForkserverSwapHeldKb::test_sums_vmswap_across_every_forkserver
- tests/unit/test_coordinator_scripts.py::TestForkserverSwapHeldKb::test_missing_status_file_degrades_that_entry_to_zero_not_a_crash
- tests/unit/test_coordinator_scripts.py::TestForkserverSwapHeldKb::test_missing_proc_returns_none
- tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_prints_no_live_holder_as_normal_resting_state_not_stale
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-18, live, while the fleet was healthy-looking:

    fleet_status:  ORPHANED FORKSERVERS: 0
                   CONCURRENT CHECKS: 0
    reality:       148 forkserver processes
                   82 of them older than 1 hour
                   12,030 MB of swap held by them
                   (system swap in use at that moment: 12 GB -- i.e.
                    essentially ALL swap in use was forkservers)

The detector is not wrong by its own definition; it is too narrow.
T-2443's orphan test is "reparented to init" (ppid == 1). These 82 still
had a LIVE ancestor -- an agent shell that had finished its check but had
not exited -- so none of them counted, and the operator-facing number
read ORPHANED: 0 while the machine was swapping 12 GB.

That is the [[silent-zero]] shape applied to the monitoring tool itself:
the count is honest about what it measures and reads as "nothing wrong".

The discriminating signal is not ancestry, it is IDLENESS + AGE +
ABSENCE OF WORK: a forkserver older than N minutes when CONCURRENT CHECKS
is 0 is not serving anything, regardless of whether its parent is alive.
Reclaiming exactly those (SIGTERM, all exited cleanly) took swap from
12 GB to 6 GB and the forkserver count from 148 to 88 with no disruption
to five running agents.

DELIVERABLE: widen fleet_status's forkserver reporting so a stale-but-
parented pool is visible. Suggested shape -- report THREE numbers, never
collapse them into one:

    ORPHANED (init-reparented, T-2443's existing test)
    STALE    (older than N, with zero checks running)
    SWAP HELD (sum of VmSwap across all forkservers, in MB)

RSS is useless here: swapped-out processes report ~0 RSS while holding
gigabytes. Sum VmSwap from /proc/<pid>/status.

CAUTION on any automated reclamation (do NOT add one in this ticket
without discussion): a forkserver whose parent is alive MAY belong to a
check that is about to start. The measurement above is safe because
CONCURRENT CHECKS was 0. A reaper that ignores that precondition would
kill live pools under load, which is worse than the leak.

MEASUREMENT HONESTY NOTE for whoever picks this up: two passes minutes
apart counted 11 and then 73 init-reparented processes. The population
shifts as agent shells exit and reparent their children, so a single
snapshot is not a stable denominator. Sample twice and say which one
you acted on.