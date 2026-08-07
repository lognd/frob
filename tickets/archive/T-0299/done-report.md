## Done report

Changed (every extraction is a new PRIVATE `_`-prefixed helper; no public
def/class/`__all__` changed in any touched file):

Changed:
  src/frob/gitio.py::_tracked_hunks
  src/frob/gitio.py::_untracked_hunks
  src/frob/exports/__init__.py::_module_exports
  src/frob/graph/__init__.py::_parse_source_file_fresh
  src/frob/scaffold/project.py::_resolve_manifest_paths
  src/frob/scaffold/project.py::_write_manifest_entries
  src/frob/stats/__init__.py::_has_open_blocker
  src/frob/stats/__init__.py::_blocked_and_doable_counts
  src/frob/stats/__init__.py::_recent_commit_subjects
  src/frob/mutate/__init__.py::_first_lineno
  src/frob/mutate/__init__.py::_mutation_at
  src/frob/mutate/__init__.py::_run_mutants
  src/frob/perf/_rules.py::_perf003_inner_equality_hit
  src/frob/perf/_rules.py::_perf003_outer_var
  src/frob/perf/_rules.py::_bracket_identifiers
  src/frob/gates/_secrets.py::_secret_violation
  src/frob/gates/_coverage.py::_select_join_root
  src/frob/gates/_coverage.py::_build_class_maps
  src/frob/gates/_coverage.py::_load_coverage_xml
  src/frob/gates/invariants.py::_validate_invariant_shape
  src/frob/dup/_pipeline.py::_statement_sequence_graph
  src/frob/dup/_pipeline.py::_body_tokens_for_symbol
  src/frob/dup/_pipeline.py::_r4_candidate_pair
  src/frob/dup/_pipeline.py::_region_candidate_pair
  src/frob/dup/_pipeline.py::_all_rung_groups
  src/frob/dup/_pipeline.py::_clone_report
  src/frob/dup/_pipeline.py::_probe_setup
  src/frob/dup/_pipeline.py::_probe_verdict
  src/frob/dup/_pipeline.py::_probe_param_strategy
  src/frob/dup/_pipeline.py::_probe_one_case
  src/frob/dup/_pipeline.py::_smt_translate_simple
  src/frob/dup/_pipeline.py::_smt_bind_params
  src/frob/dup/_pipeline.py::_smt_dedented_sources
  src/frob/dup/_pipeline.py::_smt_verdict_for_check

