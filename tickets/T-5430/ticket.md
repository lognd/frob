---
id: T-5430
title: Wire WEBSEC117-122 (T-5308) into taint_gate's process job
state: dropped
kind: bug
origin: human
created: '2026-09-23'
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
scope:
- src/frob/gates/_taint_gate.py
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
found while working T-5308: frob.webapp._websec_headers_log.websec_headers_log_findings (WEBSEC117-122) is implemented, tested standalone (tests/unit/test_websec_headers_log.py), and documented (docs/modules/webapp-websec-headers-log.md), but is NOT yet folded into frob.gates._taint_gate.taint_gate's scan (the same call-site pattern T-5307's websec_sink_findings already uses). At T-5308 implementation time both plausible wiring files -- src/frob/gates/_taint_gate.py (leased by T-5311) and src/frob/gates/__init__.py (leased by T-5395) -- were held by other in-progress tickets, so the scope lease could not be acquired. Once those tickets land and free the leases, this ticket should: import websec_headers_log_findings in _taint_gate.py, call it alongside websec_sink_findings in taint_gate(), fold its findings into the returned Violation tuple (WARN-tier, same posture as WEBSEC101-106), and extend tests/unit/test_websec_headers_log.py (or a new test) with a TestTaintGateWebsecHeadersLogExtension positive-control test proving frob check --only gates actually reports a planted WEBSEC117 finding end to end.

## Drop reason
- 2026-09-23: superseded by taint-gate module discovery in T-5311
