---
id: T-3699
title: 'macOS flake: test_daemon_proxy_lease_t1276 Unreachable in run 33625622797'
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
- tests/unit/test_daemon_proxy_lease_t1276.py
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
CI run 33625622797 (macOS leg): tests/unit/test_daemon_proxy_lease_t1276.py
::TestDaemonLease::test_round_trip_acquire_call_release_close failed with
Err(ProxyReason.Unreachable) on the SECOND try_daemon_lease call (which
expects the capacity=1 resource to be exhausted and return Unreachable
for a DIFFERENT reason -- a lease-already-held rejection, not a genuine
connection failure).

Triaged as part of T-3692 (win32 round 22)'s Part C: this test exercises
frob.daemon's unix-socket lease server (_start_daemon/try_daemon_lease/
_LeaseConnection), entirely unrelated to T-3689/T-3692/T-3693's touched
files (frob.check, frob.process._lock/_derived_lock/_guard/_pid_liveness,
tests/conftest.py, tests/unit/test_check_admission.py, .github/workflows/
ci.yml) -- no overlap in module or code path. Not fallout from those
changes. Likely a socket-server-startup-race flake (server thread not
yet listening when the client connects, or a timing-sensitive capacity
check) given the shape of the failure (Unreachable on what should be a
deterministic capacity-exhausted rejection) -- needs its own
investigation, out of T-3692's declared scope.

References: T-3692 (found while triaging its Part C).