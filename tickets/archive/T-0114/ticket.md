---
id: T-0114
title: 'threat E: std.perf/reliability/compat anti-pattern families'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0113
parent: T-0109
tier: ticket
sprint: null
scope:
- docs/strata/**
- src/frob/strata/**
- strata-core/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_threat.py::TestQualityFamilies::test_web_performance_baseline_is_satisfied
- tests/unit/strata/test_threat.py::TestQualityFamilies::test_reliability_baseline_is_satisfied
- tests/unit/strata/test_threat.py::TestQualityFamilies::test_web_quality_security_baseline_is_satisfied
- tests/unit/strata/test_threat.py::TestQualityFamilies::test_missing_out_of_scope_entry_is_a_violation
- tests/unit/strata/test_threat.py::TestQualityFamilies::test_quality_catalog_never_leaks_into_owasp_top_10_view
- tests/unit/strata/test_threat.py::TestQualityFamilies::test_dynamic_orm_scope_reuses_the_sql_capability_join
- tests/unit/strata/test_threat.py::TestQualityFamilies::test_no_kind_field_asserted_out_of_scope_entries_have_reasons
designated_repro_test: null
acceptance:
- text: GIVEN Public immutable content served from origin not cdn THEN refutes; GIVEN
    a large uncompressed structured flow THEN fires; GIVEN a synchronous over-budget
    single dependency THEN refutes
  evidence: []
threat: null
component: null
---
quality families per the threat.md table: dynamic-ORM-scope, route-authz, stored-XSS multi-hop, CORS-wildcard, uncompressed-JSON, one-at-a-time-writes, single-dep-bottleneck, un-optimistic-render, non-static-hosting. Reuses A-C. threat.md phase E.