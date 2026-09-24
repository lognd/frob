---
id: T-5475
title: WEBSEC120 positive fixture fires zero findings (webapp-owned)
state: queued
kind: bug
origin: agent
created: '2026-09-24'
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
Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing:
tests/unit/test_websec_headers_log.py::test_websec_headers_log_findings_fixture[websec120_positive-WEBSEC120-True]

The WEBSEC120 positive fixture (websec120_positive) fires ZERO findings
for rule WEBSEC120 where the test's MUST-FIRE positive control expects
>=1 (AssertionError: (); assert 0 >= 1).

Both the test file and the production symbol under test
(src/frob/webapp/_websec_headers_log.py::websec_headers_log_findings, per
the file's own frob:tests directive) are inside src/frob/webapp/** --
OUT of touch-scope for this drain (other-agent-owned). Filed and handed
off whole, not fixed here.
