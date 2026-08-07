## Done report

The Python walker (src/frob/lang/_walk_python.py, _extract.py) now scans
module/class/function leading docstrings for frob: directives. A
module-docstring directive binds to the bare file path; a class/function
docstring directive binds to the enclosing symbol -- identical semantics to
a # comment directive. Implemented via `_docstring_string_node` (single
source of truth for "what is a docstring"), `_docstring_nodes` (depth-first
collect), and `_walk_python_docstring_comments` (turns each into a RawComment
bound by span), wired through a python-only walker table in extract() so the
docstring-sourced comments join the normal comment stream before
parse_directives runs -- no downstream DSL/graph change needed.

Evidence: tests/test_graph.py::TestDsl::test_module_docstring_directive_binds_to_bare_file
and ::test_function_docstring_directive_binds_to_function (both genuinely
new coverage -- fail without the fix). Reviewer APPROVED (verified the
_docstring_string_node factoring preserves existing #-comment behavior, 121
baseline tests unchanged).

Coupling note: this change makes previously-invisible docstring directives
visible, which turned two latent kind="drift" directives (in
tests/unit/test_strata_tmlanguage.py and test_extending_guides_complete.py)
into surfaced MalformedDirectives. Those are corrected to kind="unit" under
T-0269, landed in the same commit -- verified empirically (malformed 1 -> 0).

Landed surgically onto current main (worktree tickets.md was stale); only
the lang code + tests were lifted, close re-spliced here.
