---
id: T-0149
title: 'frob test: no [[test.runner]] for language=strata blocks touched-set selection
  on .strata fixtures'
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- frob.toml
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_testing.py::TestRunners::test_placeholder_files
- tests/test_testing.py::TestRunners::test_no_runner_error
- tests/test_testing.py::TestRunners::test_valid_runner_loaded
designated_repro_test: null
threat: null
component: null
---
Found while working T-0145: adding new .strata files under tests/unit/strata/litmus/ (or anywhere) makes frob test --base main fail with NoRunner: 'language strata has selected tests but no runner -- add a [[test.runner]] entry'. frob.toml has runners for python and rust only; strata surface files (.strata) are a distinct language frob.lang/frob.testing classifies but there is no [[test.runner]] entry (and likely no sensible native pytest-equivalent for a .strata file standalone -- it is exercised THROUGH the python tests that parse it, e.g. test_litmus_cwe.py). Needs either: (1) a [[test.runner]] entry that maps .strata files to the python test files that bind them (frob:tests directives already exist on the fixtures' consuming test modules), or (2) frob.testing/select_tests excluding .strata from touched-set language classification entirely since it is data, not directly-runnable source. Verified reproducing: touching tests/unit/strata/litmus/*.strata and running 'frob test --base main' errors NoRunner before running any tests.