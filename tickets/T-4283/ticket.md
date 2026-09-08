---
id: T-4283
title: T-4273's declared scope has pre-existing SCOPE002 closure debt
state: queued
kind: docs
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

`frob check --ticket T-4273` reports 34 gate:SCOPE findings, almost all
SCOPE002 (scope-declaration-time doc/test/private-helper closure): T-4273's
declared scope (`src/frob/tickets/_leases.py`, `src/frob/app/ticket_runner/
_close_cmd.py`, `tests/test_ticket_leases.py`) does not closure-cover every
`frob:doc`/`frob:tests` target and private-helper callee those two heavily
cross-referenced modules already carry -- docs/modules/tickets-landing.md,
docs/modules/tickets-lifecycle.md, docs/modules/tickets-data-storage.md,
tests/test_ticket_leases_cross_worktree.py, tests/test_ticket_ownership_guard.py,
tests/test_tickets_leases.py, tests/test_tickets.py, tests/test_tickets_review.py,
tests/test_ticket_reverify.py, tests/test_bug002_no_behavior_change.py,
tests/system/test_spawn_budget.py, and several tests/unit/*.py files, plus
private-helper edges into src/frob/app/ticket_runner/__init__.py,
_land_cmd.py, _lifecycle.py, _verify.py, src/frob/tickets/__init__.py,
_evidence.py, _land.py, _store.py, _worktree_sweep.py.

Confirmed PRE-EXISTING: this closure gap was already present the moment
T-4273 was filed with its 2-file scope, entirely independent of T-4273's
own fix (a ledger-commit self-heal bug) -- none of the flagged symbols
(LAND_LOCK_REL, lease_age_seconds, enforce_ticket_ownership, etc.) were
touched by T-4273's diff. `_leases.py`/`_close_cmd.py` are simply two of
this repo's most heavily cross-referenced modules, and no ticket scoped
to just them (or a small extension of them) can closure-satisfy SCOPE002
without either scoping in a large fraction of `frob.tickets`/
`frob.app.ticket_runner` and its whole doc/test web, or SCOPE002 gaining
a documented exemption for a file whose existing directive count already
puts full closure out of proportion to any single ticket's own change
(the precedent this repo already uses for a monolithic doc file, see
`src/frob/gates/_rule_id_scan.py`'s own `frob:waive COV001` comment on
`SCANNED_BASES`).

## Plan

Not prescribed here -- options include: (a) a documented SCOPE002
exemption/waiver path for a ticket scoped narrowly on purpose against a
file with disproportionate pre-existing closure (mirroring the COV001
precedent), or (b) accepting these as permanent WARN-severity debt with
no expectation of ever reaching zero for these two files specifically,
documented as such. Left to whoever picks this up to decide the shape;
this ticket exists so the debt is recorded rather than silently absorbed
into T-4273's own scope.
