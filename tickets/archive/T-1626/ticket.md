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
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/**
- src/frob/graph/**
- docs/modules/vet.md
- tests/test_vet_capability.py
- tests/unit/vet/test_taint.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_python.py'
  actor: logan
  at: '2026-09-19'
  old_length: 2869
  new_length: 7570
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
anchor: false
anchor_reason: null
land_commit: null
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

T-4718 sweep (condensed from src/frob/vet/_capability_python.py:36-102,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

# T-0328: import/binding-aware resolution for Python, the priority language
# (highest coverage). The plain substring scan above is EVADED by ordinary
# aliasing/from-import Python -- `import subprocess as sp; sp.run(x)` never
# contains the literal text "subprocess.run(" the needle table looks for,
# and `from os import system as e; e(x)` contains neither "os.system(" nor
# "eval(", so the scanner observes NOTHING even though the code genuinely
# execs. This block builds a per-file IMPORT/BINDING TABLE from the same
# tree-sitter parse `_comment_byte_spans` already uses, resolves each
# call/attribute site's leftmost name through it (reconstructing the
# fully-qualified target, e.g. `sp.run` -> `subprocess.run`), and re-checks
# the SAME needle tables against the RESOLVED identity string instead of
# raw source text -- no new registry field, no new needle vocabulary, just
# a second pass over a synthesized "what this call/attribute actually
# refers to" string. Every resolved match is still confirmed against
# `comment_spans` before counting (T-0209 posture unchanged).
#
# Scope-awareness (mandatory to avoid FALSE POSITIVES): a LOCAL binding --
# a function/method parameter, an assignment target, a `for`/`with ... as`
# target, or a nested `def`/`class` name -- SHADOWS an import of the same
# name in every enclosing scope from the site up to module level. `def
# g(system): system(x)` (param) and `class Job: def run(self): ...` then
# `Job().run()` (method access on an unrelated object) must NOT resolve to
# `os.system`/a dangerous `run`, because the leftmost name in each case
# either resolves to a local binding (shadowed) or to an expression this
# resolver deliberately does not chase further (a `call` node, e.g.
# `Job()`, is not a resolvable "object" for attribute-chain purposes, so
# `Job().run` never reaches the import table at all).
#
# Known limitations, documented rather than silently eaten (mirrors this
# module's existing "Honest limits" posture): `from X import *` adds no
# binding (a star-imported name is untraceable without also modeling X's
# own exports); a function-scoped `import` is folded into the SAME
# file-wide binding table as a module-level one (a narrow, safe-direction
# over-approximation -- it can only ADD a resolution, never suppress a
# real one); a relative import's dotted text (`from . import x`) is kept
# as literal text (`"..x"`-shaped), which will not coincidentally collide
# with any real registry needle in practice. TS/C-C++ are OUT of scope for
# this pass -- C/C++'s `#include` is coarse-only by design (module
# docstring), and TS's binding table is noted as follow-up work, not
# attempted here. Rust gets its own binding-aware pass, T-0378 below.
#
# T-1626: two evasions the T-0328 resolver used to miss silently (the
# ticket's own worked examples) are now resolved rather than dropped:
# `functools.partial(dangerous, ...)` (`_resolve_py_expr`'s `call` branch
# recognizes a resolved-`functools.partial` callee and resolves through to
# its first positional argument -- `p = functools.partial(os.system, cmd);
# p()` now resolves `p()` to `os.system`), and a literal-keyed dict/list
# dispatch (`_record_py_dict_container_alias`/`_record_py_list_container_
# alias` record one alias entry per literal key/index at assignment time,
# `_resolve_py_subscript` looks it up at the call site -- `funcs = {"run":
# subprocess.run}; funcs["run"](cmd)` now resolves). Both stayed
# genuinely silent before: a NON-literal key/index or a dynamically
# computed `getattr` name is a SEPARATE, already-covered case --
# `frob.gates._opaque`'s OPAQUE001 (`RUNTIME_OPAQUE_CONSTRUCTS`/
# `RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS`, `_capability_scan.py`) already
# fires fail-closed on those (non-literal subscript-then-call, bare
# `getattr(`/`setattr(`/`eval(`/`exec(`/`__import__(`) -- this module
# only had to close the LITERAL-key gap OPAQUE001 explicitly defers to
# "the ordinary resolver's job" (`_subscript_key_looks_literal`'s
# docstring) but the ordinary resolver never actually implemented until
# now, which meant a literal-keyed dict/list dispatch fell through BOTH
# mechanisms: too resolvable to trip OPAQUE001, never actually resolved
# by this module. Cross-file wrapper attribution (a helper in another
# module forwarding to a dangerous callable) is NOT attempted here -- it
# needs `frob.graph.callgraph`-backed cross-file call resolution, a
# larger, separate unit of work; see T-1626's Done report / follow-up
# ticket for the split.