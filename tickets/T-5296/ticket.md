---
id: T-5296
title: frob-exports reports 3 packages with missing symbols (doctor, arch, vet)
state: queued
kind: bug
origin: human
created: '2026-09-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_exports.py
- src/frob/doctor
- src/frob/arch/_layering.py
- src/frob/vet/_osv.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
gh run 35717833933; re-verified on dev tip 3acf8c6b30: test_all_nine_packages_report_zero_missing_symbols fails -- src/frob missing frob.doctor.relevant_tool_findings/RelevantToolFailureKind/RelevantToolEntry/RelevantToolFinding, src/frob/arch missing arch._layering.check_layering_edges, src/frob/vet missing vet._osv.query_advisories/OsvQueryError/OsvQueryFailure from package __all__/exports.