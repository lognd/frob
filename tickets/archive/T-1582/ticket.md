---
id: T-1582
title: 'COV002 closing-diff grace is v1-only: no grace in a ledger-v2 repo'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov002_v2_done_ticket_covers_own_closing_diff
- tests/test_gates.py::TestCoverageGate::test_cov002_v2_grace_covers_ticket_created_and_closed_in_same_diff
- tests/test_gates.py::TestCoverageGate::test_cov002_v2_marker_touch_without_state_transition_still_fires
- tests/test_gates.py::TestCoverageGate::test_cov002_v2_done_ticket_without_grace_still_fires
- tests/test_gates.py::TestCoverageGate::test_cov002_v2_stale_done_ticket_unrelated_touch_still_fires
designated_repro_test: null
threat: null
component: null
---
COV002's closing-diff grace (_cov002 / _ledger_states_at_base, src/frob/gates/__init__.py) reads the ticket-id -> state map out of tickets.md HUNKS in the working diff. T-1553 made fresh repos default to ledger v2, where a ticket's state lives in tickets/T-####/ticket.md and there are no tickets.md hunks at all -- so in a v2 repo _ledger_states_at_base sees nothing, the T-0590 grace for a ticket created-and-closed inside its own diff never applies, and COV002 fires falsely on exactly the worktree-agent flow the grace exists to permit.

This repo has not hit it yet only because main is still a v1 monofile; every NEW frob repo is v2 from its first commit and gets the false COV002 immediately.

Fix: teach _ledger_states_at_base to resolve state at base per store mode -- v2 reads tickets/<id>/ticket.md at diff.base, v1 keeps the monofile-hunk path -- and make the hunk-membership test ('was this ticket's ledger entry touched in this diff') mode-aware too. Tests: tests/test_gates.py::TestCoverageGate currently pins itself to v1 via _write_ticket's tickets.md seed; add a v2-mode mirror of each grace case rather than converting the v1 ones, so both backends stay covered.