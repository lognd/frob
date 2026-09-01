from pathlib import Path

from tests.conftest import _ts_find  # noqa: F401 -- T-3596


class TestCapabilityScanKotlinTaxonomyClosureResolution:
    """T-0664: kotlin sibling of `TestCapabilityScanCTaxonomyClosureResolution`/
    `TestCapabilityScanCppTaxonomyClosureResolution` -- import/`::`-reference/
    typealias name-binding resolution for
    `docs/design/capability-evasion-taxonomy.md`'s Kotlin table, closing
    the gap `frob.lang`'s T-0723 central-dispatch wiring opened (kotlin
    files now reach `frob.lang.parse_file`, but `frob.vet._capability` had
    no import/alias-aware resolution pass for the language until this
    ticket -- only the pre-existing raw-text needle scan)."""

    def test_plain_import_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `import java.lang.Runtime; Runtime.getRuntime().exec(x)`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            'import java.lang.ProcessBuilder\nfun f() { ProcessBuilder("sh") }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_import_as_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `import java.lang.Runtime as Rt; Rt.getRuntime().exec(x)`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            'import java.lang.Runtime as Rt\nfun f() { Rt.getRuntime().exec("sh") }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_import_as_bare_constructor_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Simpler `import ... as` shape (no chained method call): a bare
        # constructor-call needle ("ProcessBuilder(") through an alias.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text('import java.lang.ProcessBuilder as PB\nfun f() { PB("sh") }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_bare_callable_reference_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `val f = ::runCmd; f(x)` -- an UNTYPED `::` callable
        # reference to a plain top-level name.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text('val f = ::ProcessBuilder\nfun g() { f("sh") }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_typed_callable_reference_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `val f = Runtime::exec; f(x)` -- a receiver-typed
        # `::` bound-member reference.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            "class SomeClass\n"
            "val f = SomeClass::getSharedPreferences\n"
            'fun g() { f("sh") }\n'
        )
        assert "client_storage" in scan_file_capabilities(pkg)

    def test_typealias_for_function_type_needs_no_special_resolution(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `typealias Handler = (String) -> Unit; val f:
        # Handler = ::runCmd; f(x)` -- the `typealias` only renames the
        # DECLARED TYPE (never touched by this resolver); the `val`'s own
        # VALUE is still a plain `::`-reference, resolved unchanged.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            "typealias Handler = (String) -> Unit\n"
            "val f: Handler = ::ProcessBuilder\n"
            'fun g() { f("sh") }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_chained_val_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # `f` aliases `ProcessBuilder` via `::`; `g` (a second `val`) is
        # initialized FROM `f` -- resolves transitively, document-order.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text('val f = ::ProcessBuilder\nval g = f\nfun h() { g("sh") }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_curated_wildcard_import_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `import java.lang.*; Runtime.getRuntime().exec(x)`
        # -- a wildcard import of a CURATED dangerous package resolves an
        # unqualified name through it.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text('import java.lang.*\nfun f() { ProcessBuilder("sh") }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_uncurated_wildcard_import_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # A wildcard import of a package NOT in the curated set must not
        # resolve an otherwise-unrelated unqualified name -- fail-closed,
        # no false claim of resolving an untracked package's contents.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            'import com.example.untracked.*\nfun f() { totallyUnrelatedName("sh") }\n'
        )
        assert scan_file_capabilities(pkg) == frozenset()

    def test_unaliased_bare_reference_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # A `val` bound to an ordinary (non-callable-reference, non-chained)
        # expression must not resolve -- fail-closed, no guess.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text('val f = 5\nfun g() { println("sh") }\n')
        assert scan_file_capabilities(pkg) == frozenset()

    def test_destructuring_declaration_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666/T-1063: taxonomy "destructuring declaration" row: `val (a,
        # b) = Pair(::runCmd, 0); a(x)`. Closed by T-1063's `_record_kt_
        # destructure_alias`/`_kt_destructure_value_elements` (positional
        # binding of each `multi_variable_declaration` element to its RHS
        # call-argument, mirrors rust's tuple-destructure alias table).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text('val (a, b) = Pair(::ProcessBuilder, 0)\nfun g() { a("sh") }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_lambda_closure_capturing_bound_name_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "lambda/closure capturing a bound name" row:
        # `val f = ::runCmd; val g = { x: String -> f(x) }; g(x)`. The
        # kotlin var-alias table is built file-wide (no per-function scope
        # split, T-0664), so a lambda body's call to an outer `val` alias
        # resolves the same as any other reference.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            "val f = ::ProcessBuilder\n"
            'val g = { x: String -> f() }\nfun h() { g("sh") }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_default_parameter_forwarding_callable_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666/T-1063: taxonomy "default parameter forwarding a callable"
        # row: `fun call(cb: (String) -> Unit = ::runCmd) { cb(x) }`. Closed
        # by T-1063's `_record_kt_param_default_aliases` -- kotlin's grammar
        # hangs a parameter's default value as a SIBLING of the `parameter`
        # node inside `function_value_parameters` (not a child of
        # `parameter` itself), so this walks the sibling list positionally
        # rather than mirroring C++'s single-node `_record_c_default_param_
        # alias` shape directly.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            'fun call(cb: (String) -> Unit = ::ProcessBuilder) { cb("sh") }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_extension_function_reference_bound_via_import_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "extension function reference bound via import"
        # row: `import kotlin.io.path.exists` -- the pattern for binding a
        # top-level callable via an ordinary import. This reduces to the
        # SAME import-table code path `test_plain_import_detected` already
        # locks (an extension function's qualified name is bound and
        # resolved identically to any other top-level import).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            'import java.lang.ProcessBuilder\nfun g() { ProcessBuilder("sh") }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_operator_fun_invoke_making_object_directly_callable_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "`operator fun invoke` making an object directly
        # callable" row: `class Handler { operator fun invoke(x: String) =
        # Runtime.getRuntime().exec(x) }; val h = Handler(); h(x)`. The
        # taxonomy doc's own caveat says this "still needs points-to on the
        # receiver instance" -- a genuine, currently UNRESOLVED gap: the
        # kotlin resolver has no receiver-instance points-to (no tracking
        # from `val h = Handler()` to a later bare `h(x)` call resolving
        # through the class's `invoke` operator). This fixture locks the
        # CURRENT honest under-detection; T-1047 tracks adding
        # instance-points-to for `operator fun invoke` to close it.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            "import java.lang.Runtime\n"
            "class Handler { operator fun invoke(x: String) { "
            "Runtime.getRuntime() } }\n"
            'fun g() { val h = Handler(); h("sh") }\n'
        )
        assert scan_file_capabilities(pkg) == frozenset()


