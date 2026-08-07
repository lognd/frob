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