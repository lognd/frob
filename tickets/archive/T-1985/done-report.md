## Done report

Changed:
- src/frob/graph/imports.py (new module) -- ImportGraph, UnresolvedImport, build_import_graph
- tests/test_graph_imports.py (new)
- docs/modules/graph.md -- new "Import graph" section, frob:describes anchors

Languages covered: Python only, v1, disclosed explicitly in the module
docstring and docs/modules/graph.md. Every other frob.lang-supported
language (Rust, C, C++, TypeScript, Kotlin, Strata) contributes zero
resolved edges and is reported as UnresolvedImport(reason=
"unsupported-language") per file, never silently absent.

Method: stdlib ast (not frob.lang tree-sitter walkers -- RawSymbol has
no import-statement extraction today, adding one is frob.lang scope,
not this ticket's). Resolves import/from-import statements against a
dotted-module index built from the tracked file list, including
relative imports and from-X-import-submodule shapes. Reports, never
drops: dynamic imports (importlib.import_module/__import__), relative
imports above the tracked root, files that fail to parse, and
non-Python files -- all as UnresolvedImport. Stdlib/third-party imports
are counted separately (external_count) for transparency, neither
resolved nor unresolved (fully-answered "not this substrate's domain").

Measured split on this repo's own src/frob tree (630 tracked files, 531
Python): 2522 resolved import edges across 479 files, 2480 external
imports, 110 unresolved (99 unsupported-language, 11 dynamic-import),
0 parse-error, 0 relative-import-above-root.

Evidence: 7 pytest node ids in tests/test_graph_imports.py::
TestBuildImportGraph, all bound via `frob ticket evidence T-1985`.
Repro designation: test_resolves_a_real_intra_repo_import_edge,
FORCED via --designate-repro-force -- BUG002 structural NO_VERDICT
(exit 5, collection failure at parent fc810277b), because
src/frob/graph/imports.py plus every one of the 7 test node ids are
brand new and did not exist at parent at all (T-1985 builds new
substrate infrastructure, not a fix to pre-existing broken behavior --
there is no version of this test that could run at parent). Matches
the documented T-1907/T-1884/T-1882/T-1911 collection-failure shape in
docs/guides/agent-playbook.md sec 6; confirmed via --check-repro before
forcing, not silently waived.

Filed: none. No out-of-scope work discovered; REF001's own narrowing
(T-1665) remains untouched by design, per the ticket's own instruction.

Gates: `frob check --ticket T-1985` is 0 errors on every ticket-relevant
gate family (ARCH/COV/SELFAUDIT/SCOPE/WIRE/PRE all clean after fixing
ARCH001 line-count, COV002 frob:ticket edges, SELFAUDIT001 capability
declarations in design/frob.strata, and a WIRE001 waiver naming T-1665
as follow_up); scope extended to include docs/modules/graph.md,
tests/test_graph_imports.py, and design/frob.strata via `frob ticket
scope --add` with reasons recorded. Remaining ruff-check/ruff-format
FAILs in the same check run are pre-existing repo-wide drift (91-92
files, unrelated modules), confirmed unrelated by diffing before/after
this ticket's own file changes. `frob test --base main`: PASS, exit 0,
11 python test outcomes recorded (7 new + 4 rippled: test_graph.py's
lock-drift integration test and the frob-self-model/PII system tests
that always run on a design/frob.strata touch).

### Changed
```
 design/frob.strata            |   4 +-
 docs/modules/graph.md         |  54 ++++++
 src/frob/graph/imports.py     | 387 ++++++++++++++++++++++++++++++++++++++++++
 tests/test_graph_imports.py   | 109 ++++++++++++
 tickets/T-1985/done-report.md |  75 ++++++++
 tickets/T-1985/ticket.md      |  39 ++++-
 6 files changed, 663 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_graph_imports.py::TestBuildImportGraph::test_resolves_a_real_intra_repo_import_edge` (pytest node id, verified passing when recorded)
- `tests/test_graph_imports.py::TestBuildImportGraph::test_dynamic_import_reports_unresolved_not_dropped` (pytest node id, verified passing when recorded)
- `tests/test_graph_imports.py::TestBuildImportGraph::test_non_python_file_reports_unsupported_language_unresolved` (pytest node id, verified passing when recorded)
- `tests/test_graph_imports.py::TestBuildImportGraph::test_stdlib_import_counts_as_external_not_unresolved` (pytest node id, verified passing when recorded)
- `tests/test_graph_imports.py::TestBuildImportGraph::test_relative_import_resolves_within_package` (pytest node id, verified passing when recorded)
- `tests/test_graph_imports.py::TestBuildImportGraph::test_star_import_resolves_the_module_not_its_names` (pytest node id, verified passing when recorded)
- `tests/test_graph_imports.py::TestBuildImportGraph::test_unreadable_file_is_reported_unresolved_not_silently_skipped` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: F401@/home/logan/projects/frob/.claude/worktrees/import-edges/tests/unit/test_tickets_evidence_only_scope.py
