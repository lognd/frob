---
id: T-1818
title: frob ticket land cannot carry a fail-transition record to main, stranding every
  honest dead-end log
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
- src/frob/tickets/_land_state.py
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_land_merge.py
- tests/test_ticket_land.py
- tickets/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_finalize.py
  reason: declared scope src/frob/tickets/_land_state.py does not exist; the queued->done
    InvalidTransition refusal this ticket must fix lives in _land_finalize.py::_close_finalized_ticket,
    mirroring the T-1701 _skip_close_for_legitimate_drop precedent in _land_merge.py
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/tickets/_land_merge.py
  reason: declared scope src/frob/tickets/_land_state.py does not exist; the queued->done
    InvalidTransition refusal this ticket must fix lives in _land_finalize.py::_close_finalized_ticket,
    mirroring the T-1701 _skip_close_for_legitimate_drop precedent in _land_merge.py
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_ticket_land.py
  reason: regression test for _skip_close_for_legitimate_fail belongs beside the existing
    _skip_close_for_legitimate_drop (T-1701) sibling tests in this file
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/**
  reason: ticket-ledger bookkeeping shards (frob ticket start/sweep auto-commits for
    T-1818 itself, plus whatever sibling shard the branch's merge-base diff against
    main happens to carry) are the sharded-ledger equivalent of tickets.md, already
    implicitly in scope for every ticket -- same precedent as T-1817
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_ticket_land.py::TestLandFailedTicket::test_failed_ticket_with_a_failure_log_lands_cleanly
- tests/test_ticket_land.py::TestLandFailedTicket::test_queued_ticket_with_no_failure_log_still_refuses
designated_repro_test: null
threat: null
component: null
---
`frob ticket fail` records an honest dead end, and `frob ticket land`
then refuses to carry that record to main. The result is that the ONE
outcome the tool exists to make durable -- "this was attempted and does
not work as scoped" -- is the one outcome that cannot reach the shared
ledger.

OBSERVED on T-1478. An agent correctly determined the ticket was
undoable as scoped: argument-level `may` scoping needs a new grammar
production in strata-core, a new field in `_ast.py`, the elaborated
field in `_models.py`, and the per-argument SYS100 join in `_effects.py`
-- none of which are in the ticket's declared scope
(`docs/strata/surface.md`, `_mutation_audit.py`, `_native_staleness.py`).

It did the right thing at every step: ran `frob ticket fail` instead of
forcing a partial build, and instead of silently widening scope. frob
generated the ledger commit. Then:

    frob ticket land T-1478
    -> InvalidTransition: queued -> done

`land` only carries `done` and `dropped` tickets. A failed ticket
returns to `queued`, so its failure log is stranded on the worktree
branch. The agent then correctly refused to `git merge` onto root, per
the never-dirty-root rule -- leaving the record reachable only by a
coordinator who happens to know the branch exists.

WHY THIS MATTERS MORE THAN IT LOOKS: the failure log is the highest-value
artifact in the whole ticket lifecycle. A landed fix is visible in the
code; a dead end is invisible unless recorded. Losing it means the next
agent picks up T-1478, spends a full dispatch rediscovering the identical
scope mismatch, and fails the same way. That is the exact "we forget we
have a stack and only pop the top half" failure this tool was built to
prevent.

It also silently punishes honesty. An agent that fails a ticket loses
its work; an agent that forces a partial build gets a land. The
incentive points the wrong way, and this repo has already paid for a
tested-but-unwired component being recorded as complete.

REQUIRED:

1. `frob ticket land` must carry a fail-transition ledger change for a
   ticket that returns to `queued`. The state check is too narrow: it
   asks "is this ticket terminal" when the real question is "does this
   changeset contain only ledger updates this ticket legitimately owns".
2. The refusal message must name the remedy. `InvalidTransition:
   queued -> done` describes the state machine, not what to do -- the
   agent had to infer that no sanctioned path existed.
3. Consider whether `fail` should also record the SCOPE MISMATCH as
   structured data, not only prose. T-1478's log says which files were
   missing; if that were a field, `frob ticket doable` could refuse to
   re-offer the ticket until its scope actually covered them, instead of
   handing the same trap to the next agent.

Interim: the T-1478 record was carried to main by cherry-picking the
frob-generated ledger commit (b4cb7c1aa). That is a coordinator
workaround, not a fix, and it does not scale -- it requires knowing the
branch exists.

## Done report

`frob ticket fail` records a `## Failure log` entry and returns the
ticket to QUEUED (no legal `queued -> done` edge in `_TRANSITIONS`), so
`_close_finalized_ticket`'s unconditional DONE-transition attempt always
refused with `InvalidTransition: queued -> done`, stranding the one
artifact a dead-end attempt produces on the worktree branch (the T-1478
incident this ticket cites).

Fix mirrors the T-1701 DROPPED precedent exactly: `_has_failure_log`
(`frob.tickets._land_merge`, the QUEUED-side twin of `_has_drop_reason`)
detects a genuine `frob ticket fail` record; `_skip_close_for_legitimate_
fail` (`frob.tickets._land_finalize`, folded together with the existing
drop-skip behind one `_skip_close_for_terminal_shortcut` call to keep
`_close_finalized_ticket` under ARCH001's 60-line threshold) publishes
that ledger state to main as-is instead of forcing the DONE transition.
`_validate_closeable` gained the matching QUEUED-with-failure-log
pre-merge branch so the preflight (before any git mutation) agrees with
the close-time behavior.

Gated on `_has_failure_log`, not merely `state == QUEUED`: a ticket that
is QUEUED for any OTHER reason (never started, `frob ticket requeue`
with no fail-log) still falls through to the ordinary DONE-precondition
path and refuses loudly if land is forced against it -- verified by
`test_queued_ticket_with_no_failure_log_still_refuses`.

Requirement 2 (name the remedy): substantially addressed by ELIMINATING
the `InvalidTransition` path for the legitimate case entirely -- an
honestly-failed ticket now lands cleanly with no refusal to explain. The
residual forced-land case (QUEUED, no failure log, evidence/Done-report
missing) already falls through to `_validate_closeable`'s existing
DONE-precondition error, which already names its own remedy ("record
evidence... add a '## Done report' section... retry `frob ticket land`
").

Requirement 3 (structured scope-mismatch data on `fail`) was NOT
attempted -- outside this ticket's declared scope
(`_land_finalize.py`/`_land_merge.py`, the land-side half only) and a
separate, larger change to `frob ticket fail`'s own write path and the
`doable` query; left for a follow-up if wanted.

### Changed
```
 tickets/T-1818/ticket.md | 38 +++++++++++++++++++++++++++++++++++++-
 1 file changed, 37 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandFailedTicket::test_failed_ticket_with_a_failure_log_lands_cleanly` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandFailedTicket::test_queued_ticket_with_no_failure_log_still_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 866 warning(s), 736 waived
- error-findings: none (measured, zero errors)
