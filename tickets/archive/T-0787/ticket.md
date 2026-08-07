---
id: T-0787
title: 'check CLI: wire resolve_lease pinning into --ticket resolution (promote T-0766''s
  lost draft)'
state: done
kind: security
origin: agent
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- src/frob/gates/__init__.py
- tests/test_tickets_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_leases.py::TestTicketLeasePin::test_no_lease_mechanism_engaged_passes_through
- tests/test_tickets_leases.py::TestTicketLeasePin::test_pinned_lease_for_this_worktree_passes
- tests/test_tickets_leases.py::TestTicketLeasePin::test_lease_absent_for_this_worktree_refuses
- tests/test_tickets_leases.py::TestTicketLeasePin::test_lease_recorded_elsewhere_refuses
- tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_pins_to_own_worktree_lease
- tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_refuses_when_lease_recorded_for_another_worktree
- tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_no_ticket_resolved_skips_the_check_entirely
designated_repro_test: null
acceptance:
- text: GIVEN an agent invoking frob check --ticket T-X from a worktree WHEN T-X has
    a lease THEN the check pins to T-X's own lease/worktree via resolve_lease and
    refuses loudly (naming frob ticket start) when the lease is absent or recorded
    for a different worktree; a test drives the check entry point across two fake
    worktrees
  evidence:
  - tests/test_tickets_leases.py::TestTicketLeasePin::test_no_lease_mechanism_engaged_passes_through
  - tests/test_tickets_leases.py::TestTicketLeasePin::test_pinned_lease_for_this_worktree_passes
  - tests/test_tickets_leases.py::TestTicketLeasePin::test_lease_absent_for_this_worktree_refuses
  - tests/test_tickets_leases.py::TestTicketLeasePin::test_lease_recorded_elsewhere_refuses
  - tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_pins_to_own_worktree_lease
  - tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_refuses_when_lease_recorded_for_another_worktree
  - tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_no_ticket_resolved_skips_the_check_entirely
threat: null
component: null
---
Promotion of a draft filed in T-0766's worktree and lost during that ticket's land recovery (premature worktree removal destroyed uncommitted ledger state; disclosed in coordinator notes). T-0766 landed the resolve_lease(root, ticket_id, invoking_worktree) fail-loud primitive in src/frob/tickets/_leases.py, but nothing in the live check path consults leases at all (verified by the T-0766 reviewer: active_ticket/_resolve_ticket derive the id from --ticket/branch only). The reviewer marked this wiring a HARD DEPENDENCY: the guard prevents nothing until check consults it. Wire check's --ticket resolution through resolve_lease when a lease exists, keeping the no-lease path working for non-agent invocations.