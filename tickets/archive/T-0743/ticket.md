---
id: T-0743
title: 'arch model: NormalizedVariant for enum associated-data shape (Rust/Kotlin
  payloads)'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0612
parent: T-0329
tier: ticket
sprint: null
scope:
- src/frob/arch/_normalized.py
- src/frob/arch/_rust.py
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestRustAdapter::test_adapt_enum_variant_payload_shapes
designated_repro_test: null
acceptance:
- text: GIVEN a Rust enum with tuple and struct variants WHEN RustAdapter.adapt runs
    THEN variant payload shapes are represented and asserted by a test
  evidence:
  - tests/unit/test_arch.py::TestRustAdapter::test_adapt_enum_variant_payload_shapes
threat: null
component: null
---
Lost draft from T-0612 (Rust adapter): enum variants with associated data currently flatten to NormalizedField, losing the payload shape. Extend the model (NormalizedVariant or fields on NormalizedClass) keeping _normalized.py tree_sitter-free, map Rust enum payloads and coordinate with T-0681 (TS phase 2, same model-extension class).