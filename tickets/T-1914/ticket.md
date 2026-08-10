---
id: T-1914
title: frob ticket land's internal merge-main step silently clobbers the landing worktree's
  own ledger edits
state: in-progress
kind: bug
origin: agent
created: '2026-08-09'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_sibling_regression.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'T-1914 fix + regression test: sibling-ticket-state-regression guard in
    the internal merge step (self-contained test file, tests/test_ticket_land.py leased
    by T-1686)'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/unit/test_land_sibling_regression.py
  reason: 'T-1914 fix + regression test: sibling-ticket-state-regression guard in
    the internal merge step (self-contained test file, tests/test_ticket_land.py leased
    by T-1686)'
  actor: logan
  at: '2026-08-09'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-09 by the T-1903/T-1907/T-1884 series agent, corroborated by the coordinator hitting the same conflict manually minutes later.

WHAT HAPPENED. The agent closed T-1884 in its worktree (commit b3fea16d6/b3bf8a753, state -> done, evidence and Done report recorded via the frob CLI). The coordinator then ran 'frob ticket land T-1903 --worktree <that same worktree>'. Land's OWN internal 'merge main into worktree' step brought main's still-'queued' copy of tickets/T-1884/ticket.md back over the worktree's 'done' edit, WITH NO CONFLICT -- from git's point of view it was an unrelated-file fast-forward. T-1884's close was silently reverted. It had to be re-recorded from scratch.

WHY IT MATTERS. Landing ticket A silently destroyed ticket B's recorded state in the same worktree. This is the ledger analogue of T-1910 (a land reporting success for a commit that never reached main): the operator sees a successful land and has no signal that a sibling ticket's work was rolled back. Both failures share a root: LAND MUTATES THE WORKTREE IT IS LANDING FROM, and nothing verifies the ledger survived that mutation.

It is also self-reinforcing with the standing dispatch policy. Agents are deliberately given a GROUP of tickets in ONE worktree to amortise cold start, so a series worktree ALWAYS contains sibling tickets' ledger edits when any one of them lands. The clobber is therefore the expected case for the recommended workflow, not an edge case.

CORROBORATION. Landing the next two tickets from the same worktree required merging main again, which THIS time produced a real conflict in tickets/T-1884/ticket.md (worktree: state=done; main: state=queued plus a retraction block). The coordinator resolved it by hand, keeping both. The silent case and the conflicting case are the same mechanism -- whether git notices is luck of the diff.

REQUIRED FIX:
1. Land must not silently overwrite ledger state for tickets OTHER than the one being landed. Detect a state regression (done -> queued) on any sibling ticket during its internal merge and REFUSE, rather than take main's copy.
2. After the internal merge, re-assert that every in-worktree ticket's state is >= what it was before the merge; report any regression by ticket id.
3. Regression test: a worktree with ticket B closed and ticket A landing must leave B closed.

Related: T-1910 (land reports success for a commit not on main), T-1903 (verification sequenced before the mutation it covers), T-1884 (whose close was the victim here).