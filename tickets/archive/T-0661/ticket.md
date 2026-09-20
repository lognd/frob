---
id: T-0661
title: 'vet: exhaustive Rust static-binding resolver (use/use-as/pub use/glob use)'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0339
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_rust.py'
  actor: logan
  at: '2026-09-19'
  old_length: 234
  new_length: 4061
evidence:
- tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_grouped_use_alias_detected
- tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_nested_grouped_use_alias_detected
- tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_pub_use_reexport_detected
- tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_glob_use_let_alias_detected
- tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_let_binding_detected
- tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_chained_shadowed_let_detected
- tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_tuple_destructure_detected
- tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_closure_capture_detected
- tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_glob_use_untracked_module_not_claimed
- tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_closure_param_shadowing_let_alias_not_detected
- tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_let_binding_benign_not_detected
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_member_rebind_lookup_used_only_for_identifier_object
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_member_rebind_lookup_skipped_without_alias_table
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_attr_rebind_lookup_climbs_past_non_matching_scope
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_resolve_expr_peels_through_chained_assignment
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_default_param_alias_recorded_for_identifier_pattern
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_default_param_alias_skips_missing_default_value
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_destructure_alias_tolerates_length_mismatch
- tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_destructure_alias_binds_only_identifier_elements
designated_repro_test: null
acceptance:
- text: Given every Rust static-resolvable construct in the taxonomy table, when the
    resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence:
  - tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_grouped_use_alias_detected
  - tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_nested_grouped_use_alias_detected
  - tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_pub_use_reexport_detected
  - tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_glob_use_let_alias_detected
  - tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_let_binding_detected
  - tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_chained_shadowed_let_detected
  - tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_tuple_destructure_detected
  - tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_closure_capture_detected
  - tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_glob_use_untracked_module_not_claimed
  - tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_closure_param_shadowing_let_alias_not_detected
  - tests/vet_suite/test_capability_scan_rust.py::TestCapabilityScanRustTaxonomyClosureResolution::test_let_binding_benign_not_detected
  - tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_member_rebind_lookup_used_only_for_identifier_object
  - tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_member_rebind_lookup_skipped_without_alias_table
  - tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_attr_rebind_lookup_climbs_past_non_matching_scope
  - tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_resolve_expr_peels_through_chained_assignment
  - tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_default_param_alias_recorded_for_identifier_pattern
  - tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_default_param_alias_skips_missing_default_value
  - tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_destructure_alias_tolerates_length_mismatch
  - tests/vet_suite/test_capability_scan_ts.py::TestCapabilityScanTsAliasTablePredicates::test_destructure_alias_binds_only_identifier_elements
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Implement per-scope, transitive, cycle-guarded static name-binding resolution for Rust per capability-evasion-taxonomy.md's Rust table (13 static + 6 opaque entries): use, use ... as, pub use re-export, glob use, module-path aliasing.

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