---
id: T-0117
title: fresh frob_core rebuild fails TestR5Dataflow::test_no_false_positive_against_unrelated_function
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- frob-core/src/**
- src/frob/dup/**
- tests/test_dup_rungs.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup_rungs.py::TestR5Dataflow::test_no_false_positive_against_unrelated_function
- tests/test_dup_rungs.py::TestR5Dataflow::test_fires_on_reordered_dataflow_identical_functions
designated_repro_test: null
threat: null
component: null
---
T-0091 adjudicated: a fresh 'make core' build of frob-core, installed byte-identical into root venv, makes tests/test_dup_rungs.py::TestR5Dataflow::test_no_false_positive_against_unrelated_function FAIL while some older installed builds passed. Venv contamination ruled out. Hypothesis: rust-source drift in R5 dataflow rung (or its python caller in src/frob/dup) after the .so most environments carry was built.