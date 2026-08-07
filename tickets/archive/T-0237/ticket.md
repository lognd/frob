---
id: T-0237
title: frob:tests edge code endpoints and kind= attr are not gate-verified
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTest010KindValidation::test_invalid_kind_reported
- tests/test_gates.py::TestTest010KindValidation::test_valid_kind_not_reported
- tests/test_gates.py::TestTest010KindValidation::test_dangling_tests_endpoint_still_caught_by_drift002
- tests/test_graph.py::TestDsl::test_tests_verb_invalid_kind_is_malformed
designated_repro_test: null
threat: null
component: null
---
Found while writing T-0159's extending guides. tests/unit/test_strata_tmlanguage.py:13 declares 'frob:tests strata-core/src/parse/mod.rs::parse_program kind="drift"'. Two problems, neither caught by any gate: (1) the code-side endpoint parse.rs::parse_program does not resolve -- frob.lang's Rust walk qualnames the symbol Parser.parse_program -- yet no DRIFT002 fires; an identical dead endpoint on a frob:describes edge DOES fire DRIFT002 (observed during T-0159: a describes edge to parse.rs::parse_program produced 'DRIFT002 ... gone' until corrected to Parser.parse_program). frob:tests edges appear exempt from endpoint resolution, so a renamed/deleted code symbol silently orphans its test-evidence edge. (2) kind="drift" is not in graph.dsl._TESTS_KINDS (unit/integration/e2e) yet is not reported as a MalformedDirective. Either widen _TESTS_KINDS deliberately or reject unknown kinds loudly; and run frob:tests code-side endpoints through the same DRIFT002 resolution describes edges get. (Refiled: first draft was lost in a tickets.md ledger splice during T-0159's concurrent-agent merge.)