Before/after `uv run frob arch .` long-function counts, by area:
  src/frob/dup/**       BEFORE 12  AFTER 0
  src/frob/gates/**     BEFORE  4  AFTER 0
  src/frob/stats/**     BEFORE  2  AFTER 0
  src/frob/perf/**      BEFORE  2  AFTER 0
  src/frob/mutate/**    BEFORE  2  AFTER 0
  src/frob/scaffold/**  BEFORE  1  AFTER 0
  src/frob/graph/**     BEFORE  1  AFTER 0
  src/frob/gitio*       BEFORE  1  AFTER 0
  src/frob/exports/**   BEFORE  1  AFTER 0
  TOTAL                 BEFORE 26  AFTER 0
Confirmed via `uv run frob arch .` after all edits: 0 `long-function` hits
anywhere under the 9 scoped src/ paths (the only remaining `long-function`
hits repo-wide are all under `tests/`, explicitly out of scope per the
dispatch, and were not touched).

Some extractions required trimming an over-long docstring (not just code)
to get a function's body span under the 30-line threshold, since
`frob.arch`'s `long-function` check measures the whole body-block span
(including the docstring) via tree-sitter, not code lines alone --
`_real_dataflow_graph`, `probe_equivalence`, `_probe_strategies`,
`_region_groups`, `_parse_classes`/`_select_join_root`, and `_perf003` in
`_pipeline.py`/`_coverage.py`/`_rules.py`. Trimmed prose was preserved by
relocating the rationale into the new helper's own docstring (e.g. R7's
KEYWORD_ONLY/T-0041 rationale moved from `_probe_strategies` onto
`_probe_param_strategy`) rather than deleted outright.

COV001 directive-displacement watch (per dispatch's #1 watch item):
manually re-verified after every extraction that `frob:doc`/`frob:waive`/
`frob:ticket` directives still sit immediately above their intended public
symbol, not a newly-inserted helper above it -- new helpers were always
inserted BELOW the directive-carrying def, never between a directive and
its symbol. Confirmed clean via `uv run frob check --only coverage`: 0
COV001 hits (25 COV003 hits present both before and after this ticket's
changes, on tickets T-0295/T-0296, unrelated pre-existing evidence-id
staleness -- reproduced identically via `git stash`/`frob check --only
coverage`/`git stash pop` against this same worktree tip, confirming they
predate this ticket).

Evidence: recorded via `frob ticket evidence T-draft-cff64e90 <node-id>...`
(all 16 resolved against a fresh `pytest --collect-only -q` cache), one
representative node id per touched-package test file:
  tests/unit/test_dup.py::TestDupResultFormat::test_as_json_group_count_matches
  tests/unit/test_dup_core.py::TestAptedSimilarity::test_disjoint_single_node_trees_similarity_zero
  tests/unit/test_dup_cache.py::TestConnectionReuse::test_close_all_drops_cached_connections
  tests/unit/test_dup_smt.py::test_degrades_to_smt_unavailable_without_z3
  tests/test_dup_smart.py::TestFindClones::test_core_unavailable_is_honest_err_not_silent_downgrade
  tests/test_dup_region.py::TestRegionKernelFindsPartialClone::test_enabled_finds_shared_region_between_otherwise_different_functions
  tests/test_dup_rungs.py::TestR4NearMiss::test_fires_on_gapped_clone
  tests/test_gates.py::TestActiveTicket::test_branch_regex_match
  tests/unit/test_check.py::TestCheckBuildsGraphOnce::test_run_check_calls_build_graph_exactly_once
  tests/test_stats.py::test_collect_combines_both
  tests/test_perf.py::test_heat_joins_pstats_rows_onto_symbol_spans
  tests/test_mutate.py::test_generate_mutants_covers_operators
  tests/system/test_scaffold_dx.py::test_all_registered_types_render_without_error
  tests/test_graph.py::TestBuildIncremental::test_second_build_is_all_cache_hits
  tests/unit/test_exports.py::TestExportsPackage::test_as_text_output
  tests/test_gitio.py::TestCurrentBranch::test_returns_branch_name
Full-file evidence ids (bare `tests/foo.py`, no `::`) do NOT resolve against
this repo's collected-test cache -- confirmed while attempting to record
evidence this way first (rejected with `UnknownEvidence`); T-0295's and
T-0296's existing bare-filename evidence entries share this exact defect,
which is what COV003 is flagging on them above (pre-existing, not
introduced by this ticket). `uv run pytest <all 16 files covering the
above node ids> -q`: all pass (0 failed, 2 skipped -- pre-existing skips
unrelated to this change).

Lint/format/type on the touched files (`src/frob/gitio.py
src/frob/exports/__init__.py src/frob/graph/__init__.py
src/frob/scaffold/project.py src/frob/stats/__init__.py
src/frob/mutate/__init__.py src/frob/perf/_rules.py
src/frob/gates/_secrets.py src/frob/gates/_coverage.py
src/frob/gates/invariants.py src/frob/dup/_pipeline.py`):
  `uv run ruff check <files>`      -- all checks passed
  `ruff check <files>` (PATH ruff) -- all checks passed
  `uv run ruff format --check <files>` -- 11 files already formatted
  `uv run ty check <files>`        -- All checks passed

Full-repo status (honest disclosure, not claimed as this ticket's own
debt): after `make coverage` + `uv run frob check`, the run is NOT clean
repo-wide -- `ty` reports 2 pre-existing diagnostics in
`src/frob/vet/_allow.py` (untouched by this ticket), and `gates` reports
25 pre-existing COV003 errors on T-0295/T-0296's stale evidence ids plus 2
pre-existing TEST005 coverage warnings in `src/frob/strata/_selfconform.py`
and `src/frob/tickets/_land.py` (also untouched by this ticket). All of
these were verified present BEFORE this ticket's changes too (via `git
stash` against this worktree's tip), so they are not a regression
introduced here -- this ticket's own scope (the 9 listed src/ areas) is
independently 0-error/0-warning under every one of the above tools.

`git diff main --diff-filter=D --stat`: empty (no deletions outside
scope). No Cargo.lock churn (git status shows no Cargo.lock modification).
No non-ASCII characters introduced.

Not closing this ticket -- leaving for the reviewer per the review-gated
workflow (playbook section 11.4).
Filed: none (no out-of-scope work found; the two full-repo pre-existing
issues above belong to their own tickets, T-0295/T-0296 for the COV003
evidence staleness and an as-yet-unfiled `src/frob/vet/_allow.py` ty
issue -- filing a new ticket for that ty issue was considered but is
explicitly out of this ticket's declared scope, which does not include
`src/frob/vet/**`; noting it here for the reviewer's awareness rather than
silently fixing or silently omitting it).
Gates: `uv run frob check --only coverage` clean of COV001 (0 hits) on
the touched files; `uv run frob arch .` clean of `long-function` on all
9 scoped src/ areas.
