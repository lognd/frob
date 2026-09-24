---
id: T-5444
title: 'Post-land sweep residue 2026-09-23_2045: ARCH104:src/frob/gates/_a11y_gate.py
  COV001:src/frob/gates/_a11y_gate.py COV001:src/frob/webapp/_a11y_structure.py DOC002:src/frob/gates/_a1'
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
scope:
- src/frob/gates/_a11y_gate.py
- tests/unit/gates/test_cov002_strata_declarations.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_a11y_gate.py
  reason: checking lease availability for ARCH104/COV001/DOC002/OPAQUE001
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/gates/test_cov002_strata_declarations.py
  reason: 'in-scope subset of post-land sweep residue: ARCH104/COV001/DOC002/OPAQUE001
    on _a11y_gate.py (gates file, in-scope), DUP002 on tests/unit/gates/test_cov002_strata_declarations.py;
    COV001/DOC002 on src/frob/webapp/_a11y_structure.py, DUP001 on tests/unit/test_webapp_a11y_structure.py,
    INV003 on docs/modules/webapp-a11y-structure.md deferred (webapp-family owned);
    DOC006 on tickets/T-5322/ticket.md deferred (never hand-edit ledger files)'
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: milestone
  old_value: null
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
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
ARCH104:src/frob/gates/_a11y_gate.py
COV001:src/frob/gates/_a11y_gate.py
COV001:src/frob/webapp/_a11y_structure.py
DOC002:src/frob/gates/_a11y_gate.py
DOC002:src/frob/webapp/_a11y_structure.py
DOC006:tickets/T-5322/ticket.md
DUP001:tests/unit/test_webapp_a11y_structure.py
DUP002:tests/unit/gates/test_cov002_strata_declarations.py
INV003:docs/modules/webapp-a11y-structure.md
OPAQUE001:src/frob/gates/_a11y_gate.py