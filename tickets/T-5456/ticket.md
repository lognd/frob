---
id: T-5456
title: 'Post-land sweep residue 2026-09-23_2251: COV001:src/frob/gates/_sql_explain_obligation.py
  COV002:src/frob/webapp/_a11y_forms_contrast.py COV002:src/frob/webapp/_a11y_statement.py
  CO'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: milestone
  old_value: null
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Findings raised by a post-land sweep and disposed against this ticket by the coordinator's runner to keep the quarantine clear. Fix each in scope:
COV001:src/frob/gates/_sql_explain_obligation.py
COV002:src/frob/webapp/_a11y_forms_contrast.py
COV002:src/frob/webapp/_a11y_statement.py
COV002:src/frob/webapp/_websec_xss.py
COV002:tests/unit/test_webapp_a11y_forms_contrast.py
COV002:tests/unit/test_webapp_a11y_statement.py
COV002:tests/unit/test_websec_sinks.py
DOC006:docs/modules/webapp-a11y-interaction.md
DUP002:tests/unit/test_websec_deser.py
INV003:docs/modules/webapp-websec-deser.md
OPAQUE001:src/frob/gates/_sql_explain_obligation.py
OPAQUE001:tests/fixtures/webapp/websec1xx/deser/webesc110_negative/app.py
OPAQUE001:tests/fixtures/webapp/websec1xx/deser/webesc110_positive/app.py
OPAQUE001:tests/unit/test_websec_deser.py
PERF002:src/frob/webapp/_websec_deser.py
REF002:docs/modules/webapp-websec-deser.md
WIRE001:src/frob/gates/_sql_explain_obligation.py