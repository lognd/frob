---
id: T-0299
title: 'arch: src-remainder long-function burndown to zero'
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/**
- src/frob/gates/**
- src/frob/stats/**
- src/frob/perf/**
- src/frob/mutate/**
- src/frob/scaffold/**
- src/frob/graph/**
- src/frob/gitio*
- src/frob/exports/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_dup.py::TestDupResultFormat::test_as_json_group_count_matches
- tests/unit/test_dup_core.py::TestAptedSimilarity::test_disjoint_single_node_trees_similarity_zero
- tests/unit/test_dup_cache.py::TestConnectionReuse::test_close_all_drops_cached_connections
- tests/unit/test_dup_smt.py::test_degrades_to_smt_unavailable_without_z3
- tests/test_dup_smart.py::TestFindClones::test_core_unavailable_is_honest_err_not_silent_downgrade
- tests/test_dup_region.py::TestRegionKernelFindsPartialClone::test_enabled_finds_shared_region_between_otherwise_different_functions
- tests/test_dup_rungs.py::TestR4NearMiss::test_fires_on_gapped_clone
- tests/test_gates.py::TestActiveTicket::test_branch_regex_match
- tests/unit/test_check.py::TestCheckBuildsGraphOnce::test_run_check_calls_build_graph_exactly_once
- tests/test_stats.py::test_collect_combines_both
- tests/test_perf.py::test_heat_joins_pstats_rows_onto_symbol_spans
- tests/test_mutate.py::test_generate_mutants_covers_operators
- tests/system/test_scaffold_dx.py::test_all_registered_types_render_without_error
- tests/test_graph.py::TestBuildIncremental::test_second_build_is_all_cache_hits
- tests/unit/test_exports.py::TestExportsPackage::test_as_text_output
- tests/test_gitio.py::TestCurrentBranch::test_returns_branch_name
designated_repro_test: null
threat: null
component: null
---
Drive frob arch long-function warnings to zero for the src-remainder areas: dup/(12) gates/(4) stats/(2) perf/(2) mutate/(2) scaffold/(1) graph/(1) gitio*(1) exports/(1). Behavior-preserving extraction into private helpers only, no public API change, no threshold edits. Watch for COV001 directive-displacement when inserting helpers above existing defs.