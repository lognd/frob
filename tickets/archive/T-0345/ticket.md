---
id: T-0345
title: CWE_TOP_25_CATALOG pinned to 2023, two releases stale -- update to 2025 + add
  untranscribed ids (CWE-120/121/122/284/770/200)
state: done
kind: security
origin: agent
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_threat.py
- tests/**
- docs/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_200_matches_the_weaknesses_registrys_own_disposition
- tests/unit/strata/test_threat.py::TestCweTop25::test_buffer_overflow_trio_name_the_same_missing_bounds_model
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_639_reuses_the_sql_capability_join
designated_repro_test: null
acceptance:
- text: given MITRE's current (2025) CWE Top 25 Most Dangerous Software Weaknesses,
    when CWE_TOP_25_CATALOG/_CWE_TOP_25_IDS and its staleness pin are updated, then
    all 25 current ids are represented (as a reused WeaknessEntry, a new one, or an
    honest OutOfScopeEntry naming the missing kernel concept) and the pin references
    the 2025 list
  evidence: []
- text: the ~6 ids never transcribed at all (CWE-120 buffer copy w/o size check, CWE-121
    stack overflow, CWE-122 heap overflow, CWE-284 improper access control, CWE-770
    unbounded resource allocation, CWE-200 information exposure) are each classified
    (memory-safety group -> OutOfScope with the named missing model per the existing
    CWE-787 precedent; CWE-284/770/200 -> WeaknessEntry or OutOfScope with rationale)
  evidence: []
threat: elevation-of-privilege
component: null
---
Found by the security-corpus exhaustive research (docs/design/security-corpus.md, 2026-07-20): frob's CWE_TOP_25_CATALOG + _CWE_TOP_25_IDS + OUT_OF_SCOPE pair in src/frob/strata/_threat.py is pinned to the 2023 MITRE Top 25, now two releases stale (2024 and 2025 have shipped). Five 2025-list ids plus CWE-200 have never been transcribed. The module's own staleness-review rule (docs/strata/threat.md, 'pinned to a release ... staleness past a review bound is a gate warning') says to re-verify and bump, not leave stale. This is a real security-catalog coverage gap; the T-0343 exhaustiveness drift-lock against security-corpus.md's DENOMINATOR MANIFEST would catch it once wired, but the pin should be updated now. Reuse the existing WeaknessEntry/OutOfScopeEntry machinery and the CWE-787-style memory-safety-group rationale.