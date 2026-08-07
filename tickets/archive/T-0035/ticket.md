---
id: T-0035
title: 'REL001 release gate: mechanical semver from public-API digests'
state: done
kind: feature
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/release/**
- src/frob/gates/**
- src/frob/app/release_runner.py
- src/frob/app/app.py
- src/frob/app/config.py
- src/frob/__main__.py
- tests/test_release.py
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_release.py::test_release_gate_flags_missing_bump
- tests/test_release.py::test_changed_signature_is_major
designated_repro_test: null
threat: null
component: null
---
