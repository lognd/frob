---
id: T-draft-fdd012cc
title: 'Burn ruff I001 batch 1: src/frob non-gates files'
state: in-progress
kind: bug
origin: human
created: '2026-08-21'
priority: medium
parent: T-2373
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/config.py
- src/frob/arch/__init__.py
- src/frob/doctor.py
- src/frob/scaffold/__init__.py
- src/frob/strata/__init__.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_store.py
- src/frob/verify/_backpressure.py
- src/frob/vet/_capability.py
- src/frob/vet/_scan.py
- tickets/T-2373/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/T-2373/ticket.md
  reason: sibling ticket-metadata edit (declare-no-scope on the parent epic) landed
    in the same worktree commit range
  actor: logan
  at: '2026-08-21'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Batch 1 of T-2373's ruff I001 (import-sort) burn-down: the src/frob/**
(non-gates) files carrying an I001 finding, measured via
`uv run frob check --json --budget 500` piped through a manual JSON
filter for code=="I001" in a fresh worktree, 2026-08-21 (10 findings,
one per file below):

- src/frob/app/config.py
- src/frob/arch/__init__.py
- src/frob/doctor.py
- src/frob/scaffold/__init__.py
- src/frob/strata/__init__.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_store.py
- src/frob/verify/_backpressure.py
- src/frob/vet/_capability.py
- src/frob/vet/_scan.py

Deliberately excludes every file under src/frob/gates/ (T-2359's bulk
ruff-format reformat batches are concentrated there per coordinator
guidance) and every tests/ file (left for a later batch to keep this
diff small and land-check fast).

Fix: `ruff check --select I001 --fix` on exactly these files (import
reordering only, no other rule families), then promote I001 from
warning to error severity in its gate module per T-2373's own closure
requirement -- but ONLY once every sibling batch has also landed (do
not flip severity from a partial batch; that would make every
not-yet-fixed file in another batch a new ERROR-tier finding for
nobody's ticket).
