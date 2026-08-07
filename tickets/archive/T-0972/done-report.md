## Done report

DECOMPOSE-THEN-START finding: the ticket's stated "1730 unwaived
PERF001-004" baseline was stale. A fresh chunked `frob check --only
gates-native` measurement on this worktree (post-merge with main) found
only 46 unwaived PERF001-004 findings (34 PERF004, 9 PERF003, 2 PERF001,
1 PERF002), plus 30 already-waived findings matching the ticket's own
note. The 1730 figure evidently predates PERF012 (T-0919, a separate,
much noisier rule added after this ticket was filed) or another baseline
drift; at 46 findings the burn-down is directly tractable in one pass,
so this ticket executes the full burn-down rather than decomposing into
children (T-0399 "executed decomposition" precedent still honored in
spirit: every non-mechanical finding got an individually reasoned
disposition, not a blanket waiver).

Cluster table (46 unwaived findings):

| Cluster | Rule | Count | Disposition |
|---|---|---|---|
| sorted() on a fresh per-iteration/per-key collection (message-format or dict-value), nothing shared to hoist | PERF004 | 32 | frob:waive, reasoned per-site |
| sorted(CONSTANT) re-sorted every loop iteration in `_delivery_semantics.py` | PERF004 | 1 | FIXED: hoisted `sorted(DELIVERY_SEMANTICS)` above the loop |
| BFS/DFS/Tarjan/two-pointer graph or tree traversal misread as a nested-loop cross join (PERF's structural blindness, audit findings 8/9) | PERF003 | 9 | frob:waive, reasoned per-site |
| membership test against a list rebuilt/tested inside a loop | PERF001 | 2 | FIXED: build the set once outside the loop (`app/ticket_runner.py`, `arch/_patterns.py`) |
| `.count()` over a distinct byte sub-range per iteration (not a repeated identical query) | PERF002 | 1 | frob:waive, reasoned |
| already-waived baseline (untouched) | PERF001-004 | 30 | left as-is |

Executed reductions:
- 2 real mechanical fixes (PERF001 x2: `app/ticket_runner.py::doable`,
  `arch/_patterns.py::_check_manual_callback_list`) -- hoist membership
  set construction out of the loop.
- 1 real mechanical fix (PERF004: `strata/_delivery_semantics.py::
  _missing_or_invalid_delivery_semantics_violations`) -- hoist
  `sorted(DELIVERY_SEMANTICS)` (a module constant) out of the loop.
- 43 reasoned `frob:waive` markers across two dominant false-positive
  clusters the gates-quality audit (T-0399 findings 8/9) already
  disclosed: (a) `sorted()` over a small collection that is genuinely
  distinct every loop iteration, used only for deterministic
  message/log formatting -- nothing to hoist; (b) a real BFS/DFS/
  Tarjan/two-pointer traversal PERF's position-free, nesting-blind
  token-stream detector cannot distinguish from an O(n^2) cross join.
- Net: 46 -> 0 unwaived PERF001-004 findings, confirmed by a full
  `frob check --only gates-native` re-run (`gate:PERF 0 errors, 1681
  warnings, 73 waived`).
- Promoted `[gates.severity]` PERF001/002/003/004 = "error" in
  `frob.toml`, following the T-0971/T-0973 precedent -- re-verified
  green immediately after the flip (no regression, since the unwaived
  count is genuinely zero).
- AFFECT001 (touched-symbol doc-drift) required a short, honest note
  in each affected doc anchor (docs/modules/arch.md, gates.md, graph.md,
  perf.md, vet.md; docs/strata/kernel.md, surface.md) recording exactly
  what changed and that it is behavior-preserving -- scope extended to
  cover these files plus `frob.toml` (see `frob ticket scope` history).

Children filed: none -- no cluster required a follow-on ticket; the
count was small enough to fully dispose of directly, and the two real
hoist fixes were trivial and low-risk.

Additional ticket filed (out-of-scope discovery, NOT part of this
ticket's own burn-down): T-0983 -- `frob test`'s stability-
capture pass (src/frob/testing/_stability.py, called from the `frob
test` CLI path) builds a second pytest node-id list using a dotted
`Class.method` separator instead of `::`, so every run's stability-
capture invocation collects 0 tests and silently no-ops
`.frob/test-stability.json`. Observed twice while verifying this
ticket's own touched-set; unrelated to PERF gates, filed separately per
scope discipline.

Process note (own mistake, corrected): a first attempt at clearing the
new PERF004/PERF003 waiver-comment E501s ran `uv run frob fmt src/frob`
repo-wide, which has an off-by-one line-wrap bug (wraps to 89 chars,
one over the 88-char limit) and touched ~180 files outside this
ticket's scope. Reverted every file `frob fmt` touched that was not an
intentional T-0972 edit (`git checkout --` per file, verified against
the pre-run `git status`), then re-applied every T-0972 edit by hand
with an explicit `# noqa: E501` suffix on the rare over-88-char waiver-
reason lines instead of relying on the buggy formatter. `ruff-format`
also auto-fixed two pre-existing, unrelated formatting drifts inside
files already in this ticket's touched set (`arch/_lock_ordering.py`,
`tests/unit/test_arch.py`) -- accepted since they are in-scope files
and the fix is a no-op reformat, not a content change.

