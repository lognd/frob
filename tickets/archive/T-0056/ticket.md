---
id: T-0056
title: strata fact base + semi-naive Datalog closure engine
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0055
parent: T-0049
tier: ticket
sprint: null
scope:
- docs/strata/**
- tickets.md
- src/frob/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_facts.py::TestClosure::test_boundaries_stop_taint_unless_asked_otherwise
- tests/unit/strata/test_facts.py::TestClosure::test_worst_age_accumulates_along_the_stalest_path
- tests/unit/strata/test_facts.py::TestBuildFacts::test_at_least_once_into_non_idempotent_node_is_diagnosed
designated_repro_test: null
threat: null
component: null
---
Tuple store + fixpoint closure (reach/taint over lattices). Pure Python; port to strata-core when litmus models make it slow.