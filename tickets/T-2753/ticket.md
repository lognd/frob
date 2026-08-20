---
id: T-2753
title: WIRE001 call-graph resolver cannot see pytest fixture consumption via dependency
  injection
state: queued
kind: bug
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
WIRE001's static call-graph resolver flags a pytest fixture (test_app_runners_batch6.py's outside_view fixture, T-2486) as apparently-dead because fixture consumption happens via pytest's dependency-injection mechanism (declared as a test method parameter name), which the resolver cannot see as a call site. Currently worked around with a per-site frob:waive WIRE001 (this same site now carries a required follow_up= pointing here, T-2743's SC004 disposition). A proper fix would teach the resolver to recognize a symbol used as a fixture (any test function parameter matching a @pytest.fixture-decorated function's name in the same or an imported module) as wired, closing this blind spot for the whole test suite rather than one waiver at a time.