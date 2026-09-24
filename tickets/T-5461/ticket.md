---
id: T-5461
title: 'frob:tests edge: bare function id of a parametrized test does not resolve;
  refuse at fmt/dry-run, not at land'
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
Measured 2026-09-23: T-5325 was refused at the real land four times with "new public symbol has no frob:tests edge" although each symbol carried a frob:tests line. The cited target was `tests/unit/test_webapp_websec_headers.py::test_full_evidence_all_present`, a PARAMETRIZED test, so the bare function id is not a collected pytest node id and the edge resolver treats it as unresolved. A sibling symbol citing a non-parametrized test passed. Neither `frob fmt --directives` nor `frob ticket land --dry-run` reported the problem; only the real land did, costing four drain slots.

Fix (either, preferably both): the edge resolver accepts the bare function id of a parametrized test as resolving to all of its parametrizations; and the directive linter / dry-run refuses a frob:tests target that resolves to nothing at fmt time, listing the concrete collected ids that share the prefix.
