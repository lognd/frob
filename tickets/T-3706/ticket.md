---
id: T-3706
title: 'cache: sibling connect loop crashes on bare sqlite3.DatabaseError (round 8)'
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
- src/frob/graph/cache.py
- tests/unit/test_graph_cache.py
- tests/unit/test_graph_build_lock.py
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
Round 8 of the cache two-process saga (T-3607/T-3623/T-3632/T-3634/T-3644/T-3654/T-3669/T-3700). Run 33680767948 macOS: sibling crashed silently on a bare sqlite3.DatabaseError ('file is not a database' shape) that every T-3634/T-3700 stale-reconnect handler only catches as sqlite3.OperationalError -- DatabaseError is the PARENT class, not a subclass, so it escapes uncaught. Fix: broaden the catch clauses to sqlite3.DatabaseError.