Changed (symrefs, T-0972-bound via `frob:ticket T-0972`):
- src/frob/app/ticket_runner.py::doable (PERF001 fix)
- src/frob/arch/_patterns.py::_check_manual_callback_list (PERF001 fix)
- src/frob/strata/_delivery_semantics.py::
  _missing_or_invalid_delivery_semantics_violations (PERF004 fix)
- src/frob/app/check_runner.py::_run_baseline_chunks
- src/frob/arch/_exceptions.py::check_errors_as_values
- src/frob/arch/_fallibility.py::check_over_broad_except
- src/frob/arch/_ocp.py::_check_non_exhaustive_enum_match
- src/frob/arch/_patterns.py::_check_scattered_construction
- src/frob/arch/_smells.py::check_data_clumps,check_temporal_coupling
- src/frob/arch/_solid.py::check_override_strengthened_precondition
- src/frob/arch/_typedesign.py::check_illegal_states_representable
- src/frob/arch/_lock_ordering.py (waiver only, no COV002 edge required)
- src/frob/dup/_pipeline.py (waiver only)
- src/frob/gates/_fmt_directives.py::canonicalize_text
- src/frob/gates/_lang_conformance.py::_lang003_unsound_gaps
- src/frob/gates/_protocol_summary.py::protocol_summary_gate
- src/frob/graph/affects.py::affects
- src/frob/graph/callgraph.py::_resolve_edges_python
- src/frob/graph/lock.py::acknowledge
- src/frob/graph/summary.py::_reachable,_tarjan_sccs
- src/frob/perf/_advisories.py::external_call_advisories
- src/frob/perf/_dup_spawn.py (waiver only)
- src/frob/perf/_hotgraph.py::build_section_index,language_deciles
- src/frob/perf/_loop_effects.py (waiver only)
- src/frob/perf/_sampler.py::StackSampler
- src/frob/strata/_contention.py::_duplicate_port_violations,
  _shared_pipe_violations,_shared_store_write_violations
- src/frob/strata/_design_load.py::unbound_constructs
- src/frob/strata/_distributed_txn.py::_missing_saga_violations
- src/frob/strata/_facts.py::FactBase,FactBase.aggregate_demand
- src/frob/strata/_infra.py::_sticky_balancer_diagnostics
- src/frob/strata/_shared_state.py::_shared_state_violations
- src/frob/strata/_ssot.py::_missing_owner_violations
- src/frob/strata/_starvation.py::_writer_starvation_violations,
  _unbounded_wait_violations
