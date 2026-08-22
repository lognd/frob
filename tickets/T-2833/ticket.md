---
id: T-2833
title: Split frob.tickets._leases's worktree-sweep family into _worktree_sweep.py
state: queued
kind: feature
origin: human
created: '2026-08-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
- src/frob/tickets/_worktree_sweep.py
- design/frob.strata
- src/frob/app/worktree_runner.py
- src/frob/app/ticket_runner/_rapid_sweep.py
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
frob.tickets._leases.py (3587 lines) has a real, investigated seam: the worktree-sweep family (sweep_worktrees, remove_worktree, _WorktreeVerdict, _sweep_verdict_for_worktree, _kept_*, _worktree_is_clean, _worktree_head_age_seconds, _list_agent_worktrees, _is_agent_worktree_path, _WorktreeSweepError -- roughly lines 3065-3502) is consumed by a distinct CLI surface (frob.app.worktree_runner, frob.app.ticket_runner._rapid_sweep) than the lease-CRUD/ledger-commit machinery the rest of the module serves.

Extraction into a new frob.tickets._worktree_sweep module was rejected in T-2822 (LARGE001 batch 2) purely on scope grounds:

1. A new source file performing git-worktree-remove/fs-stat operations needs its own capability grant in design/frob.strata's fs.write/fs.read/env declarations (lines ~1263/1274/1275 currently enumerate _leases.py by name) before SYS100/SYS003 will accept it -- design/frob.strata was outside T-2822's declared scope.
2. frob.tickets._leases.py would need to keep re-exporting sweep_worktrees/remove_worktree for its existing external importers (frob.app.worktree_runner, frob.app.ticket_runner._rapid_sweep both do `from frob.tickets._leases import sweep_worktrees`/`remove_worktree` directly) -- straightforward, but still needs those two call sites' import path double-checked post-split.

This is a legitimate real split (not a T-1651-style waive candidate) -- scope it explicitly to include design/frob.strata plus the new _worktree_sweep.py file, and land it as its own ticket.
