---
id: T-3629
title: 'ARCH102: split src/frob/tickets/_land_squash.py (38 exports, 3 clusters)'
state: in-progress
kind: feature
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_squash.py
- tests/unit/test_land_squash_residue_reclaim.py
- tests/unit/test_land_squash_stage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/**/*land_squash*
  reason: narrow overbroad glob that phantom-matches T-1661s live lease on tests/unit/strata/**;
    the real test files live in tests/unit/
  actor: logan
  at: '2026-09-01'
- op: add
  glob: tests/unit/test_land_squash_residue_reclaim.py
  reason: narrow overbroad glob that phantom-matches T-1661s live lease on tests/unit/strata/**;
    the real test files live in tests/unit/
  actor: logan
  at: '2026-09-01'
- op: add
  glob: tests/unit/test_land_squash_stage.py
  reason: narrow overbroad glob that phantom-matches T-1661s live lease on tests/unit/strata/**;
    the real test files live in tests/unit/
  actor: logan
  at: '2026-09-01'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
ARCH102: src/frob/tickets/_land_squash.py has 38 exports clustering
into roughly 3 concerns -- split it along those clusters. Write the
split plan (which exports go into which new module, and why) in this
ticket's body BEFORE coding. MUST use `uv run frob refactor split` /
`uv run frob refactor move-module` to perform the actual split, never
a hand-copy (standing user directive) -- append any tool gaps
encountered to T-3596. After the split, run a repo-wide import check
and `ty` type-check.

Scope: src/frob/tickets/_land_squash.py + its test file + any direct
importers whose import statement must be updated.

Previously specified but never filed (LandInProgress starvation
during a prior agent's ~45 min of retries); refiled now as part of
draining that starved backlog.
