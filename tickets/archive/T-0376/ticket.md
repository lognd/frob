---
id: T-0376
title: 'Depth epic: real source resolution, compensating out-of-scope controls, full
  registry enforcement, advisories'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/
- src/frob/strata/
- docs/design/registry/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_threat.py::TestCaughtByIntegrity::test_fabricated_cwe_reference_fails_closed
- tests/unit/strata/test_threat.py::TestCaughtByIntegrity::test_honest_none_caught_by_never_fails
- tests/unit/strata/test_threat.py::TestCaughtByIntegrity::test_real_cwe_reference_resolves
designated_repro_test: null
threat: null
component: null
---
User directive (2026-07-20): four depth gaps to close. (1) VET must do ACTUAL SOURCE RESOLUTION not lexical: today only Python is binding/import/alias/scope-resolved (T-0328/0337); TS, Rust, C/C++ are pure needle-matching and CVE fingerprints are lexical for ALL langs -- aliased/renamed imports evade detection in every non-Python language. (2) OUT-OF-SCOPE threats must be CAUGHT ELSEWHERE: OutOfScopeEntry is id+reason only, no compensating-control reference, no verification -- an excused CWE may be caught nowhere. Require each out-of-scope entry to name where it IS caught and verify that control exists/fires. (3) REGISTRIES must be ACTUALLY IMPLEMENTED FULLY: catalogues are large (944 CWEs, 346 patterns) but enforcement covers ~30 CWEs / ~20 rule ids; pii(7)/secrets(3)/compliance(27) are thin; RECONCILIATION.md has undispositioned entries. Every catalogued registry entry must map to an enforced check OR a documented out-of-scope-with-compensating-control. (4) ADVISORIES: address the 74 frob-arch suggestions. Children to be filed per area.