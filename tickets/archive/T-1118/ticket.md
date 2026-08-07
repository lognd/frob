---
id: T-1118
title: 'daemon: wire run_coverage_wait through the T-1097 daemon-owned coverage lease'
state: dropped
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/_coverage_wait.py
- src/frob/app/_daemon_proxy.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1097 shipped a daemon-owned named resource lease/semaphore primitive
(frob.serve._leases.ResourceLeaseManager, frob_lease_acquire/frob_lease_
release RPC methods) with connection-liveness release, proven against
real socket clients directly.

It did NOT rewire frob.testing._coverage_wait.run_coverage_wait's own
subprocess flow to acquire the coverage lock THROUGH this daemon RPC
instead of its existing file-lock layers (T-0322's per-worktree
fcntl.flock, T-1095's shared per-digest fcntl.flock) -- that wiring
touches frob.app's CLI-proxy layer (_daemon_proxy.query), which was
contended with T-1106's own src/frob/app/ work this wave and out of
T-1097's src/frob/serve/**/src/frob/testing/** scope.

Follow-on: wire run_coverage_wait (or a new coverage-specific daemon
client call) to acquire/release the "coverage" resource lease via the
daemon RPC when a daemon is reachable, falling back to the existing
file-lock layers when it is not -- mirroring frob.app._daemon_proxy.
query's own Ok(daemon)/Err(fallback) shape.

## Drop reason
- 2026-07-28: done by T-1126 (landed 9d606789): run_coverage_wait tries the daemon lease first with file-lock fallback; independent filing of the same follow-up