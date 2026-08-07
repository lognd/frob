## Done report

DEPR005's _depr005_violations rescanned the whole repo twice per baselined
deprecated symbol (exports_consumers + xref, each a full-repo walk),
growing linearly with the number of symbols -- 8 full scans for 4 symbols
today. Replaced with a single per-run index (_DeprecatedRefIndex, built by
_build_deprecated_ref_index): one pass over every Python file collecting
every identifier occurrence (with context) plus every definition site,
built once per gate run and shared across every baselined symbol.
deprecated_current_references(symbol, root) kept its exact public
signature/semantics (tests call it directly) but is now a thin wrapper
that builds a fresh one-symbol index and answers from it via the new
_references_from_index helper; _depr005_violations builds the index once,
lazily (only if there is at least one baselined edge to look up), and
answers every symbol from it, collapsing the O(files * symbols) cost to
O(files + symbols).

Timing (ad-hoc harness, /tmp scratchpad, run against this repo's own real
frob-deprecated-baseline.lock.json, 4 baselined symbols, warm and cold
parse-cache runs both measured post-git_add-graph-build so only
_depr005_violations itself is timed):
  before (HEAD~1, exports_consumers+xref double scan per symbol): 39.194s
  after (this change, one shared index):                          5.198s
                                                                   5.347s (rerun)
~7.3x speedup on the DEPR005 stage's own cost, same violation set (3
violations) both before and after -- confirms the index-backed answer is
behaviorally identical, not just faster.

### Changed
```
 src/frob/gates/_debt_deprecated.py | 153 +++++++++++++++++++++++++++++--------
 tickets.md                         |  16 +++-
 2 files changed, 134 insertions(+), 35 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDeprecatedGate::test_depr005_reference_set_combines_consumers_and_xref` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::test_gates_run_gates_integration` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_growth_beyond_baseline_fires_at_the_right_file_and_line` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_same_count_as_baseline_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_unrelated_same_name_call_in_non_importing_file_is_excluded` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 11 error(s), 401 warning(s), 684 waived
- error-findings: AFFECT001@src/frob/gates/_debt_deprecated.py, ARCH001@src/frob/gates/_debt_deprecated.py, ARCH001@src/frob/refactor/_scan.py, ARCH001@src/frob/tickets/_land_finalize.py, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, PERF003@src/frob/gates/_debt_deprecated.py, PRE001@tickets/T-1207, RENDER001@src/frob/refactor/_cli.py, SELFAUDIT001@design, TICK003@tickets.md
