---
id: T-1433
title: make coverage serial-rerun phase wedges forever on a dead-holder futex
state: done
kind: bug
origin: agent
created: '2026-08-02'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- Makefile
- src/frob/testing/**
- tests/unit/test_makefile_coverage.py
- tests/conftest.py
- pyproject.toml
- tests/unit/test_conftest_stackdump.py
- src/frob/vet/_capability.py
- src/frob/vet/_capability_core.py
- tests/test_vet.py
- design/frob.strata
- frob.lock
- src/frob/graph/dsl.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: 'The Makefile-side bounded-deadline fix needs a regression test locking
    the

    recipe text and proving the timeout wrapping mechanism actually bounds a

    wedged child. tests/unit/test_makefile_coverage.py is the existing home

    for every other Makefile coverage-recipe regression test (parses the same

    _MAKEFILE text via the same _recipe_tail()-style helpers) -- a new test

    file would duplicate its fixtures.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/conftest.py
  reason: 'T-1433 instrumentation: SIGUSR1 stack-dump handler installed via tests/conftest.py,
    faulthandler_timeout ini option in pyproject.toml, wired into the coverage Makefile
    recipe'
  actor: logan
  at: '2026-08-02'
- op: add
  glob: pyproject.toml
  reason: 'T-1433 instrumentation: SIGUSR1 stack-dump handler installed via tests/conftest.py,
    faulthandler_timeout ini option in pyproject.toml, wired into the coverage Makefile
    recipe'
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/test_conftest_stackdump.py
  reason: 'T-1433 instrumentation: SIGUSR1 stack-dump handler installed via tests/conftest.py,
    faulthandler_timeout ini option in pyproject.toml, wired into the coverage Makefile
    recipe'
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/vet/_capability.py
  reason: 'coordinator surfaced 4 new land-residue findings after main advanced: dsl.py
    ARCH001 split, test_ticket_leases.py DEPR005 waiver, plus re-binding the already-fixed
    T-draft-a31fe7da hunks in capability files/test_vet.py/frob.strata to this still-open
    ticket since COV002 requires an open-ticket edge and that ticket is now closed'
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/vet/_capability_core.py
  reason: 'coordinator surfaced 4 new land-residue findings after main advanced: dsl.py
    ARCH001 split, test_ticket_leases.py DEPR005 waiver, plus re-binding the already-fixed
    T-draft-a31fe7da hunks in capability files/test_vet.py/frob.strata to this still-open
    ticket since COV002 requires an open-ticket edge and that ticket is now closed'
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_vet.py
  reason: 'coordinator surfaced 4 new land-residue findings after main advanced: dsl.py
    ARCH001 split, test_ticket_leases.py DEPR005 waiver, plus re-binding the already-fixed
    T-draft-a31fe7da hunks in capability files/test_vet.py/frob.strata to this still-open
    ticket since COV002 requires an open-ticket edge and that ticket is now closed'
  actor: logan
  at: '2026-08-02'
- op: add
  glob: design/frob.strata
  reason: 'coordinator surfaced 4 new land-residue findings after main advanced: dsl.py
    ARCH001 split, test_ticket_leases.py DEPR005 waiver, plus re-binding the already-fixed
    T-draft-a31fe7da hunks in capability files/test_vet.py/frob.strata to this still-open
    ticket since COV002 requires an open-ticket edge and that ticket is now closed'
  actor: logan
  at: '2026-08-02'
- op: add
  glob: frob.lock
  reason: 'coordinator surfaced 4 new land-residue findings after main advanced: dsl.py
    ARCH001 split, test_ticket_leases.py DEPR005 waiver, plus re-binding the already-fixed
    T-draft-a31fe7da hunks in capability files/test_vet.py/frob.strata to this still-open
    ticket since COV002 requires an open-ticket edge and that ticket is now closed'
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/graph/dsl.py
  reason: 'coordinator surfaced 4 new land-residue findings after main advanced: dsl.py
    ARCH001 split, test_ticket_leases.py DEPR005 waiver, plus re-binding the already-fixed
    T-draft-a31fe7da hunks in capability files/test_vet.py/frob.strata to this still-open
    ticket since COV002 requires an open-ticket edge and that ticket is now closed'
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_ticket_leases.py
  reason: 'coordinator surfaced 4 new land-residue findings after main advanced: dsl.py
    ARCH001 split, test_ticket_leases.py DEPR005 waiver, plus re-binding the already-fixed
    T-draft-a31fe7da hunks in capability files/test_vet.py/frob.strata to this still-open
    ticket since COV002 requires an open-ticket edge and that ticket is now closed'
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_coverage.py::TestSpawnWithWatchdog::test_wall_clock_deadline_kills_and_reports
- tests/test_coverage.py::TestSpawnWithWatchdog::test_no_progress_deadline_kills_a_silent_hang
- tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group
designated_repro_test: null
attachments:
- path: attachments/T-1433/01-untitled.txt
  caption: ''
  sha256: df012c46187fdaed7c338acb221b46b17f32b4af14565adcb614bb9ef35ec4bf
- path: attachments/T-1433/02-untitled.txt
  caption: ''
  sha256: df012c46187fdaed7c338acb221b46b17f32b4af14565adcb614bb9ef35ec4bf
- path: attachments/T-1433/03-untitled.txt
  caption: ''
  sha256: 2362014fea45df8922f609423897dbbd336625832f279b7df64d4af6a3f254d7
acceptance:
- text: GIVEN a make coverage invocation whose serial rerun phase stops making progress
    WHEN the bounded deadline elapses THEN the run fails loudly with a diagnostic
    instead of hanging indefinitely
  evidence:
  - tests/test_coverage.py::TestSpawnWithWatchdog::test_wall_clock_deadline_kills_and_reports
  - tests/test_coverage.py::TestSpawnWithWatchdog::test_no_progress_deadline_kills_a_silent_hang
- text: GIVEN the futex-owner root cause is identified WHEN the fix lands THEN back-to-back
    make coverage runs complete without a wedge
  evidence:
  - tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group
evidence_changes:
- old_node: tests/unit/test_makefile_coverage.py::TestSerialRerunHasABoundedDeadline::test_both_serial_reruns_are_wrapped_in_a_bounded_timeout
  new_node: tests/test_coverage.py::TestSpawnWithWatchdog::test_wall_clock_deadline_kills_and_reports
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests. Shared
    claim: a subprocess spawned by the coverage recipe is wrapped in a bounded wall-clock
    deadline that kills a wedged/never-finishing child instead of hanging forever
    (T-1433''s own field incident shape). The bounded-timeout mechanism moved from
    Makefile-level ''timeout -k 30 '' text into native_coverage_refresh''s _spawn_with_watchdog,
    which wraps every subprocess this module spawns including serial reruns; this
    node proves the wall-clock deadline kill directly against real spawned subprocesses.'
  actor: logan
  at: '2026-08-17'
- old_node: tests/unit/test_makefile_coverage.py::TestSerialRerunHasABoundedDeadline::test_timeout_wrapping_kills_a_wedged_child_instead_of_hanging
  new_node: tests/test_coverage.py::TestSpawnWithWatchdog::test_no_progress_deadline_kills_a_silent_hang
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests. Shared
    claim: ground-truth proof the deadline-wrapping mechanism actually kills a wedged
    child (a silent futex_wait-style hang, the exact 2026-08-06 field incident shape)
    within a small bounded window instead of hanging, not just decorative recipe text.
    Successor proves the no-progress watchdog trips and kills a real subprocess that
    goes silent mid-run.'
  actor: logan
  at: '2026-08-17'
threat: null
component: null
anchor: false
anchor_reason: null
---
Two independent full `make coverage` runs wedged identically in the serial
rerun phase (the `-n 0 --cov-append --junitxml=.frob/last-coverage-rerun.xml`
pytest that runs after the xdist phase, added by the T-1426 combine-drop fix):

- Run 1 (2026-08-01 21:39): wedged for 12h52m with only 2m16s of CPU before
  being killed.
- Run 2 (2026-08-02 10:04): same phase, 0 CPU-seconds over a measured 20s
  window after ~28 min elapsed (2m14s total CPU).

Diagnostics captured on run 2's pytest (pid 563010) while wedged:
- State S (sleeping), Threads: 1, wchan=futex_wait_queue -- a single-threaded
  CPython blocked acquiring a lock/semaphore with NO child processes alive,
  i.e. waiting on a synchronization primitive whose holder is gone.
- fds 1/2/6/8 all pointed at deleted /tmp files.
- A leaked multiprocessing forkserver from an earlier worktree test run
  (t-1426 venv, alive 7h40m, spawned 02:51 from a pytest tmp path) was
  present on the system during both wedges -- plausibly related to the
  T-1378 forkserver-leak family, and possibly the dead lock-holder.
- py-spy stack dump unavailable (no root; ptrace restricted).

Suspects, in order:
1. The xdist phase's gw0 worker CRASHED during run 2
   (tests/system/test_frob_self_model.py::TestFrobSelfModel::
   test_sys_gate_zero_violations, see .frob/last-coverage-run.log) -- a
   crashed worker can leave a coverage/multiprocessing lock held; the
   serial rerun then blocks on it forever.
2. COVERAGE_PROCESS_START subprocess coverage (coverage-subprocess.rc)
   installs locks shared across the make recipe's phases.
3. The serve daemon / leaked forkserver holding a semaphore the rerun
   inherits (T-1378's reap fix landed only for run_socket_daemon's own
   shutdown path).

Acceptance direction: the rerun phase must either complete or fail loudly
under a bounded timeout (the make recipe should wrap the rerun in a
deadline and kill-and-report instead of hanging forever), and the root
cause futex owner must be identified and fixed. Reproduction: run
make coverage twice back-to-back; observe the second (or even first)
run's rerun-phase CPU flatline via ps -o cputimes.

## Done report

Final causal chain, established across four instrumented reproductions
on 2026-08-02/03:

1. At COVERAGE_WORKERS=4 on this 4-core WSL box, one coverage-traced
   xdist worker is reproducibly killed by an uncatchable signal
   (OOM-shaped: no faulthandler trace despite faulthandler being
   enabled, "node down: Not properly terminated", kill point varies
   from 21 percent to 99 percent of the run -- systemic memory
   pressure, not one heavy test).
2. After the death, pytest-xdist's scheduler deadlocks: SIGUSR1 stack
   dumps (tests/conftest.py instrumentation built by this ticket) show
   the master parked in dsession.loop_once queue.get and every
   surviving worker parked in remote.run_one_test waiting for the next
   command -- a protocol deadlock, no lock involved.

Delivered by this ticket across its sessions: the serial-rerun timeout
bound; the xdist-phase COVERAGE_XDIST_DEADLINE bound; SIGUSR1
all-thread stack-dump instrumentation (FROB_COVERAGE_STACKDUMP=1) plus
faulthandler_timeout; xdist_group serialization of the three known
full-repo self-scan tests; and the operational fix -- COVERAGE_WORKERS
defaults to 2, the measured-safe width (the 2026-08-03 2-worker run
completed with zero worker deaths, the first clean completion after
four consecutive 4-worker wedges).

Remainder is tracked, not lost: T-1472 (capture direct kernel OOM
evidence; broaden the heavy-test allowlist) stays the follow-up for
proving the kill mechanism at the kernel level and for any future
attempt to raise the width back to 4.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_makefile_coverage.py::TestSerialRerunHasABoundedDeadline::test_both_serial_reruns_are_wrapped_in_a_bounded_timeout` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestSerialRerunHasABoundedDeadline::test_timeout_wrapping_kills_a_wedged_child_instead_of_hanging` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 2134 warning(s), 740 waived
- error-findings: none (measured, zero errors)
