---
id: T-0377
title: 'vet: TypeScript/JS binding-aware capability resolution'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: T-0376
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability.py
- tests/test_vet*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_c.py'
  actor: logan
  at: '2026-09-19'
  old_length: 547
  new_length: 2770
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_kotlin.py'
  actor: logan
  at: '2026-09-19'
  old_length: 2769
  new_length: 4495
evidence:
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_default_import_alias_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_require_bare_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_require_destructure_rename_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_namespace_import_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_ts_import_require_clause_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_operation_names_registry_entry_for_aliased_import
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_param_named_get_not_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_param_shadowing_import_not_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_method_on_unrelated_object_not_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_bare_name_call_with_no_import_not_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_direct_unaliased_call_still_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_bracket_access_inline_require_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_bracket_access_aliased_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_dynamic_import_then_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_await_dynamic_import_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_child_process_bracket_and_dynamic_import_caught
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_computed_subscript_not_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_static_template_literal_subscript_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsBindingResolution::test_interpolated_template_subscript_not_detected
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Extend scan_file_capabilities/_scan_file_operations binding-aware resolution (currently Python-only, T-0328/T-0337) to TypeScript/JS: resolve ES import/require/destructure/alias bindings and scope-shadowing using the existing tree-sitter parse, mirroring the Python import-table/alias-copy-propagation/scope-bound-names discipline. Acceptance: an aliased import like `import {run} from 'child_process'` (renamed binding) is still flagged, while a locally-shadowed identifier of the same name is NOT flagged; adversarial tests added for both cases.

T-4718 sweep (condensed from src/frob/vet/_capability_c.py:31-61, trimmed
for DOCARCH002's 12-line cap): the trimmed block's full original text,
kept verbatim below.

# T-0379: import/binding-aware resolution for C/C++, the fourth binding
# resolver alongside T-0328 (python) / T-0377 (TS) / T-0378 (rust). C/C++'s
# dominant renaming idiom is the preprocessor, not an import system: `#define
# SYS system` makes `SYS("sh")` a call to `system` with no `"system("`
# substring anywhere in the file's own text, evading the raw-text needle
# scan the same way an aliased python `import`/rust `use` does. Only a
# SIMPLE object-like macro whose value is a single bare identifier is
# resolved (`#define SYS system`) -- a function-like macro (`#define SYS(x)
# system(x)`) is a `preproc_function_def` node, a structurally different
# shape, and is a documented, deliberately out-of-scope limitation here
# (mirrors the T-0378 grouped-`use` limitation note above): a function-like
# macro already re-expands to literal "system(" text at its call site in
# common usage, so the raw-text lexical scan still has a real (if weaker)
# chance at it, unlike the pure-rename case this resolver targets.
#
# A `using NAMESPACE::NAME;` declaration or namespace-qualified call site
# (`fs::system(...)` after `namespace fs = std;`) needs NO special
# resolution here: the registry's own needles are bare substrings
# (`"system("`), which still occur verbatim inside a qualified call --
# `_needle_hits_outside_comments` already catches those lexically. Type-only
# aliases (`typedef`/C++11 `using X = Y;` alias-declarations) do not rename
# a CALLABLE and are out of scope for the same reason.
#
# Shadow-awareness mirrors `_rust_shadowing_scope`'s POSITION-aware
# discipline (T-0378 round 2, T-0339 fail-closed): a local variable or
# function parameter sharing a macro alias's name must not have a call site
# textually BEFORE its own declaration wrongly treated as shadowed. Block
# scoping (nested `compound_statement` scopes each shadowing independently)
# is over-approximated to "the whole enclosing function" -- matching the
# python/rust resolvers' function-granularity, not per-block C scoping;
# documented, not a silent gap.

T-4718 sweep (condensed from src/frob/vet/_capability_kotlin.py:19-42,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

# --------------------------------------------------------------- kotlin (T-0664)
#
# Kotlin static-binding resolution (docs/design/capability-evasion-
# taxonomy.md's Kotlin table, T-0664 -- the fourth per-language resolver
# after T-0328/T-0377/T-0378/T-0379/T-0662/T-0663's python/TS/rust/C/C++
# ones). `frob.lang.raw_tree`'s `"kotlin"` label reaches `frob.lang._walk_
# kotlin`'s grammar via T-0723's central-dispatch wiring.
#
# SCOPE, disclosed up front rather than silently narrowed: this resolver
# uses a FLAT, FILE-WIDE alias table (no per-scope/position shadow
# discipline the way `_c_shadowing_scope`/`_rust_shadowing_scope` give the
# C/rust resolvers) -- a local variable that happens to share a name with
# an imported/aliased binding is NOT distinguished from the import here.
# This is a REDUCED-FIDELITY model versus the other four resolvers (a
# genuine over-approximation risk, not a silent gap: a shadowing local
# could theoretically cause a spurious "detected" on a name that is
# locally rebound to something harmless), accepted for this pass given
# kotlin's own grammar has no separate compilation-unit-vs-function-body
# scope split as clean as C's `_C_SCOPE_TYPES`/rust's `_RUST_SCOPE_TYPES`
# to hang position-aware bookkeeping off of without materially more
# machinery than this ticket's own time budget allows. A future pass
# tightening this to per-function scoping (mirroring `_c_scope_bound_
# names`'s shape against kotlin's `function_declaration`/`class_body`
# nodes) is a natural follow-up, not attempted here.