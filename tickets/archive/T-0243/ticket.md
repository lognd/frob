---
id: T-0243
title: cache.db not invalidated across frob/parser upgrades
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- tests/**
- docs/modules/graph.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestBuildIncremental::test_fingerprint_bump_rebuilds
designated_repro_test: null
threat: null
component: null
---
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (medium): a stale cache served 2830 symbols where a fresh parse of identical sources gave 3007 -- cache survived a frob upgrade with changed parser behavior. Include the frob version + grammar/parser fingerprint in the cache key so any upgrade invalidates cleanly. Regression: bump a fake version constant in test, assert cold rebuild.