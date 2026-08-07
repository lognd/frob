---
id: T-0468
title: 'vet: verify Python T-0328 resolver for the same order-insensitive shadow bug
  T-0378 fixed in Rust (attribute-access rebind) -- needs a failing repro test before
  fixing'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestCapabilityScanLocalRebindResolution::test_call_before_rebinding_still_detected
- tests/test_vet.py::TestCapabilityScanLocalRebindResolution::test_call_after_rebinding_still_not_detected
designated_repro_test: null
threat: null
component: null
---
