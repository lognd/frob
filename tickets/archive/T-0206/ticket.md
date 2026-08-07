---
id: T-0206
title: tickets-archive.md has a stale duplicate T-0169 entry from a ledger-conflict
  splice
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets-archive.md
- tests/test_tickets_collision.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_collision.py::TestRealLedgerIntegrity::test_no_duplicate_ids_within_or_across_ledgers
designated_repro_test: null
threat: null
component: null
---
Found while merging main into the T-0169 worktree: tickets-archive.md on main contains a T-0169 block with state=queued and no Done report/evidence, silently spliced in by an unrelated ledger-conflict merge (same incident class the agent playbook's ledger-conflict splice guidance warns about) -- NOT a real close. The authoritative T-0169 record is in tickets.md (in-progress, with a full Done report). Delete the stray tickets-archive.md duplicate so frob ticket listings don't show two T-0169 records in conflicting states. Also check tickets-archive.md for other stray splices from the same merge incident. (The branch's second draft, e1beb2a8 covering the html_render self-match, was dropped at landing as a duplicate of T-0201, which carries the same analysis and is already dispatched.)

## Failure log
- 2026-07-18 attempt 1: Premise stale on main: the stray queued-state T-0169 archive duplicate existed only in the T-0169 worktree's pre-archive ledger copy (branched at 1101c3e). Current main archive (rebuilt at 0b4ff16) has zero T-0169 entries and a cross-ledger id-duplicate grep is clean. Nothing to delete.