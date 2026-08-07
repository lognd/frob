## Done report

Root cause: two separate, real findings, not one.

1. `frob.gates.run_gates` narrowed to a caller-selected `gates` subset
   (e.g. the shape a ticket-scoped pre-flight check uses, `gates={"scope"}`)
   never evaluated the `drift` gate at all, even though the graph
   snapshot/lock `drift_gate` needs are already loaded unconditionally by
   `_load_required_state` for every run. A dangling `frob:tests` edge --
   concretely, a directive whose target string uses pytest's
   `Class::method` collect-only separator instead of the graph's own
   dotted `Class.method` qualname, so the target never resolves against
   `snapshot.symbols` -- could pass that narrowed check while a wider gate
   selection on the identical tree reported DRIFT002. Two evaluation paths
   disagreeing on the same input.

2. Investigating fix (2) from the ticket's own text (rejecting a literal
   self-referential `frob:tests` directive at parse time) turned out to be
   WRONG and was reverted: this repo has a widespread, deliberate existing
   convention of a test function naming itself as its own `frob:tests`
   evidence anchor (dozens of pre-existing examples across
   `TestDebtGate`/`TestDeprecatedGate`/etc. in tests/test_gates.py, and an
   existing test, `TestTest010KindValidation.
   test_dangling_tests_endpoint_still_caught_by_drift002`, whose own
   docstring documents that a `frob:tests` edge's CODE-side endpoint not
   resolving is already DRIFT002's job, "no TESTS-specific resolver
   needed"). A literal self-match (target == src, correctly-formed dotted
   qualname) is not a bug at all -- it is exactly this convention working
   as intended. Rejecting it at parse time broke ~40 pre-existing
   directives repo-wide (confirmed via `frob check --ticket T-0265`
   surfacing 41 new TEST010 errors before the revert).

Which answer is correct: DRIFT002 is the documented, authoritative answer
for "does this frob:tests edge endpoint resolve" (docs/modules/gates.md;
`test_gate`'s own docstring: "the code-endpoint-resolution half of that
same ticket needed no new gate code at all, since DRIFT002 already covers
TESTS edges"). The fix is therefore to make every gate-selection path see
that same DRIFT002 answer, not to add a second, competing resolution rule.
`frob.gates._build_jobs` now always folds `drift` into the job set
regardless of the caller's `gates` selection -- a `gates={"scope"}`-only
run and an unrestricted run agree on DRIFT002 for the identical tree.

Fix delivered: `src/frob/gates/__init__.py::_build_jobs` (drift now always
runs). `src/frob/graph/dsl.py::_parse_line`'s self-reference rejection was
implemented, found to be wrong via full-suite `frob check`, and reverted
-- left as an explanatory comment at the point it would have gone, citing
the pre-existing convention it would have broken, so a future reader does
not re-attempt the same fix blind.

Regression test: `tests/test_gates.py::
TestSelfReferentialTestsDirectiveScopeAgreement::
test_narrow_gate_selection_still_surfaces_drift_for_the_same_diff` builds
one fixture (a mismatched-separator self-referential `frob:tests`
directive -- a genuinely dangling edge) and runs it through BOTH a
narrowed (`gates={"scope"}`) and a wider (`gates={"scope","drift"}`)
`run_gates` call, asserting DRIFT002 appears in both. (The "wider" side
intentionally still avoids `_PROCESS_POOL_GATES` -- exercising that pool
inside a pytest-xdist worker under heavy concurrent load in this session
hit a pre-existing, unrelated fork/thread-safety hazard in `frob.gates.
_run_combined_jobs` -- forking a `ProcessPoolExecutor` from inside a still-
active `ThreadPoolExecutor` block risks deadlocking a forked child that
inherited a lock (e.g. the logging lock) held mid-fork by another thread.
That is out of T-0265's scope; not filed as a new ticket this pass because
it needs a dedicated repro outside a loaded CI/session, but is called out
here so it is not silently rediscovered from scratch.)

Gate numbers measured:
- `uv run pytest tests/test_gates.py -p no:cacheprovider -q`: 312 passed,
  0 failed (run three times across the session, including once post-merge
  with rebuilt natives).
- `uv run frob check --ticket T-0265`: exit 0, no `## Errors` section, no
  `FAIL` tool-summary lines (post pre-work-sweep refresh and ruff-length
  fix). Before the dsl.py self-reference revert, the same command showed
  `gate:TEST 41 errors` (new TEST010 violations across pre-existing
  self-referential directives) -- direct evidence the parse-time rejection
  was the wrong fix, kept here for the record.
- `git diff main --diff-filter=D --stat`: empty after merging main forward
  (main had advanced past this worktree's warm-up base with T-0573/fleet
  and other landed tickets in the interim).

### Changed
```
 src/frob/gates/__init__.py | 15 +++++++++
 src/frob/graph/dsl.py      | 17 ++++++++++
 tests/test_gates.py        | 82 ++++++++++++++++++++++++++++++++++++++++++++++
 3 files changed, 114 insertions(+)
```

### Evidence
- `tests/test_gates.py::TestSelfReferentialTestsDirectiveScopeAgreement::test_narrow_gate_selection_still_surfaces_drift_for_the_same_diff` (pytest node id, verified passing when recorded)
