---
id: T-2411
title: wire LANG004 capability_conformance_gate into the check job table
state: queued
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2365 built capability_conformance_gate (LANG004, src/frob/gates/_lang_conformance.py) -- the behavioral half of the adapter-capability axis, verified directly by tests/test_lang_conformance_gate.py but NOT wired into frob check's job table (src/frob/gates/__init__.py's _GATE_JOBS/_STAGE_GROUPS dicts, mirroring lang_conformance/lang_project_conformance's own entries) because that file was out of T-2365's declared scope. Wire it in the same way lang_conformance_gate/project_lang_conformance_gate are wired (search for 'lang_conformance' in src/frob/gates/__init__.py for the exact pattern: job table entry, stage group membership, --only list membership).