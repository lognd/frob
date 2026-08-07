## Done report

Rust use/use-as binding-aware capability resolution in vet/_capability.py
(_rust_use_table, _resolve_rust_expr/_identifier/_scoped, shadow logic,
_rust_binding_capabilities/operations), wired into scan_file_capabilities +
_scan_file_operations, mirroring the Python (T-0328) and TS (T-0377)
resolvers. An aliased `use std::process::Command as C; C::new(...)` resolves
to exec; a bare `use foo::danger; danger()` resolves; a local param/let
shadow of the alias correctly does NOT false-positive.

SOUNDNESS FIX (reviewer round-1 REJECT, security-critical): the first cut's
shadow check was ORDER-INSENSITIVE -- it treated a name as shadowed anywhere
in the enclosing scope, so a capability call occurring textually BEFORE a
same-name local rebinding was silently MISSED (a real dangerous call
un-flagged). Fixed: _rust_scope_bound_names now returns dict[name -> shadow-
onset byte position]; params/nested-fn always shadow (-1), a `let` records
its own start_byte; _rust_shadowing_scope only shadows when
site.start_byte >= that position. Verified against the reviewer's exact
repro (`C::new("sh"); let C = 5;` now returns exec, was frozenset()); the
reverse order still correctly returns nothing. 2 ordering regression tests
added; 180 test_vet.py pass; fail-closed (T-0339) preserved. Grouped/nested
`use {..}` documented as an explicit out-of-scope limitation, not a silent
miss.

Evidence (3 of 8): call-before-rebinding-still-detected (the security
property), call-after-rebinding-still-not-detected, use-as-alias-detected.
Filed T-0468: the Python resolver may have the same order-insensitivity class
for attribute-access rebinds -- needs a failing repro before fixing. Landed
via 3-way (branch-committed diff).
