---
id: T-0302
title: close 3 TEST005 branch-coverage gaps on security-critical functions
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestBindingErrorPropagation::test_ambiguous_code_binding_propagates_as_err
- tests/unit/strata/test_host_isolation.py::TestHostIsolationWaivers::test_propagates_lateral_isolation_error
- tests/unit/strata/test_host_isolation.py::TestHostIsolationWaivers::test_propagates_vertical_isolation_error
- tests/test_ticket_land.py::TestSpliceLedger::test_malformed_ours_propagates_as_err
- tests/test_ticket_land.py::TestSpliceLedger::test_malformed_theirs_propagates_as_err
designated_repro_test: null
threat: null
component: null
---
