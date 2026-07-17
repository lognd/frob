---
id: T-0029
title: 'graph: concurrent build_graph on shared cache.db raises disk I/O error; add
  busy_timeout'
state: done
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/graph/cache.py
evidence:
- tests/test_graph.py::TestConcurrentCache::test_concurrent_connections_do_not_raise_disk_io
attachments: []
---

REMAINING (kept open beyond the connection fix): fully race-free
concurrent build_graph on one cache.db needs a build lockfile or
single-writer guard; WAL + busy_timeout fixes the hard disk-I/O-error
crash but overlapping schema rebuilds/commits can still return Err. A
lockfile is the follow-up.

## Done report

WAL journal mode + 30s busy_timeout in a shared _open() helper; the
connection-level disk-I/O crash is gone. Full race-free concurrent
build_graph (a build lockfile) remains open in the ticket body.
