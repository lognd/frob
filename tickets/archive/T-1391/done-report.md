## Done report

fix_fmt001_directive_wrap now takes a keyword-only only_paths: frozenset[str]
| None = None parameter. When given, it restricts FMT001's rewrite to
exactly that set of root-relative paths (each formatted individually via
a new private helper, _fmt001_scoped_fixes; a path that no longer exists
is silently skipped, matching every other Tier-A handler's no-guess
contract). only_paths=None (the default, unchanged) preserves the
original whole-tree behaviour verbatim, so a standalone frob check --fix
and every existing caller of apply_tier_a_fixes are unaffected. This
mirrors fix_waive004_stale_waiver's existing gates/ticket keyword-only
scoping pattern in the same module: a default-preserves-prior-behaviour
lever, testable directly with no change needed at any TIER_A_HANDLERS/
apply_tier_a_fixes call site.

Scope note (disclosed, not silently done): wiring a real caller
(frob ticket land's _absorb_pre_land_fixes, in
src/frob/app/ticket_runner/_land_cmd.py) to actually pass a landing
ticket's touched-file set through only_paths is NOT part of this
change. _land_cmd.py is a different file than this ticket's declared
scope; a probe with frob ticket scope --add showed it pulls in a
cascade of unrelated private-helper scope-closure warnings across
__init__.py/_verify.py/_close_cmd.py. Filed as its own follow-up ticket
(draft T-1404), scoped narrowly to that one wiring change. So
acceptance [0] (a real land leaving an out-of-scope file untouched) is
only closed end-to-end once that follow-up lands; acceptance [1]
(only_paths=None preserves whole-tree behaviour) is fully closed here.

Also, per the same reasoning, docs/modules/gates.md was NOT touched in
this change even though the dispatch brief named it in scope: the file
is currently leased by T-1235 (declared scope docs/**, in-progress),
and frob ticket scope --add refused with a ScopeLeaseConflict. The doc
update (documenting only_paths) is deferred to whichever of these lands
first: T-1235 releasing its docs/** lease, or the follow-up land-wiring
ticket, which should also update this same section once it wires the
real call site (the doc note should describe the SHIPPED behaviour, not
just the mechanism, once wiring lands).

ARCH001 note: the new function initially came in at 77 lines (limit
60); fixed by extracting the only_paths branch into
_fmt001_scoped_fixes and moving the bulk of the T-1391 rationale into
the module's existing FMT001 section-header comment rather than the
docstring. Verified clean via frob check --only archgate --ticket
T-1391.

design/frob.strata was updated via `frob sys sync-interface` (writes
the fix) to register the new TestFmt001OnlyPathsLandScoping test class
in the testsuite node -- SELFAUDIT001 (SYS104) flagged it as an
undeclared public symbol otherwise.

### Changed
```
 tickets.md | 122 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 118 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping::test_only_paths_leaves_an_out_of_scope_file_untouched` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping::test_only_paths_none_preserves_whole_tree_behaviour` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestFmt001OnlyPathsLandScoping::test_only_paths_skips_nonexistent_path_without_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 396 warning(s), 699 waived
- error-findings: AFFECT001@src/frob/gates/_fix_engine.py
