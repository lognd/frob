---
id: T-1985
title: build a file-level resolved-import edge substrate in frob.graph (prerequisite
  for T-1665)
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/graph/imports.py
- tests/test_graph_imports.py
- docs/modules/graph.md
- design/frob.strata
evidence_scope:
- tests/test_graph_imports.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/graph.md
  reason: evidence tests and the new module's doc anchor land alongside the substrate
    itself, per playbook sec 6 (docs move in the same change as the code)
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/graph/**
  reason: 'narrow the src/frob/graph/** umbrella to the three files this ticket''s
    committed work actually touches (verified via git diff main...HEAD in its worktree:
    imports.py, test_graph_imports.py, docs/modules/graph.md -- it never touches dsl.py
    or __init__.py). The umbrella was blocking T-1970/T-1968, whose fix is complete
    and committed but needs src/frob/graph/dsl.py. Umbrella scopes cap parallelism
    across the whole queue; this costs T-1985 nothing.'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/graph/imports.py
  reason: 'narrow the src/frob/graph/** umbrella to the three files this ticket''s
    committed work actually touches (verified via git diff main...HEAD in its worktree:
    imports.py, test_graph_imports.py, docs/modules/graph.md -- it never touches dsl.py
    or __init__.py). The umbrella was blocking T-1970/T-1968, whose fix is complete
    and committed but needs src/frob/graph/dsl.py. Umbrella scopes cap parallelism
    across the whole queue; this costs T-1985 nothing.'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_graph_imports.py
  reason: 'narrow the src/frob/graph/** umbrella to the three files this ticket''s
    committed work actually touches (verified via git diff main...HEAD in its worktree:
    imports.py, test_graph_imports.py, docs/modules/graph.md -- it never touches dsl.py
    or __init__.py). The umbrella was blocking T-1970/T-1968, whose fix is complete
    and committed but needs src/frob/graph/dsl.py. Umbrella scopes cap parallelism
    across the whole queue; this costs T-1985 nothing.'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/graph.md
  reason: 'narrow the src/frob/graph/** umbrella to the three files this ticket''s
    committed work actually touches (verified via git diff main...HEAD in its worktree:
    imports.py, test_graph_imports.py, docs/modules/graph.md -- it never touches dsl.py
    or __init__.py). The umbrella was blocking T-1970/T-1968, whose fix is complete
    and committed but needs src/frob/graph/dsl.py. Umbrella scopes cap parallelism
    across the whole queue; this costs T-1985 nothing.'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001 requires declaring the new module's fs.read capability (and
    the new test file's fs.write) in the design model alongside the code that introduces
    them
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_graph_imports.py::TestBuildImportGraph::test_resolves_a_real_intra_repo_import_edge
- tests/test_graph_imports.py::TestBuildImportGraph::test_dynamic_import_reports_unresolved_not_dropped
- tests/test_graph_imports.py::TestBuildImportGraph::test_non_python_file_reports_unsupported_language_unresolved
- tests/test_graph_imports.py::TestBuildImportGraph::test_stdlib_import_counts_as_external_not_unresolved
- tests/test_graph_imports.py::TestBuildImportGraph::test_relative_import_resolves_within_package
- tests/test_graph_imports.py::TestBuildImportGraph::test_star_import_resolves_the_module_not_its_names
- tests/test_graph_imports.py::TestBuildImportGraph::test_unreadable_file_is_reported_unresolved_not_silently_skipped
designated_repro_test: tests/test_graph_imports.py::TestBuildImportGraph::test_resolves_a_real_intra_repo_import_edge
designated_repro_changes:
- old_value: tests/test_graph_imports.py::TestBuildImportGraph.test_resolves_a_real_intra_repo_import_edge
  new_value: tests/test_graph_imports.py::TestBuildImportGraph::test_resolves_a_real_intra_repo_import_edge
  reason: 're-point repro designation onto the pytest-native :: form after the dotted
    Class.method form (this ticket''s own evidence-refresh residue) failed land''s
    post-merge resolve check; same BUG002 structural NO_VERDICT as before (brand-new
    module/tests, no version exists at parent), confirmed via --check-repro'
  actor: logan
  at: '2026-08-10'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed while investigating T-1665 so the real blocker has a concrete id
and a design, instead of a half-measure landing inside a carefully
three-times-hardened 795-line gate.

MEASUREMENT (this session, natives-built worktree, frob check --only
refs --json): REF gate currently reports 2 REF001 findings and 2 REF002
findings, 0 waived total. Both REF001 findings are non-code evidence
artifacts (tickets/T-1881/evidence/stage1-frob-check.json, tickets/
T-1959/evidence/class3-reverted.md) -- files no import/call resolution
of any kind would ever reach, so a semantic rewrite would not change
either of TODAY's live findings. REF001 has ZERO waivers anywhere in
the tree right now (`frob:waive REF001` appears only in _refs.py's own
docstrings/messages, never as a live directive) -- the "waivers
compensating for the lexical gap" question T-1665 asks has a clean
answer for THIS moment: there is nothing to migrate or remove. (T-1665's
cited "REF002 is at 51 findings" figure is from earlier in this drive;
current REF002 count is 2, 0 waived -- already resolved by other work
since, unrelated to this ticket.)

WHY NOT LANDED THIS SESSION: T-1665 asks for inbound-reference decisions
"from resolved imports and calls... frob.graph.callgraph and the
snapshot's edges already model this." Checked directly -- they do not,
for this purpose:
- frob.graph._models.EdgeKind only models frob:-directive edges (doc/
  uses-contract/tests/ticket/...), never a plain source-level import or
  call reference. There is no IMPORT edge kind.
- frob.graph.callgraph (build_call_graph et al.) resolves calls to
  PRIVATE/module-local symbols only, by design ("public/exported
  callees are deliberately never recorded as edges here" -- its own
  module docstring) -- it structurally cannot answer "does file Y
  import module X", which is exactly REF001's question for the common
  case (importing a module to use its public API).
- No other file-level "who imports this module" substrate exists in
  frob.graph or frob.lang today.

_refs.py's existing Python-import extraction (_python_import_targets,
_FROM_IMPORT_RE/_PLAIN_IMPORT_RE) is already closer to "resolved
import" than a naive substring scan -- T-0396 round 2 already fixed the
multi-name/parenthesized-import false positive, and aliases already
resolve to their real imported name (_split_import_names strips " as
...."). What T-1665 actually wants beyond that is real AST/graph-based
resolution: handling conditional/nested imports, confirming a matched
token is genuinely an import statement rather than a look-alike string,
and covering non-Python languages' import forms with the same rigor.
Building that (a real file-level resolved-import graph, reusable beyond
this one gate) is infrastructure, not a REF001-local fix.

RECOMMENDATION (matches the brief's own escape valve: report as a
BLOCKER with the design rather than half-land):
1. Build a file-level import-edge substrate in frob.graph (or a
   sibling module) -- for each tracked source file, the set of other
   tracked files its import statements resolve to, per language,
   reusing frob.lang's existing parse trees rather than a fresh regex
   pass. This is the real "resolved imports" REF001 needs and is
   reusable by any future rule that wants the same question answered.
2. Once that exists, REF001's auto-scan narrows to: for CODE targets,
   an inbound reference means a resolved edge from step 1 reaches this
   file; for non-code targets, the existing textual auto-scan stays
   (docs/config/data files have no "import" to resolve) OR narrows
   further to a stricter link-shape than plain path/basename mention,
   TBD once real doc-link precision is measured too.
3. Per T-1664, a target the substrate cannot resolve (parse failure,
   unsupported language, degraded analysis) reports Severity.UNRESOLVED
   (T-1664, landed) rather than silently "referenced" or "dead" --
   REF001 becomes the first concrete UNRESOLVED consumer this way.
4. Re-run the measurement THEN: before/after REF001 finding counts,
   split by derivation (resolved-import vs textual vs UNRESOLVED), is
   the acceptance evidence T-1665 itself asks for.

Scope for a follow-up ticket building step 1: a new module (proposed
frob.graph.imports or similar), NOT src/frob/gates/_refs.py directly --
the substrate is reusable infrastructure, REF001's own rewrite is a
separate, smaller follow-up once it exists.

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
