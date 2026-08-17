---
id: T-1983
title: 'Sweep-filed tickets go stale before anyone reads them: 2 today, one cost a
  full agent investigation, and they displace genuinely starved work'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
evidence_scope:
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: test evidence for the T-1983 fix lives here, matching the existing test
    file's coverage of this same module
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_rapid_sweep.py::TestDeferredSweepClosesResolvedRegressions::test_resolved_finding_is_dropped_by_the_next_sweep
- tests/unit/test_rapid_sweep.py::TestDeferredSweepClosesResolvedRegressions::test_still_reproducing_finding_is_left_untouched
- tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_drops_a_fully_resolved_sweep_ticket
- tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_leaves_a_partially_resolved_ticket_untouched
- tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_in_progress_sweep_ticket_is_never_touched
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REPEATED-MISTAKE AUDIT (2026-08-10). T-1684's deferred post-land sweep
files a bug ticket for every new (rule, file) identity it sees. Under
parallel dispatch those conditions are routinely fixed by OTHER agents,
or by an existing Tier-A auto-fix, before anyone reads the ticket. The
ticket then sits in the queue at its filed priority, indistinguishable
from live work.

MEASURED, two instances today:
- T-1947 (high) -- "post-land sweep regression from T-1922: 2 new
  error(s) (DOC002, DRIFT002)". By the time it reached the top of the
  starved queue, DOC002 had been fixed by T-1954 and DRIFT002 x2 by
  T-1951. Verified before dropping: `frob check --only doclink --only
  drift` -> 0 errors, and `git grep` finds no remaining reference to the
  stale target `test_land_committed_waive_deletion_own_files`. Dropped.
- T-1972 (low) -- "REG010: file CHK-GATE-SYS110 in check-coverage.yaml".
  Already resolved by REG010's existing Tier-A auto-fix
  (`fix_reg010_registry_sync`), which had run during T-1629's own land.
  This one COST REAL WORK: a dispatched agent spent an investigation
  cycle establishing there was nothing to do, then dropped it.

COST: queue noise, wasted dispatch, and a corrupted priority signal.
T-1947 sat as a HIGH ticket in the starved set, competing for the first
dispatch slot against genuinely starved work (T-1614 at 120h, T-1638/
T-1664/T-1665/T-1669/T-1696 at 96h). A stale ticket does not merely
waste its own slot; it displaces real work at the top of the queue.

WHY THIS IS MECHANICALLY FIXABLE AND NOT A JUDGEMENT CALL: the sweep
files the EXACT (rule, file) identities in the ticket body. That is a
precise, re-runnable predicate. Deciding whether the ticket is still
live is `frob check --only <gate>` filtered to those identities -- no
interpretation required.

DO NOT FIX IT THIS WAY:
- Do NOT stop the sweep from filing tickets. Sweep-filed tickets have
  caught real post-land regressions repeatedly this session (T-1901,
  T-1912, T-1933, T-1962 all began this way). The filing is correct; the
  staleness is the defect.
- Do NOT auto-CLOSE a stale sweep ticket. Closing implies work was done
  and evidence exists; it would pollute the done set and BUG002's
  evidence model with tickets nobody fixed. Auto-DROP with a recorded
  reason is the honest disposition, matching how T-1947 and T-1972 were
  handled by hand.
- Do NOT rely on the operator noticing. Both instances here were found
  only because a coordinator happened to re-measure; one was found only
  after an agent had already spent a cycle.

FIX DIRECTION, preferred order:
(a) Re-verify a sweep-filed ticket's recorded identities at the moment it
    would be dispatched (`frob ticket doable`), and drop-with-reason or
    visibly mark any whose findings no longer reproduce.
(b) Have the sweep itself, on each subsequent run, close the loop on its
    own prior tickets whose identities have disappeared from the current
    baseline -- it already computes exactly that set difference.

(b) may be nearly free: the sweep already diffs against a rolling
baseline, so identities that vanished are already known to it.

ACCEPTANCE: first test must FAIL before the fix -- file a sweep-shaped
ticket naming a (rule, file) identity, resolve that finding, and assert
the ticket is reported as no-longer-reproducing (and dropped, with a
reason naming the identities). Then assert a sweep ticket whose finding
STILL reproduces is left untouched -- no false drops, since dropping a
live regression is strictly worse than leaving a stale one.

## Done report

The sweep already computed both halves of the diff (fresh vs baseline)
but only ever used one direction (new_findings = fresh - baseline). This
adds the mirror: vanished = baseline - fresh, and a
_close_resolved_sweep_tickets pass that auto-DROPS (never closes -- no
work was done, no evidence exists) every QUEUED/PLANNED sweep-filed
ticket whose full recorded (rule, file) identity set is a subset of
vanished. IN_PROGRESS tickets are never touched. A partially-resolved
ticket (some but not all identities vanished) is left alone entirely --
no partial drop, matching the acceptance bar that a false drop is worse
than a stale ticket.

_parse_sweep_ticket_identities recovers the exact identity set
_file_regression_ticket already writes into the ticket body (scanning
from the same heading, now a shared constant _REGRESSION_IDENTITY_HEADING,
and stopping before the attribution section which reuses the same "-
rule  file" shape for a different purpose) rather than re-deriving a
second notion of what the ticket is about.

Wired into run_deferred_post_land_sweep unconditionally (runs whether
this sweep is itself clean or red -- a resolved regression and a new one
are independent outcomes of the same measurement), right after the
existing new_findings computation.

### Changed
```
 tickets/T-1983/done-report.md | 42 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1983/ticket.md      | 20 ++++++++++++++++++--
 2 files changed, 60 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestDeferredSweepClosesResolvedRegressions::test_resolved_finding_is_dropped_by_the_next_sweep` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDeferredSweepClosesResolvedRegressions::test_still_reproducing_finding_is_left_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_drops_a_fully_resolved_sweep_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_leaves_a_partially_resolved_ticket_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_in_progress_sweep_ticket_is_never_touched` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: F401@/home/logan/projects/frob/.claude/worktrees/queue-hygiene/tests/unit/test_tickets_evidence_only_scope.py
