---
id: T-1841
title: post-land sweep files regression tickets into root and leaves them untracked,
  DirtyMain-blocking every concurrent land
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: unit tests for the commit-retry-then-rollback fix
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_commits_the_ledger_write
- tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_commit_failure_logs_at_error_and_does_not_raise
- tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_retries_then_succeeds_on_a_transient_land_in_progress
- tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_exhausted_retries_discard_the_v2_ticket_dir_rather_than_leave_it_dirty
- tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_exhausted_retries_leave_a_v1_store_dirty_rather_than_guess
designated_repro_test: tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_retries_then_succeeds_on_a_transient_land_in_progress
threat: null
component: null
---
The deferred post-land sweep files a regression ticket into the ROOT
checkout and leaves it UNTRACKED. Root is then dirty, and every
concurrent `frob ticket land` in the fleet refuses with DirtyMain until
a human or coordinator commits the file by hand.

FOUR OCCURRENCES TODAY, each blocking a different agent's land:
T-1812/T-1813 (from T-1735 and T-1811), T-1826 (from T-1738), T-1839
(from T-1787). Every one required a coordinator to run `git add` plus
`git commit` with an explicit pathspec before the blocked agent could
proceed.

WHY IT IS WORSE THAN IT LOOKS. The blocked agent cannot diagnose it and
cannot fix it:

- The refusal names a file belonging to no open ticket's scope, and the
  agent is worktree-isolated, so it cannot inspect root to see what the
  file is or where it came from.
- Root-ownership discipline correctly forbids an agent from committing
  or discarding dirt it did not create -- so the correct behaviour for a
  well-behaved agent is to STOP AND REPORT, which is exactly what
  happened each time.
- So the sweep converts its own bookkeeping into a fleet-wide stall that
  only an actor outside the sandbox can clear. Three separate agents
  burned a land attempt on this today, and one idled a fleet slot waiting
  on it.

The sweep already knows how to file the ticket. It just does not commit
it. `frob ticket new` grew a uniform ledger auto-commit under T-1615, and
T-1758 extended that to programmatic (non-CLI) callers precisely because
uncommitted ledger writes DirtyMain-block lands. The sweep's own filing
path is evidently not going through that, or is failing silently after
the write.

REQUIRED:

1. The sweep must commit the ticket it files, in the same operation, via
   the same auto-commit path T-1615/T-1758 established. A file written
   and not committed is the defect; nothing else about the sweep needs to
   change.
2. If the commit cannot succeed (a land holds the index, say), the sweep
   must NOT leave the file behind. Either write-then-commit atomically or
   do not write -- a half-completed bookkeeping step that stalls the
   fleet is worse than a skipped one it can retry.
3. The sweep runs detached after a land, so it must assume a concurrent
   land is likely, not exceptional. Today's four instances all happened
   with five agents live, which is the normal operating condition here.

SIBLING: T-1804 fixed the sweep FILING SPURIOUS tickets (PRE001/SCOPE001
from an unscoped check with no derivable active ticket). This is the
mirror defect -- the sweep failing to DURABLY RECORD the legitimate ones.
Same actor, same detached-write assumption, opposite symptom.