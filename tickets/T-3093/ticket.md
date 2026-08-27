---
id: T-3093
title: 'fleet_status reports lock WAITERS as holders: label claims more than the /proc
  fd scan measures'
state: done
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: Record the measured mislabel, its cost today, and the requirement to declare
    the limit rather than print a confident wrong holder set
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 3032
evidence:
- tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_finds_the_true_holder
- tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_ignores_a_lock_on_a_different_inode
- tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_unreadable_proc_locks_is_indeterminate
- tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_missing_lock_file_is_true_none
- tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_distinguishes_true_holder_from_waiters
- tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_must_stay_quiet_single_holder_no_waiters_unchanged_meaning
- tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_indeterminate_true_holder_says_so_not_a_confident_number
- tests/unit/test_coordinator_scripts.py::TestConcurrentCheckCount::test_counts_module_invoked_check
- tests/unit/test_coordinator_scripts.py::TestIsLiveCheckCmdline::test_does_not_match_check_repro_subcommand
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid::test_finds_the_true_holder
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27. `scripts/fleet_status.py` reported:

    LAND LOCK: held, live holder pid(s)=[1435787, 1438943, 1442733]

with three lands in flight. Read literally, that says three processes held the
same lock simultaneously, which would be a serious correctness bug. I nearly
reported it as one.

IT IS NOT A LOCK BUG. `land_lock_holder_pids` scans `/proc/*/fd` for any live
process with `land.lock` OPEN. `_land_lock` is a NON-BLOCKING flock poll loop,
so every WAITING process also holds the file open -- without holding the flock
-- for the whole time it polls. The reading was one real holder plus two
waiters.

WHY THIS IS WORTH FIXING RATHER THAN SHRUGGING OFF. The label says "holder".
The number it prints is "has the file open". Those are different sets, and the
difference is exactly the distinction an operator is consulting this line to
make. Today it cost real time: I saw three holders, suspected a serialization
defect, and had to hand the question to an implementer to disprove. Earlier in
the same session I made a CONFIDENT WRONG CLAIM about `land.lock` (asserting a
stale lock was deadlocking the fleet; it is flock-based and the kernel releases
it on holder death) and had to retract it. A probe that overstates its own
evidence is how that kind of error gets made twice.

This is the same class as the repo's other measurement-integrity findings: a
number that is honest about what it counted, versus a number that is read as
answering the question you asked. `fleet_status.py` is the FIRST thing consulted
when the fleet looks wrong, so a misleading line there propagates into every
subsequent diagnosis.

WHAT IS WANTED
- Distinguish HOLDER from WAITER. The holder is the process actually holding
  the flock; waiters are polling with the file open. Report them separately, or
  report only the true holder and count the waiters.
- If the true holder cannot be determined from /proc alone (plausible -- flock
  ownership is not directly exposed the way fd-open is), then SAY SO in the
  output rather than printing the fd-open set under a "holder" label. An
  honest "N processes have the lock file open; true holder not determinable
  from /proc" is strictly better than a confident wrong number. Declaring the
  limit is the standing doctrine here.
- While in this function, audit the other lines in `fleet_status.py` for the
  same gap: a label that claims more than the measurement supports. The
  ORPHANED FORKSERVERS line and the IDLE?/[ACTIVE] worktree annotations are the
  obvious candidates. Report what you find even if you change nothing.

ACCEPTANCE
- With one land running and two waiting, the output distinguishes the single
  holder from the two waiters, or explicitly declares that it cannot.
  Must-fire fixture reproducing the 1-holder/2-waiter arrangement.
- With a single land and no waiters, the output is unchanged in meaning.
  Must-stay-quiet fixture.
- No line in `fleet_status.py` claims more than its measurement supports; list
  the lines audited and the verdict for each.