- src/frob/strata/_txn.py::_missing_txn_boundary_violations
- src/frob/vet/_capability.py::non_executable_line_numbers
- tests/test_arch_near_duplicate_native.py,tests/test_gates.py,
  tests/unit/strata/test_registry_cross_refs.py (waiver only)
- frob.toml ([gates.severity] PERF001-004 = "error")
- docs/modules/arch.md,gates.md,graph.md,perf.md,vet.md;
  docs/strata/kernel.md,surface.md (AFFECT001 touch notes)

Evidence: 22 pytest node ids recorded via `frob ticket evidence T-0972`
(TestLockOrderingHazards, TestOverBroadExcept, TestDataClumps,
TestTemporalCoupling, TestOverrideStrengthenedPrecondition,
TestIllegalStatesRepresentable, TestPatternRecommender,
TestNonExhaustiveEnumMatch, TestCanonicalizeText,
TestProtocolSummaryGate, TestAffects, TestAckDrift,
test_graph_build_lock_drift_integration, TestExternalCallAdvisories,
TestResolveStream, TestStackSampler, TestAggregateDemand, TestUnbound,
TestLinkedGroupsResolveAndAreNavigable,
TestDocstringProseNotObservedLineLevel,
test_native_kernel_matches_difflib_over_this_repos_own_arch_tree,
TestCheckRunner) -- the full 88-test touched-set `frob test --base
main` run these are drawn from passed clean (`[PASS] python exit=0`,
two independent runs, before and after the frob-fmt revert/redo).

Gates: `frob check --only gates-fast --ticket T-0972` PASS (0 errors),
`--only gates-native --ticket T-0972` PASS (0 errors, `gate:PERF` 0
errors/1681 warnings/73 waived), `--only gates-security --ticket
T-0972` PASS (0 errors), `--only static --ticket T-0972` PASS, `--only
lint --ticket T-0972` PASS (ruff-check/ruff-format/ty all clean) -- the
sanctioned chunked per-stage-group loop (playbook section 3b), no full
undelta'd `frob check`.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/perf/test_hotgraph.py::TestStackSampler::test_collects_at_least_one_sample_over_a_hot_loop` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestOverBroadExcept::test_bare_except_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestDataClumps::test_same_three_keyword_group_at_three_sites_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTemporalCoupling::test_guard_clause_on_initialized_flag_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestOverrideStrengthenedPrecondition::test_added_guard_raise_on_shared_param_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestIllegalStatesRepresentable::test_bool_field_cross_field_guard_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_manual_callback_list_recommends_observer` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_ocp.py::TestNonExhaustiveEnumMatch::test_missing_member_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_idempotent_on_already_canonical_text` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolSummaryGate::test_real_repo_scan_runs_end_to_end_without_crashing` (pytest node id, verified passing when recorded)
- `tests/test_graph_affects.py::TestAffects::test_transitive_uses_contract_chain` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestAckDrift::test_acknowledge_records_every_describes_facet` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::test_graph_build_lock_drift_integration` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_advisories.py::TestExternalCallAdvisories::test_dominant_external_edge_fires` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotgraph.py::TestResolveStream::test_leaf_in_loop_body_attributes_to_loop_section` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_demand.py::TestAggregateDemand::test_two_entry_nodes_sum_at_fan_in` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_design_load.py::TestUnbound::test_bound_excluded` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_registry_cross_refs.py::TestLinkedGroupsResolveAndAreNavigable::test_every_member_cross_refs_every_other_member` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_non_executable_line_numbers_covers_docstring_and_comment` (pytest node id, verified passing when recorded)
- `tests/test_arch_near_duplicate_native.py::test_native_kernel_matches_difflib_over_this_repos_own_arch_tree` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_mode_calls_stamp_and_returns` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 22 passed (from 22 evidence id(s))
- gates: 0 error(s), 4898 warning(s), 282 waived
- error-findings: none (measured, zero errors)
