---
id: T-0067
title: 'strata policy sublanguage: 5 forms, semantic scoping, tree-sitter compilation'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0050
parent: T-0051
tier: ticket
sprint: null
scope:
- docs/strata/**
- tickets.md
- strata-core/**
- Makefile
- .github/**
- design/litmus/**
- src/frob/strata/**
- src/frob/policy/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_policy.py::TestGrammarRoundTrip::test_forbid_call_round_trips
- tests/unit/strata/test_policy.py::TestScopeResolution::test_trust_scope_resolves_via_lattice
- tests/unit/strata/test_policy.py::TestScopeResolution::test_unknown_component_scope_fails_closed
designated_repro_test: null
threat: null
component: null
---
forbid/confine/at-require/mediate/structural, scoped over the model (trust level, component, label) and resolved to files via code globs; compiles to per-language tree-sitter queries; extends existing POL machinery.