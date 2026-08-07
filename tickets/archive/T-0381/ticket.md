---
id: T-0381
title: 'strata: add mandatory caught_by field to OutOfScopeEntry/OutOfScopeRegulation/BenignCapability'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: T-0376
tier: ticket
sprint: null
scope:
- src/frob/strata/_threat.py
- src/frob/strata/_compliance.py
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_threat.py::TestBenignCapability::test_empty_caught_by_is_rejected
- tests/unit/strata/test_threat.py::TestBenignCapability::test_missing_caught_by_is_rejected
- tests/unit/strata/test_threat.py::TestLoadRepoBenignCapabilities::test_missing_caught_by_is_malformed
designated_repro_test: null
threat: null
component: null
---
OutOfScopeEntry (_threat.py) is {id, reason} only; OutOfScopeRegulation (_compliance.py) adds owner+review but still no compensating-control reference. Add a mandatory caught_by field (naming the gate/rule/mechanism that DOES catch the excused CWE/threat/regulation elsewhere) to OutOfScopeEntry, and mirror the field onto OutOfScopeRegulation and BenignCapability. Acceptance: pydantic models reject construction without caught_by; existing tests updated for the new required field.