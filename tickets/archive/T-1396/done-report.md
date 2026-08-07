## Done report

Continuation of T-1279's src/frob/gates TEST005 burn-down, past the 12-symbol
0.0% priority tier. Scope for this ticket is narrow ('tests/gates/**',
'src/frob/gates/__init__.py'), so this pass focused specifically on
__init__.py -- the single largest module in the package (7446 lines) and
the one this ticket's own scope permits source edits to.

MEASUREMENT: no coverage.xml/coverage stamp exists in this worktree (no
`make coverage` has run here -- confirmed via `frob check --only test`
reporting "no coverage.xml at coverage.xml" and TEST006 "no coverage stamp
found"). Per playbook sections 6b/6c/6d, a full unscoped `make coverage` run
is a coordinator-only step; this dispatch did not and structurally could not
run it. As a substitute, I ran a SCOPED `pytest --cov=src/frob/gates
--cov-branch` over tests/test_gates.py + tests/gates/ to get a rough,
non-authoritative read of which __init__.py lines/branches show zero hits
under that partial run. I verified directly that this scoped coverage.xml
cannot be trusted as a real TEST005 measurement: `frob check --stamp-coverage`
against it refuses outright (CoverageDeflated: canary module
src/frob/__main__.py reads 0.0%, T-1236's canary check), and a bare `frob
check --only test` against it reports 0 TEST005 findings repo-wide --
consistent with section 6e's documented risk that a scoped run silently
undercounts rather than measuring cleanly. I deleted the scratch coverage.xml
before finishing so it could not be mistaken for real data by a later run.

Given that, I used the scoped XML only as a POINTER to candidate gaps, then
verified each candidate by reading source + grepping for existing direct
tests (the same discipline as T-1279): a genuine gap needs BOTH zero hits in
the scoped read AND no existing frob:tests-bound test naming the symbol
directly. Three private helpers in __init__.py matched both conditions:
`_macro_symbol_file`, `_node_id_matches_symref`, `_file_of_symref_in_scope`
-- each is used by the ticket-evidence/scope-binding machinery
(`evidence_covers_scope`, `_evidence_binds_to_scope`) but had never been
exercised by a test that calls them directly; only indirect coverage through
much larger integration-style tests, which does not walk every one of their
own branches (e.g. the bare-file-vs-dotted-symref split in
`_node_id_matches_symref`, the no-separator guard in `_macro_symbol_file`).

Added tests/gates/test_scope_symref_helpers.py with 3 test classes (12 test
methods) exercising every branch of these 3 functions directly -- no filler,
each asserts a specific real return value for a specific real input shape
(exact match, prefix match, no-match, macro-suffix match, non-suffix
no-match, missing-separator guard, in-scope, out-of-scope). Bound each
function to its covering test class via `frob:tests` directives.

design/frob.strata: `frob sys sync-interface` reported this file needs the
3 new test class names added to the testsuite interface (SYS104/SELFAUDIT001),
but the file itself is OUTSIDE this ticket's declared scope and is currently
leased by T-1220 (`frob ticket scope T-1396 --add design/frob.strata` refused
with ScopeLeaseConflict). Per playbook section 0.5, `frob ticket land`
absorbs `frob sys sync-interface` automatically before merge -- this is
land-owned, not worktree-owned -- so I reverted my local sync-interface write
and left the SELFAUDIT001/SYS104 drift for land to resolve, exactly as it did
for T-1279's identical situation. Confirmed via `frob check --land-parity`:
clean, 0 unscoped errors -- the SELFAUDIT001 finding a scoped
`--only sys`/`--only coverage`/`--only scope` run still shows locally is
checkpoint-exempt at the real land sweep, not a real blocker.

This closes 3 of the remaining ~167 non-0.0%-tier findings this ticket's
brief described (a small fraction; the file is 7446 lines and covers 30+
gate implementations). The bulk of the remaining audit is unstarted --
genuinely triaging the rest requires a trustworthy TEST005 read, which
requires the coordinator's own full `make coverage` stamp (this dispatch
could not produce one). I am not filing a further continuation ticket for
this specific remainder since T-1396 itself already exists as that
continuation vehicle and its acceptance criteria (triage findings, close
genuine gaps with behavioral tests, no filler) remain open and accurately
describe the work still to do -- a future dispatch with a real coverage
stamp available should re-open/continue this ticket rather than treating it
as fully closed by this partial pass.

No new out-of-scope work found beyond the design/frob.strata lease conflict
noted above (not filed as a new ticket -- it is expected, land-owned drift
per playbook 0.5/4b, not a defect).

### Changed
```
 tickets.md | 148 +++++++++++++++++++++++++++++++++++++++++--------------------
 1 file changed, 99 insertions(+), 49 deletions(-)
```

### Evidence
- `tests/gates/test_scope_symref_helpers.py::TestMacroSymbolFile::test_no_separator_returns_none` (pytest node id, verified passing when recorded)
- `tests/gates/test_scope_symref_helpers.py::TestMacroSymbolFile::test_qualname_not_macro_suffixed_returns_none` (pytest node id, verified passing when recorded)
- `tests/gates/test_scope_symref_helpers.py::TestMacroSymbolFile::test_macro_suffixed_qualname_returns_file_path` (pytest node id, verified passing when recorded)
- `tests/gates/test_scope_symref_helpers.py::TestNodeIdMatchesSymref::test_bare_file_symref_exact_match` (pytest node id, verified passing when recorded)
- `tests/gates/test_scope_symref_helpers.py::TestNodeIdMatchesSymref::test_bare_file_symref_prefix_match` (pytest node id, verified passing when recorded)
- `tests/gates/test_scope_symref_helpers.py::TestNodeIdMatchesSymref::test_bare_file_symref_no_match` (pytest node id, verified passing when recorded)
- `tests/gates/test_scope_symref_helpers.py::TestNodeIdMatchesSymref::test_dotted_symref_exact_match` (pytest node id, verified passing when recorded)
- `tests/gates/test_scope_symref_helpers.py::TestNodeIdMatchesSymref::test_dotted_symref_parametrized_match` (pytest node id, verified passing when recorded)
- `tests/gates/test_scope_symref_helpers.py::TestNodeIdMatchesSymref::test_dotted_symref_no_match` (pytest node id, verified passing when recorded)
- `tests/gates/test_scope_symref_helpers.py::TestFileOfSymrefInScope::test_dotted_symref_file_in_scope` (pytest node id, verified passing when recorded)
- `tests/gates/test_scope_symref_helpers.py::TestFileOfSymrefInScope::test_dotted_symref_file_out_of_scope` (pytest node id, verified passing when recorded)
- `tests/gates/test_scope_symref_helpers.py::TestFileOfSymrefInScope::test_bare_path_symref_in_scope` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 0 error(s), 493 warning(s), 784 waived
- error-findings: none (measured, zero errors)
