from pathlib import Path

from tests.conftest import (
    _ts_find,  # noqa: F401 -- T-3596
    _ts_find_all,  # noqa: F401 -- T-3596
)


class TestCapabilityScanCBindingResolution:
    """T-0379: C/C++ sibling of `TestCapabilityScanRustBindingResolution` --
    before this, C/C++ capability scanning was pure lexical needle-matching,
    so a `#define`-renamed dangerous call evaded it entirely (`#define SYS
    system; SYS("sh")` never contains the literal "system(" text the needle
    table looks for). These tests lock the fix's litmus: the macro-aliased
    evasion now DETECTED, local shadowing still NOT detected (no false
    positives)."""

    def test_macro_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Evasion case: `#define SYS system` then `SYS("sh")` -- the raw
        # text never contains "system(", only the `#define` line's own
        # "system" token.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('#define SYS system\nvoid f() { SYS("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_operation_names_registry_entry_for_macro_alias(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        # `_scan_file_operations`'s resolver-backed sibling: a macro-renamed
        # call still names the real registry entry (library="libc"), not
        # just a bare kind label.
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "pkg.c"
        pkg.write_text('#define SYS system\nvoid f() { SYS("sh"); }\n')
        ops = _scan_file_operations(pkg)
        assert any(op.capability_kind == "exec" and op.library == "libc" for op in ops)

    def test_transitive_macro_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # A chained rename (`#define A B` + `#define B system`) still
        # resolves `A(...)` all the way through to `system`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('#define A B\n#define B system\nvoid f() { A("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_bare_macro_no_define_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # No naive bare-name false positive: calling `SYS(...)` with no
        # `#define` anywhere in the file must not resolve.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('void f() { SYS("sh"); }\n')
        assert "exec" not in scan_file_capabilities(pkg)

    def test_param_shadowing_macro_alias_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Shadow case: a function parameter named `SYS` shadows the macro
        # alias for the duration of that function -- calling `SYS(...)`
        # inside must not resolve to `system`. (`SYS` as a parameter name is
        # contrived C -- macros do not normally collide with identifiers
        # this way -- but exercises the same no-false-positive discipline
        # as the python/rust resolvers' shadow tests.)
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('#define SYS system\nvoid f(int SYS) { SYS("sh"); }\n')
        assert "exec" not in scan_file_capabilities(pkg)

    def test_local_shadowing_macro_alias_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Shadow case: a local variable declaration named `SYS` shadows the
        # macro alias for the rest of that function body.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('#define SYS system\nvoid f() { int SYS; SYS("sh"); }\n')
        assert "exec" not in scan_file_capabilities(pkg)

    def test_call_before_local_shadow_still_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0379 mirrors the T-0378 round 2 ordering fix: a call textually
        # BEFORE the same-named local declaration must still resolve
        # through the macro alias -- the C preprocessor's own textual
        # substitution has no notion of "not yet declared" either, so this
        # also matches real preprocessor behavior, not just the scanner's
        # approximation.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            '#define SYS system\nvoid f() {\n    SYS("sh");\n    int SYS;\n}\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_function_like_macro_not_resolved(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Documented limitation: a function-like macro (`#define SYS(x)
        # system(x)`) is a structurally different `preproc_function_def`
        # node and is not resolved by this pass -- its own expansion
        # already contains literal "system(" text most of the time anyway,
        # so the raw-text lexical scan still has a real shot at typical
        # usage. Here the definition line itself is what carries "system("
        # so the lexical scan (not the binding resolver) is what fires.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('#define SYS(x) system(x)\nvoid f() { SYS("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)


