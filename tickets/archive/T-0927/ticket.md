---
id: T-0927
title: 'EPIC: frob check performance -- audit, quick wins, Rust hot-path migration'
state: done
kind: feature
origin: human
created: '2026-07-26'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- docs/audits/check-performance.md
- tests/unit/perf/test_serial_pools.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/perf/test_serial_pools.py
  reason: 'docs-scoped epic: evidence test file per D-02 route'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_gates.py
  reason: 'docs-scoped epic: second evidence test file per D-02 route'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/perf/test_serial_pools.py::TestInstallSerialPools::test_with_serial_pools_worker_is_majority_attributed
- tests/test_gates.py::TestProcessPoolGates::test_open_process_pool_preloads_forkserver_when_available
designated_repro_test: null
threat: null
component: null
---
User directive 2026-07-27: agents and the coordinator repeatedly kill/timeout frob check (full run measures 90-300s+ under load; today's foreground caps forced constant chunking, orphaned xdist fleets, and TEST016/done-report friction). Audit frob check performance end to end and, where the audit proves it out, move hot paths to Rust (frob_core / strata_core natives via the T-0864 frob natives build infra). Seed data from today's gate-summary timings on this repo (idle): archgate 10-20s, test 13-28s, sys 6-12s, perf 8-12s, coverage 5-11s, pii_structural 5-9s, dead_symbols 4-7s, secrets 3-5s, refs 2-3s, tickets 2-5s; under 8-agent load a full check exceeded a 5-minute timeout. Children carry the work; this epic closes when a full frob check on this repo runs comfortably inside the 120s agent foreground budget.