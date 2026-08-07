---
id: T-0592
title: 'REG008/REG009 conformance pool: anchor frob:enforces in gate code for the
  115 registry claims'
state: done
kind: docs
origin: agent
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/design/registry/**
- src/frob/dup/_rules.py
- src/frob/fuzz/_rules.py
- src/frob/perf/_rules.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/test_secrets_gate.py::TestTrackedEnvFile::test_env_file_sec002
designated_repro_test: null
threat: null
component: null
---
Batch-anchor frob:enforces directives at the actual enforcing functions for the REG008 pool flagged by frob check --only registry (91 CHK-GATE entries in check-coverage.yaml plus arch-checks.yaml/pii.yaml/secrets.yaml/weaknesses.yaml entries). Verify each anchor against real enforcing code before adding; flip disposition to deferred:ticket if a yaml claim is false.