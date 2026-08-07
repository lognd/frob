---
id: T-0300
title: Rebind frob.fuzz deferred-work TODOs off dropped T-0002
state: done
kind: bug
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/fuzz/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_fuzz.py::TestResolve::test_registered_type_resolves
- tests/test_fuzz.py::TestRunFuzz::test_derived_model_produces_examples
- tests/test_fuzz.py::TestRunFuzz::test_digests_map_is_stamped_onto_matching_ref
designated_repro_test: null
threat: null
component: null
---
T-0294 fixed the DSL parser's trailing-prose rejection, which un-masked two frob:todo T-0002 directives in src/frob/fuzz/_run.py:30 and src/frob/fuzz/_arbitrary.py:41 (process-global registry scoping; wall-clock budget_s). T-0002 (frob.fuzz generators + FUZZ gates Phase 8) is dropped, so TODO001 now correctly fires: these TODOs are not bound to an open ticket. Either reopen T-0002's scope in a live ticket and rebind, or file focused successor tickets per TODO and rebind. Filed rather than fixed in T-0294 to stay within that ticket's declared DSL-parser scope (this is a ticket-graph bookkeeping fix, not a parser fix).