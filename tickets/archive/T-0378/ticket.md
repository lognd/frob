---
id: T-0378
title: 'vet: Rust binding-aware capability resolution'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: T-0376
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- tests/test_vet*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestCapabilityScanRustBindingResolution::test_call_before_rebinding_still_detected
- tests/test_vet.py::TestCapabilityScanRustBindingResolution::test_call_after_rebinding_still_not_detected
- tests/test_vet.py::TestCapabilityScanRustBindingResolution::test_use_as_alias_detected
designated_repro_test: null
threat: null
component: null
---
Extend binding-aware resolution to Rust: resolve 'use' aliases (as-renames) and path resolution so `use std::process::Command as C` still resolves to the dangerous capability, mirroring Python's scope-shadowing discipline (a local binding of the same name must NOT false-positive). Acceptance: aliased use-import still caught; local shadow not caught; adversarial tests added.