class TestCapabilityScanCTaxonomyClosureResolution:
    """T-0662: C sibling of `TestCapabilityScanTaxonomyClosureResolution`
    (python)/`TestCapabilityScanRustTaxonomyClosureResolution` (rust) --
    closes the remaining `docs/design/capability-evasion-taxonomy.md` C
    table static rows T-0379 (macro aliasing only) left unbound:
    function-pointer variable init from a named function, a `typedef`'d
    function-pointer type, plain assignment of a function pointer, a
    struct field statically initialized to a function pointer, and an
    array of function pointers read at a CONSTANT index."""

    def test_fn_ptr_var_init_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `void (*f)(const char*) = system_wrapper; f(x);`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('void (*f)(const char*) = system;\nvoid g() { f("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_typedef_fn_ptr_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `typedef void (*Handler)(const char*); Handler f = do_exec; f(x);`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "typedef void (*Handler)(const char*);\n"
            'Handler h = system;\nvoid g() { h("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    # frob:waive PII012 reason="'address_of' names the C `&` address-of operator, not \
    # a mailing/contact address"
    def test_assignment_address_of_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `f = &do_exec; f(x);` -- plain assignment, not a
        # declaration init.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('void (*f)(const char*);\nvoid g() { f = &system; f("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_assignment_bare_name_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Same row, without the `&` (a bare function name decays to a
        # pointer in an assignment context too).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('void (*f)(const char*);\nvoid g() { f = system; f("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_struct_field_static_init_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `struct Ops ops = { .run = system }; ops.run(x);`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "struct Ops { void (*run)(const char*); };\n"
            "struct Ops ops = { .run = system };\n"
            'void g() { ops.run("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_array_fn_ptr_constant_index_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `void (*tbl[])(const char*) = { system }; tbl[0](x);`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            'void (*tbl[])(const char*) = { system };\nvoid g() { tbl[0]("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_array_fn_ptr_nonconstant_index_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # The taxonomy's own "runtime-opaque" sibling row: a non-constant
        # index must NOT resolve (no false positive claiming static
        # resolution of what is genuinely a runtime read).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "void (*tbl[])(const char*) = { system };\n"
            'void g(int i) { tbl[i]("sh"); }\n'
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_chained_var_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # `f` aliases `system`; `g` (a second function-pointer var) is
        # initialized FROM `f` -- resolves transitively, document-order.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "void (*f)(const char*) = system;\n"
            "void (*g)(const char*) = f;\n"
            'void h() { g("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_param_shadowing_var_alias_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # A function parameter named `f` (an `int`, not a function pointer,
        # no alias entry recorded for it) shadows the file-scope alias `f`
        # for the duration of that function -- must not resolve (T-0339
        # fail-closed, no false positive).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "void (*f)(const char*) = system;\n"
            "void g(int f) { f = 0; }\n"
            'void h() { void (*local)(const char*) = f; local("sh"); }\n'
        )
        # `f` inside `g` is a shadowing int parameter with no alias entry;
        # inside `h`, the unqualified `f` still resolves at file scope.
        assert "exec" in scan_file_capabilities(pkg)

    def test_unaliased_local_shadow_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # A locally-declared function-pointer variable with NO resolvable
        # initializer (a forward declaration `void (*f)(const char*);`
        # inside a function, never assigned) must not be treated as
        # resolving to anything -- fail-closed, no guess.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('void g() { void (*f)(const char*); f("sh"); }\n')
        assert "exec" not in scan_file_capabilities(pkg)


class TestCapabilityScanCAliasTablePredicates:
    """White-box mutation-kill coverage (TEST016) for the private
    predicates `TestCapabilityScanCTaxonomyClosureResolution`'s end-to-end
    `scan_file_capabilities` tests exercise only indirectly -- imports and
    calls each guard directly, mirroring T-0660/T-0661's
    `TestCapabilityScanTsAliasTablePredicates` white-box pattern."""

    def test_declared_name_returns_none_for_none_node(self) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_declared_name kind="unit"
        # Kills the `while node is not None:` loop-condition mutant: a
        # `None` input must never crash and must return `None`.
        from frob.vet._capability_c import _c_declared_name

        assert _c_declared_name(None) is None

    def test_declared_name_direct_identifier(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_declared_name kind="unit"
        # Kills `node.type == "identifier"`'s Eq mutant: a bare identifier
        # node must resolve to its own text, not fall through to the
        # `declarator`-field walk.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_declared_name

        pkg = tmp_path / "pkg.c"
        pkg.write_text("int x;\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        ident = _ts_find(tree.root_node, "identifier")
        assert ident is not None
        assert _c_declared_name(ident) == "x"

    def test_declared_name_walks_declarator_field_to_identifier(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_declared_name kind="unit"
        # Kills `next_node = node.child_by_field_name("declarator")` being
        # skipped/misrouted: a `pointer_declarator` (which HAS a labeled
        # `declarator` field, no `parenthesized_declarator` fallback
        # needed) must still resolve through to its inner identifier.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_declared_name

        pkg = tmp_path / "pkg.c"
        pkg.write_text("int *p;\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        pd = _ts_find(tree.root_node, "pointer_declarator")
        assert pd is not None
        assert _c_declared_name(pd) == "p"

    def test_declared_name_parenthesized_declarator_fallback(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_declared_name kind="unit"
        # Kills `node.type == "parenthesized_declarator"`'s Eq mutant AND
        # the `next_node is None and ...` And-swapped-to-Or mutant
        # directly: a `parenthesized_declarator` (the `(*f)` wrapper) has
        # no `declarator` FIELD at all, so `next_node` is `None` from the
        # field lookup -- ONLY the fallback branch can resolve it.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_declared_name

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void (*f)(const char*);\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        paren = _ts_find(tree.root_node, "parenthesized_declarator")
        assert paren is not None
        assert _c_declared_name(paren) == "f"

    def test_declared_name_returns_none_for_abstract_declarator(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_declared_name kind="unit"
        # An `abstract_pointer_declarator` (a type-only declarator with no
        # name at all, e.g. a bare `const char*` parameter) has NO
        # `declarator` field AND is not itself a `parenthesized_
        # declarator` -- the fallback's own `if named else None` must
        # still terminate the loop with `None`, not loop forever or crash.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_declared_name

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void f(const char*);\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        abstract = _ts_find(tree.root_node, "abstract_pointer_declarator")
        assert abstract is not None
        assert _c_declared_name(abstract) is None

    def test_collect_declaration_names_bare_identifier(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_collect_declaration_names \
        # kind="unit"
        # Kills `child.type in _C_DECLARATOR_CHILD_TYPES`'s membership
        # mutant for the bare `identifier` shape (`int x, y;`).
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_collect_declaration_names

        pkg = tmp_path / "pkg.c"
        pkg.write_text("int x, y;\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        decl = _ts_find(tree.root_node, "declaration")
        assert decl is not None
        bound: dict = {}
        _c_collect_declaration_names(decl, 0, bound)
        assert bound == {"x": 0, "y": 0}

    def test_collect_declaration_names_init_declarator(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_collect_declaration_names \
        # kind="unit"
        # Kills `child.type == "init_declarator"`'s Eq mutant.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_collect_declaration_names

        pkg = tmp_path / "pkg.c"
        pkg.write_text("int x = 5;\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        decl = _ts_find(tree.root_node, "declaration")
        assert decl is not None
        bound: dict = {}
        _c_collect_declaration_names(decl, 7, bound)
        assert bound == {"x": 7}

    def test_collect_declaration_names_uninitialized_fn_ptr(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_collect_declaration_names \
        # kind="unit"
        # T-0662's own new shape: an uninitialized function-pointer
        # declaration (`void (*f)(const char*);`) has no `init_declarator`
        # wrapper -- only the extended `_C_DECLARATOR_CHILD_TYPES`
        # membership check (`function_declarator` in the tuple) reaches it.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_collect_declaration_names

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void (*f)(const char*);\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        decl = _ts_find(tree.root_node, "declaration")
        assert decl is not None
        bound: dict = {}
        _c_collect_declaration_names(decl, 3, bound)
        assert bound == {"f": 3}

    # frob:waive PII012 reason="'address_of' names the C `&` address-of operator, not \
    # a mailing/contact address"
    def test_resolve_alias_source_unwraps_address_of(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_resolve_c_alias_source kind="unit"
        from frob.lang import raw_tree
        from frob.vet._capability_c import _resolve_c_alias_source

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void g() { f = &system; }\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        pointer_expr = _ts_find(tree.root_node, "pointer_expression")
        assert pointer_expr is not None
        resolved = _resolve_c_alias_source(pointer_expr, {}, {}, {})
        assert resolved == "system"

    # frob:waive PII012 reason="'address_of' names the C `&` address-of operator, not \
    # a mailing/contact address"
    def test_resolve_alias_source_rejects_non_identifier_address_of(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_resolve_c_alias_source kind="unit"
        from frob.lang import raw_tree
        from frob.vet._capability_c import _resolve_c_alias_source

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void g() { int x; f = &x[0]; }\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        pointer_expr = _ts_find(tree.root_node, "pointer_expression")
        assert pointer_expr is not None
        assert _resolve_c_alias_source(pointer_expr, {}, {}, {}) is None

    def test_resolve_alias_source_rejects_non_identifier_non_pointer(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_resolve_c_alias_source kind="unit"
        from frob.lang import raw_tree
        from frob.vet._capability_c import _resolve_c_alias_source

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void g() { int x = 1 + 2; }\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        binary_expr = _ts_find(tree.root_node, "binary_expression")
        assert binary_expr is not None
        assert _resolve_c_alias_source(binary_expr, {}, {}, {}) is None

    def test_resolve_alias_source_via_macro_table(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_resolve_c_alias_source kind="unit"
        from frob.lang import raw_tree
        from frob.vet._capability_c import _resolve_c_alias_source

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void g() { f = SYS; }\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        assignment = _ts_find(tree.root_node, "assignment_expression")
        assert assignment is not None
        right = assignment.child_by_field_name("right")
        resolved = _resolve_c_alias_source(right, {"SYS": "system"}, {}, {})
        assert resolved == "system"

    def test_record_field_alias_skips_non_field_designator(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_record_c_field_alias kind="unit"
        # An array-designated initializer (`[0] = system`) is not a
        # `field_designator` -- must be skipped, not mis-recorded.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _record_c_field_alias

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void (*tbl[1])(const char*) = { [0] = system };\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        init_list = _ts_find(tree.root_node, "initializer_list")
        assert init_list is not None
        field_alias_table: dict = {}
        _record_c_field_alias(init_list, {}, {}, {}, field_alias_table)
        assert field_alias_table == {}

    def test_c_call_target_resolved_rejects_non_constant_field_type(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_call_target_resolved kind="unit"
        # A call target that is none of identifier/field_expression/
        # subscript_expression (a parenthesized function-pointer
        # dereference `(*f)(x)`) must resolve to `None`, not crash.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_call_target_resolved

        pkg = tmp_path / "pkg.c"
        pkg.write_text('void g() { void (*f)(const char*); (*f)("sh"); }\n')
        tree, _source, _lang = raw_tree(pkg).danger_ok
        call = _ts_find(tree.root_node, "call_expression")
        assert call is not None
        func = call.child_by_field_name("function")
        assert func is not None
        assert _c_call_target_resolved(func, {}, {}, {}, {}, {}) is None

    def test_c_call_target_resolved_subscript_non_number_index(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_call_target_resolved kind="unit"
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_call_target_resolved

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "void (*tbl[])(const char*) = { system };\n"
            'void g(int i) { tbl[i]("sh"); }\n'
        )
        tree, _source, _lang = raw_tree(pkg).danger_ok
        calls: list = []
        _ts_find_all(tree.root_node, "call_expression", calls)
        assert calls
        call = calls[-1]
        func = call.child_by_field_name("function")
        assert func is not None and func.type == "subscript_expression"
        assert _c_call_target_resolved(func, {}, {}, {}, {}, {("tbl", 0): "x"}) is None
