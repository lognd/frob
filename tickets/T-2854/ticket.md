---
id: T-2854
title: 'malformed-directive false-positive: docstring prose containing ''frob:waive
  reason'' parsed as an attribute'
state: queued
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_coordinator_scripts.py
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
Found during T-2846's land: tests/unit/test_coordinator_scripts.py:5110's docstring prose (T-2845's added test) contains the substring 'frob:waive reason still parses as one directive and still binds,' -- the directive scanner appears to treat this prose as an attempted frob:waive directive and reports 'malformed directive: bad attribute syntax'. This is a WARNING, not currently gate-blocking, but is either (a) a real directive-scanner false positive that should not fire inside a docstring/comment quoting the DSL by name, or (b) confirms directive scanning is comment-scoped correctly and the fix is simply to reword the docstring to avoid the substring. Fix by rewording the docstring in the smaller-scope case; if the scanner is firing outside comments entirely, that is the larger and more concerning finding.