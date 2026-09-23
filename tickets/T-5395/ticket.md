---
id: T-5395
title: 'test_every_registered_rule_has_a_liveness_fixture: 249 reserved WEBSEC/COMPLY/A11Y/SEO/WEBPERF/SQL
  ids from T-5301 lack liveness fixtures'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/gates_suite/test_sys_rule_liveness.py
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
CI run 35863437945 (ubuntu+macos, dev 08b02016db); re-verified failing on current dev tip: tests/gates_suite/test_sys_rule_liveness.py::test_every_registered_rule_has_a_liveness_fixture fails -- T-5301 added the WEBSEC/COMPLY/A11Y/SEO/WEBPERF/SQL rule-id ranges to _KNOWN_GATE_RULES as a RESERVED block (placeholder comments naming the future ticket, same shape as PERF015-018's T-5136 reservation), but this liveness test has no exemption mechanism for reserved-but-unimplemented ids and expects every registered id to have a real fixture proving it can actually fire. Decide using the gate's own rules (read test_sys_rule_liveness.py's fixture-discovery logic and check whether PERF015-018's T-5136 reservation already has a working exemption precedent to copy) whether reserved ids need a registry-level exemption flag or genuinely need liveness fixtures -- do not blanket-skip the whole test or wildcard-exempt the range without checking the PERF015-018 precedent first.