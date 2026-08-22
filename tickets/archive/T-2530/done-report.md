## Done report

Changed:
src/frob/strata/_multifile.py::SealedGrantSet
src/frob/strata/_multifile.py::SealedGrantSet.from_root_node
src/frob/strata/_multifile.py::SealedGrantSet.widen
src/frob/strata/_multifile.py::SealedGrantSet.grants
src/frob/strata/_multifile.py::_widen_node_grants
src/frob/strata/_multifile.py::_seed_grants_by_root_node
src/frob/strata/_multifile.py::_apply_fragment_extends
src/frob/strata/_multifile.py::_rebuild_resolved_files
tests/unit/strata/test_fragments.py::TestSealedGrantSet
docs/strata/surface.md (Fragments section, item 2 upgraded)

Evidence: 4 new pytest node ids in tests/unit/strata/test_fragments.py bound
via `frob ticket evidence T-2530`:
TestSealedGrantSet.test_widen_on_declared_atom_still_works
TestSealedGrantSet.test_widen_on_undeclared_atom_refuses_closed
TestSealedGrantSet.test_fresh_insert_raises_at_runtime
TestSealedGrantSet.test_fresh_insert_fails_static_type_check

Plus all 34 pre-existing T-2502 tests (test_fragments.py's other classes,
test_multifile.py, test_design_load.py) stay green (38 total), and
load_design_ids(Path(repo_root)) against the real design/frob.strata
still produces 0 errors, 25 nodes, 106 flows, 1 boundary -- byte-identical
must-still-pass control, unaffected by this ticket (design/frob.strata
was never touched).

Structural enforcement delivered: the merge's grant mapping is now a
SealedGrantSet whose only construction path is `from_root_node` (fed
exclusively by a resolved ROOT Module's own nodes) and whose only public
mutator is `widen` (union onto an EXISTING atom; refuses and changes
nothing on an unknown one). The read view `grants` is typed
`Mapping[str, MayGrantDecl]` (never `dict`) and backed by a real
`types.MappingProxyType`, so an attempt to insert a fresh atom through
this type is BOTH a static `ty` `invalid-assignment` error (verified via
`ty check` against a scratch probe, and permanently locked by
test_fresh_insert_fails_static_type_check, which shells to the real `ty`
binary the same way tests/test_gates_fix_engine.py's own
TestSnapshotParameterDroppedStaticallyEnforced precedent does) AND a
runtime TypeError (verified by test_fresh_insert_raises_at_runtime).
This moves the guarantee out of the test suite (T-2502's own tests, which
only ever exercised the current implementation) and into the type
system, per the ticket's own charter -- "insert a new atom" is no longer
an unexercised branch, it is an inexpressible operation on this type.

Honest limit, stated in both the code and docs/strata/surface.md: Python
has no true access control. `from_root_node` being the "only" constructor
is a convention a determined caller could bypass by calling
`SealedGrantSet.__init__` directly with a hand-built dict, or by reaching
into the private `_grants` attribute via `object.__getattribute__`-style
reflection. What this ticket actually closes is the merge's OWN mutation
surface -- `_widen_node_grants`/`_apply_fragment_extends`/
`_rebuild_resolved_files` no longer have (or could regain by a careless
edit) direct dict access at all; they can only call `.widen()`. That is
the class of edit (T-1967-shaped: an exemption that quietly matches the
normal case) this ticket exists to close, and it is now closed at the
type level for that class.

Lower-priority note carried from T-2502 (fold-all-errors-collectively in
resolve_fragments): did not fall out naturally from this change (the
sealing work is orthogonal to how CrossFileErrors are accumulated across
nodes/fragments) -- left untouched, as the coordinator authorized.

Filed: T-2532 (bug, WIRE001 reach-scan misses dotted classmethod/
staticmethod calls -- SealedGrantSet.from_root_node's own legitimate
call site is invisible to the gate's call_pattern regex; cited as the
WIRE001 waiver's follow_up).

Gates: `frob check --only lint --only wire --only archgate --only perf
--only affect_drift --only docanchor --only doclink --ticket T-2530`
clean on every file this ticket touches (src/frob/strata/_multifile.py,
tests/unit/strata/test_fragments.py, docs/strata/surface.md) -- the one
WIRE001 finding on SealedGrantSet.from_root_node is waived with
follow_up=T-2532 (a real, open, filed-this-ticket gate defect, not a
promise to wire something already wired). `ty` reports "no issues"
repo-wide. Every other error line in that run (ARCH103 release/_cli.py,
DOC001/DOC002 docs/commands/release.md + gates/_refs_schema.py, WIRE002
tests/unit/test_app_runners_batch6.py, WIRE003 docs/modules/cli.md,
166-file ruff-format debt) is pre-existing and untouched by this ticket
-- confirmed by grepping the run's output for this ticket's own files.

### Changed
```
 docs/strata/surface.md              |  27 +++++++
 src/frob/strata/_multifile.py       | 138 +++++++++++++++++++++++++-------
 tests/unit/strata/test_fragments.py | 153 +++++++++++++++++++++++++++++++++---
 tickets/T-2530/ticket.md            |  22 +++++-
 4 files changed, 300 insertions(+), 40 deletions(-)
```

### Evidence
- `tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_widen_on_declared_atom_still_works` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_widen_on_undeclared_atom_refuses_closed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_fresh_insert_raises_at_runtime` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_fresh_insert_fails_static_type_check` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2530/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2530/src/frob/graph/summary.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2530/src/frob/testing/_collect_kotlin.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2530/tests/unit/test_ticket_runner_repro_merge_base.py, F811@/home/logan/projects/frob/.claude/worktrees/t-2530/tests/unit/test_app_runners_json_guard_t2492.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2530, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
