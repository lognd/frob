---
id: T-4521
title: 'ticket verb family: hide internal callbacks (merge-driver, sweep-async), drop
  migrate and the debt/deprecated aliases, fold runs-last-parallel-safe into a flag,
  move renumber/restore/reconcile under ticket admin'
state: done
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
- src/frob/app/ticket_runner/__init__.py
- tests/unit/test_ticket_cli_surface.py
- docs/commands/ticket.md
- src/frob/_cli_parsers/_ticket/__init__.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/_cli_parsers/_ticket/_progress.py
- src/frob/_cli_parsers/_ticket/_query.py
- tests/test_tickets_migration.py
- tests/unit/test_app_runners_batch7.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/_ticket
  reason: avoid lease collision with T-draft-db13b6bc on _closeout_evidence.py; re-scoping
    to individual files
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/_cli_parsers/_ticket/__init__.py
  reason: re-add individual _ticket parser files, excluding _closeout_evidence.py
    which is leased by T-draft-db13b6bc
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: re-add individual _ticket parser files, excluding _closeout_evidence.py
    which is leased by T-draft-db13b6bc
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: re-add individual _ticket parser files, excluding _closeout_evidence.py
    which is leased by T-draft-db13b6bc
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_new.py
  reason: re-add individual _ticket parser files, excluding _closeout_evidence.py
    which is leased by T-draft-db13b6bc
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_progress.py
  reason: re-add individual _ticket parser files, excluding _closeout_evidence.py
    which is leased by T-draft-db13b6bc
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_query.py
  reason: re-add individual _ticket parser files, excluding _closeout_evidence.py
    which is leased by T-draft-db13b6bc
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/test_tickets_migration.py
  reason: criterion 2 (migrate/debt/deprecated removal) makes these tests' old-behavior
    assertions stale; updating them is a direct consequence of this ticket's own change,
    not unrelated scope creep
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: criterion 2 (migrate/debt/deprecated removal) makes these tests' old-behavior
    assertions stale; updating them is a direct consequence of this ticket's own change,
    not unrelated scope creep
  actor: logan
  at: '2026-09-16'
evidence:
- tests/unit/test_ticket_cli_surface.py::TestHiddenInternalCallbacks::test_merge_driver_still_dispatches
- tests/unit/test_ticket_cli_surface.py::TestRemovedVerbsExitTwo::test_migrate_removed_notice_names_replacement
- tests/unit/test_ticket_cli_surface.py::TestAdminGroup::test_admin_renumber_matches_hidden_top_level_alias
designated_repro_test: null
acceptance:
- text: GIVEN frob ticket --help WHEN rendered THEN merge-driver and sweep-async are
    absent from the listing but still dispatch when invoked by git and by land
  evidence:
  - tests/unit/test_ticket_cli_surface.py::TestHiddenInternalCallbacks::test_merge_driver_still_dispatches
- text: GIVEN frob ticket migrate, ticket debt, ticket deprecated WHEN invoked THEN
    each prints a one-line removal notice naming the replacement and exits 2
  evidence:
  - tests/unit/test_ticket_cli_surface.py::TestRemovedVerbsExitTwo::test_migrate_removed_notice_names_replacement
- text: GIVEN frob ticket admin renumber|restore|reconcile WHEN run THEN behaviour
    is byte-for-byte the old top-level ticket verbs
  evidence:
  - tests/unit/test_ticket_cli_surface.py::TestAdminGroup::test_admin_renumber_matches_hidden_top_level_alias
acceptance_amendments:
- op: remove
  index: 3
  old_text: GIVEN frob ticket runs-last --parallel-safe WHEN run THEN it records what
    runs-last-parallel-safe recorded, and the old verb is gone
  new_text: null
  reason: runs-last --parallel-safe deferred into T-3614 by coordinator decision (config.py
    lease)
  actor: logan
  at: '2026-09-17'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-16: ticket has 53 subverbs (next largest group 10). 14 are maintenance/one-off: migrate (one-time ledger migration already run), merge-driver (a git merge-driver callback, _progress.py:201, not a user verb), sweep-async (spawned by land, _closeout_evidence.py:536), runs-last-parallel-safe (a 26-char verb setting one boolean, _metadata.py:691), ticket debt / ticket deprecated (pure aliases of top-level verbs, _ticket/__init__.py:185,189; 4 and 1 references), renumber/restore/reconcile (disaster-recovery only). Zero-reference leaves: waive-audit scan, waive-audit complete, sprint show.