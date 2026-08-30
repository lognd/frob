---
id: T-3460
title: 'INV051 also collapses to one identity: no real-file token in its message for
  T-3419''s extraction to use'
state: queued
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_policy_weakening_gate.py
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
found while working T-3419. INV051 (src/frob/gates/_policy_weakening_gate.py:130, Violation(file=design_dir,...) same as SELFAUDIT001) shares the identical anchor-collapse defect T-3419 fixed generically via message-text path extraction. Unlike SELFAUDIT001 (whose message always embeds the real offending file as node=<path>), INV051's message names policy ids (child_id/parent_id), not a file path, so T-3419's _real_file_from_message extraction cannot recover a distinguishing file for it -- it still degrades to the shared design_dir anchor identity. A real fix needs either (a) policy_id included in the (rule, file) identity via a separate mechanism, or (b) frob.gates._policy_weakening_gate resolving policy_id back to the .strata file that declares it (the same node_file-map pattern _vmodel.py::_vmodel_violations already uses for VMOD001, T-3264) so Violation.file becomes that real file instead of the constant design_dir.