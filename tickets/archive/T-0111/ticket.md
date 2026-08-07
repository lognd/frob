---
id: T-0111
title: 'threat A: std.cwe catalog + weakness/capability grammar + THREAT001/003'
state: done
kind: security
origin: human
created: '2026-07-17'
priority: medium
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
- tests/unit/strata/test_threat.py::TestCatalogCompleteness::test_missing_entry_is_a_violation
- tests/unit/strata/test_threat.py::TestDischargeCompleteness::test_discharge_claim_that_evaluates_refuted_is_a_violation
designated_repro_test: null
acceptance:
- text: GIVEN an owasp-top-10 baseline WHEN a model omits a required weakness entry
    THEN THREAT001 fails; WHEN a fired weakness has no mitigation THEN THREAT003 fails
  evidence: []
threat: null
component: null
---
weakness/capability/out-of-scope grammar; baseline views; std.cwe pack as cited data (OWASP Top 10 subset); precondition matcher over model flows; THREAT001 catalog-completeness + THREAT003 discharge-completeness. Design-level only. threat.md phase A.
## Done report

Phase-A threat catalog per docs/strata/threat.md: CWE_CATALOG with the
charter's nine core-reframe entries (MITRE citations, capability_kind
per the capabilities-drag-in-obligations table; three entries carry
None with an in-line phase-B/C sink-taxonomy note), OutOfScopeEntry,
and the owasp-top-10 view (other views deliberately not stubbed so
THREAT001 cannot lie). THREAT001 check_catalog_completeness fails
closed on unknown views; THREAT003 check_discharge_completeness
requires a weakness:<cwe>:<node> claim at/above the catalog rung via
the real prover, never REFUTED, assumed-with-owner. evaluate_threats
is gate-agnostic; SYS-gate wiring deferred until after T-0080 (landed;
follow-up welcome under T-0109). Review round: redundant per-node sort
deleted (waiver removed) and the REFUTED path pinned by a live test
that drives evaluate_claims to REFUTED. Verified at merge: 288 strata
tests green, imports clean, main exit 0.