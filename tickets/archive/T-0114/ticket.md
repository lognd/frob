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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/strata/**
- src/frob/strata/**
- strata-core/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense QUALITY_CATALOG phase-E rationale into T-0114 body
  actor: logan
  at: '2026-09-19'
  old_length: 247
  new_length: 1983
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
anchor: false
anchor_reason: null
land_commit: null
---
quality families per the threat.md table: dynamic-ORM-scope, route-authz, stored-XSS multi-hop, CORS-wildcard, uncompressed-JSON, one-at-a-time-writes, single-dep-bottleneck, un-optimistic-render, non-static-hosting. Reuses A-C. threat.md phase E.

<!-- narrative-moved:src/frob/strata/_threat_catalog_quality.py:15:T-0114 -->
frob:doc docs/strata/threat.md#beyond-security-the-anti-pattern-families
Phase E (T-0114, docs/strata/threat.md#phasing item E): the anti-pattern
families table's rows that map onto EXISTING kernel detectables with NO
new precondition logic -- a `capability_kind` join THREAT002/THREAT003
already run (dynamic ORM scope reuses the SAME `sql` capability CWE-89
fires on, just a different cited id/mitigation), or a citation-only entry
(`capability_kind=None`, the CWE-22/352/798 precedent above) whose actual
firing/discharge lives in another already-shipped module -- capacity/
budget arithmetic (T-0066) for the single-dependency-bottleneck row, the
std.infra immutable/cdn machinery for the static-hosting row -- so THREAT001
catalog completeness can cite and prove baseline coverage of them without
THREAT002/THREAT003 re-detecting what those modules already refute.
Kept in a SEPARATE tuple from `CWE_CATALOG` (not appended to it) so the
`owasp-top-10` view -- built directly from `CWE_CATALOG`'s ids above --
never silently grows to include non-OWASP quality rows; a caller checking
the quality baseline passes this catalog explicitly.

Stored XSS (the table's third security-family row) needs NO catalog
addition at all: `_discharges_as_chokepoint`'s `NoFlow(src=foreign,
dst=node_id)` is evaluated over `reachable`, which is already transitive
-- a foreign flow through an intermediate store to an `html_render` sink
is the SAME multi-hop path the existing CWE-79 entry already covers, so
the persistent/two-hop variant is the SAME obligation, not a new one
(disclosed here rather than duplicated as a second entry with the same
precondition shape).