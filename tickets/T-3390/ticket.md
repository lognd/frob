---
id: T-3390
title: Narrow PII012 name-signature heuristic to avoid identifier false positives
state: in-progress
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_pii_structural/**
- src/frob/doctor_runner.py
- src/frob/serve/_socketd.py
- tests/unit/test_doctor_runner_t1276.py
- docs/modules/gates.md
- tests/test_pii_structural_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates
  reason: narrow scope to actual PII012 detector + the 4 finding sites
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_pii_structural/**
  reason: narrow scope to actual PII012 detector + the 4 finding sites
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/doctor_runner.py
  reason: narrow scope to actual PII012 detector + the 4 finding sites
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/serve/_socketd.py
  reason: narrow scope to actual PII012 detector + the 4 finding sites
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_doctor_runner_t1276.py
  reason: narrow scope to actual PII012 detector + the 4 finding sites
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/gates.md
  reason: doc anchor for pii_structural_gate touched by scope
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_pii_structural_gate.py
  reason: new regression tests for the two PII012 allowlist entries
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
PII012: 4 findings (run_diagnosis, allow_reuse_address, _run_diagnosis_records_levels x2) are identifier-name-shaped, not actual PII. Verify whether they are genuine false positives; if so, narrow the PII012 detector's name-signature heuristic (symbolic check per standing directive), not per-site waivers. Part of PyPI release error-floor burn (Series EQ slice).