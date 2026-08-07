---
id: T-0284
title: 'coverage: deploy modules to TEST005 zero'
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/deploy/**
- src/frob/app/deploy_runner.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/deploy/test_vm_runner.py::TestFullSequence::test_run_vm_audit_runs_full_sequence
- tests/unit/deploy/test_deploy_runner.py::TestGenerate::test_generate_writes_files
designated_repro_test: null
threat: null
component: null
---
