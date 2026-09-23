---
id: T-5260
title: 'Post-land sweep residue 2026-09-21_2054: AFFECT001:src/frob/strata/_pii.py
  AFFECT001:strata-core/src/parse/grammar_policy.rs COV001:src/frob/gates/_sys_provenance.py
  COV001:src/frob'
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.540.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.540.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Findings raised by a post-land sweep and disposed against this ticket by the coordinator's runner to keep the quarantine clear. Fix each in scope:
AFFECT001:src/frob/strata/_pii.py
AFFECT001:strata-core/src/parse/grammar_policy.rs
COV001:src/frob/gates/_sys_provenance.py
COV001:src/frob/strata/_pii.py
COV002:src/frob/strata/_pii.py
COV002:tests/gates/test_docptr.py
COV002:tests/tickets/test_land_squash.py
COV002:tests/unit/test_land_in_progress_window.py
COV002:tests/unit/test_ticket_runner_base_forward_t4105.py
COV002:tests/unit/verify/test_drain.py
COV007:src/frob/strata/_pii.py
DOC002:src/frob/gates/_sys_provenance.py
DOC002:src/frob/strata/_pii.py
DOC011:docs/strata/surface.md
DRIFT001:src/frob/gates/_fix_engine_scope.py
DUP001:strata-core/src/parse/grammar_module.rs
DUP002:tests/test_pii_provenance_trust_identity.py
DUP002:tests/test_ticket_reconcile.py
DUP002:tests/test_tickets_parent.py
FLAGCOV001:frob.toml
REF002:strata-core/src/parse/grammar_module.rs
WIRE001:src/frob/gates/_sys_provenance.py