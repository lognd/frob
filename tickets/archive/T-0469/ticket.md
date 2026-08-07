---
id: T-0469
title: 'frob.fuzz v1 limits: process-global generator registry and example-count budget'
state: done
kind: feature
origin: agent
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/fuzz/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_fuzz.py::TestResolve::test_unknown_type_is_no_generator
- tests/test_fuzz.py::TestFuzzRegistry::test_scoped_registry_registration_is_isolated
- tests/test_fuzz.py::TestFuzzRegistry::test_register_accepts_explicit_registry_kwarg
- tests/test_fuzz.py::TestRunFuzz::test_budget_s_is_a_real_wall_clock_cutoff
designated_repro_test: null
threat: null
component: null
---
Two genuine v1 deferrals in frob.fuzz, formerly parked on dropped T-0002 then done-tracker T-0300 (both closed). Track here as live open work: (1) src/frob/fuzz/_arbitrary.py generator registry is process-global rather than per-project scoped; (2) src/frob/fuzz/_run.py budget_s is interpreted as an example count, not a wall-clock budget. Rebind the two frob:todo directives here.