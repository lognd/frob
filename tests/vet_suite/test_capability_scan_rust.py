from pathlib import Path


class TestCapabilityScanRustBindingResolution:
    """T-0378: Rust sibling of `TestCapabilityScanBindingResolution`/
    `TestCapabilityScanTsBindingResolution` -- before this, Rust capability
    scanning was pure lexical needle-matching, so an `as`-aliased `use`
    import to a dangerous path evaded it entirely (`use std::process::
    Command as C; C::new(cmd)` never contains the literal "Command::new("
    text the needle table looks for). These tests lock the fix's litmus:
    the aliased evasion now DETECTED, local shadowing still NOT detected
    (no false positives)."""

    def test_use_as_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Evasion case: `use std::process::Command as C; C::new(cmd)` -- the
        # raw text never contains "Command::new(", only the `use` line's
        # own "std::process::Command" text.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text('use std::process::Command as C;\nfn f() { C::new("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_operation_names_registry_entry_for_use_alias(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        # `_scan_file_operations`'s resolver-backed sibling: an `as`-aliased
        # `use` still names the real registry entry (library="std::
        # process"), not just a bare kind label.
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "pkg.rs"
        pkg.write_text('use std::process::Command as C;\nfn f() { C::new("sh"); }\n')
        ops = _scan_file_operations(pkg)
        assert any(
            op.capability_kind == "exec" and op.library == "std::process" for op in ops
        )

    def test_bare_use_import_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # An unaliased `use` (no rename) still resolves through the same
        # binding table -- `Command::new(cmd)` after `use std::process::
        # Command;`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text('use std::process::Command;\nfn f() { Command::new("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_param_shadowing_use_alias_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Shadow case: a function parameter named `C` shadows a `use
        # std::process::Command as C` alias for the duration of that
        # function -- calling `C::new(...)` inside must not resolve to
        # `std::process::Command::new`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'use std::process::Command as C;\nfn f(C: i32) { C::new("sh"); }\n'
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_let_shadowing_use_alias_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Shadow case: a local `let C = ...` binding shadows the `use`
        # alias for the rest of that function body.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'use std::process::Command as C;\nfn f() { let C = 5; C::new("sh"); }\n'
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_bare_name_call_with_no_use_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # No naive bare-name false positive: calling `C::new(...)` with no
        # `use` binding anywhere in the file must not resolve.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text('fn f() { C::new("sh"); }\n')
        assert "exec" not in scan_file_capabilities(pkg)

    def test_call_before_rebinding_still_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0378 round 2 (reviewer REJECT, T-0339 fail-closed): round 1's
        # shadow check was ORDER-INSENSITIVE -- it collected every name
        # bound ANYWHERE in the scope regardless of position, so a call
        # textually BEFORE a same-named `let` rebinding was wrongly
        # treated as already shadowed and the real dangerous call got
        # silently dropped. A `let` does not hoist in Rust: the call here
        # executes before `let C = 5` takes effect, so it MUST still
        # resolve through the `use`-bound alias.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            "fn f() {\n"
            '    C::new("sh");\n'
            "    let C = 5;\n"
            "}\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_call_after_rebinding_still_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0378 round 2 sibling of the ordering test above: the position-
        # aware fix must not become UNCONDITIONALLY permissive -- a call
        # AFTER the same `let C = 5` rebinding is still correctly shadowed
        # (this is `test_let_shadowing_use_alias_not_detected` restated
        # with an explicit two-statement body so both orderings are
        # exercised side by side).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            "fn f() {\n"
            "    let C = 5;\n"
            '    C::new("sh");\n'
            "}\n"
        )
        assert "exec" not in scan_file_capabilities(pkg)


