---
id: T-5299
title: LANDPARITY001/T-2114 check ignores test-side frob:tests declarations (T-4710)
state: done
kind: bug
origin: human
created: '2026-09-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_land_parity.py
- tests/test_land_parity.py
- tests/gates_suite/test_land_parity.py
- tests/unit/test_land_parity_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_parity_gate.py
  reason: T-2114 doc/test-edge coverage lives here, the actual test file to touch
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
evidence:
- tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate::test_new_public_symbol_missing_both_directives_fires
- tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate::test_new_public_symbol_with_both_directives_is_quiet
- tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate::test_no_diff_is_quiet
- tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate::test_new_public_symbol_with_only_test_side_tests_edge_is_quiet
- tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate::test_new_public_symbol_with_neither_lexical_nor_test_side_edge_fires
designated_repro_test: tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate::test_new_public_symbol_with_only_test_side_tests_edge_is_quiet
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5299
branch: t-5299
---
_new_public_symbols_in_file_missing_doc_or_test_edge (LANDPARITY001/T-2114) only
scans the lexical comment block immediately above a new public symbol's def/class
for a frob:tests directive. It never consults the graph's derived reverse edge
from a test-side frob:tests declaration, which T-4710's redundant-test-declaration
convention promises is equivalent (a directive living on the TEST symbol,
targeting the production symbol, rather than duplicated on the production symbol
itself). Since T-5289 fixed fix_test010_redundant_test_declaration to correctly
DELETE the redundant production-side frob:tests line when a test-side twin
already exists, the pre-land Tier-A pass now legitimately removes those lines --
and this check then refuses the land with "has no frob:tests edge" for symbols
that always had real test coverage via the test-side declaration.

Observed refusals:
- T-5289's own land: fix_fmt002_noqa_strip, fix_test010_redundant_test_declaration
- T-5285's land: announce_shim, is_past_sunset

Fix: the check must accept a test-side frob:tests declaration that targets the
symbol, using the graph's already-derived edges (GraphSnapshot/build_graph),
not a second lexical scan for the reverse direction.