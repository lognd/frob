## Done report

Before: 14 long-function, 0 god-class. After: 0 UNWAIVED (3 reason-waived).

Refactored 11 over-long functions by extracting private helpers (behavior
identical, verified by the reviewer's per-extraction audit + touched-set
suite): gates/__init__.py::_valid_edges (->_edge_has_execution_evidence),
gates/_prework.py::sweep_ticket (->_xref_hit_for_scope_pattern),
vet/_capability.py::_resolve_py_expr (->_resolve_py_identifier/
_resolve_py_attribute) and _build_py_alias_table (->_record_py_alias),
strata/_selfconform.py::_fully_excluded_node_ids
(->_repo_files_excluding_skip_dirs), strata/_elaborate.py::
_validate_node_observability (->_validate_observe_field),
dup/_pipeline.py::_substitute_calls (->_splice_call_site/
_matching_paren_end), graph/callgraph.py::build_call_graph
(->_short_name_index/_resolve_call_edges), graph/__init__.py::load_graph
(->_first_stale_cached_file), app/vet_runner.py::_run_scan
(->_exit_code_for_report) and _print_table (->_notes_by_verdict_name/
_print_verdict_row).

Reason-waived 3 (ARCH001, T-0289's waivable channel): scan_file_operations
(vet/_capability.py, linear orchestration over already-extracted match
helpers), check_capability_completeness (strata/_threat.py, 9 logic lines +
long contract docstring), _collect_dispatch_refs (arch/_python.py, single
cohesive tree-walk owned by T-0360).

Verification: `uv run frob check --only arch` -> 0 unwaived long-function/
god-class. `uv run frob test --base main` 12 selected, exit 0. pytest
gates/graph/dup 189 pass. Scope clean (only named src files + tickets.md).
Reviewer APPROVED behavior preservation on all 11 extractions (REJECT was
solely for this missing Done report, now written by coordinator at land).
