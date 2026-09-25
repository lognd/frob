---
id: T-4655
title: 'Gate kernel: one registration interface from which job list, known-rule set,
  docs and check-coverage are derived'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: T-4651
tier: story
sprint: null
runs_last: false
milestone: 0.535.0
flavour: user_story
due: null
rank: null
points: null
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
no_scope_declared_reason: 'tier=epic/story rollup for the kernel-decoupling epic:
  all file work lives in the leaf children; this ticket carries no write lease by
  design'
triage_changes:
- field: sprint
  old_value: v0.535.0
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: flavour
  old_value: null
  new_value: user_story
  reason: 'E2 (T-5766): census-based flavour classification (heuristic per E1''s own
    candidate signal)'
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
GATES concern of the kernel-decoupling epic (T-4651).

Today adding one detector means hand-editing at least four places: the job list in src/frob/gates/__init__.py (9658 lines), the `_KNOWN_GATE_RULES` frozenset literal in src/frob/gates/_waive.py (3014 lines), the rule table in docs/modules/gates.md, and docs/design/registry/check-coverage.yaml. Measured consequence: T-4647 (a finished detector, TESTMOCK001, sat unwired), T-3854 (a consumer repo cannot register its own rule at all, because `_KNOWN_GATE_RULES` is a closed frozenset of frob's OWN ids), and every one of those four files is a shared-registry lease hotspot.

Target shape: ONE registration interface -- a decorator or a registry module -- that a detector module declares itself through. The job list, the known-rule set, the docs/modules/gates.md enumeration and check-coverage.yaml are all DERIVED from it (generated or verified-against, never hand-maintained). Adding a detector becomes editing ONE file. Third-party registration is an explicit, supported entry point, not a frozenset edit.

Frozen contract: rule ids, their severities and the `frob:waive` DSL do not change.
