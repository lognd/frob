## Done report

Root cause: `_enclosing_src` in src/frob/graph/dsl.py checked `comment.enclosing`
before `comment.following`. `_find_enclosing` (src/frob/lang/_extract.py) returns
the narrowest symbol whose span *contains* the comment line, so a directive
placed directly above a nested method's `def` line falls inside the enclosing
class's span and was picked over the method that starts 1-2 lines below (already
identified by `_find_following`), silently binding the edge to the class.

Fix: swapped the priority in `_enclosing_src` to prefer `comment.following` over
`comment.enclosing` (following, then enclosing, then bare path). This matches the
natural-placement case (directive directly above a def) while leaving the
existing "directive as first line inside a function body" case unaffected,
since no symbol starts within range there so `following` stays None.

Changed:
- src/frob/graph/dsl.py::_enclosing_src (private helper used by `parse_directives`)

Evidence: tests/test_graph.py::TestDsl::test_binds_to_nested_method_not_enclosing_class
(new regression test, reproduces the exact nested-class-method case from this
ticket; fails before the fix, passes after). Also re-ran the full existing
TestDsl suite (test_binds_to_enclosing_symbol, test_binds_to_following_symbol,
test_bare_file_when_no_binding, test_tests_verb_attrs, test_tests_verb_default_kind)
-- all green, no regression in prior binding behavior.

Full-suite verification: `uv run pytest -q` all green except two pre-existing,
unrelated failures confirmed present on `main` before this change (verified via
`git stash`): `tests/test_dup_rungs.py::TestR5Dataflow::test_no_false_positive_against_unrelated_function`
(dup module, out of scope) and `tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately`
(flaky under xdist parallelism, passes in isolation). Neither touches
src/frob/graph or src/frob/lang.

`frob test --base main` selected touched-set (tests/test_graph.py +
test_graph_build_lock_drift_integration): PASS, exit=0.

Filed: none (no out-of-scope work found; native strata_core/frob_core
extensions were missing from the environment, built via `make core` to
unblock `frob check`'s pytest-collection gate -- a build step, not a code
change, so no ticket needed).

Gates: `frob check --ticket T-0044` clean, exit=0, no errors/warnings.
