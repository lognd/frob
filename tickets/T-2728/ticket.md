---
id: T-2728
title: Wire migrate_missing_v2 into the CLI, or delete it
state: done
kind: feature
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_store_migrate.py
- src/frob/_cli_parsers/_ticket/_progress.py
- src/frob/app/ticket_runner/_query.py
- tests/test_tickets_migration.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_migration.py
  reason: 'T-2728: CLI wiring tests for migrate_missing_v2 live here alongside the
    existing --to v2 CLI test class'
  actor: logan
  at: '2026-08-27'
evidence:
- tests/test_tickets_migration.py::TestMigrateCliFillGapsFlag::test_fill_gaps_flag_calls_migrate_missing_v2
- tests/test_tickets_migration.py::TestMigrateCliFillGapsFlag::test_fill_gaps_omitted_keeps_original_behavior
- tests/test_tickets_migration.py::TestMigrateCliFillGapsFlag::test_fill_gaps_combines_with_to_v2
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

`migrate_missing_v2` (T-2355, `src/frob/tickets/_store_migrate.py`, moved
there from `_store.py` by T-2695) has no CLI wiring anywhere in `src/
frob/_cli_parsers/` or `src/frob/app/` -- confirmed via a targeted search
(no hits outside its own tests). It closes a real partial-migration gap
`migrate_v1_to_v2` leaves open (per its own docstring, T-2355), but is
currently reachable only from tests, never from `frob ticket migrate` or
any other CLI surface.

T-2695's own extraction surfaced this as a fresh WIRE001 (diff-based
novelty heuristic sees the moved function as "new"), waived there with
this ticket as the follow_up -- the underlying gap (no CLI wiring) is
pre-existing, not new debt from the move.

Wire it into `frob ticket migrate` (e.g. a `--fill-gaps`/similar flag
alongside the existing `--to v2` wiring of `migrate_v1_to_v2`), or delete
it if it has been superseded and is genuinely no longer needed.