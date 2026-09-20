---
id: T-0378
title: 'vet: Rust binding-aware capability resolution'
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
  old_length: 376
  new_length: 2599
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_kotlin.py'
  actor: logan
  at: '2026-09-19'
  old_length: 2598
  new_length: 4324
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_python.py'
  actor: logan
  at: '2026-09-19'
  old_length: 4323
  new_length: 9024
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_rust.py'
  actor: logan
  at: '2026-09-19'
  old_length: 9023
  new_length: 12850
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_typescript_bindtable.py'
  actor: logan
  at: '2026-09-19'
  old_length: 12849
  new_length: 21765
evidence:
- tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustBindingResolution::test_call_before_rebinding_still_detected
- tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustBindingResolution::test_call_after_rebinding_still_not_detected
- tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustBindingResolution::test_use_as_alias_detected
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Extend binding-aware resolution to Rust: resolve 'use' aliases (as-renames) and path resolution so `use std::process::Command as C` still resolves to the dangerous capability, mirroring Python's scope-shadowing discipline (a local binding of the same name must NOT false-positive). Acceptance: aliased use-import still caught; local shadow not caught; adversarial tests added.

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

T-4718 sweep (condensed from src/frob/vet/_capability_rust.py:19-78,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

# T-0378: import/binding-aware resolution for Rust, mirroring the T-0328
# python / T-0377 TS discipline above but scoped to what a Rust `use`
# statement actually needs: `use std::process::Command as C;` binds a local
# alias to a fully-qualified path, and a subsequent `C::new(...)` call must
# resolve to `std::process::Command::new` the same way `Command::new(...)`
# would -- the raw-text lexical scan looks for a literal `Command::new(`/
# `std::` substring, so a renamed `use` import evades it entirely.
#
# Bind table (`_rust_use_table`) forms:
#   use std::process::Command;        -> {"Command": "std::process::Command"}
#   use std::process::Command as C;   -> {"C": "std::process::Command"}
#   use foo;                          -> {"foo": "foo"}
# T-0661 closes the T-0378 grouped/nested-`use`/glob-`use` gap: `use a::{b,
# c as d};` -> `{"b": "a::b", "d": "a::c"}` (`_bind_rust_use_list`, recursed
# for a further-nested group like `a::{b::{c, d as e}}`); `use std::process
# ::*;` -> a best-effort glob wildcard fallback for a `_RUST_WILDCARD_
# DANGEROUS_MODULES`-curated path only (`_bind_rust_use_wildcard`, mirrors
# the python resolver's `from X import *` fallback). `use std::fs::{self,
# File};` -- the `self` re-export-of-the-parent-module keyword inside a
# group -- is not specially recognized (falls through as an ordinary
# `identifier` child bound to `"<prefix>::self"`, a harmless dead binding
# rather than a crash); a real fix is a narrow follow-up, not attempted
# here since it is not itself a capability-routing evasion.
#
# `pub use` re-export (taxonomy row): needs NO special-case at all -- a
# `pub` visibility modifier is simply one more `use_declaration` child this
# walk never dispatches on, so the path/alias/group/glob children are found
# exactly the same regardless of whether `pub` precedes them.
#
# Scope-awareness (mandatory, mirrors T-0328/T-0377): a function/closure
# PARAMETER or a local `let` binding of the same name as a `use`-bound alias
# SHADOWS it in every enclosing scope from the site up to the file
# (`source_file`) root -- `fn f() { let C = 5; C::new(...) }` (a local
# variable that happens to share the alias's name, then gets called like a
# path -- contrived but the same no-false-positive discipline as the
# python/TS resolvers) must not resolve `C` to the `use`-bound path.
#
# T-0378 ROUND 2 (reviewer REJECT -- soundness hole, T-0339 fail-closed):
# round 1's shadow check was ORDER-INSENSITIVE -- it collected every name
# bound ANYWHERE in the enclosing scope into a plain set, so a capability
# call textually BEFORE a same-named `let` rebinding was wrongly treated as
# already shadowed and silently dropped:
#
#   use std::process::Command as C;
#   fn f() {
#       C::new("sh");   // executes BEFORE `let C` -- MUST resolve to exec
#       let C = 5;
#   }
#
# A `let` binding does not hoist in Rust -- a use of the name before its
# `let` refers to whatever it resolved to beforehand (here, the `use`-bound
# alias), not the not-yet-effective local. Fixed: `_rust_scope_bound_names`
# now maps `name -> byte position from which it shadows`, not just `name`;
# `_rust_shadowing_scope` only treats a binding as shadowing a given call
# site when `site.start_byte >= that position` (`_RUST_ALWAYS_SHADOWS`, -1,
# for parameters and nested-fn-item names, which ARE in scope for the whole
# body/block by construction -- only `let` targets get a real position, the
# `let_declaration` node's own `start_byte`). A name rebound multiple times
# keeps its EARLIEST recorded position (`_record_rust_binding`): once truly
# shadowed, a call site stays shadowed, it never un-shadows.

T-4718 sweep (condensed from
src/frob/vet/_capability_typescript_bindtable.py:18-147, trimmed for
DOCARCH002's 12-line cap): the trimmed block's full original text, kept
verbatim below.

# T-0377: import/binding-aware resolution for TypeScript/JS, mirroring the
# T-0328/T-0337 Python discipline above -- same shape (import/require/alias
# table + scope-shadowing over the same tree-sitter parse), different
# grammar. Before this, TS/JS capability scanning was pure lexical needle-
# matching over raw text, so any renamed/destructured/namespaced import to a
# dangerous module evaded it entirely: `import {run as r} from
# 'child_process'; r(cmd)` never contains the literal text "child_process"
# or "exec("/"run(" the needle table looks for at the call site; neither
# does `const {exec} = require('child_process'); exec(cmd)` or `import cp =
# require('child_process'); cp.exec(cmd)`.
#
# Import/require forms resolved into the binding table (`_ts_import_table`):
#   import {run as r} from 'child_process'   -> {"r": "child_process.run"}
#   import * as cp from 'child_process'      -> {"cp": "child_process"}
#   import dflt from 'child_process'         -> {"dflt": "child_process"}
#   import cp = require('child_process')     -> {"cp": "child_process"}
#   const {exec} = require('child_process')  -> {"exec": "child_process.exec"}
#   const cp = require('child_process')      -> {"cp": "child_process"}
#
# Scope-awareness (mandatory to avoid FALSE POSITIVES, mirrors T-0328): a
# function/method PARAMETER, or a local `const`/`let`/`var` binding, of the
# same name as an imported binding SHADOWS it in every enclosing scope from
# the site up to the module (`program`) root -- `function g(run){ run(x); }`
# must not resolve `run` to a dangerous import. A property access on an
# unrelated object (`class Job { run(){} }` then `new Job().run()`) never
# even reaches the import table: the object side of that member expression
# is a `new_expression`/`call_expression`, not a resolvable identifier/
# member chain, so resolution stops there by construction -- same posture
# as `Job().run()` in the Python resolver.
#
# T-0377 REVIEWER ROUND 2 (two live evasion classes the round-1 pass above
# missed -- both ORDINARY JS/TS idioms, not obfuscation, confirmed against
# axios/"net" to isolate the resolver from the pre-existing lexical layer):
#
#   1. COMPUTED/BRACKET MEMBER ACCESS: `require('axios')['get'](url)` and
#      `const ax = require('axios'); ax['get'](url)` evaded round 1 --
#      `_resolve_ts_expr`/`_collect_ts_candidates` only ever inspected
#      `identifier`/`member_expression` nodes, never `subscript_expression`.
#      Fixed: `_resolve_ts_subscript` resolves `obj['fn']` the same as
#      `obj.fn` whenever the subscript is STATICALLY resolvable -- a
#      string literal, or (round 3) a NO-INTERPOLATION TEMPLATE LITERAL
#      (`` ax[`get`](url) `` -- template literals are an everyday idiom
#      many lint configs PREFER over quotes, not an obfuscation trick, and
#      `` `get` `` carries identical static text to `'get'`). A genuinely
#      COMPUTED subscript -- a non-literal key OR an INTERPOLATED template
#      literal (`ax[dynamicKey](url)`, `` ax[`${dynamicKey}`](url) ``) --
#      still resolves to `None`: the property name is a runtime value this
#      static resolver cannot evaluate. This is an intentional, tested,
#      documented gap (`test_computed_subscript_not_detected`,
#      `test_interpolated_template_subscript_not_detected`), not a silent
#      one -- filed as follow-up T-draft-e7c8b53c (dynamic-key resolution
#      is a fundamentally different problem: it needs either taint-style
#      "any string-keyed access on a dangerous object is worth flagging"
#      heuristics, or giving up precision entirely for that one case).
#   2. DYNAMIC `import()`: `import('axios').then(ax => ax.get(url))` and
#      `const ax = await import('axios'); ax.get(url)` evaded round 1 --
#      `_ts_import_table`'s walk only ever dispatched on `import_statement`/
#      `variable_declarator`, never an `import(...)` CALL expression (the
#      dynamic form is syntactically a call, not a statement). Fixed:
#      `_bind_ts_dynamic_import_then` binds a `.then(cb)` callback's first
#      parameter to the imported module; `_ts_module_call_target` (shared
#      with the `require()` path via `_unwrap_ts_await`) resolves an
#      `await`-ed dynamic import assignment the same way `require()`
#      already was. Both are STANDARD ways to consume a dynamic import
#      (the standard way to conditionally load a module in TS/JS at all,
#      and a natural place to hide a dangerous one) -- both now resolve
#      identically to a namespace `import * as`.
#
# T-0432 (computed/non-literal bracket-subscript resolution, light
# dataflow): a COMPUTED subscript that is a bare identifier or a single-
# substitution template literal (`ax[key](url)`, `` ax[`${key}`](url) ``)
# now resolves when `key` is bound to exactly ONE string literal anywhere
# in the file (`_ts_local_string_bindings`/`_ts_bound_subscript_text`) --
# closes the trivial `const key = 'exec'; ax[key](url)` indirection the
# T-0377 audit flagged as accepted-but-checkable. Deliberately NOT real
# reaching-definitions dataflow: a name reassigned to two DIFFERENT
# literal values anywhere in the file (including a plain `key = 'x'`
# reassignment, not just a second declarator) is excluded from the table
# entirely (stays unresolved, never guesses which value is live at the
# subscript site); a name assigned a non-literal value (a function call, a
# concatenation, a member-access key) is excluded the same way; a template
# literal with MORE than one substitution or any surrounding literal text
# still resolves to `None`. Considered and REJECTED: a fail-open heuristic
# ("any bracket access on an object resolved to a known-dangerous import
# is worth flagging regardless of subscript shape") -- the false-positive
# cost against ordinary dynamic-dispatch idioms (a lookup table, a plugin
# registry) was judged too high without a concrete finding to weigh it
# against; the light single-literal-binding dataflow above is the
# genuinely-closed subset, everything else stays an honest, tested
# limitation (`test_non_literal_bound_subscript_not_detected`,
# `test_multi_substitution_template_subscript_not_detected`,
# `test_reassigned_const_string_subscript_not_detected`).
#
# Known limitations, documented rather than silently eaten (mirrors this
# module's "Honest limits" posture): `export {x as y}` / re-export forms
# add no binding (not import sites -- a cross-FILE resolution, and this
# resolver, like the whole capability scanner, works one file at a time; no
# `export ... from`/`export * from`/`export default` cross-module linking is
# attempted, matching the taxonomy's own "needs source-module enumerability"
# caveat for the `export * from` row); a function-scoped `const`/`require`
# is folded into the same file-wide binding table as a module-level one when
# it is a plain `require()` destructure (a narrow, safe-direction over-
# approximation, same as Python's function-scoped `import`); a COMPUTED
# bracket subscript -- a NON-LITERAL key OR an INTERPOLATED template literal
# (a static, no-interpolation template literal DOES resolve, round 3 above)
# -- resolves only through the T-0432 single-literal-binding case above,
# else stays unresolved (T-draft-e7c8b53c tracks the fully-general case, see
# above); a `.then(cb)` callback's module binding is added to the FILE-WIDE
# table rather than scoped to the callback body (the same over-
# approximation as every other binding here -- can only ADD a resolution,
# never suppress a real one). A `class` FIELD holding a bound reference
# (taxonomy "class field/method holding a bound reference" row, `class C {
# run = cp.exec; }`) is NOT resolved through a later `new C().run(x)` call
# site -- that needs points-to tracking through CONSTRUCTED instances, a
# strictly harder problem than the by-local-name object-identity best effort
# `_ts_attr_rebind_lookup` gives ordinary object rebinding (T-0660); a
# `macro`-free language has no analog to Rust's `macro_rules!` row, so no
# gap exists here for it.
#
# T-0660: closes the previously-documented "no scope-local alias copy-
# propagation" gap (the T-0337 Python enhancement's TS/JS sibling) --
# `_build_ts_alias_table`/`_record_ts_alias`/`_record_ts_declarator_alias`/
# `_record_ts_default_param_aliases` now chase a local reassignment
# (`f = cp.exec`), a chained assignment (`a = b = cp.exec`), an array-
# destructuring bind (`const [f] = [cp.exec]`), default-parameter
# forwarding (`function f(cb = cp.exec)`), and a by-name member-target
# rebind (`obj.run = cp.exec`) the same way the python resolver's alias
# table does.
# C-C++/Kotlin remain OUT of scope for this pass; Rust gets its own binding-
# aware pass, T-0378 below.