---
id: T-3703
title: WIRE001 call_pattern misses module-alias dotted calls for FUNCTION records
state: queued
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
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
WIRE001 flagged src/frob/graph/cache.py::get_root as unwired after T-3700 rewrapped its body (making it new-in-diff), but it has a real production caller at src/frob/graph/__init__.py:754: root_str = _cache.get_root(conn) via from frob.graph import cache as _cache. frob explore xref get_root finds it. Root cause: _wire_reach_patterns default call_pattern for a FUNCTION record is (?<![A-Za-z0-9_.]){short}\\s*\\( -- the negative lookbehind excludes a dotted call, so a module-alias dotted call (module_alias.func(...)) is never matched. The expanded dotted-call alternative is only enabled for METHOD records (instance.method(...)). A module-level function called as _mod.func(...) through an import alias is thus a WIRE001 false positive. Fix: allow a dotted module/alias prefix in the FUNCTION call_pattern too (or reuse the METHOD-record expanded pattern for FUNCTION records). Found while working T-3700.