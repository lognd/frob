---
id: T-0379
title: 'vet: C/C++ binding-aware capability resolution'
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
- tests/test_vet.py::TestCapabilityScanCBindingResolution::test_macro_alias_detected
- tests/test_vet.py::TestCapabilityScanCBindingResolution::test_call_before_local_shadow_still_detected
- tests/test_vet.py::TestCapabilityScanCBindingResolution::test_local_shadowing_macro_alias_not_detected
- tests/test_vet.py::TestCapabilityScanCBindingResolution::test_transitive_macro_alias_detected
designated_repro_test: null
threat: null
component: null
---
Extend binding-aware resolution to C/C++: expand #define macro aliases, using-declarations, and typedef/namespace aliases (e.g. `#define SYS system`) so renamed calls still resolve to the dangerous capability, without false-positiving on unrelated local shadows. Acceptance: macro-aliased dangerous call still caught; local shadow not caught; adversarial tests added.