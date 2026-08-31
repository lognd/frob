---
id: T-3522
title: Wire _save_unlanded_summary_cache into the reconcile path
state: queued
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_reconcile.py
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
src/frob/app/ticket_runner/_query.py::_save_unlanded_summary_cache's own docstring (and _load_unlanded_summary_cache's caller docstring, doable's read side) documents the intended production write path: frob.tickets._reconcile, after _unlanded_branch_work computes branches, should call _save_unlanded_summary_cache to populate the cache doable reads. That call was never actually added -- grep confirms frob.tickets._reconcile never references _save_unlanded_summary_cache or _UNLANDED_SUMMARY_CACHE at all. Found while reviewing DEAD001 for T-3521 (_save_unlanded_summary_cache is currently only exercised by tests/unit/test_app_runners_doable_stale_lease.py, never by production code). Wire the real call in _reconcile.py so the doc's own claim becomes true, or correct the docstring if the intended design changed.