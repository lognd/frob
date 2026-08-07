---
id: T-0198
title: 'cross-language clone litmus: same logic in two grammars through the real pipeline'
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: T-0187
tier: ticket
sprint: null
scope:
- tickets.md
- tests/**
- src/frob/dup/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup_cross_lang.py::TestCrossLanguageCloneNotYetDetected::test_both_languages_parse_into_the_snapshot
- tests/test_dup_cross_lang.py::TestCrossLanguageCloneNotYetDetected::test_both_symbols_are_individually_fingerprinted
designated_repro_test: null
threat: null
component: null
---
Survey item 13: the cross-language claim rests on shared node vocabulary between frob.lang grammars but no fixture proves it. One fixture pair (python+ts same algorithm) through the REAL pipeline; if vocabulary does not align, that is the finding -- document and file rather than force.