class TestCapabilityScanKotlinAliasTablePredicates:
    """T-0664 white-box mutation-kill coverage (TEST016) for the private
    kotlin resolver predicates -- mirrors `TestCapabilityScanCAliasTable
    Predicates`/`TestCapabilityScanCppAliasTablePredicates`'s pattern."""

    def test_import_table_plain_import_binds_last_segment(self) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_import_table kind="unit"
        # Kills the plain-import branch's `.rsplit(".", 1)[-1]` mutant and
        # the `elif alias_node is not None:`/`is_wildcard` dispatch: a
        # plain `import a.b.C` (no `as`, no `*`) must bind `"C"` (the last
        # dotted segment), not the full path or nothing at all.
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_import_table

        tree = parse_kotlin(b"import java.lang.ProcessBuilder\n")
        table, wildcard = _kt_import_table(tree.root_node)
        assert table == {"ProcessBuilder": "java.lang.ProcessBuilder"}
        assert wildcard == frozenset()

    def test_import_table_as_alias_binds_alias_name(self) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_import_table kind="unit"
        # Kills `elif alias_node is not None:`'s Is-swap mutant: an `as`
        # import must bind the ALIAS name, not the last dotted segment.
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_import_table

        tree = parse_kotlin(b"import java.lang.Runtime as Rt\n")
        table, wildcard = _kt_import_table(tree.root_node)
        assert table == {"Rt": "java.lang.Runtime"}
        assert "Runtime" not in table
        assert wildcard == frozenset()

    def test_import_table_curated_wildcard_recorded(self) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_import_table kind="unit"
        # Kills `dotted in _KT_WILDCARD_DANGEROUS_MODULES`'s membership
        # mutant: a wildcard import of a CURATED package must land in the
        # wildcard set, not the plain import table.
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_import_table

        tree = parse_kotlin(b"import java.lang.*\n")
        table, wildcard = _kt_import_table(tree.root_node)
        assert table == {}
        assert wildcard == frozenset({"java.lang"})

    def test_import_table_uncurated_wildcard_not_recorded(self) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_import_table kind="unit"
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_import_table

        tree = parse_kotlin(b"import com.example.untracked.*\n")
        table, wildcard = _kt_import_table(tree.root_node)
        assert table == {}
        assert wildcard == frozenset()

    def test_property_name_and_value_returns_none_none_without_variable_declaration(
        self,
    ) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_property_name_and_value \
        # kind="unit"
        # Kills `if name_node is None: return None, None`'s guard: a
        # `property_declaration` node itself passed with no `variable_
        # declaration` child at all (constructed here via a destructuring
        # declaration, which has no plain `variable_declaration` child)
        # must return `(None, None)`, not crash on a `None` var_decl.
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_property_name_and_value

        tree = parse_kotlin(b"val (a, b) = Pair(1, 2)\n")
        prop = _ts_find(tree.root_node, "property_declaration")
        assert prop is not None
        name_node, value = _kt_property_name_and_value(prop)
        assert name_node is None
        assert value is None

    def test_property_name_and_value_extracts_name_and_value(self) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_property_name_and_value \
        # kind="unit"
        # Kills the `seen_eq`/`if c.type == "=":`'s Eq mutant: the VALUE
        # returned must be the child strictly AFTER the `=` token, not the
        # `=` token itself or an earlier child.
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_property_name_and_value

        tree = parse_kotlin(b"val f = runCmd\n")
        prop = _ts_find(tree.root_node, "property_declaration")
        assert prop is not None
        name_node, value = _kt_property_name_and_value(prop)
        assert name_node is not None and name_node.text == b"f"
        assert value is not None and value.type == "simple_identifier"
        assert value.text == b"runCmd"

    def test_resolve_callable_reference_rejects_non_identifier_member(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_kotlin.py::_kt_resolve_callable_reference kind="unit"
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_resolve_callable_reference

        tree = parse_kotlin(b"val f = ::runCmd\n")
        ref = _ts_find(tree.root_node, "callable_reference")
        assert ref is not None
        assert _kt_resolve_callable_reference(ref, {}) == "runCmd"

    def test_resolve_callable_reference_typed_falls_back_to_literal_receiver(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_kotlin.py::_kt_resolve_callable_reference kind="unit"
        # `tree-sitter-kotlin` only parses `X::Y` as `callable_reference`
        # (as opposed to a bare `navigation_expression`) once `X` is a
        # KNOWN type in the file -- a preceding `class` declaration for
        # the receiver, matching real kotlin usage (referencing a member
        # of an unresolvable/undeclared type is not valid kotlin either).
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_resolve_callable_reference

        tree = parse_kotlin(
            b'class Runtime\nval f = Runtime::exec\nfun g() { f("x") }\n'
        )
        ref = _ts_find(tree.root_node, "callable_reference")
        assert ref is not None
        assert _kt_resolve_callable_reference(ref, {}) == "Runtime.exec"
        assert (
            _kt_resolve_callable_reference(ref, {"Runtime": "java.lang.Runtime"})
            == "java.lang.Runtime.exec"
        )

    def test_resolve_expr_text_returns_none_for_unbound_identifier(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_resolve_expr_text \
        # kind="unit"
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_resolve_expr_text

        tree = parse_kotlin(b"fun f() { g(x) }\n")
        call = _ts_find(tree.root_node, "call_expression")
        assert call is not None
        callee = call.children[0]
        assert _kt_resolve_expr_text(callee, {}, {}) is None

    def test_resolve_expr_text_call_expression_wraps_with_parens(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_resolve_expr_text \
        # kind="unit"
        # The intermediate-call "()" marker this resolver's own docstring
        # explains is required for the real taxonomy needle to match at
        # all -- locked in directly against the private predicate.
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_resolve_expr_text

        tree = parse_kotlin(b"fun f() { Rt.getRuntime() }\n")
        call = _ts_find(tree.root_node, "call_expression")
        assert call is not None
        resolved = _kt_resolve_expr_text(call, {"Rt": "java.lang.Runtime"}, {})
        assert resolved == "java.lang.Runtime.getRuntime()"

    def test_kt_call_callee_picks_last_non_call_suffix_child(self) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_call_callee kind="unit"
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_call_callee

        tree = parse_kotlin(b"fun f() { g() }\n")
        call = _ts_find(tree.root_node, "call_expression")
        assert call is not None
        callee = _kt_call_callee(call)
        assert callee is not None and callee.type == "simple_identifier"
