---
id: T-0537
title: 'ledger merge: terminal->non-terminal state regression guard (splice + post-merge
  lint) -- manual conflict resolution resurrected 7 closed tickets'
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/__init__.py
- src/frob/gates/__init__.py
- tests/**
- Makefile
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'declare scope from ticket prose (Scope: _land.py, tickets/__init__.py,
    gates/__init__.py, tests)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: 'declare scope from ticket prose (Scope: _land.py, tickets/__init__.py,
    gates/__init__.py, tests)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'declare scope from ticket prose (Scope: _land.py, tickets/__init__.py,
    gates/__init__.py, tests)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/**
  reason: 'declare scope from ticket prose (Scope: _land.py, tickets/__init__.py,
    gates/__init__.py, tests)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: Makefile
  reason: 'SCOPE001 collision: T-0538''s own already-closed changes are still in this
    worktree''s uncommitted-vs-main diff (sequential tickets, one worktree); not new
    edits by T-0537 itself'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/testing.md
  reason: 'SCOPE001 collision: T-0538''s own already-closed changes are still in this
    worktree''s uncommitted-vs-main diff (sequential tickets, one worktree); not new
    edits by T-0537 itself'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_hand_resolved_conflict_resurrecting_done_ticket_is_flagged
- tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_forward_progress_across_a_merge_is_clean
- tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_non_merge_commit_never_checked
- tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_archived_ticket_is_not_flagged
- tests/test_ticket_land.py::TestSpliceOnlyTicket::test_whole_ledger_splice_never_regresses_a_sibling_from_done
designated_repro_test: null
threat: null
component: null
---
Incident (2026-07-22): the COV-finish branch hit a tickets.md conflict mid-flight, resolved it manually, and its land carried stale queued states for 7 tickets main had already closed (T-0454/T-0498/T-0500/T-0514/T-0520/T-0526/T-0527); coordinator restored from the pre-merge ledger. T-0479's own-block splice protects frob ticket land, and T-0505 protects CLI writes, but a raw git merge with hand-resolved conflicts bypasses both. Fix: (1) splice_ledger/merge-driver must never move a ticket from done/dropped to an earlier state unless the landing ticket IS that ticket; (2) a cheap post-merge lint (tickets gate) that diffs states vs the merge's first parent and errors on terminal->non-terminal transitions outside the landed ticket. Scope: src/frob/tickets/_land.py, src/frob/tickets/__init__.py, src/frob/gates/__init__.py, tests.