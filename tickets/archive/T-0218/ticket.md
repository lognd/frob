---
id: T-0218
title: graph build reports edges=0 on cache-hit runs while the loaded graph has edges
state: done
kind: ux
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestBuildIncremental::test_cache_hit_build_reports_real_edge_count
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (gap 14): build counter means newly-parsed edges, so cache-hit runs print edges=0 followed later by load_graph: ... 60 edges. Rename the counter (new_edges=) or report total after load.