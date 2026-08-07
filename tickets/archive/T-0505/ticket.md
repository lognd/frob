---
id: T-0505
title: off-default-branch ticket write silently reverts an unrelated already-finalized
  ticket id to draft form
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets.py::TestSingleFileLedger::test_write_ticket_never_touches_a_sibling_ticket_bytes
designated_repro_test: null
threat: null
component: null
---
Found while landing T-0483 in a worktree (branch worktree-agent-ae00df0ca54dd3df2, off main). Running frob ticket start/evidence/done-report/sweep (any command that rewrites the whole tickets.md ledger) on this branch silently reverted an already-finalized, unrelated ticket (T-0503, real id on main) back to its draft form (T-draft-94774bc5) in the rewritten tickets.md -- confirmed by diffing against main: the T-0503 marker+id both became T-draft-94774bc5 with no ticket CLI command targeting T-0503 at all. A stale Done report elsewhere in the ledger mentions 'Filed T-draft-94774bc5' in prose (harmless, just text), and something in the ledger-write path appears to match that provisional id string against a currently-finalized ticket sharing the same title and reassign its id backward when the write happens off the default branch. This corrupts a finalized ticket's identity as a side effect of an unrelated ticket's write -- worked around by hand-restoring the T-0503 marker/id in tickets.md before landing T-0483 (not a real fix). Needs root-causing in src/frob/tickets (is_draft_id/on_default_branch/finalize_draft or wherever ledger writes reconcile ids) and a regression test that writing an unrelated ticket off-default-branch never touches another already-finalized ticket's id.