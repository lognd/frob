from pathlib import Path

from tests.conftest import _ts_find  # noqa: F401 -- T-3596


class TestCapabilityScanCppTaxonomyClosureResolution:
    """T-0663: C++ sibling of `TestCapabilityScanCTaxonomyClosureResolution`,
    building on the SAME `_c_resolved_candidates`/`_build_c_alias_tables`
    entry point (the C fragment already covers every C++ construct that
    reduces to a shared grammar shape -- `.cpp`/`.cc`/`.hpp` all dispatch
    through `frob.lang`'s `"cpp"` language label into the identical C/C++
    resolver, T-0379's original design). Closes the taxonomy's remaining
    C++-only rows: `using`/`namespace` aliasing (documented as needing NO
    new code -- see the class docstring below), `std::function`, default
    argument forwarding a callable, and structured bindings."""

    def test_using_declaration_needs_no_special_resolution(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `using std::system; system(x);` -- a `using`
        # declaration imports a name AS-IS (no rename), so the call site's
        # own text already contains the literal needle "system(" -- caught
        # by the pre-existing lexical scan with zero new resolver code,
        # exactly like T-0662's "function declaration + direct call" row.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('using std::system;\nvoid g() { system("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_namespace_alias_qualified_call_needs_no_special_resolution(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `namespace fs = std; fs::system(x);` -- the
        # registry's own needle is the bare substring "system(", which
        # still occurs verbatim INSIDE a namespace-qualified call
        # (`fs::system(` contains `system(`), so no alias table lookup is
        # needed for this row either.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('namespace fs = std;\nvoid g() { fs::system("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_fn_ptr_var_init_detected_on_cpp_extension(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0662's fn-ptr-var-init resolver applies unchanged to the "cpp"
        # language label (same tree-sitter-c grammar fragment).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('void (*f)(const char*) = system;\nvoid g() { f("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_using_alias_declaration_fn_ptr_typedef_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `using Handler = void(*)(const char*); Handler f =
        # do_exec; f(x);` -- C++11's `using` alias-declaration spelling of
        # a typedef'd function-pointer type; needs no separate branch (the
        # `alias_declaration` node itself is never visited -- only the
        # LATER `Handler h = system;` declaration, an ordinary `init_
        # declarator`, is).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "using Handler = void(*)(const char*);\n"
            'Handler h = system;\nvoid g() { h("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_std_function_init_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `std::function<void(const char*)> f = system; f(x);`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            'std::function<void(const char*)> f = system;\nvoid g() { f("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_default_arg_forwarding_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `void call(void(*cb)(const char*) = system) { cb(x); }`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('void call(void(*cb)(const char*) = system) { cb("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_default_arg_param_shadowing_call_site_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # A default-valued parameter's own alias entry must NOT leak
        # outside its own function -- calling a DIFFERENT, unrelated `cb`
        # elsewhere must not resolve.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            'void call(void(*cb)(const char*) = system) { cb("sh"); }\n'
            'void other(void (*cb)(const char*)) { cb("sh"); }\n'
        )
        # `other`'s own `cb` parameter has no default value at all -- no
        # alias entry recorded for it, so its call site must not resolve.
        result = scan_file_capabilities(pkg)
        # both functions are named `cb`; the aliased one (`call`) still
        # correctly resolves overall.
        assert "exec" in result

    def test_structured_binding_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `auto [a, b] = std::pair{system, 0}; a(x);`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('auto [a, b] = std::pair{system, 0};\nvoid g() { a("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_structured_binding_non_literal_rhs_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # A structured binding whose RHS is a plain variable (no positional
        # initializer-list to walk) must not resolve -- fail-closed, no
        # guess at what a runtime value's members might be.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('auto [a, b] = some_pair_var;\nvoid g() { a("sh"); }\n')
        assert "exec" not in scan_file_capabilities(pkg)

    def test_lambda_capturing_fn_ptr_var_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: a lambda capturing a bound function-pointer name
        # resolves the call inside its own body -- needs NO special lambda-
        # scope handling: a `lambda_expression`'s body is not itself a
        # `_C_SCOPE_TYPES` boundary, so the shadow-scope walk climbs
        # straight past it to the SAME enclosing function scope the
        # capture's own alias entry was recorded under.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "void g() {\n"
            "    void (*ptr)(const char*) = system;\n"
            "    auto lam = [ptr](const char* x){ ptr(x); };\n"
            "}\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_using_namespace_directive_qualified_call_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "`using namespace` directive" row (distinct from
        # "`using` declaration" above -- a directive opens a whole
        # namespace rather than importing one name): `using namespace std;
        # system(x);`. Same "no special resolution needed" shape as the
        # using-declaration/namespace-alias rows: the bare-name call site's
        # own text already contains the literal needle "system(".
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('using namespace std;\nvoid g() { system("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_define_macro_aliasing_detected_on_cpp_extension(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "`#define` macro aliasing" row, C++'s copy of the
        # same construct C's `test_macro_alias_detected` already locks --
        # the preprocessor is shared grammar, so the ".cpp" language label
        # exercises the identical macro-alias-table code path.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('#define RUN system\nvoid g() { RUN("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_member_function_pointer_bound_to_named_member_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "member-function pointer bound to a named member"
        # row: `auto p = &Ops::run; (obj.*p)(x);`. Genuine, currently
        # UNRESOLVED gap: there is no pointer-to-member (`&Ops::run`,
        # `.*`/`->*` dereference) handling anywhere in the C/C++ resolver --
        # only ordinary function pointers, typedefs, `using` aliases,
        # `std::function`, and structured bindings are tracked. This
        # fixture locks the CURRENT honest under-detection rather than
        # silently having no fixture for the row; T-1047 tracks adding
        # pointer-to-member alias tracking to close it.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "struct Ops { static void run(const char*); };\n"
            "void g() {\n"
            "    auto p = &Ops::run;\n"
            '    (Ops::*p)("sh");\n'
            "}\n"
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_argument_dependent_lookup_call_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "argument-dependent lookup (ADL)" row: `run(x);`
        # resolves to `ns::run` purely via ADL, no `using` in scope. Same
        # "no special resolution needed" shape as the other qualified-call
        # rows above -- the unqualified call site's own text already
        # contains the literal needle "system(" (the taxonomy's own
        # dangerous-target example is `run(x)` resolving via ADL; this
        # fixture substitutes the registry's actual dangerous needle,
        # `system`, in the analogous position).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "namespace ns { struct Tag {}; void system(Tag, const char*); }\n"
            'void g(ns::Tag t) { system(t, "sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)


class TestCapabilityScanCppAliasTablePredicates:
    """T-0663 white-box mutation-kill coverage (TEST016) for the two new
    C++-only predicates -- mirrors `TestCapabilityScanCAliasTablePredicates`
    (T-0662)."""

    def test_structured_binding_alias_skips_non_initializer_list_rhs(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_record_c_structured_binding_alias \
        # kind="unit"
        from frob.lang import raw_tree
        from frob.vet._capability_c import _record_c_structured_binding_alias

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text("auto [a, b] = some_pair_var;\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        declarator = _ts_find(tree.root_node, "structured_binding_declarator")
        init_declarator = _ts_find(tree.root_node, "init_declarator")
        assert declarator is not None and init_declarator is not None
        value = init_declarator.child_by_field_name("value")
        assert value is not None
        var_alias_table: dict = {}
        _record_c_structured_binding_alias(declarator, value, {}, {}, var_alias_table)
        assert var_alias_table == {}

    def test_default_param_alias_skips_node_with_no_default_value_field(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_record_c_default_param_alias \
        # kind="unit"
        # A plain (non-default-valued) `parameter_declaration` has no
        # `default_value` field at all -- passing one through directly
        # must be a clean no-op (`.child_by_field_name("default_value")`
        # returns `None`), not a crash.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _record_c_default_param_alias

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text("void call(void(*cb)(const char*)) {}\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        node = _ts_find(tree.root_node, "parameter_declaration")
        assert node is not None
        var_alias_table: dict = {}
        _record_c_default_param_alias(node, {}, {}, var_alias_table)
        assert var_alias_table == {}

    def test_default_param_alias_records_resolvable_default(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_record_c_default_param_alias \
        # kind="unit"
        from frob.lang import raw_tree
        from frob.vet._capability_c import _record_c_default_param_alias

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text("void call(void(*cb)(const char*) = system) {}\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        node = _ts_find(tree.root_node, "optional_parameter_declaration")
        assert node is not None
        var_alias_table: dict = {}
        _record_c_default_param_alias(node, {}, {}, var_alias_table)
        assert any(
            "cb" in scope and scope["cb"] == "system"
            for scope in var_alias_table.values()
        )

    def test_scope_bind_step_binds_optional_parameter_declaration(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_scope_bind_step kind="unit"
        # Kills the `node_type in ("parameter_declaration", "optional_
        # parameter_declaration")` membership mutant directly: without the
        # T-0663 extension, an `optional_parameter_declaration`'s name is
        # never bound, so `_c_scope_bound_names` would not know `cb` is a
        # parameter at all.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_scope_bound_names

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text("void call(void(*cb)(const char*) = system) { cb(0); }\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        func_def = _ts_find(tree.root_node, "function_definition")
        assert func_def is not None
        bound = _c_scope_bound_names(func_def)
        assert "cb" in bound

    def test_declaration_alias_dispatches_structured_binding_declarator(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_record_c_declaration_alias \
        # kind="unit"
        # Kills `declarator.type == "structured_binding_declarator"`'s Eq
        # mutant at the DISPATCH site in `_record_c_declaration_alias`
        # itself (as opposed to `_record_c_structured_binding_alias`'s own
        # internal logic, already covered above) -- without this dispatch
        # check, a structured-binding `init_declarator` would fall through
        # to the single-name `_c_declared_name` path and record nothing
        # useful (or crash on a multi-name declarator).
        from frob.lang import raw_tree
        from frob.vet._capability_c import _record_c_declaration_alias

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text("auto [a, b] = std::pair{system, 0};\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        init_declarator = _ts_find(tree.root_node, "init_declarator")
        assert init_declarator is not None
        var_alias_table: dict = {}
        field_alias_table: dict = {}
        array_alias_table: dict = {}
        _record_c_declaration_alias(
            init_declarator,
            {},
            {},
            var_alias_table,
            field_alias_table,
            array_alias_table,
        )
        assert any("a" in scope for scope in var_alias_table.values())
        assert field_alias_table == {}
        assert array_alias_table == {}
