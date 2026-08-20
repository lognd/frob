---
id: T-2695
title: 'LARGE001 remainder batch 2: ~80 files after T-1656''s batch-1 (2 waived, 1
  seam filed)'
state: in-progress
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_store.py
- tests/unit/test_ticket_store.py
- src/frob/tickets/_store_migrate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/**
  reason: 'T-2695: narrow to a tractable first batch -- src/frob/** as declared scope
    is a repo-wide write lease that stalls every other agent; per coordinator direction,
    narrow before start and work in batches'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/tickets/_store.py
  reason: 'T-2695 batch 2a: two named split-candidate files from the ticket body --
    _store.py (single-vs-legacy-backend seam) and _selfconform.py (SYS100-SYS107 numbered-rule
    seam)'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: 'T-2695 batch 2a: two named split-candidate files from the ticket body --
    _store.py (single-vs-legacy-backend seam) and _selfconform.py (SYS100-SYS107 numbered-rule
    seam)'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: 'T-2695 batch 2a: two named split-candidate files from the ticket body --
    _store.py (single-vs-legacy-backend seam) and _selfconform.py (SYS100-SYS107 numbered-rule
    seam)'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: 'T-2695 batch 2a: two named split-candidate files from the ticket body --
    _store.py (single-vs-legacy-backend seam) and _selfconform.py (SYS100-SYS107 numbered-rule
    seam)'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/tickets/_store_migrate.py
  reason: 'T-2695: new module the _store.py migration split created'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/tickets/_store_migrate.py
  reason: 'T-2695: new module the _store.py migration split created'
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: src/frob/strata/_selfconform.py
  reason: 'T-2695: _selfconform.py split deferred to its own ticket (draft filed)
    -- a safe split needs a real 3-layer helper-dependency map (shared observed-kinds
    computation / per-rule violation classification / orchestration), genuinely larger
    surgery than this batch''s remaining budget, not a lazy waiver or a forced line-count
    split'
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: tests/unit/strata/test_selfconform.py
  reason: 'T-2695: _selfconform.py split deferred to its own ticket (draft filed)
    -- a safe split needs a real 3-layer helper-dependency map (shared observed-kinds
    computation / per-rule violation classification / orchestration), genuinely larger
    surgery than this batch''s remaining budget, not a lazy waiver or a forced line-count
    split'
  actor: logan
  at: '2026-08-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Continuation of T-1656 (LARGE001 remainder). T-1656's batch-1 pass
examined and disposed of 2 files (check_runner.py, sys_runner.py -- real
per-file frob:waive LARGE001 reasoning) and identified one genuine split
seam filed separately (telemetry.py, T-2694). ~80 files remain
unexamined, measured via `frob check --only archgate --json` (gate:LARGE
warning-severity file count grew from T-1656's original 48 to 82 -- other
work has added new over-threshold files since T-1656 was filed; re-measure
at pickup time rather than trusting either number).

Apply the same per-file judgement T-1651/T-1656 both used: find the real
seam (cohesive responsibility, pipeline phase, distinct consumer set) or
waive with a specific reason naming what was actually checked. A
line-count-only split is strictly worse than the warning; do not force
one to move the number.

Files already flagged in T-1656's own body as split candidates but NOT
yet attempted (still true):
- src/frob/gates/__init__.py -- highest-value target (rule-family
  section dividers already present).
- src/frob/tickets/_store.py -- single-vs-legacy-backend seam.
- src/frob/strata/_selfconform.py -- SYS100-SYS107 numbered-rule seam.

Flagged high-risk (already multiply split, orchestrator-shaped, needs
dedicated investigation before deciding split-vs-waive):
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py

Note: several of the highest-value files above live under another
agent's lease at various points in this repo's fleet history (tickets/**,
ticket_runner/**, gates/**, strata/**) -- check current lease state
before scoping a batch; narrow scope BEFORE `ticket start`, per this
repo's standing TICK009 guidance, rather than claiming the whole
remainder in one broad scope.
