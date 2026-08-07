---
id: T-0278
title: 'fix(lang): rust directive binding must look through stacked attributes'
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/lang/_walk_rust.py
- tests/test_lang.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_lang.py::TestParseTsRustCppC::test_rust_directive_binds_above_stacked_attributes
- tests/test_lang.py::TestParseTsRustCppC::test_rust_directive_binds_above_single_attribute
- tests/test_lang.py::TestParseTsRustCppC::test_rust_directive_binds_directly_above_keyword_no_attrs
- tests/test_lang.py::TestParseTsRustCppC::test_rust_directive_binds_below_attributes_workaround_placement
designated_repro_test: null
threat: null
component: null
---
Coordinator-reported bug (Bug D, same mechanism class as Bug B):
`// frob:doc`/`// frob:tests` above a stack of 2+ rust attribute lines
(`#[derive(...)]`, `#[serde(...)]`) on a pub item silently fails to
associate; the identical comment below all attributes (directly above
the `pub fn|struct|enum` keyword) binds fine. Documented lithos
FROBLEMS.md 2026-07-18 (wave agent W1b).