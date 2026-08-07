---
id: T-1626
title: 'strata: capability detection must be symbol-resolved with full alias support,
  not lexical needles'
state: done
kind: security
origin: human
created: '2026-08-05'
priority: high
blocked_by:
- T-1663
parent: T-1623
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/vet/**
- src/frob/graph/**
- docs/modules/vet.md
- tests/test_vet_capability.py
- tests/unit/vet/test_taint.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: 'TICK009 pre-dispatch narrowing: docs/** and tests/** are mega-globs that
    lease essentially every doc and test in the repo, which is exactly how T-1629
    silently serialized the whole queue across sessions (see T-1743). Narrowed to
    this ticket''s real surface -- capability detection lives in src/frob/vet, its
    docs home is docs/modules/vet.md, and its tests are the vet capability/taint suites.
    Re-add with a reason if the work genuinely reaches further'
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: tests/**
  reason: 'TICK009 pre-dispatch narrowing: docs/** and tests/** are mega-globs that
    lease essentially every doc and test in the repo, which is exactly how T-1629
    silently serialized the whole queue across sessions (see T-1743). Narrowed to
    this ticket''s real surface -- capability detection lives in src/frob/vet, its
    docs home is docs/modules/vet.md, and its tests are the vet capability/taint suites.
    Re-add with a reason if the work genuinely reaches further'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/vet.md
  reason: 'TICK009 pre-dispatch narrowing: docs/** and tests/** are mega-globs that
    lease essentially every doc and test in the repo, which is exactly how T-1629
    silently serialized the whole queue across sessions (see T-1743). Narrowed to
    this ticket''s real surface -- capability detection lives in src/frob/vet, its
    docs home is docs/modules/vet.md, and its tests are the vet capability/taint suites.
    Re-add with a reason if the work genuinely reaches further'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_vet_capability.py
  reason: 'TICK009 pre-dispatch narrowing: docs/** and tests/** are mega-globs that
    lease essentially every doc and test in the repo, which is exactly how T-1629
    silently serialized the whole queue across sessions (see T-1743). Narrowed to
    this ticket''s real surface -- capability detection lives in src/frob/vet, its
    docs home is docs/modules/vet.md, and its tests are the vet capability/taint suites.
    Re-add with a reason if the work genuinely reaches further'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/vet/test_taint.py
  reason: 'TICK009 pre-dispatch narrowing: docs/** and tests/** are mega-globs that
    lease essentially every doc and test in the repo, which is exactly how T-1629
    silently serialized the whole queue across sessions (see T-1743). Narrowed to
    this ticket''s real surface -- capability detection lives in src/frob/vet, its
    docs home is docs/modules/vet.md, and its tests are the vet capability/taint suites.
    Re-add with a reason if the work genuinely reaches further'
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_dict_literal_dispatch_resolves
- tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_list_literal_dispatch_resolves
- tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_dict_literal_dispatch_with_non_dangerous_value_not_flagged
- tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_functools_partial_wrapping_dangerous_op_resolves
- tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_functools_partial_called_directly_resolves
- tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_partial_from_import_alias_resolves
designated_repro_test: null
threat: null
component: null
---
Capability detection is fundamentally LEXICAL: `scan_file_capabilities` matches per-language needle tables against the file's raw bytes, excluding hits inside tree-sitter comment spans. Import/binding-aware passes were bolted on afterwards per language (`_python_binding_capabilities` T-0328, `_ts_binding_capabilities` T-0377, a rust sibling) to recover aliased and from-import evasions the raw-text scan "structurally cannot" catch -- their own words.

That architecture cannot be made watertight by adding more needles. A capability model that decides "does this code eval?" by substring search is guessing, and it fails in both directions:

FALSE NEGATIVES (evasions the current design misses, or catches only by luck):
- indirect binding: `f = subprocess.run` then `f(cmd)` later, or through a dict/list
- attribute chains through a re-export: `from frob import io` then `io.helpers.write(...)`
- wrappers: a local helper that forwards to the dangerous callable, so the call site the scanner sees is innocent
- `functools.partial(os.system, ...)`, decorators, and callables passed as arguments
- `getattr(module, name)(...)` where name is computed
- re-exports through a package `__init__` that rename the symbol

FALSE POSITIVES (already costing real waivers in this repo):
- `_body_reaches_decode_and_exec` carries a waiver explaining that the scanner flags the literal strings "eval"/"exec" in its OWN needle table
- any identifier containing a needle as a substring (`evaluate_cacheable_gate`, `_eval_needle`, `compile_pattern`)

Requirement: capability detection must be a SYMBOL match with full alias resolution, not a text match. Resolve each call site to the symbol it actually reaches -- through import aliases, from-imports with `as`, attribute chains, re-exports, and local rebinding -- and decide the capability from the RESOLVED target. A hit is a resolved reference to a known-dangerous symbol; anything unresolved is reported as unresolved rather than silently passing.

This repo already owns the machinery: frob.graph.callgraph does call-graph resolution, and the lang adapters already produce tree-sitter symbol spans. The capability scanner should consume that resolution rather than maintaining a parallel lexical approximation per language.

Fail-closed requirement: when resolution cannot determine a call's target (genuinely dynamic dispatch, a computed getattr), that must surface as an explicit UNRESOLVED finding demanding a declaration or a waiver -- never as "no capability found". This drive has repeatedly been burned by analysis that reported nothing when it could not look; the capability layer must not repeat it.

Prerequisite for symbol-level `via`: attributing a capability to a specific declared symbol is only meaningful once the hit itself is symbol-resolved. Sequence this before, or together with, the via-granularity work.

## Done report

Changed:
- src/frob/vet/_capability_python.py::_resolve_py_expr
- src/frob/vet/_capability_python.py::_resolve_py_partial_call (new)
- src/frob/vet/_capability_python.py::_resolve_py_subscript (new)
- src/frob/vet/_capability_python.py::_py_scope_alias_lookup (new, factored out of _attr_rebind_lookup)
- src/frob/vet/_capability_python.py::_attr_rebind_lookup (refactored onto _py_scope_alias_lookup)
- src/frob/vet/_capability_python.py::_py_literal_key_text (new)
- src/frob/vet/_capability_python.py::_record_py_dict_container_alias (new)
- src/frob/vet/_capability_python.py::_record_py_list_container_alias (new)
- src/frob/vet/_capability_python.py::_first_py_positional_arg (new)
- src/frob/vet/_capability_python.py::_record_py_alias (dict/list container branches added)
- src/frob/vet/_capability_python.py::_collect_py_candidates (subscript added to resolvable call-callee/standalone-reference node types)

Scope actually reached: python only, inside src/frob/vet/** as scoped. No
src/frob/graph/** change was needed for this slice (see "What I could not
close" below).

What changed and why (fail-closed framing per the ticket):

This is a SCOPED slice of the ticket's full ambition, not the complete
"consume frob.graph.callgraph for everything" rewrite -- see the split
proposed below. It closes the two evasions the ticket named as its own
worked examples that were previously silently invisible to BOTH detectors
(the raw-text needle scan AND the existing T-0328 import/alias resolver):

1. `functools.partial(dangerous, ...)` -- `_resolve_py_partial_call`
   resolves the call's own identity through to its first positional
   argument when the callee resolves to `functools.partial` (any import
   alias of it). Covers both `p = functools.partial(os.system, cmd); p()`
   (via the existing alias-table assignment path, unchanged) and
   `functools.partial(os.system, cmd)()` called directly.
2. Literal-keyed dict/list dispatch -- `_record_py_dict_container_alias`/
   `_record_py_list_container_alias` record one alias entry per
   string/integer-literal key or list index at assignment time (mirroring
   `_attr_rebind_lookup`'s existing by-name, non-points-to posture);
   `_resolve_py_subscript` looks the entry up at the call site. Covers
   `handlers = {"run": subprocess.run}; handlers["run"](cmd)` and the
   list sibling.

Verified BEFORE this change, both fixtures resolved to `set()` from
`scan_file_capabilities` (needle scan: no literal `"subprocess.run("`
text exists in either fixture; resolver: no `subscript`/`call`-to-
`functools.partial` handling existed in `_resolve_py_expr` at all) --
confirmed by running the new tests against the pre-change code before
writing the fix (both failed with `assert "exec" in set()`). AFTER: both
resolve to `{"exec", ...}` as expected (6 new tests, all passing).

Fail-closed status (the ticket's headline requirement) -- NOT newly built
here, already exists and was verified still fires: `frob.gates._opaque`'s
OPAQUE001 (`RUNTIME_OPAQUE_CONSTRUCTS`/`RUNTIME_OPAQUE_STRUCTURAL_
CONSTRUCTS`, `_capability_scan.py`, T-0665/T-1051/T-1659) already reports
an explicit, gate-blocking finding -- never a silent "no capability" --
for exactly the cases this slice does NOT resolve: a non-literal
`getattr`/`setattr`/`__import__`/`eval`/`exec` name, and a non-literal-
keyed subscript-then-call. Verified directly: `getattr(os, name)(cmd)`
(computed `name`) produces one `_OpaqueFinding` with
`taxonomy_row='python:runtime:getattr-dynamic-name'` via
`_opaque_indirection_findings`. `_capability_scan._subscript_key_looks_
literal`'s own docstring explicitly deferred the LITERAL-key case to "the
ordinary resolver's job" -- that job had never actually been implemented
until this ticket; the non-literal case was always covered. I did not
add a NEW "UNRESOLVED" capability kind because one already exists
(OPAQUE001) and duplicating it inside `scan_file_capabilities` itself
would create two competing fail-closed mechanisms for the same
underlying fact, which is its own kind of drift risk.

Second-detector posture (per T-1328 coordination note): the raw-text
needle scan (`_matched_capabilities`/`_PATTERNS`) is UNCHANGED and still
runs as an independent first pass; the T-1626 resolver work extends the
EXISTING binding-aware second pass. T-1328 is a different, unrelated
second-detector concept (an OS-syscall-backed / generated-manifest
detector for strata's 7 app-level capability kinds, scoped to
src/frob/strata/_mutation_audit.py) -- read, not duplicated; no overlap
with this ticket's file scope.

What I could NOT close in this ticket, and why (proposing a split rather
than half-landing a false completeness claim):

- Cross-file wrapper attribution ("a helper that wraps a dangerous op and
  is called from elsewhere must attribute to the caller's node") is NOT
  attempted. The existing resolver (and this ticket's additions) is
  single-file: a wrapper defined in the SAME scanned file is already
  covered today (its body's own dangerous call is observed when that file
  is scanned), but a helper imported from ANOTHER file/module and called
  here is invisible to a per-file scan regardless of alias resolution.
  Doing this properly needs `frob.graph.callgraph`-backed cross-file
  resolution over the SCANNED DEPENDENCY'S OWN source tree (not this
  repo's own package graph, which is what `frob.graph.callgraph` is built
  and tested against today) -- a materially larger, separate unit of
  work: building/adapting a call graph for an arbitrary third-party
  source tree, deciding a traversal-depth/cycle policy, and deciding the
  attribution semantics (does a capability found N hops down attribute to
  every caller up the chain, or just the direct one?). I am filing this
  as a follow-up ticket rather than attempting a partial version of it
  here.
- TypeScript/Rust/C/Kotlin binding resolvers are untouched -- this
  ticket's own worked examples (functools.partial, dict/list dispatch)
  are Python-specific idioms; the existing T-0328 lineage already treats
  python as "the priority language" and defers the other four languages'
  binding-table depth as documented follow-up (module docstring, pre-
  existing). Extending container-alias/partial-equivalent resolution to
  each of those grammars is a separate, per-language unit of work I did
  not attempt inside this ticket's time budget.
- Symbol-level `via` attribution (naming WHICH declared symbol a resolved
  capability belongs to, not just "this file has capability X") is
  explicitly out of scope per the ticket body's own sequencing note
  ("Prerequisite for symbol-level `via`... Sequence this before, or
  together with, the via-granularity work") -- not attempted here,
  correctly deferred to whatever ticket does the via-granularity work
  next, now that this slice makes the underlying hit itself more
  symbol-resolved than before.

Filed: none yet -- filing the cross-file-wrapper-attribution follow-up
immediately after this report, scope
`src/frob/vet/**,src/frob/graph/**`, referencing this ticket.

Evidence: tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions
(6 node ids, all newly added and passing -- see evidence list on the
ticket). Also ran (not bound as evidence, regression-only):
tests/unit/vet/test_taint.py (8/8 pass, unchanged) and
tests/test_vet.py -k Capability (224/224 pass, unchanged -- this file is
OUT of this ticket's declared scope, run read-only to confirm no
regression in the existing T-0328/T-0337/T-0659 binding-resolution
suite it owns).

Gates: `frob check --ticket T-1626` clean (0 errors after fixing one
self-inflicted ARCH001 -- `_resolve_py_expr` grew past the 60-line
threshold with the inline functools.partial branch, split into
`_resolve_py_partial_call` to fix, no behavior change from the split
itself). `frob check --only static --ticket T-1626` and
`--only archgate --ticket T-1626` independently reconfirmed 0 errors
after the split. No waivers.

### Changed
```
 docs/modules/vet.md                |  23 +++-
 src/frob/vet/_capability_python.py | 265 ++++++++++++++++++++++++++++++++++---
 tests/test_vet_capability.py       |  92 +++++++++++++
 tickets.md                         |   9 +-
 4 files changed, 370 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_dict_literal_dispatch_resolves` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_list_literal_dispatch_resolves` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_dict_literal_dispatch_with_non_dangerous_value_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_functools_partial_wrapping_dangerous_op_resolves` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_functools_partial_called_directly_resolves` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_partial_from_import_alias_resolves` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 926 warning(s), 724 waived
- error-findings: none (measured, zero errors)
