## Done report

G4 (src/frob/lang/_common.py): _find_following_symbol's fixed `end + 2`
look-ahead window is now a named _FOLLOWING_SYMBOL_WINDOW = 3 constant with
a rationale docstring, so a directive followed by two blank lines then a
`def` binds to that def instead of silently rebinding to a broader
enclosing/module scope. G9 (src/frob/lang/__init__.py): new
_warn_if_partial_tree helper (called from _parse) logs a WARNING when
tree-sitter returns a salvaged/partial tree (has_error but children
present), surfacing the previously-silent obligation loss without changing
_parse's Ok/Err contract (extracted to a helper to stay under the ARCH001
60-line threshold).

Evidence (2 tests, pass): test_directive_binds_across_two_blank_lines (G4)
and test_syntax_error_logs_partial_tree_warning (G9). Implemented by the
easy-wins sweeper; coordinator inline-reviewed (small, in-scope, clean
gates) and landed via 3-way. The graph-side escalation
(MalformedDirective/MalformedFile) noted in the audit is out of lang/ scope,
already tracked separately.
