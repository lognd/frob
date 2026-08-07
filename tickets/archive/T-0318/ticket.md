---
id: T-0318
title: rust proptest! macro block is not a valid frob:tests binding target (expands
  to tests, not literal AST)
state: done
kind: bug
origin: auditor
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- src/frob/lang/_walk_rust.py
- src/frob/gates/__init__.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTestGate::test_test003_satisfied_by_proptest_macro_block
- tests/test_lang.py::TestParseTsRustCppC::test_rust_directive_binds_above_proptest_macro_block
- tests/test_lang.py::TestParseTsRustCppC::test_rust_non_test_macro_does_not_bind
designated_repro_test: null
threat: null
component: null
---
FROBLEMS (feldspar L3): a '// frob:tests <crate>/src kind=integration' comment directly above a 'proptest! { ... }' block does not bind for TEST003 -- proptest! expands to multiple #[test] fns at compile time that do not exist as literal AST nodes at the comment site (v0.6.0 fixed attribute-stack placement above a plain #[test] fn, not macro blocks). Lower priority (rare); related to T-0307 multi-case counting. Fix: recognize a frob:tests comment above a proptest!/parametrizing macro block and resolve it against the cargo-test-collected expanded case ids for that file. Test: frob:tests above a proptest! block satisfies TEST003.

## Failure log
- 2026-07-19 attempt 1: Fix chain is out of T-0318's scope: frob/lang/_walk_rust.py._visit never emits a symbol for macro_invocation (proptest!{...}), so the directive binds to a bare file path via graph/dsl.py's fallback; gates/_symref_to_nodeid then turns that into '<path>::' which never matches real cargo-collected '<path>::case' ids in gates/_node_id_collected. Both files are outside src/frob/testing/**. Smallest next step: widen scope to include _walk_rust.py (emit a symbol spanning proptest! blocks) and gates/__init__.py (match bare-path edges against any collected id under that file). Did T-0317 fully instead; see Done report.