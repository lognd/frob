---
id: T-draft-e03cfa51
title: 'ticket close: hardcoded 600s own-obligations check budget refuses under fleet
  load'
state: queued
kind: bug
origin: agent
created: '2026-09-25'
priority: high
parent: T-5630
tier: ticket
sprint: null
runs_last: false
milestone: v0.535.0
flavour: null
due: null
rank: null
points: 3
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
scope:
- src/frob/app/ticket_runner/_close_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working E3 (T-5776, ledger-tiers). frob ticket close spawns 'frob check --only gates' internally with a hardcoded timeout=600 (src/frob/app/ticket_runner/_close_cmd.py:_own_obligations_diff_findings, guarded_subprocess_run call, no CLI flag or env var override exists) to verify COV001/SELFAUDIT001 own-obligations before allowing the DONE transition. Under fleet-wide load the spawned check cannot finish inside 600s, so close refuses with OwnObligationsUnclean every time -- reproduced twice closing T-3611 (uptime 1-min load ~15 on the first attempt, ~13 on the second after a brief dip to ~8 mid-attempt), both times ending in: 'process: spawn of [...frob, check, --only, gates] exceeded its timeout=600 budget' then 'ticket close: T-3611 frob check --only gates refused to spawn (Timeout...) -- cannot verify T-1384 own-obligations, refusing to close on unverifiable evidence' then 'ERROR: close failed: OwnObligationsUnclean'. Fix: derive the budget from the same admission/worker accounting frob check already uses (_compute_admitted_workers) instead of a bare literal, or honour a --check-timeout flag / FROB_CHECK_TIMEOUT env var override, and log the budget actually chosen so a future repro is a one-line read instead of a source dive.