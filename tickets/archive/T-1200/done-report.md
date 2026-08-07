## Done report

Changed:
src/frob/refactor/_repointer.py::scan_pii_allowlist_carrier
src/frob/refactor/_repointer.py::scan_registry_citations
src/frob/refactor/_repointer.py::scan_evidence_citations
src/frob/refactor/_transaction.py::build_plan (wires the three repointer scans into reference_ops/unresolved)
src/frob/refactor/__init__.py (re-exports the three new functions)
docs/commands/refactor.md (anchors + build_plan blurb update)
tests/test_refactor.py::TestRepointer (4 tests)

Evidence:
tests/test_refactor.py::TestRepointer::test_pii_allowlist_entry_rekeyed_on_move (accepts 0)
tests/test_refactor.py::TestRepointer::test_registry_cross_ref_rewritten (accepts 1)
tests/test_refactor.py::TestRepointer::test_ticket_evidence_symref_rewritten (accepts 2)
tests/test_refactor.py::TestRepointer::test_no_matching_citation_yields_no_ops (supporting, not bound to an acceptance index)
All 41 tests in tests/test_refactor.py pass.

Filed: none

Gates: scoped check clean of gate:SCOPE, gate:PRE, gate:WIRE after scope
widen + sweep + direct-call wiring. Remaining findings in the run (2 ruff
E501, 3 ty, 1 ARCH001, 8 SELFAUDIT SYS104) are pre-existing in
src/frob/refactor/_directives.py (T-1199s own file) and the
design/frob.strata interface-declaration gap T-1199 already left
unresolved for its own public symbols; this tickets new symbols inherit
the identical pre-existing gap, outside this tickets declared scope.

### Changed
```
 docs/commands/refactor.md         |  31 +++++-
 src/frob/refactor/__init__.py     |   8 ++
 src/frob/refactor/_directives.py  | 218 ++++++++++++++++++++++++++++++++++++++
 src/frob/refactor/_transaction.py |  28 ++++-
 tests/test_refactor.py            | 122 +++++++++++++++++++++
 tickets.md                        | 109 +++++++++++++++++--
 6 files changed, 504 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestRepointer::test_pii_allowlist_entry_rekeyed_on_move` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestRepointer::test_registry_cross_ref_rewritten` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestRepointer::test_ticket_evidence_symref_rewritten` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 4 error(s), 154 warning(s), 745 waived
- error-findings: ARCH001@src/frob/refactor/_directives.py, E501@/home/logan/projects/frob/.claude/worktrees/w16d-refactor/src/frob/refactor/_directives.py:156, E501@/home/logan/projects/frob/.claude/worktrees/w16d-refactor/src/frob/refactor/_directives.py:59, SELFAUDIT001@design
