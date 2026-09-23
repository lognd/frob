---
id: T-5305
title: 'frob ticket reconcile --strip-stale-fields: remove pydantic-extra fields (branch/worktree
  from an older writer) from live ledger records so TICK008 stops flagging the real
  ledger'
state: done
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_store.py
- tests/test_ticket_reconcile.py
- src/frob/tickets/_reconcile.py
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/_cli_parsers/_ticket/_progress.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/ticket_runner/_reconcile.py
  reason: original scope named a file that does not exist; the real reconcile module
    is src/frob/tickets/_reconcile.py, dispatch is _lifecycle.py, CLI flag registration
    is _progress.py, plus the AppConfig field and its external-config allowlist entry
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/tickets/_reconcile.py
  reason: original scope named a file that does not exist; the real reconcile module
    is src/frob/tickets/_reconcile.py, dispatch is _lifecycle.py, CLI flag registration
    is _progress.py, plus the AppConfig field and its external-config allowlist entry
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: original scope named a file that does not exist; the real reconcile module
    is src/frob/tickets/_reconcile.py, dispatch is _lifecycle.py, CLI flag registration
    is _progress.py, plus the AppConfig field and its external-config allowlist entry
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_progress.py
  reason: original scope named a file that does not exist; the real reconcile module
    is src/frob/tickets/_reconcile.py, dispatch is _lifecycle.py, CLI flag registration
    is _progress.py, plus the AppConfig field and its external-config allowlist entry
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/app/config.py
  reason: original scope named a file that does not exist; the real reconcile module
    is src/frob/tickets/_reconcile.py, dispatch is _lifecycle.py, CLI flag registration
    is _progress.py, plus the AppConfig field and its external-config allowlist entry
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/app/_config_external.py
  reason: original scope named a file that does not exist; the real reconcile module
    is src/frob/tickets/_reconcile.py, dispatch is _lifecycle.py, CLI flag registration
    is _progress.py, plus the AppConfig field and its external-config allowlist entry
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/test_ticket_reconcile.py::TestReconcileStripStaleFields::test_dry_run_reports_but_does_not_strip
- tests/test_ticket_reconcile.py::TestReconcileStripStaleFields::test_apply_strips_stale_fields
- tests/test_ticket_reconcile.py::TestReconcileStripStaleFields::test_second_run_is_a_no_op
- tests/test_ticket_reconcile.py::TestReconcileStripStaleFields::test_clean_ticket_is_untouched
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5305
branch: t-5305
---
Found while working T-5292 (CI: test_real_repo_ledger_is_tick008_clean): ~35 live tickets carry stale 'branch'/'worktree' extra fields written by an older ledger writer; TICK008 flags them, hand-editing tickets/*.md is forbidden, and no frob verb can strip them. Add a reconcile mode (or a one-shot migrate verb) that drops fields the current Ticket model does not declare, logs each id and field, commits once, and is idempotent; then T-5292's test passes on the real ledger. Positive control: a fixture ledger with one record carrying an extra field is cleaned and a second run is a no-op.