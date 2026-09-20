---
id: T-4910
title: Wire T-4760 wrapper-drift gate + make.bat manifest entries (blocked on T-3962
  lease)
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: v0.537.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/scaffold/project.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.537.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4760 implemented wrapper_drift_gate (src/frob/gates/_wrapper_drift.py, WRAP001/002/003) and the dynamic Makefile/make.bat wrapper-target managed blocks in src/frob/scaffold/_managed.py, but could not: (1) register wrapper_drift_gate in the _ALL_GATES pipeline in src/frob/gates/__init__.py, or (2) add make.bat.j2 manifest entries to src/frob/scaffold/project.py's per-type render manifests -- both files are leased by T-3962 at time of landing. Until this lands, make.bat is created lazily by the first 'frob scaffold apply' run (already supported: _apply_text_block creates a missing target file) rather than shipped at 'frob scaffold new' time, and the drift gate exists but is not yet wired into 'frob check'. Wire both once T-3962's lease clears.