---
id: T-1045
title: ffi_boundary gate missing from _STAGE_GROUPS breaks --stamp-baseline --only
  chunking
state: dropped
kind: bug
origin: agent
created: '2026-07-27'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/__init__.py
- tests/unit/test_app_runners_batch6.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-0690 registered ffi_boundary in frob.gates._ALL_GATES (38 gates total) but never added it to any _STAGE_GROUPS member, leaving it as a 1-gate leftover chunk that _stamp_baseline_gate_chunks() expects but no --only <group-or-gate> loop in the agent playbook enumerates by name, so the chunked accumulator in _run_stamp_baseline never converges (37/38 covered forever) and test_stamp_baseline_only_chunk_completes_and_stamps fails.

## Drop reason
- 2026-07-27: duplicate of T-1044, filed by mistake