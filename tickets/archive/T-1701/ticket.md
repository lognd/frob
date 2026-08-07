---
id: T-1701
title: frob ticket land cannot land a DROPPED ticket, forcing agents to write the
  root ledger directly
state: done
kind: bug
origin: agent
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_evidence.py
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/tickets.md
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_land_merge.py
- tests/test_ticket_land.py
- tests/unit/test_ticket_runner_gate_findings.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_finalize.py
  reason: the two functions that actually gate a dropped ticket's land -- _close_finalized_ticket
    (forces DONE unconditionally) and _validate_closeable (requires evidence+Done-report
    unconditionally) -- live in _land_finalize.py/_land_merge.py, not _land.py itself
    (which only imports/orchestrates them); T-1701's own named requirement ('_validate_closeable's
    evidence requirement must become state-dependent') names the function directly,
    so this is the ticket's own declared fix location, not scope creep
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_land_merge.py
  reason: the two functions that actually gate a dropped ticket's land -- _close_finalized_ticket
    (forces DONE unconditionally) and _validate_closeable (requires evidence+Done-report
    unconditionally) -- live in _land_finalize.py/_land_merge.py, not _land.py itself
    (which only imports/orchestrates them); T-1701's own named requirement ('_validate_closeable's
    evidence requirement must become state-dependent') names the function directly,
    so this is the ticket's own declared fix location, not scope creep
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_ticket_land.py
  reason: the two functions that actually gate a dropped ticket's land -- _close_finalized_ticket
    (forces DONE unconditionally) and _validate_closeable (requires evidence+Done-report
    unconditionally) -- live in _land_finalize.py/_land_merge.py, not _land.py itself
    (which only imports/orchestrates them); T-1701's own named requirement ('_validate_closeable's
    evidence requirement must become state-dependent') names the function directly,
    so this is the ticket's own declared fix location, not scope creep
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_ticket_runner_gate_findings.py
  reason: trivial pre-existing type-annotation bug (list[...] annotated param with
    a tuple default) surfaced by frob check --land-parity while verifying T-1701's
    own changes; fixing inline rather than leaving a known ty error on main or opening
    process overhead for a 2-line type fix
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_ticket_land.py::TestLandDroppedTicket::test_dropped_ticket_with_a_reason_lands_cleanly
- tests/test_ticket_land.py::TestLandDroppedTicket::test_dropped_ticket_with_no_reason_refuses
- tests/test_ticket_land.py::TestCloseFailAfterMerge::test_close_fails_after_merge_when_main_dropped_same_id
designated_repro_test: null
threat: null
component: null
---
Found while landing T-1538 (2026-08-06): a ticket whose correct outcome
is DROPPED has no path through `frob ticket land`.

T-1538's premise had already been fixed by T-1318's own land before the
ticket's refile even existed, so there was nothing to implement and
`drop` was the right disposition. But `_validate_closeable`
unconditionally requires evidence plus a Done report, and `close`/`land`
only know the `-> done` transition. The agent had to run `frob ticket
drop` directly against the ROOT checkout to record it -- bypassing the
land path entirely, from a worktree-isolated agent that is otherwise
correctly forbidden from touching root.

That bypass is the defect. Every ledger transition an agent can legitimately
reach should be reachable through the same gated path as the others; a
verb that can only be exercised by reaching around the isolation boundary
will eventually be used to reach around it for something that matters.

Requirements:

- `frob ticket land` accepts a ticket whose target state is DROPPED, and
  lands the ledger change (drop reason, state transition) the same way it
  lands a done ticket's ledger change -- from the agent's own worktree,
  no root access needed.
- A dropped ticket requires a REASON and does NOT require evidence or a
  Done report. Dropping is the explicit record that scope was cut; the
  reason is the whole artifact. `_validate_closeable`'s evidence
  requirement must become state-dependent rather than unconditional.
- A drop must never be a silent alternative to doing the work: log it at
  WARNING with the reason, and keep it visible in `frob ticket board` /
  epic progress as DROPPED rather than folding it into "done".
- The "no code changed" case must not trip the already-landed detection
  (see T-1675, which is about exactly the ambiguity between "no diff" and
  "docs-only ticket" -- coordinate, do not duplicate).

Regression coverage: a queued ticket with a drop reason and no evidence
lands cleanly from a worktree; the same ticket without a reason refuses.