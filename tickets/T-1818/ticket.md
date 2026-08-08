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