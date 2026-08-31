---
id: T-3581
title: 'WAIVE009: _normalized.py AFFECT001 waivers promise follow-up work that already
  landed (T-3473/T-3474); remove or convert'
state: done
kind: bug
origin: agent
created: '2026-08-31'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_normalized.py
- docs/modules/arch.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/arch.md
  reason: AFFECT001 fix requires updating the normalized-code-model doc table row
    for comprehension_id
  actor: logan
  at: '2026-08-31'
body_changes:
- mode: append
  reason: 'mark no-behavior-change: doc/waiver-only fix'
  actor: logan
  at: '2026-08-31'
  old_length: 197
  new_length: 369
evidence:
- tests/unit/test_arch.py::TestNormalizedModel::test_hand_built_python_snippet_shape
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33380974368 macos self-gate: two WAIVE009 ERRORs on NormalizedCall/NormalizedBranch. Check AFFECT001 scoped first; remove the waivers if quiet, else close the doc drift or convert to frob:debt.

frob:no-behavior-change reason="removes two frob:waive AFFECT001 directives (comments) and documents an existing field in a markdown table; no runtime code path changes"