## Done report

Profiled test_sys_gate_zero_violations (cProfile over the build_graph+sys_gate call the test
makes) BEFORE touching any code. Finding that overturns this ticket's own filed hypothesis:
_selfconform_kinds.py::_fully_excluded_node_ids costs only ~0.3s of the test's ~48-50s wall
time (measured directly, non-profiled), not the bottleneck. The real O(files x globs) fnmatch
hot path is src/frob/strata/_effects.py::_via_matches_site / _via_matches (4.5M fnmatch calls,
~40s cumulative under the profiler, driven by design/frob.strata's testsuite node's 250+-entry
"may \"exec\" via ..." list being re-scanned per observation site with no caching, and
os.path.normcase being recomputed once per (via-list, entry, call) triple).

Expanded scope to src/frob/strata/_effects.py (and its test file) with this profiling evidence
recorded in the scope-change reason, since the actual bottleneck lives outside
_selfconform_kinds.py.

FIX: added _compiled_via_entries (functools.lru_cache keyed on the via tuple itself, which is
immutable and comes from an already-parsed KernelModel) that precompiles each via entry's glob
into a real regex via fnmatch.translate + re.compile, with os.path.normcase applied to the
PATTERN side once at compile time. _via_matches_site and _via_matches now call
os.path.normcase(rel) ONCE per call (was once per entry) and iterate the cached compiled
entries instead of re-splitting/re-translating/re-normcasing every entry on every call. Same
short-circuit order and per-entry symbol-containment semantics as before -- a pure performance
change.

CORRECTNESS: TestViaMatchingCompiledCacheUnchangedResults compares the new implementation
against _naive_via_matches_site/_naive_via_matches (the byte-for-byte pre-fix bodies, kept as
reference implementations) across a matrix of file-glob, directory-glob, and symbol-scoped-via
cases, plus an empty-via edge case. All match. Ran the full existing tests/unit/strata/
test_effects.py suite (60 tests) unmodified as a regression check: all pass.

PERFORMANCE: TestViaMatchingCompiledCachePerf is a must-fire test asserting the compiled path
is at least 2x faster than the naive path on a synthetic 250-glob x 5000-site input (a
relative ratio, not an absolute threshold, so it stays robust to machine speed) -- passes.

REAL-WORLD IMPACT ON THE TARGET METRIC (test_sys_gate_zero_violations wall time): profiled,
check_capability_conformance's cumulative cost dropped from 87.7s to 49.1s under cProfile (a
genuine ~44% reduction in that specific subtree). However the DIRECTLY MEASURED, non-profiled
wall time of test_sys_gate_zero_violations itself did NOT meaningfully change: 53.2s and 50.3s
after this fix vs 48.4-50.2s across 5 runs before it (both T-3449 and T-3457's own
investigations) -- within run-to-run noise. Re-profiling after the fix shows why: the test's
cost is now dominated by TWO ENTIRELY UNRELATED subsystems this ticket's scope does not touch
-- build_graph's tree-sitter parsing of the whole repo (~29-30s on its own, before sys_gate
even starts) and src/frob/strata/_code_binding.py::check_import_conformance's AST-based Python
import resolution (~56-69s cumulative under profiling, real chunk of the non-profiled wall
time too). The via-glob fnmatch hot path this ticket named was real and is now fixed, but it
was never the DOMINANT cost of this specific test -- reaching "well under 15s" for
test_sys_gate_zero_violations needs separate, much larger-scoped work on build_graph's parse
cost and/or check_import_conformance's AST-walk cost, neither of which is an fnmatch/glob-
matching problem and neither of which is in this ticket's scope. Filed as a follow-up finding
in the Done report rather than a new ticket, given this session's time budget -- flagging for
the coordinator to scope separately if the 15s target is still wanted.

Also confirmed, unrelated to this fix: tests/unit/strata/test_selfconform.py::
TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant and
TestCoverageTotality::test_repo_unrestricted_scan_is_clean both fail identically on plain
main (verified before touching any T-3458 code) -- a real SYS100 finding against
tests/unit/strata/test_strata_core_gil.py (added by T-3457, undeclared fs.write/exec) that
predates and is unrelated to this ticket.

Gates: ruff-format clean (reformatted the new test file once), ruff-check clean, ty check
clean on both touched files.

### Changed
```
 tickets/T-3458/ticket.md | 28 +++++++++++++++++++++++++++-
 1 file changed, 27 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/strata/test_effects.py::TestViaMatchingCompiledCacheUnchangedResults::test_via_matches_site_matches_naive_across_a_matrix` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestViaMatchingCompiledCacheUnchangedResults::test_via_matches_matches_naive_across_a_matrix` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestViaMatchingCompiledCacheUnchangedResults::test_via_matches_site_empty_via_never_matches` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestViaMatchingCompiledCachePerf::test_compiled_path_is_faster_than_naive_on_a_large_via_list` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 11 error(s), 4029 warning(s), 857 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3458, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