class TestCapabilityScanRustTaxonomyClosureResolution:
    """T-0661: Rust sibling of `TestCapabilityScanTaxonomyClosureResolution`
    (python T-0659)/`TestCapabilityScanTsTaxonomyClosureResolution` (TS
    T-0660) -- T-0378 covered aliased `use`/`use ... as` and local-shadow
    discipline, but left grouped/nested `use` lists, glob `use`, and any
    `let`-binding alias-copy-propagation entirely unbound (documented
    limitation). These tests lock the T-0661 fix's litmus against
    capability-evasion-taxonomy.md's Rust static-resolvable rows not
    already covered by T-0378: grouped/nested `use`, `pub use`, glob `use`,
    `let` binding, chained/shadowed `let`, tuple destructuring, and closure
    capture. Uses an `as`-aliased target throughout (`Command as C`/local
    let-bound names) so the raw text never contains the literal
    `"Command::new("` needle -- same isolation rationale as
    `TestCapabilityScanRustBindingResolution`."""

    def test_grouped_use_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy "use path::{a, b}" (grouped/nested) row, combined with
        # an `as` rename inside the group: `use std::process::{Command as
        # C, Stdio}; C::new(cmd)`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'use std::process::{Command as C, Stdio};\nfn f() { C::new("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_nested_grouped_use_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # A further-nested group (`a::{b, c::{d as e}}`) recurses correctly.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'use std::{fs, process::{Command as C}};\nfn f() { C::new("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_pub_use_reexport_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy "pub use re-export" row, combined with an `as` rename so
        # the raw text never contains "Command::new(".
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'pub use std::process::Command as C;\nfn f() { C::new("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_glob_use_let_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy "use path::*" (glob) row: `use std::process::*;` binds
        # the wildcard-fallback sentinel, and a further `let`-bound alias
        # off the glob-brought-in name resolves through it.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'use std::process::*;\nfn f() { let c = Command::new; c("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_let_binding_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy "let binding" row: `let f = std::process::Command::new;
        # f("sh").spawn();`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'use std::process::Command as C;\nfn f() { let g = C::new; g("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_chained_shadowed_let_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy "chained/shadowed let" row: `let f = cmd_new; let f = f;`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            'fn f() { let g = C::new; let g = g; g("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_tuple_destructure_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy "tuple/struct destructuring bind" row: `let (f, _) =
        # (Command::new, 0); f("sh");`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            'fn f() { let (g, _) = (C::new, 0); g("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_closure_capture_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy "closure capturing a bound path" row: `let f =
        # Command::new; let c = move |a| f(a).spawn();`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            'fn f() { let g = C::new; let c = move |a: &str| { g(a); }; c("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_glob_use_untracked_module_not_claimed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # No false claim: a glob `use` of a module `DANGEROUS_OPERATIONS`
        # does NOT curate must not resolve any bare name (honest
        # under-approximation, mirrors `_RUST_WILDCARD_DANGEROUS_MODULES`).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text('use my_own_crate::*;\nfn f() { helper("sh"); }\n')
        assert "exec" not in scan_file_capabilities(pkg)

    def test_closure_param_shadowing_let_alias_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # No regression: a CLOSURE parameter of the same name as an
        # enclosing `let`-aliased dangerous target shadows it FOR THE
        # CLOSURE'S OWN BODY -- the alias table must not resolve through a
        # local closure-param shadow (the closure's own scope binds `g` to
        # nothing dangerous, unlike the enclosing function's scope).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            "fn f() {\n"
            "    let g = C::new;\n"
            "    let c = move |g: i32| { g(5); };\n"
            "    c(5);\n"
            "}\n"
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_let_binding_benign_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # No regression: a `let` binding to an ORDINARY (non-`use`-bound)
        # value must stay silent.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text('fn f() { let x = 5; println!("{}", x); }\n')
        assert "exec" not in scan_file_capabilities(pkg)

    def test_function_pointer_coercion_from_named_fn_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "function-pointer coercion from a named fn" row:
        # `let f: fn(&str) -> _ = Command::new; f("sh");` -- an explicit
        # `fn(...)` type annotation on the `let` target does not change the
        # binding grammar from an ordinary `let` (per `_capability.py`'s
        # T-0662 comment: a typedef/type annotation only renames the
        # declared TYPE, not the binding shape), so this reduces to the
        # same code path `test_let_binding_detected` already locks.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            'fn f() { let g: fn(&str) -> _ = C::new; g("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_type_alias_for_function_pointer_type_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "`type` alias (data, not routing by itself, but
        # aliases the function-pointer type)" row: `type Spawner = fn(&str)
        # -> Child;` then `let f: Spawner = Command::new; f("sh");` -- the
        # `type` item itself never routes a call (the doc's own note); what
        # this row needs a litmus for is the SUBSEQUENT `let` binding typed
        # through the alias, same reduction as the fn-pointer-coercion row
        # above.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            "type Spawner = fn(&str) -> std::process::Child;\n"
            'fn f() { let g: Spawner = C::new; g("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_struct_update_field_rebind_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666/T-1063: taxonomy "field rebinding via struct update" row:
        # `let h = Handlers { run: Command::new, ..default }; (h.run)
        # ("sh");`. Closed by T-1063's `_record_rust_field_alias`/`_build_
        # rust_field_alias_table` (file-wide field-name-keyed table, mirrors
        # C's `_record_c_field_alias`/`_c_field_alias_table`) plus a new
        # parenthesized-field-expression call-target shape in `_collect_
        # rust_candidates`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            "struct Handlers { run: fn(&str) -> std::process::Child }\n"
            "fn f(default: Handlers) {\n"
            "    let h = Handlers { run: C::new, ..default };\n"
            '    (h.run)("sh");\n'
            "}\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_macro_rules_expansion_emitting_fixed_call_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "`macro_rules!` expansion emitting a fixed call"
        # row. Honest documented limitation: this module's own comment
        # ("`macro`-free language has no analog to Rust's `macro_rules!`
        # row") is about OTHER languages lacking the row, not about Rust
        # itself having macro-expansion-aware resolution -- there is no
        # `macro_rules!`/macro-invocation handling anywhere in the Rust
        # resolver (no `macro_rule`/`macro_invocation` node type is ever
        # matched). A macro invocation SITE (`run!("sh")`) produces no
        # finding since the resolver never expands it to see the
        # `Command::new(...).spawn()` the macro body defines. This fixture
        # locks that honest current gap rather than leaving the row
        # unregistered.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            'macro_rules! run { ($x:expr) => { C::new("sh").arg($x).spawn() } }\n'
            'fn f() { run!("x"); }\n'
        )
        assert "exec" not in scan_file_capabilities(pkg)
