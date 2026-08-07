---
id: T-0143
title: 'std.cwe catalog: transcribe the cwe-top-25 view (and stub-free ASVS decision)'
state: done
kind: security
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_top_25_view_is_satisfied
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_top_25_view_has_25_members
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_top_25_view_not_merged_into_default_views
- tests/unit/strata/test_threat.py::TestCweTop25::test_missing_out_of_scope_entry_is_a_violation
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_top_25_catalog_never_leaks_into_owasp_top_10_view
- tests/unit/strata/test_threat.py::TestCweTop25::test_out_of_scope_entries_have_specific_nonempty_reasons
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_94_reuses_the_exec_capability_join
- tests/unit/strata/test_threat.py::TestCweTop25::test_memory_safety_entries_name_the_missing_kernel_concept
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_77_discloses_duplicate_coverage_of_cwe_78
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_94_fires_and_discharges_on_exec_capability
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_94_fires_and_is_undischarged_with_no_claim
designated_repro_test: null
threat: null
component: null
---
Phase A shipped the 9 charter core-reframe CWEs backing owasp-top-10 only; cwe-top-25 / owasp-asvs / cwe-1000 were deliberately not stubbed so THREAT001 cannot lie. User asks for fuller coverage. Scope: transcribe the current MITRE CWE Top 25 into WeaknessEntry rows -- each with real cite URL, accurate title, meaningful mitigation, capability_kind where the charter's instantiation semantics genuinely apply, and honest OutOfScopeEntry rows (with specific reasons) for entries whose preconditions the kernel cannot yet express (matching the T-0114 discipline). Add the cwe-top-25 view; extend tests: view completeness proves, per-entry data spot checks, and at least two new fired-obligation cases for newly-instantiable kinds. owasp-asvs/cwe-1000: make an explicit documented decision (transcribe, or keep unstubbed with rationale in threat.md) rather than silence. Pin the catalog to a named CWE release version per the charter's staleness-review requirement.