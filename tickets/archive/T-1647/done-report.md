## Done report

Natives confirmed built and healthy in this worktree before any measurement (strata_core/frob_core import cleanly from .venv; make core ran clean). Baseline unscoped gate:PERF matched the brief's stated 47 unwaived warnings exactly.

Classified PERF011 first per the brief's own hint (largest cluster). Manually read all 31 live findings against their real source: 22 were a genuine rule-level false positive -- the detector flagged a repo-scan call (iter_files/xref/exports_consumers) the instant ANY for/while token had appeared earlier in the flattened token stream, with no notion of what the call sits inside. The dominant shape was `for x in iter_files(...):` -- the repo-scan call IS the loop's own iterable expression, evaluated exactly once to build the iterator, never "once per iteration" the way the mined T-1207 shape (a call inside the loop body) is. One case (tests/integration/test_integration.py) was a variant: an unrelated genexpr's own for-clause tripped the flag for a later, entirely un-looped call.

Fixed PERF011 at the rule level (src/frob/perf/_hotpath_smells.py::_perf011_repo_scan_in_loop): track bracket depth so a comprehension/genexpr's own for-clause never sets loop-context, and exempt a repo-scan call landing in the FIRST depth-0 loop's own header (provably a single evaluation). A call in a later/nested loop's own header still fires -- verified against the real nested case (src/frob/vet/_capability_scan.py) which stayed correctly flagged. Added 3 new regression tests, all 16 tests in the file pass. Unscoped gate:PERF: 47 -> 27.

2 residual PERF011 findings (src/frob/bind/__init__.py's scan_bindings/scan_sources) are a disclosed, different false-positive shape the token-only fix cannot resolve: two SIBLING top-level loops (not nested), which a flat token stream with no indent/dedent markers cannot distinguish from real nesting. Waived per-site with that specific reason.

PERF013 (src/frob/gates/_cache_gate.py::_scan_function_reads) was genuine debt: two separate ast.walk(node) passes over the identical tree. Merged into one walk with a type-dispatched body. Verified via tests/test_cache_gate.py (4/4 pass).

PERF008's 3 remaining findings all matched this repo's own already-established precedent exactly (8 sibling findings already waived under the identical reasoning). Waived per-site.

PERF005: 1 of 3 in scope (src/frob/vet/_taint.py::_assigned_names) got the frob:invariant terminates annotation the rule asks for, matching existing precedent. The other 2 (frob-core/src/extract.rs) are Rust, outside this ticket's declared scope -- disclosed to the follow-up ticket.

PERF014's 9 remaining findings were NOT fixed. A brief 2-site spot check found the SAME systemic flaw class PERF011 had (sibling-loop count inflation). Needs the same audit-then-fix treatment, not attempted here due to time.

Filed T-1649 for the full disclosed remainder.

ARCH001 regression caught and fixed in-flight: the PERF011 fix's own docstring pushed the function past the 60-line threshold; moved rationale to a module-level comment, re-verified archgate clean.

Verified before finishing: frob check --only test/archgate/coverage/sys --ticket T-1647 all clean; frob check --land-parity clean; git diff main --diff-filter=D --stat empty; FROB_NO_GATE_CACHE=1 re-measurement confirms the 47 -> 20 unwaived-warning delta is stable.

### Changed
```
 src/frob/arch/_ffi.py                  |  1 +
 src/frob/bind/__init__.py              |  2 +
 src/frob/gates/_cache_gate.py          | 56 ++++++++++++++---------
 src/frob/perf/_hotpath_smells.py       | 63 +++++++++++++++++++++-----
 src/frob/serve/_watch.py               |  1 +
 src/frob/vet/_taint.py                 |  1 +
 tests/test_serve_watch.py              |  1 +
 tests/unit/perf/test_hotpath_smells.py | 69 +++++++++++++++++++++++++++++
 tickets.md                             | 81 +++++++++++++++++++++++++++++++++-
 9 files changed, 241 insertions(+), 34 deletions(-)
```

### Evidence
- `tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_does_not_fire_when_scan_is_the_loops_own_iterable` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_does_not_fire_when_earlier_loop_is_an_unrelated_genexpr` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_fires_when_scan_is_a_nested_loops_own_iterable` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_fires_on_pre_fix_shape` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_does_not_fire_when_scan_is_hoisted` (pytest node id, verified passing when recorded)
- `tests/test_cache_gate.py::TestMemoizedReadCoverage::test_uncovered_read_fires` (pytest node id, verified passing when recorded)
- `tests/test_cache_gate.py::TestT1454RegressionShape::test_env_read_fires` (pytest node id, verified passing when recorded)
- `tests/test_serve_watch.py::TestWatchTick::test_watch_tick_never_disagrees_with_pull_signal` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 0 error(s), 2917 warning(s), 850 waived
- error-findings: none (measured, zero errors)
