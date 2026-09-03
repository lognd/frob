---
id: T-3719
title: scaffold python-tool template does not pass frob check clean
state: queued
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
apollo FROBLEMS.md 2026-09-03: a fresh 'frob scaffold new python-tool' repo does not pass frob check clean even after the first commit: ROOT001 warns on scaffold-created .github/ and invariants/ (the scaffold's own frob.toml declares refs.entrypoint for files inside them but ROOT001 wants directory-level external-reader declarations), COV001 warns on scripts/bump_version.py::PYPROJECT, TEST003 wants an integration test for scripts/, TEST006 wants a coverage stamp. The template should ship its own conformance so a fresh scaffold is check-clean out of the box.