## Done report

Fixed the two remaining stale `frob test --collect` references (T-0292
sibling): src/frob/tickets/__init__.py::add_evidence and
src/frob/app/ticket_runner.py::_log_evidence_result now describe the real
content-hash cache auto-refresh + .frob/pytest-collect.json /
.frob/cargo-collect.json fallback instead of the nonexistent flag, matching
the T-0292 fix already in gates/__init__.py.

Evidence (2 tests, pass): test_unresolvable_id_warning_names_no_nonexistent_flag
(the tickets store warning) and test_error_remedy_names_no_nonexistent_flag
(the CLI evidence-failure log). Implemented by the easy-wins sweeper;
coordinator inline-reviewed and landed via 3-way (all files tracked; untracked
enumeration checked per T-0463, none this time).
