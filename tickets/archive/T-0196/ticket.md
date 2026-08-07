---
id: T-0196
title: 'R5 fidelity: real control-flow edges from frob.lang where available, proxy
  demoted to true fallback'
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
parent: T-0187
tier: ticket
sprint: null
scope:
- tickets.md
- src/frob/dup/**
- src/frob/lang/**
- frob-core/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup_r5_multilang.py::TestRealDataflowGraphPerGrammar::test_python_block_still_matches
- tests/test_dup_r5_multilang.py::TestRealDataflowGraphPerGrammar::test_rust_block_matches_and_labels_def_use
- tests/test_dup_r5_multilang.py::TestRealDataflowGraphPerGrammar::test_typescript_statement_block_matches_and_labels_def_use
- tests/test_dup_r5_multilang.py::TestRealDataflowGraphPerGrammar::test_c_compound_statement_matches_and_labels_def_use
- tests/test_dup_r5_multilang.py::TestRealDataflowGraphPerGrammar::test_cpp_compound_statement_matches_and_labels_def_use
- tests/test_dup_r5_multilang.py::TestRealDataflowGraphHonestFallback::test_unrecognized_grammar_label_returns_none
designated_repro_test: null
threat: null
component: null
---
Survey items 7/8 ADAPT: verify frob.lang actual CFG-edge coverage FIRST (the survey flags this VERIFY), then follow R4 established two-tier pattern (real primary, proxy fallback for unparseable symbols). Disclose per-language coverage honestly in dup.md.