---
id: T-2604
title: quarantine re-raises on findings already owned by an open ticket, forcing synchronous
  lands fleet-wide every sweep
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: T-2604 fix changes _raise_quarantine_for_red_batch behavior; two existing
    tests encode the pre-fix expected raise and need updating, plus new positive-control
    tests
  actor: logan
  at: '2026-08-19'
evidence:
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_open_ticket_attribution_clears_the_quarantine_raise
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_closed_ticket_attribution_still_raises
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_unattributed_still_raises_alongside_open_ticket_finding
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_never_drops_an_attributed_finding
- tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_leaves_quarantine_raised_when_other_findings_remain_undisposed
designated_repro_test: tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_open_ticket_attribution_clears_the_quarantine_raise
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 0559e1939587cdcd51466cf3408fe9aebdc0c286
---
## Measured tonight

The SAME finding raised quarantine twice, roughly 30 minutes apart:

    ~02:00  E501:/home/logan/projects/frob/src/frob/scaffold/project.py
    ~02:33  E501:/home/logan/projects/frob/src/frob/scaffold/project.py

Both times it was already tracked: the first disposal filed it to T-2596
(open, in progress, an agent actively fixing it). The second raise happened
anyway, against a different batch, for the identical identity.

Each raise turns OFF deferred landing repo-wide -- every land runs
fully-synchronous verification (T-1693). That puts a multi-minute inline
re-verification on the critical path of every agent's land, and lands in
this repo already run close to the 540s shell cap. Both times it took a
manual coordinator `frob verify dispose` to clear.

This will recur on every sweep until T-2596 lands. That is a treadmill, and
the cost is paid by the whole fleet each lap.

## Root cause: the raise path and the filing path disagree

Both live in `src/frob/app/ticket_runner/_rapid_sweep.py`.

The FILING path already gets this right. `_split_attributed_pairs`:

    if attr.status == "attributed" and _ticket_is_open(root, attr.ticket_id):
        already_open[attr.ticket_id] = ...
        continue          # logged at INFO, NOT re-filed -- it has a home

The QUARANTINE RAISE path has no equivalent. Its only filter is
`_warm_tree_clears_unattributed_native_noise` (the cold-worktree
native-extension shape from T-1847). A finding that is attributed to a
still-open ticket sails straight through and raises the circuit breaker.

So the system knows the finding has an owner, and acts on that knowledge in
one place and not the other.

## The fix has an existing, correct home

T-1847 already established exactly this pattern -- filtering the
quarantine-raise set separately from the filing set, with the rationale
recorded in the docstring: such a pair is "still filed as a regression
ticket, just not sent to the dispose queue".

Add a second filter alongside it: drop from the quarantine-raise set any
pair already attributed to a STILL-OPEN ticket. Reuse `_ticket_is_open`,
which `_split_attributed_pairs` already calls -- do NOT write a second
open-ticket predicate.

## What must NOT change

- The finding must STILL be recorded/filed as it is today. This ticket
  changes only whether it trips the circuit breaker, exactly as T-1847 did.
  Suppressing the finding itself would be a silent zero.
- A finding attributed to a CLOSED or DROPPED ticket must STILL raise. That
  is a real regression against work believed finished, and it is the case
  quarantine exists for.
- An UNATTRIBUTED finding must STILL raise. No owner means nobody is on it.

## Positive controls, both directions

- a finding attributed to an open ticket does NOT raise quarantine, and IS
  still filed/recorded
- a finding attributed to a closed/dropped ticket DOES raise -- without
  this case the fix is indistinguishable from disabling quarantine
- an unattributed finding DOES raise
- the T-1847 cold-worktree native-extension filter still behaves exactly as
  before
- a batch containing one open-ticket finding and one unattributed finding
  STILL raises, naming only the unattributed one