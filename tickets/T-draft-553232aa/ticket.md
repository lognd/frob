---
id: T-draft-553232aa
title: Wire a real frob.gates._seo_gate (SEO family discovery)
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
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
- src/frob/gates/_seo_gate.py
- src/frob/gates/__init__.py
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
found while working T-5374: docs/modules/webapp-seo.md defines no leaf-hook convention, so no live gate calls src/frob/webapp/_seo_tags.py's websec_findings hook (frob.gates._taint_gate only discovers frob.webapp._websec_* modules by name prefix, and _seo_tags does not match it). Mirror frob.gates._a11y_gate's pkgutil-discovery pattern (T-5323) for a new frob.gates._seo_gate over frob.webapp._seo_* modules, and register it in gates/__init__.py (_ALL_GATES, _CANONICAL_GATE_ORDER, _build_process_jobs, _KNOWN_GATE_RULES for SEO101-112). Coordinate with sibling SEO leaves (T-5365 spam, T-5362 crawl) since they hit the same gap.