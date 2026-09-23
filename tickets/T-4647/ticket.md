---
id: T-4647
title: wire TESTMOCK001 (T-3997) into the live frob check job list
state: queued
kind: security
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-3962
parent: T-4655
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- design/frob.strata
- docs/design/registry/check-coverage.yaml
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-4655
  reason: 'kernel-decoupling epic T-4651: rederive the frob kernel behind enforced
    module boundaries; this ticket already states the right work for this concern
    and is adopted as a child rather than duplicated'
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: null
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3997 implemented and tested testmock001_violations in src/frob/gates/_coverage.py (a frob:tests-bound Python symbol whose only binding test(s) mock every collaborator it calls -- T-3933's own LANGUAGE_COLLECTORS stand-in shape). Wiring it into the live frob check job list requires editing src/frob/gates/__init__.py's _build_jobs/import list plus the rule-severity table, which is leased by T-3962 for T-3997's entire duration (frob ticket scope T-3997 --add src/frob/gates/__init__.py was refused on that lease). This ticket: once T-3962's lease clears, import testmock001_violations into gates/__init__.py, add it to _build_jobs and the rule table (mirroring entrypoint_coverage_violations/COV010's own wiring), add a design/frob.strata testsuite node + docs/design/registry/check-coverage.yaml row, and fold docs/modules/gate-testmock001.md into docs/modules/gates.md (also noted in T-4605's fold-in list).