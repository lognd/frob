---
id: T-5447
title: 'Post-land sweep residue 2026-09-23_2142: COV001:src/frob/sql/_orm_rules.py
  COV001:src/frob/webapp/_a11y_statement.py COV002:.claude/hooks/pgrep-self-match-guard.py
  COV002:src/frob/g'
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
no_scope_declared: true
no_scope_declared_reason: both in-scope files (.claude/hooks/pgrep-self-match-guard.py,
  src/frob/gates/_a11y_gate.py) are leased live by my own enqueued-but-not-landed
  T-5440/T-5444; every other finding in this ticket lives inside src/frob/sql/** or
  src/frob/webapp/** (or their tests/docs), out of touch-scope. Nothing fixable here
  until T-5440/T-5444 land -- re-check then.
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
COV001:src/frob/sql/_orm_rules.py
COV001:src/frob/webapp/_a11y_statement.py
COV002:.claude/hooks/pgrep-self-match-guard.py
COV002:src/frob/gates/_a11y_gate.py
COV002:src/frob/sql/_extract.py
COV002:src/frob/sql/_orm_rules.py
COV002:src/frob/webapp/_comply_substrate.py
COV002:src/frob/webapp/_seo_substrate.py
COV002:src/frob/webapp/_websec_authz_substrate.py
COV002:src/frob/webapp/_websec_bounds.py
COV002:src/frob/webapp/_websec_sinks.py
COV002:tests/unit/test_webapp_comply_substrate.py
COV002:tests/unit/test_websec_bounds.py
COV002:tests/unit/test_websec_headers_log.py
COV007:src/frob/webapp/_a11y_forms_contrast.py
COV007:src/frob/webapp/_a11y_statement.py
DOC002:src/frob/sql/_orm_rules.py
DOC002:src/frob/webapp/_a11y_forms_contrast.py
DOC002:src/frob/webapp/_a11y_statement.py
DUP001:src/frob/webapp/_a11y_forms_contrast.py
DUP001:tests/unit/test_webapp_a11y_forms_contrast.py
DUP002:src/frob/webapp/_a11y_forms_contrast.py
DUP002:tests/unit/sql/test_orm_rules.py
DUP002:tests/unit/test_webapp_a11y_forms_contrast.py
INV003:docs/modules/webapp-a11y-forms-contrast.md
PII012:src/frob/webapp/_a11y_forms_contrast.py
REF002:docs/modules/webapp-a11y-forms-contrast.md
REF002:src/frob/webapp/_a11y_forms_contrast.py
WIRE001:src/frob/sql/_orm_rules.py