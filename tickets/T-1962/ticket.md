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

## Done report

frob:no-behavior-change reason="pure structural split of two over-length functions (_walk_dead_ranges into itself plus _track_assign_locals/_fold_if_branch; _dead_only_names into itself plus _collect_trees_and_const_funcs/_dead_lines_by_file/_dead_candidate_names/_transitive_dead_names) -- every extracted helper is a verbatim cut-and-paste of the original inline code with parameters/mutation threaded through identically, no logic changed, no new branch, no reordering. Proven, not just claimed: frob check --only dead_symbols before and after this change reports byte-identical gate:DEAD counts (0 errors, 3 warnings, 42 waived), and the existing 12-test TestDeadSymbolGate suite (including the two tests that specifically exercise _walk_dead_ranges/_dead_only_names's constant-fold behavior) passes unmodified against both."

ARCH001 x2 in src/frob/gates/_dead_symbols.py, introduced by T-1881's land
(gate:ARCH is repo-wide under --ticket, so it did not block that land):
- _walk_dead_ranges: 65 lines (threshold 60)
- _dead_only_names: 106 lines (threshold 60)

Per the coordinator's explicit caution (T-1881 shipped a real, measured
dead-code-detection improvement; a later EXTENSION attempt was reverted
for producing 114 false positives on unchanged code), treated this
module as sensitive: the fix is a PURE structural split along the seams
the ticket itself named, with zero logic change.

_walk_dead_ranges (per-statement-kind branches, per the ticket's own
suggestion): extracted the single-target-name Assign bookkeeping into
_track_assign_locals(stmt, const_funcs, local, bool_locals) -> None
(mutates in place, verbatim body) and the ast.If handling into
_fold_if_branch(stmt, index, stmts, const_funcs, local, bool_locals,
dead_ranges) -> bool (verbatim body, returns whether the caller must
stop iterating -- same shape as the original `return` statement it
replaces). The outer loop now only sequences these two calls plus the
pre-existing nested-scope and fold-ifexps steps.

_dead_only_names (already loosely separated by blank lines/comments,
per the ticket): extracted _collect_trees_and_const_funcs (file-parsing
loop), _dead_lines_by_file (per-file _walk_dead_ranges pass), the
formerly-nested _scan_names closure promoted to module-level
_dead_candidate_names (same body, now takes trees/dead_lines_by_file as
explicit params instead of closing over them), and _transitive_dead_names
(the bounded fixed-point loop). _dead_only_names itself is now an
8-line sequencing body.

VERIFICATION (the coordinator's required proof):
  BEFORE (baseline, recorded before touching the file):
    frob check --only dead_symbols -> gate:DEAD 0 errors, 3 warnings, 42 waived
  AFTER:
    frob check --only dead_symbols --only archgate ->
      gate:DEAD  0 errors, 3 warnings, 42 waived   (IDENTICAL)
      gate:ARCH  0 errors, 0 warnings, 64 waived   (was 2 errors before the fix)
  tests/test_gates.py::TestDeadSymbolGate (12 tests, unmodified) all pass
  against the new code, including
  test_call_site_in_constant_folded_dead_branch_is_flagged and
  test_call_site_in_constant_folded_local_var_dead_branch_is_flagged,
  which directly exercise the const-fold path both extractions touched.

Filed: none.

### Changed
```
 tickets/T-1962/ticket.md | 7 ++++++-
 1 file changed, 6 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_constant_folded_dead_branch_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_constant_folded_local_var_dead_branch_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_call_site_in_live_branch_is_not_flagged_by_constant_fold` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeadSymbolGate::test_dead_caller_two_hops_deep_still_misses_confirming_open_defect` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 1 error(s), 868 warning(s), 705 waived
- error-findings: PRE001@tickets/T-1962
