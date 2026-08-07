---
id: T-0064
title: 'strata std.infra: store/cache/queue/cdn/balancer elaboration'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0050
parent: T-0051
tier: ticket
sprint: null
scope:
- docs/strata/**
- tickets.md
- strata-core/**
- Makefile
- .github/**
- design/litmus/**
- src/frob/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_cache_without_invalidation_is_err
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_ttl_and_staleness_must_agree
- tests/unit/strata/test_infra.py::TestCdnDesugar::test_cdn_unlimited_on_mutable_is_err
- tests/unit/strata/test_infra.py::TestCdnDesugar::test_cdn_tls_terminates_adds_declassify_boundary
- tests/unit/strata/test_infra.py::TestQueueDesugar::test_queue_delivery_propagates_to_outbound_flows_and_fires_diagnostic
- tests/unit/strata/test_infra.py::TestEndToEnd::test_cache_staleness_refutes_age_bound_claim
designated_repro_test: null
threat: null
component: null
---
Caches are derived views: mandatory source-of-truth + invalidation edge + staleness bound; queues carry delivery semantics; delivery x idempotency join; managed components skip tier-2.