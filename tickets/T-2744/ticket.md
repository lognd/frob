---
id: T-2744
title: Quarantine was cleared citing an auto-filed ticket that does not exist, releasing
  findings against a phantom home
state: done
kind: bug
origin: human
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/verify/_quarantine.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/verify/test_quarantine.py
- tests/unit/test_rapid_sweep.py
- docs/modules/tickets-verify-sweep.md
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/verify/_quarantine.py
  reason: quarantine clear-time ticket-existence validation + rapid-sweep commit-success
    gating (T-2736 phantom-ticket incident)
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: quarantine clear-time ticket-existence validation + rapid-sweep commit-success
    gating (T-2736 phantom-ticket incident)
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/verify/test_quarantine.py
  reason: quarantine clear-time ticket-existence validation + rapid-sweep commit-success
    gating (T-2736 phantom-ticket incident)
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: quarantine clear-time ticket-existence validation + rapid-sweep commit-success
    gating (T-2736 phantom-ticket incident)
  actor: logan
  at: '2026-08-20'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: quarantine clear-time ticket-existence validation + rapid-sweep commit-success
    gating (T-2736 phantom-ticket incident)
  actor: logan
  at: '2026-08-20'
- op: add
  glob: frob.lock
  reason: frob ack on _file_regression_ticket writes frob.lock
  actor: logan
  at: '2026-08-20'
body_changes:
- mode: append
  reason: record that the auto-file succeeds intermittently, which rules out an unconditional-clear
    cause and points at a race or an unreachable write
  actor: logan
  at: '2026-08-20'
  old_length: 2965
  new_length: 3857
evidence:
- tests/unit/verify/test_quarantine.py::TestClearQuarantine::test_refuses_when_filed_ticket_does_not_resolve
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_commit_failure_skips_auto_dispose_and_returns_none
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured, 2026-08-20

`.frob/quarantine.json` was observed carrying:

    cleared_reason: auto-filed by rapid sweep as T-2736
    findings: 2

T-2736 does not exist and never did:

    ls tickets/T-2736            -> No such file or directory
    ls tickets/archive/T-2736    -> No such file or directory
    git log --all -- 'tickets/T-2736/**'  -> empty

An independent agent, dispatched to triage it, searched main, worktree
history, the full git history and the ledger archive and reached the same
conclusion -- then reported the absence rather than fabricating triage for
a ticket that was not there.

## Why this is serious

Quarantine is the circuit breaker: while raised, deferred landing is OFF
and every land runs fully-synchronous verification repo-wide. Clearing it
is therefore load-bearing, and the ONLY justification recorded is the
`cleared_reason`. Here that reason names a home that does not exist.

So the findings were released from quarantine against a phantom ticket.
Whatever they were, nothing now tracks them, and the ledger asserts
otherwise. This is the disposal-side twin of the silent-zero: the record
says "handled", the handling is absent, and nothing downstream re-checks.

## What to determine first

Do not assume the mechanism. Read `_rapid_sweep.py`'s auto-file-then-clear
path and establish which of these it is:

(a) the file genuinely failed and the clear proceeded anyway (the clear is
    not conditional on the filing succeeding);
(b) the file succeeded on a worktree branch that never landed, so the id
    exists only there -- this repo has three measured instances today of
    work stranded on a branch and invisible on main, so it is a live
    possibility;
(c) the id was allocated and reported before the write, and the write was
    lost to a race or an interrupted ledger commit.

The remedy differs per branch: (a) needs the clear gated on the filing;
(b) needs the sweep's filing mirrored to the primary checkout the way
ledger writes already are; (c) needs the id allocated after a durable
write.

## Required, whichever it is

Clearing quarantine must be conditional on the cited ticket EXISTING and
being reachable on main. A `cleared_reason` naming an unresolvable id
should refuse the clear, loudly, rather than release the findings.

## Positive controls, both directions

- a sweep whose auto-file fails leaves quarantine RAISED and says why
- a sweep whose auto-file succeeds clears quarantine and the cited id
  resolves on main afterwards
- an operator clearing manually with a real ticket id still works
  unchanged (do not make the normal path harder)

## Recovery for the instance already lost

The 2 findings released under the phantom T-2736 reference are untracked.
They cannot be recovered from the cleared record alone. A full unbudgeted
`frob check --json` re-measurement will re-surface them if they are still
live -- do that as part of this ticket rather than assuming they were
trivial.




## The defect is INTERMITTENT, which narrows the cause

Observed a second auto-file-then-clear cycle on 2026-08-20T14:17:32Z:

    cleared_reason: auto-filed by rapid sweep as T-2749

and T-2749 DOES exist on main. So the sweep's auto-file succeeds
sometimes and not others -- the T-2736 case was not a permanently broken
path.

That argues against hypothesis (a) (the clear is simply never conditional
on the filing) and toward (b) or (c): a filing that landed somewhere
unreachable, or a race between id allocation and a durable write. Two
successful cycles were also observed clearing to T-2732 and T-2743.

Do not let the intermittency reduce the severity. A clear that USUALLY
cites a real ticket is more dangerous than one that never does, because
nothing downstream ever checks -- the one failure in four releases its
findings silently and looks identical to the three that worked.