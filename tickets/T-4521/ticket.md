---
id: T-4521
title: 'ticket verb family: hide internal callbacks (merge-driver, sweep-async), drop
  migrate and the debt/deprecated aliases, fold runs-last-parallel-safe into a flag,
  move renumber/restore/reconcile under ticket admin'
state: queued
kind: ux
origin: agent
created: '2026-09-16'
priority: medium
parent: T-2994
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: v0.534.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ticket
- src/frob/app/ticket_runner/__init__.py
- tests/unit/test_ticket_cli_surface.py
- docs/commands/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN frob ticket --help WHEN rendered THEN merge-driver and sweep-async are
    absent from the listing but still dispatch when invoked by git and by land
  evidence: []
- text: GIVEN frob ticket migrate, ticket debt, ticket deprecated WHEN invoked THEN
    each prints a one-line removal notice naming the replacement and exits 2
  evidence: []
- text: GIVEN frob ticket runs-last --parallel-safe WHEN run THEN it records what
    runs-last-parallel-safe recorded, and the old verb is gone
  evidence: []
- text: GIVEN frob ticket admin renumber|restore|reconcile WHEN run THEN behaviour
    is byte-for-byte the old top-level ticket verbs
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-16: ticket has 53 subverbs (next largest group 10). 14 are maintenance/one-off: migrate (one-time ledger migration already run), merge-driver (a git merge-driver callback, _progress.py:201, not a user verb), sweep-async (spawned by land, _closeout_evidence.py:536), runs-last-parallel-safe (a 26-char verb setting one boolean, _metadata.py:691), ticket debt / ticket deprecated (pure aliases of top-level verbs, _ticket/__init__.py:185,189; 4 and 1 references), renumber/restore/reconcile (disaster-recovery only). Zero-reference leaves: waive-audit scan, waive-audit complete, sprint show.