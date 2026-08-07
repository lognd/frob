---
id: T-1072
title: 'arch: split src/frob/gates/__init__.py (12047 lines, T-0395 remainder tier
  1)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/test_gates.py
- tests/test_secrets_gate.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: 'The WAIVE-family split moved several symbols'' physical location from

    src/frob/gates/__init__.py to the new src/frob/gates/_waive.py. Every

    frob:tests/frob:describes directive that hardcoded the old

    src/frob/gates/__init__.py::<symbol> symref now fails DRIFT002 since the

    symbol no longer resolves at that path. Fixing these references (updating

    the module path component only, same symbol name) is a direct, mechanical

    consequence of the split itself, not new work -- widening scope to the

    handful of test/doc files carrying those directives so DRIFT002 can be

    cleared without leaving broken doc/test bindings behind.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_secrets_gate.py
  reason: 'The WAIVE-family split moved several symbols'' physical location from

    src/frob/gates/__init__.py to the new src/frob/gates/_waive.py. Every

    frob:tests/frob:describes directive that hardcoded the old

    src/frob/gates/__init__.py::<symbol> symref now fails DRIFT002 since the

    symbol no longer resolves at that path. Fixing these references (updating

    the module path component only, same symbol name) is a direct, mechanical

    consequence of the split itself, not new work -- widening scope to the

    handful of test/doc files carrying those directives so DRIFT002 can be

    cleared without leaving broken doc/test bindings behind.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/gates.md
  reason: 'The WAIVE-family split moved several symbols'' physical location from

    src/frob/gates/__init__.py to the new src/frob/gates/_waive.py. Every

    frob:tests/frob:describes directive that hardcoded the old

    src/frob/gates/__init__.py::<symbol> symref now fails DRIFT002 since the

    symbol no longer resolves at that path. Fixing these references (updating

    the module path component only, same symbol name) is a direct, mechanical

    consequence of the split itself, not new work -- widening scope to the

    handful of test/doc files carrying those directives so DRIFT002 can be

    cleared without leaving broken doc/test bindings behind.

    '
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestCoverageGate::test_waive002_known_gate_rule_is_not_flagged
- tests/test_gates.py::TestPlace001Gate::test_missed_following_binding_fires
- tests/test_gates.py::TestTestGate::test_match_waiver_prefix_reach_gated_to_package_scoped_rules
- tests/test_gates.py::TestCov002ScopeCoverage::test_active_ticket_own_scope_wins_over_a_broader_open_ticket
- tests/test_gates.py::TestDsl001::test_waive_reason_and_tests_kind_not_double_flagged
- tests/test_secrets_gate.py::TestFindsTokens::test_sec003_waiver_is_inert
- tests/test_waive_gate.py::TestWaive006Registration::test_waive006_gate_combines_both_channels
- tests/test_waive_gate.py::TestWaive007Registration::test_waive007_gate_combines_both_channels
- tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo
designated_repro_test: null
threat: null
component: null
---
Filed from T-0395 (failed as too large for one pass). Split
src/frob/gates/__init__.py (12047 lines, the single largest offender by
a wide margin) into per-gate-family submodules under src/frob/gates/
(mirroring the existing _pii_structural.py/_docblocks.py/_secrets.py/
_registry_exhaustiveness.py/_protocol_summary.py/_refs.py/_docptr.py
sibling-module pattern already established in this package) -- e.g. one
module per gate cluster (COV00x, WAIVE00x, TICK00x, DOC00x, TEST00x,
etc.), re-exported from __init__.py so `frob.gates.<gate_fn>` call sites
elsewhere keep working unchanged. This is a large, high-risk refactor
(thousands of lines, dozens of gate functions with cross-references) --
plan the split boundaries carefully before moving code, verify with the
full gates test suite (tests/test_gates.py) after each chunk, and land
incrementally rather than as one giant diff. large-file is unwaivable
(docs/modules/gates.md); real decomposition is the only path to zero.