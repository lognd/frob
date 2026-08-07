---
id: T-0442
title: 'arch tool-summary: frob check _run_arch stage still uses default thresholds,
  not load_arch_config (T-0373 sibling)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/_python.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_arch_stage_uses_calibrated_default_not_library_default
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_arch_stage_respects_explicit_frob_toml_override
designated_repro_test: null
threat: null
component: null
---
