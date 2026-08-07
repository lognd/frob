---
id: T-0524
title: burn down 130 COV007 findings (frob:doc on private symbols)
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_lease.py::TestBreadthPerf::test_computed_once_per_doable_call
- tests/test_capability_registry.py::TestValidateRegistryKinds::test_known_kinds_pass
- tests/test_gates.py::TestInv003Gate::test_illustrative_example_reason_does_not_self_waive
designated_repro_test: null
threat: null
component: null
---
COV007 (frob:doc bound to a private symbol) currently has 130 warn-level findings repo-wide (measured via frob check --only coverage on this worktree), spread across src/frob/strata, src/frob/lang, src/frob/tickets, src/frob/dup, src/frob/graph, src/frob/app, etc. T-0483 explicitly scoped COV007 out of its own ticket ('COV007 unchanged at 126 -- out of scope for this ticket; a different gate') and T-0516 (COV006's successor) never took it on either -- no ticket has triaged this list yet. Per policy, most of these frob:doc edges on private helpers should move to the public caller they actually document (updating doc text if needed); a genuine minority may warrant a waive with a specific reason (private symbol IS the documented contract). This ticket exists so the 130-finding COV007 list gets the same per-finding triage COV006 got in T-0516, rather than being silently absorbed into an unrelated ticket's scope.