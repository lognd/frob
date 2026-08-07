---
id: T-0766
title: 'lease resolution cross-talk: frob check --ticket ran against another agent''s
  worktree via stale lease under concurrent load'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_leases.py
- tests/test_tickets_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_leases.py::TestResolveLease::test_resolves_own_ticket_own_worktree
- tests/test_tickets_leases.py::TestResolveLease::test_never_returns_a_sibling_tickets_lease
- tests/test_tickets_leases.py::TestResolveLease::test_no_lease_for_ticket_fails_loudly
- tests/test_tickets_leases.py::TestResolveLease::test_lease_recorded_for_a_different_worktree_fails_loudly
designated_repro_test: null
acceptance:
- text: GIVEN two agents with leases on different tickets in different worktrees WHEN
    one runs frob check --ticket for its own ticket THEN the check resolves that ticket's
    own lease/worktree and never another agent's worktree; a regression test reproduces
    the cross-talk shape
  evidence:
  - tests/test_tickets_leases.py::TestResolveLease::test_resolves_own_ticket_own_worktree
  - tests/test_tickets_leases.py::TestResolveLease::test_never_returns_a_sibling_tickets_lease
  - tests/test_tickets_leases.py::TestResolveLease::test_no_lease_for_ticket_fails_loudly
  - tests/test_tickets_leases.py::TestResolveLease::test_lease_recorded_for_a_different_worktree_fails_loudly
threat: null
component: null
---
Observed during T-0695 (2026-07-22, heavy concurrent multi-agent load): frob check --ticket T-0695 twice ran against a completely different worktree (agent-a86ce74bd40394899, which held the T-0733 lease) via stale ticket-lease state, until frob ticket start T-0695 was re-run. Leases are worktree-local since T-0473, but some path in check's lease resolution still picked up a sibling worktree's state. Root-cause the resolution order (env FROB_WORKTREE? lease file mtime? first-match iteration?) and pin check --ticket to the invoking worktree's own lease, failing loudly if absent rather than borrowing a sibling's.