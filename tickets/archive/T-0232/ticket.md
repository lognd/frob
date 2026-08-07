---
id: T-0232
title: per-gate timing attribution shared/wrong; concurrent frob runs contend on .frob
  db
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestRunJobsTimingAttribution::test_cpu_bound_neighbor_does_not_inflate_a_cheap_jobs_timing
- tests/test_graph.py::TestCacheModule::test_connect_readonly_rejects_writes_no_lock_contention
- tests/test_graph.py::TestConcurrentCache::test_connect_on_current_schema_does_not_block_on_a_held_write_lock
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 20: graphite shows secrets=39.71s sys=39.71s tickets=39.69s (identical; 3.6s when quiet) -- shared scan time is attributed to every gate; stages balloon ~56s while a frob vet runs concurrently in the same repo (db contention). Attribute shared scans once (report separately), and check .frob cache.db locking behavior under concurrent invocations (WAL was added once before -- verify it covers this path).