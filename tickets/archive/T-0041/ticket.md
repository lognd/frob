---
id: T-0041
title: 'dup follow-on: --probe CLI, full APTED, real CFG/DFG'
state: done
kind: feature
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- frob-core/**
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/dup_runner.py
- src/frob/dup/**
- tests/test_dup_rungs.py
- tests/fixtures/dup_rungs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup_rungs.py::TestR6Probing::test_fires_on_equivalent_functions_with_renamed_multi_arg_params
- tests/test_dup_rungs.py::TestR6Probing::test_refuses_keyword_only_params_instead_of_vacuous_pass
- tests/test_dup_rungs.py::TestR6Probing::test_refuses_mismatched_arity_instead_of_vacuous_pass
- tests/test_dup_rungs.py::test_cli_probe_equivalent_functions
designated_repro_test: null
threat: null
component: null
---
Follow-on polish from T-0001 (rungs complete): wire frob dup --probe
to probe_equivalence; replace statement-Levenshtein with full APTED;
replace R5's co-occurrence proxy with a real CFG/DFG.