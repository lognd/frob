## Done report

PREMISE CORRECTION (recorded here so nobody re-derives it): this ticket
was originally filed on the theory that finding identities carry
ABSOLUTE paths while attribution measures repo-relative paths, so a
match was structurally impossible. That premise is FALSE, disproved
directly during investigation: `frob verify explain "ARCH001:scripts/
fleet_status.py"` (a repo-relative identity, no absolute-path involved
at all) attributed CLEANLY -- but to the WRONG commit, through a
reachability path that ran through symbols the attributing land's own
test file does not call. A second, cleaner reproduction confirmed it:
`frob verify explain "E402:tests/test_ticket_leases.py"` (one of the
ticket's own two original example findings) also attributed to the same
unrelated land, via `test_clean_root_is_a_no_op -> tests/test_ticket_
leases.py::_run` -- a function that test never calls.

REAL MECHANISM. `frob.graph.callgraph._ordered_private_callees`/
`_resolve_edges` (used by `build_reference_graph`, which `frob.verify.
_attribution._load_snapshot_and_call_graph` called before this fix)
resolve a called bare name via `by_name.get(name, ())`, where `by_name`
(`_short_name_index`) is a codebase-wide index keyed on SHORT NAME ONLY.
For every candidate sharing that name, in ANY file, an edge is added --
the candidate's own file path (`_cand_path`, right there in the tuple)
is unpacked and discarded, never checked. Confirmed at scale: `git grep
-c "^def _run(argv"` over tests/**/*.py finds 17 independent
definitions; `_commit_all` has 18. This is a deliberate, common test-
fixture convention in this repo (mirrored explicitly across several test
files' own docstrings), not an accident -- and every single one of those
same-named pairs is a live false-attribution hazard under the old
resolution rule. This is ALSO the true root cause of the original
`commit=None` findings this ticket was filed against: `_attribution.py`'s
own documented "zero or MORE THAN ONE candidate reaching = unattributed"
rule fired correctly once a collision inflated the reaching-candidate
count past one -- the rule was right, its graph input was wrong.

WHY NOT FIXED AT THE SHARED PRIMITIVE. `build_reference_graph`'s over-
inclusive resolution is DELIBERATE and SAFE for its documented original
consumer, T-0422's dead-symbol gate ("is this symbol referenced anywhere
at all") -- an extra fabricated edge there only means fewer false dead-
code positives, never a false accusation. Narrowing it globally would
risk resurrecting dead-symbol false positives repo-wide to fix an
attribution-only problem, and was explicitly ruled out by the
coordinator before implementation began.

FIX. Added `build_reference_graph_module_scoped` (src/frob/graph/
callgraph.py) alongside `build_reference_graph`, sharing the same
`_parse_package`/`_short_name_index`/`_referenced_names` extraction (no
duplicated parsing logic) but with its own resolution rule: a cross-file
private candidate only resolves when the caller's file actually IMPORTS
the candidate's file (`frob.lang.extract_imports` +
`frob.lang.resolve_local_import`, best-effort per file -- language
detection by suffix, matching `frob.arch._python._check_high_coupling`'s
own existing pattern for the identical extract+resolve pairing). A
same-file candidate always resolves, unchanged from before.
`build_reference_graph` itself is completely untouched; T-0422's gate
keeps calling it directly with its original, broader recall.
`_attribution.py::_load_snapshot_and_call_graph` now calls the scoped
builder instead -- the only wiring change outside callgraph.py.

Two consumers, two resolutions, one shared module (not the T-1966 "one
rule, two homes" defect) -- the difference is documented in both
functions' docstrings, not independently reinvented.

VERIFIED (BUG002 repro discipline, playbook 0.6): repro tests committed
ALONE first (85fa46f70), confirmed FAILING there for real reasons (3
ImportErrors for the new callgraph-level tests, plus a genuine assertion
failure for the end-to-end attribution test showing main's
build_reference_graph really does fabricate an a.py::caller ->
b.py::_run edge across two unrelated files) -- then the fix committed
separately (70887ee5e, plus a ty-typing follow-up b7acb4b9b),
confirmed all 4 new tests pass:
`pytest tests/unit/test_callgraph_module_scoped.py tests/unit/verify/
test_attribution_module_scope.py` -> SUITE-RESULT: exitstatus=0
collected=4 failed=0. Designated the end-to-end test as repro via
--designate-repro (validated FAILED_AT_PARENT at designate time).
Confirmed no regression in the existing, UNCHANGED consumer:
`pytest tests/test_graph.py -k "CallGraph or Reference"` -> 13 passed,
and the full existing attribution suite `pytest tests/unit/verify/
test_attribution.py` -> 14 passed. `frob check --only lint --json
--ticket T-2156` (FROB_NO_GATE_CACHE=1, to avoid a stale cached read)
shows zero ruff/ty findings for either changed file (one ty
invalid-assignment was caught and fixed in b7acb4b9b -- set.discard(None)
does not narrow a set's static type). The 115-file "would reformat"
count is pre-existing repo-wide drift (same frob-fmt-directive-
preservation-vs-raw-ruff-format disagreement already documented in
T-2157's Done report this session), not a regression here.

### Changed
```
 src/frob/graph/callgraph.py                        | 132 +++++++++++++++++++++
 src/frob/verify/_attribution.py                    |  17 ++-
 tests/unit/test_callgraph_module_scoped.py         | 105 ++++++++++++++++
 tests/unit/verify/test_attribution_module_scope.py | 104 ++++++++++++++++
 tickets/T-2156/ticket.md                           |  45 ++++++-
 5 files changed, 398 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_callgraph_module_scoped.py::TestBuildReferenceGraphModuleScoped::test_does_not_cross_wire_same_named_helpers_in_unrelated_files` (pytest node id, verified passing when recorded)
- `tests/unit/test_callgraph_module_scoped.py::TestBuildReferenceGraphModuleScoped::test_resolves_a_genuine_cross_file_import` (pytest node id, verified passing when recorded)
- `tests/unit/test_callgraph_module_scoped.py::TestBuildReferenceGraphModuleScoped::test_same_file_candidate_always_resolves` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution_module_scope.py::TestAttributionDoesNotCrossFileOnSameNamedHelper::test_finding_in_file_a_does_not_attribute_through_unrelated_file_bs_same_named_helper` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/graph/callgraph.py, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/graph/callgraph.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_land_git_ops.py, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DUP001@tests/unit/verify/test_attribution_module_scope.py, PRE001@tickets/T-2156, SELFAUDIT001@design, TEST001@src/frob/graph/callgraph.py, TEST001@src/frob/tickets/_land_git_ops.py, TICK004@tickets.md
