## Done report

## Done report

Built the shared per-function protocol-summary fixpoint engine
(`frob.graph.summary.compute_protocol_summaries`): a bottom-up fixpoint
over an explicit `CallGraph` + T-0744 `Edge` sequence (PROTOCOL/
TRANSITION/REQUIRES), decomposing the graph into SCCs via a private,
iterative (non-recursive) Tarjan implementation -- deliberately not
`frob.cycle.graph.find_cycles`, which drops non-cyclic singleton
components this engine still needs a node for -- processed strictly
bottom-up (a callee's summary always finalizes before its caller's).
Recursive clusters (mutual recursion or a self-recursive function)
iterate the union/or-poison join to a fixpoint, bounded by
`max_iterations` (default 100).

NO-FAIL-SILENT channels implemented per acceptance: `UNRESOLVED_CALLEE`
(a sentinel callee symref a caller wires into `CallGraph.calls`) POISONS
the calling function's summary and propagates through every transitive
caller, never resetting at a clean intermediate hop
(`test_poisoning_propagates_transitively_through_a_clean_caller`). A
function never reached from any passed-in `entrypoints` gets NO summary
at all -- reported in `SummaryResult.not_analyzed`, not a falsely-clean
empty one (`test_unreachable_function_is_reported_not_analyzed_never_
silent`). A recursive SCC that fails to converge within `max_iterations`
is reported as an `SCCTimeout` naming the cluster, with every member
poisoned (`test_non_converging_scc_is_reported_as_a_timeout_error_and_
poisoned`).

Deferred, disclosed, filed as T-0809 (scope:
src/frob/graph/**, src/frob/graph/dsl.py, docs/modules/graph.md):
1. Real callee-resolution wiring (the "T-0339-family resolvers for
   callee binding" the ticket's design sketch names) -- nothing yet
   decides, from real source, when a call becomes `UNRESOLVED_CALLEE`;
   `build_call_graph` today silently omits unresolved calls rather than
   marking them. This ticket's engine defines what an unresolved callee
   DOES to a summary; wiring real detection is separate.
2. The "acquired/released/escaped resources" third of the design
   sketch's summary shape -- no DSL exists yet for resource acquire/
   release (only T-0744's protocol/transition/requires).
3. The T-0686 may-raise DESIGN CONSTRAINT ("ONE engine, whichever builds
   first hosts it") could not be coordinated on this pass -- T-0686 does
   not exist yet in this repo. Whoever builds it should consume
   `frob.graph.summary`'s SCC/fixpoint machinery rather than re-deriving
   a second one; noted in the module docstring and docs/modules/graph.md.

Scope deviation: T-0745's declared scope omitted a docs file, but every
new public symbol needs a `frob:doc` edge resolving to a real anchor
(COV001). Used the sanctioned `frob ticket scope --add --reason-file`
mechanism (not a hand-edit) to add `docs/modules/graph.md` to scope
before writing the new "Protocol summary engine" section there.

Changed:
  src/frob/graph/summary.py (new) -- UNRESOLVED_CALLEE, FunctionSummary,
    SCCTimeout, SummaryResult, compute_protocol_summaries
  tests/unit/test_arch.py -- TestProtocolSummaryEngine (10 tests)
  docs/modules/graph.md -- new "Protocol summary engine" section
  tickets.md -- T-0745 scope change, evidence, this Done report

Evidence (bound via --accepts 0, all pass):
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_function_summary_is_its_own_declarations
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_caller_summary_includes_callee_transitions
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_requires_and_transitions_join_across_two_hops
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_recursive_cluster_converges_to_hand_computed_fixpoint
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_self_recursive_function_converges
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unresolved_callee_poisons_the_summary
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_poisoning_propagates_transitively_through_a_clean_caller
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unreachable_function_is_reported_not_analyzed_never_silent
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_non_converging_scc_is_reported_as_a_timeout_error_and_poisoned
  tests/unit/test_arch.py::TestProtocolSummaryEngine::test_diamond_shaped_calls_join_without_duplication_or_loss

`uv run pytest tests/unit/test_arch.py tests/unit/graph/ -q`: 164 passed
(10 new + full pre-existing arch/graph suites, all green).
`uv run frob test --base main`: python selection touched=28 ripple=0,
exit=0, 4.01s.

Filed: T-0809 (deferred callee-resolution wiring + resource-
tracking DSL, out-of-scope machinery per the ticket's own instruction to
disclose rather than build).

Gates: `frob check --ticket T-0745 --only lint/static/gates-fast/
gates-native/gates-security` all PASS except `gate:REL` (REL001, land-
owned per docs/guides/agent-playbook.md section 4b -- FROB_AGENT was not
set in this interactive shell so the bump-suppression half didn't
trigger; land recomputes the version bump itself, not a worktree
concern). `frob ticket sweep T-0745` re-run after the scope change to
clear the stale-sweep PRE001 the scope add produced. No waivers added by
this ticket's own code.

Worktree: /home/logan/projects/frob/.claude/worktrees/agent-ae284e6e98e77b58f
Not closed, not landed (per dispatch instructions) -- ready for review/land.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_function_summary_is_its_own_declarations` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_caller_summary_includes_callee_transitions` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_requires_and_transitions_join_across_two_hops` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_recursive_cluster_converges_to_hand_computed_fixpoint` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_self_recursive_function_converges` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unresolved_callee_poisons_the_summary` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_poisoning_propagates_transitively_through_a_clean_caller` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unreachable_function_is_reported_not_analyzed_never_silent` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_non_converging_scc_is_reported_as_a_timeout_error_and_poisoned` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestProtocolSummaryEngine::test_diamond_shaped_calls_join_without_duplication_or_loss` (pytest node id, verified passing when recorded)
