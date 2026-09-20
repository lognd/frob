---
id: T-0328
title: 'capability scanner: import/binding-aware symbol resolution, not evadable substring
  needles'
state: done
kind: security
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability.py
- src/frob/vet/_capability_registry.py
- tests/**
- docs/modules/vet.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_c.py'
  actor: logan
  at: '2026-09-19'
  old_length: 2219
  new_length: 4442
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_kotlin.py'
  actor: logan
  at: '2026-09-19'
  old_length: 4441
  new_length: 6167
evidence:
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScanBindingResolution::test_import_as_alias_detected
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScanBindingResolution::test_from_import_detected
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScanBindingResolution::test_from_import_as_detected_with_correct_kind
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScanBindingResolution::test_import_as_alias_operation_names_registry_entry
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScanBindingResolution::test_method_shadowing_import_not_detected
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScanBindingResolution::test_param_shadowing_import_not_detected
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScanBindingResolution::test_local_variable_shadowing_import_not_detected
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScanBindingResolution::test_bare_name_call_with_no_import_not_detected
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScanBindingResolution::test_direct_call_still_detected_via_resolver
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScanBindingResolution::test_attribute_only_env_access_via_alias_detected
designated_repro_test: null
acceptance:
- text: given 'import subprocess as sp' then 'sp.run(x)', when scanned, then exec
    is observed (alias resolved to subprocess.run) -- currently MISSED
  evidence: []
- text: given 'from subprocess import run' then 'run(x)', when scanned, then exec
    is observed (from-import resolved) -- currently MISSED
  evidence: []
- text: given 'from os import system as e' then 'e(x)', when scanned, then exec is
    observed (NOT eval) -- currently WRONG kind
  evidence: []
- text: given a LOCAL binding shadowing an import (a class method or var named 'run',
    a param 'system'), when scanned, then the dangerous kind is NOT observed -- scope-aware,
    no false positive
  evidence: []
- text: given re-export chains and attribute access on a shadowed name (x.subprocess.run
    where subprocess is an unrelated attribute), then it does not falsely fire
  evidence: []
threat: elevation-of-privilege
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CONFIRMED live 2026-07-19: frob.vet._capability is fundamentally a lexical substring/needle matcher (even after T-0308 comment/word-boundary hardening). It only matches the LITERAL qualified form in the registry needle (e.g. 'subprocess.run('), so it is EVADED by ordinary Python: 'import subprocess as sp; sp.run()' -> MISSED; 'from subprocess import run; run()' -> MISSED; 'from os import system as e; e()' -> reported 'eval' not 'exec'. This is an ELEVATION-OF-PRIVILEGE soundness hole -- a node can genuinely exec/net/ffi while the scanner observes nothing, so SYS100 never flags the undeclared capability, and a developer (lazy OR malicious) dodges the 'may' declaration just by aliasing an import. FIX: replace/augment the lexical match with real import/binding-aware resolution using the existing tree-sitter parse (frob.lang). Per language: (1) build the module's IMPORT/BINDING TABLE -- import X, import X as Y, from X import Z, from X import Z as W (python); the analogous forms for TS (import {x} from, import * as, require), rust (use path::to::item, use ... as), c/c++ (#include is coarse -- keep needles there but note the limit). (2) For each call/attribute site, resolve the leftmost name through the binding table (and enclosing scope) to its ORIGIN, reconstruct the fully-qualified target (sp.run -> subprocess.run; run -> subprocess.run), and match the registry by RESOLVED IDENTITY (module + attribute path), not raw text. (3) SCOPE-AWARENESS is mandatory to avoid FALSE POSITIVES: a local binding (param, assignment, class method, nested def) SHADOWS an import of the same name -- 'Job().run()' or a param 'system' must NOT resolve to the dangerous symbol. The registry likely needs a resolvable (library, symbol) key alongside the display needle. Python is the priority (highest coverage); design the resolver so TS/rust plug in. Keep the comment/string-exclusion + word-boundary guards. LITMUS: every evasion case above now detected; every shadowing case NOT detected; no new false positive on frob's own tree (frob check --only sys / capability tests unchanged); the exhaustiveness meta-test still green. This is the 'actually parse the symbols and see if they refer to what they match' upgrade.

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