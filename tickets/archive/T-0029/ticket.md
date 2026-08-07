---
id: T-0029
title: 'graph: concurrent build_graph on shared cache.db raises disk I/O error; add
  busy_timeout'
state: done
kind: bug
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestConcurrentCache::test_concurrent_connections_do_not_raise_disk_io
designated_repro_test: null
threat: null
component: null
---
REMAINING (kept open beyond the connection fix): fully race-free
concurrent build_graph on one cache.db needs a build lockfile or
single-writer guard; WAL + busy_timeout fixes the hard disk-I/O-error
crash but overlapping schema rebuilds/commits can still return Err. A
lockfile is the follow-up.