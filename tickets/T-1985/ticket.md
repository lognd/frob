---
id: T-1985
title: build a file-level resolved-import edge substrate in frob.graph (prerequisite
  for T-1665)
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
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
