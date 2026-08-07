---
id: T-0201
title: 'selfconform self-match: pattern-catalog data files observed as live capabilities
  -- main red'
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_selfconform.py
- src/frob/strata/_effects.py
- src/frob/vet/_capability.py
- design/frob.strata
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/test_vet.py::TestFingerprintScan::test_own_catalog_file_excluded_from_directory_aggregation
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_covers_every_needle_table_module
designated_repro_test: null
threat: null
component: null
---
T-0153+T-0181 interaction, invisible to both branches (TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant skips without strata_core natives, so it only runs on main): 5 SYS100 violations -- stratamod 'fs' x2 (_cve_fingerprint.py:120/:190 needle literals), stratamod 'deserialize'+'sql' (extended kinds from catalog needles), vet 'html_render' (T-0181 jinja2 needles in _capability_registry.py). Root cause: self-conformance scans pattern-catalog DATA files as if their needle literals exercise capabilities -- the exact T-0151 self-match class. Fix: a single shared self-match exclusion (registry + fingerprint catalog + any future pattern-table file) applied consistently in BOTH vet aggregation (_is_self_path, already done piecemeal) and the selfconform scan paths (THREAT004 core + extended kinds); one source of truth, not per-file patches. Drift-lock: a test asserting the exclusion list covers every module that defines needle tables (registry-of-pattern-files), plus the real-gate test back to green. Do NOT declare fake capabilities on stratamod/vet in design/frob.strata -- the nodes do not exercise these capabilities; excluding descriptive data is the honest fix.