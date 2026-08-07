---
id: T-0242
title: 'strata runner: frob test should invoke sys audit natively for touched .strata
  files'
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- src/frob/strata/**
- tests/**
- docs/modules/testing.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_testing.py::TestNativeStrataAudit::test_no_runner_config_needed
- tests/test_testing.py::TestNativeStrataAudit::test_no_models_is_neutral_pass
- tests/test_testing.py::TestNativeStrataAudit::test_bad_design_file_fails
designated_repro_test: null
threat: null
component: null
---
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot: touching a .strata file breaks frob test with NoRunner (language strata has selected tests but no [[test.runner]]); workaround registering frob sys audit as runner demands a dummy {ids} placeholder (BadRunnerSpec otherwise). Fix: native strata selection path -- touched .strata invokes sys audit without per-repo runner config; placeholder validation should accept runners that take no ids. Relates T-0149 (closed, per-repo config path) -- this makes it zero-config.