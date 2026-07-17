---
id: T-0020
title: 'Gate convergence: collection oracle, evidence matching, fixture excludes'
state: done
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/**
- tests/**
- invariants/**
- scripts/**
- pyproject.toml
evidence:
- tests/test_gates.py::TestSeverityOverrides::test_override_downgrades_and_ignores_garbage
- tests/test_prework_parity.py::TestCliStartRecordsGateCompatibleDigest::test_start_then_gate_is_clean
- tests/test_graph.py::TestCorruptCacheRecovery::test_garbage_cache_file_is_recreated
attachments: []
---

## Done report

frob check exits 0 on frob itself: collection oracle fixed (addopts
neutralization), parametrized evidence matching, COV001 test-code
exclusion, [gates.severity] implemented, PRE001 digest parity, corrupt
cache recovery, invariant evidence ids corrected, whole-tree ty clean.
901 warnings remain as tracked legacy debt (T-0013, T-0014).
