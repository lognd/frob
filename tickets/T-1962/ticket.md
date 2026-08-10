---
id: T-1962
title: 'ARCH001: _walk_dead_ranges/_dead_only_names exceed the 60-line threshold (T-1881
  residue)'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_dead_symbols.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_constant_folded_dead_branch_is_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_constant_folded_local_var_dead_branch_is_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_live_branch_is_not_flagged_by_constant_fold
- tests/test_gates.py::TestDeadSymbolGate::test_dead_caller_two_hops_deep_still_misses_confirming_open_defect
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Unscoped `frob check --only gates` re-measure after T-1881/T-1959
surfaced 2 ARCH001 errors introduced by T-1881's landed constant-folding
fix, not caught at land time because gate:ARCH was repo-wide (not
diff-scoped) under `--ticket` and evidently did not block that land:

- src/frob/gates/_dead_symbols.py::_walk_dead_ranges -- 65 lines
  (threshold 60)
- src/frob/gates/_dead_symbols.py::_dead_only_names -- 106 lines
  (threshold 60)

Both are mechanical over-length, not correctness issues -- split each
into smaller helpers along its existing natural seams (e.g.
_walk_dead_ranges's per-statement-kind branches; _dead_only_names's
package-wide const_funcs collection vs. the per-file dead-range walk vs.
the transitive fixed-point loop, already loosely separated by blank
lines/comments in the current body).