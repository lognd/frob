## Done report

STRING-quoted attr values reach the surface language: the lexer's
existing Str token is now accepted in exactly two new positions --
code="<glob>" (one or more, landing in Node attrs per the T-0078
convention) and may "<capability>" (landing in Node.may) -- with
unterminated/malformed strings failing closed through the existing
line/col diagnostic path and no loosening anywhere an IDENT was
expected (reviewer-verified live). Wired parse.rs -> _ast.NodeDecl ->
_elaborate. Existing litmus goldens byte-identical; 4 new rust tests
plus python parse/elaborate tests. Reviewer verified the round trip
end-to-end and APPROVED the code; this trail was completed at merge by
the coordinator. Verified on main: 378 strata tests green after make
core.
