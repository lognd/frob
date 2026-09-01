"""Split from tests/unit/test_arch.py (T-1201)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.arch_suite.conftest import FIXTURES, HAS_ARCH

pytestmark = pytest.mark.skipif(not HAS_ARCH, reason="frob.arch not available")


class TestNormalizedModel:
    """T-0609: hand-build a `NormalizedModule` for a trivial python snippet
    (no adapter exists yet -- that is T-0610's migration) and assert the
    model's shape holds together: every entity the ticket calls out
    (module/class/function/method/param/branch/loop/call/import/override/
    field-access/return/raise/catch) round-trips through construction and
    (de)serialization."""

    def test_hand_built_python_snippet_shape(self) -> None:
        # Mirrors a trivial snippet -- an import, a class with a base
        # method and an overriding method that branches/loops/calls/raises:
        #     import os
        #     class Base:
        #         def greet(self) -> str: ...
        #         def speak(self):  # overrides greet
        #             if self.mood == 'ok': ...
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedCall,
            NormalizedCatch,
            NormalizedClass,
            NormalizedField,
            NormalizedFieldAccess,
            NormalizedFunction,
            NormalizedImport,
            NormalizedLoop,
            NormalizedModule,
            NormalizedParam,
            NormalizedRaise,
            NormalizedReturn,
        )

        greet = NormalizedFunction(
            name="greet",
            line=4,
            body_line_count=1,
            params=[NormalizedParam(name="self")],
            return_type="str",
            is_method=True,
            returns=[NormalizedReturn(line=5, value_text="'hi'")],
        )
        speak = NormalizedFunction(
            name="speak",
            line=7,
            body_line_count=6,
            params=[NormalizedParam(name="self", type=None)],
            is_method=True,
            overrides="greet",
            branches=[NormalizedBranch(line=8, condition_text="self.mood == 'ok'")],
            loops=[NormalizedLoop(line=10, kind="for")],
            calls=[NormalizedCall(callee="print", line=9)],
            field_accesses=[NormalizedFieldAccess(name="mood", line=8, is_write=False)],
            raises=[NormalizedRaise(line=11, exception_type="ValueError")],
            catches=[NormalizedCatch(line=12, exception_type="ValueError")],
        )
        base = NormalizedClass(
            name="Base",
            line=3,
            fields=[NormalizedField(name="mood", line=3, type="str")],
            methods=[greet, speak],
        )
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            imports=[NormalizedImport(module="os", line=1)],
            classes=[base],
            functions=[],
        )

        assert module.language == "python"
        assert module.imports[0].module == "os"
        assert module.classes[0].name == "Base"
        assert module.classes[0].fields[0].name == "mood"
        methods = {m.name: m for m in module.classes[0].methods}
        assert methods["greet"].returns[0].value_text == "'hi'"
        assert methods["speak"].overrides == "greet"
        assert methods["speak"].branches[0].condition_text == "self.mood == 'ok'"
        assert methods["speak"].loops[0].kind == "for"
        assert methods["speak"].calls[0].callee == "print"
        assert methods["speak"].field_accesses[0].name == "mood"
        assert methods["speak"].raises[0].exception_type == "ValueError"
        assert methods["speak"].catches[0].exception_type == "ValueError"

        # Round-trips through the pydantic (de)serialization boundary too --
        # a `NormalizedModule` must survive a dump/reload cycle unchanged,
        # since a future adapter registry (T-0610) may cache/transport it.
        restored = NormalizedModule.model_validate(module.model_dump())
        assert restored == module

    def test_language_adapter_is_a_runtime_checkable_protocol(self) -> None:
        # No adapter is implemented in this ticket's scope -- only assert
        # the protocol shape itself is usable for an isinstance check, the
        # mechanism a future adapter registry (T-0610) dispatches on.
        from frob.arch._normalized import LanguageAdapter, NormalizedModule

        class _StubAdapter:
            language = "python"

            def adapt(self, tree: object, source: bytes, rel: str) -> NormalizedModule:
                return NormalizedModule(path=rel, language=self.language)

        stub = _StubAdapter()
        assert isinstance(stub, LanguageAdapter)
        result = stub.adapt(tree=object(), source=b"", rel="a.py")
        assert result.path == "a.py"


class TestPythonAdapter:
    """T-0610: `frob.arch._python.PythonAdapter` is the first `LanguageAdapter`
    implementation, built off this module's existing tree-sitter walkers.
    These tests exercise it directly against real fixture files, separately
    from the (unchanged) `analyze_project`-level suggestion assertions
    above."""

    def test_is_a_language_adapter(self) -> None:
        from frob.arch._normalized import LanguageAdapter
        from frob.arch._python import PythonAdapter

        adapter = PythonAdapter()
        assert isinstance(adapter, LanguageAdapter)
        assert adapter.language == "python"

    def test_adapt_arch_python_fixture_shape(self) -> None:
        from frob.arch._python import PythonAdapter
        from frob.lang import raw_tree

        path = FIXTURES / "arch_python" / "src" / "big_class.py"
        parsed = raw_tree(path)
        assert parsed.is_ok
        tree, source, language = parsed.danger_ok
        assert language == "python"

        module = PythonAdapter().adapt(tree, source, "big_class.py")
        assert module.path == "big_class.py"
        assert module.language == "python"
        assert len(module.classes) == 1
        cls = module.classes[0]
        assert cls.name == "BigService"
        assert len(cls.methods) == 16
        assert all(m.is_method for m in cls.methods)
        assert {m.name for m in cls.methods} == {
            f"method_{i:02d}" for i in range(1, 17)
        }

    def test_adapt_imports(self, tmp_path: Path) -> None:
        # frob:tests src/frob/arch/_python.py::_py_plain_import_statement_imports
        # frob:tests src/frob/arch/_python.py::_py_build_module
        from frob.arch._python import PythonAdapter
        from frob.lang import raw_tree

        path = tmp_path / "mod.py"
        path.write_text(
            "import os\nimport os.path as osp\nfrom collections import OrderedDict\n"
        )
        parsed = raw_tree(path)
        assert parsed.is_ok
        tree, source, language = parsed.danger_ok
        assert language == "python"

        module = PythonAdapter().adapt(tree, source, "mod.py")
        plain = [i for i in module.imports if i.module in ("os", "os.path")]
        assert len(plain) == 2
        bare = next(i for i in plain if i.module == "os")
        assert bare.names == []
        assert bare.line == 1
        aliased = next(i for i in plain if i.module == "os.path")
        assert aliased.names == []
        assert aliased.line == 2
        from_import = next(i for i in module.imports if i.module == "collections")
        assert "OrderedDict" in from_import.names
        assert from_import.line == 3

    def test_adapt_long_func_fixture_structural_events(self) -> None:
        from frob.arch._python import PythonAdapter
        from frob.lang import raw_tree

        path = FIXTURES / "arch_python" / "src" / "long_func.py"
        parsed = raw_tree(path)
        assert parsed.is_ok
        tree, source, _language = parsed.danger_ok

        module = PythonAdapter().adapt(tree, source, "long_func.py")
        funcs = {f.name: f for f in module.functions}
        assert "configure_pipeline" in funcs
        target = funcs["configure_pipeline"]
        # The long-function fixture is complex enough to trigger the rule --
        # its normalized nesting/cyclomatic metrics must reflect that, since
        # `_check_long_functions` (T-0610) reads these fields directly.
        assert target.max_nesting_depth >= 3 or target.cyclomatic >= 8

    def test_adapt_deep_nest_fixture_nesting_depth(self) -> None:
        from frob.arch._python import PythonAdapter
        from frob.lang import raw_tree

        path = FIXTURES / "arch_python" / "src" / "deep_nest.py"
        parsed = raw_tree(path)
        assert parsed.is_ok
        tree, source, _language = parsed.danger_ok

        module = PythonAdapter().adapt(tree, source, "deep_nest.py")
        funcs = {f.name: f for f in module.functions}
        assert "process_matrix" in funcs
        assert funcs["process_matrix"].max_nesting_depth >= 4

    def test_adapt_call_args_capture_position_keyword_and_identifier(
        self, tmp_path: Path
    ) -> None:
        # T-0632: NormalizedCall.args carries per-argument position/keyword
        # + bare-identifier detail -- a positional identifier arg, a
        # keyword identifier arg, and a non-identifier (literal) arg that
        # must NOT get an `ident` back.
        from frob.arch._python import PythonAdapter
        from frob.lang import raw_tree

        src_path = tmp_path / "call_args.py"
        src_path.write_text(
            "def run(handler, mode):\n    dispatch(handler, mode=mode, retries=3)\n"
        )
        parsed = raw_tree(src_path)
        assert parsed.is_ok
        tree, source, _language = parsed.danger_ok

        module = PythonAdapter().adapt(tree, source, "call_args.py")
        funcs = {f.name: f for f in module.functions}
        call = funcs["run"].calls[0]
        assert call.callee == "dispatch"
        by_pos = {a.index: a for a in call.args if a.index is not None}
        by_kw = {a.keyword: a for a in call.args if a.keyword is not None}
        assert by_pos[0].ident == "handler"
        assert by_kw["mode"].ident == "mode"
        assert by_kw["retries"].ident is None

    # frob:ticket T-0689
    def test_adapt_parses_frob_raises_declaration_on_call_line(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/arch/_python.py::PythonAdapter.adapt kind="unit"
        # A same-line `# frob:callee-raises A, B` comment on a call site
        # becomes that NormalizedCall's declared_raises; a call with no such
        # comment stays None; an empty-after-marker comment
        # (`# frob:callee-raises`) declares the empty set, not "no
        # declaration". Renamed from `frob:raises` (T-0931) to disambiguate
        # from the unrelated above-the-def, function-wide `frob:raises`
        # declared-propagation directive EXHAUST002 consumes (T-0688).
        from frob.arch._python import PythonAdapter
        from frob.lang import raw_tree

        src_path = tmp_path / "ffi.py"
        src_path.write_text(
            "def call_native(lib):\n"
            "    lib.risky_call()  # frob:callee-raises OSError, ValueError\n"
            "    lib.quiet_call()  # frob:callee-raises\n"
            "    plain()\n"
        )
        parsed = raw_tree(src_path)
        assert parsed.is_ok
        tree, source, _language = parsed.danger_ok

        module = PythonAdapter().adapt(tree, source, "ffi.py")
        calls = {c.callee: c for c in module.functions[0].calls}
        assert calls["lib.risky_call"].declared_raises == frozenset(
            {"OSError", "ValueError"}
        )
        assert calls["lib.quiet_call"].declared_raises == frozenset()
        assert calls["plain"].declared_raises is None

    # frob:ticket T-3473
    def test_adapt_records_top_level_regex_compile_pattern_text(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/arch/_python.py::PythonAdapter.adapt kind="unit"
        from frob.arch._python import PythonAdapter
        from frob.lang import raw_tree

        src_path = tmp_path / "pat.py"
        src_path.write_text("import re\n\n_RE = re.compile(r'a(\\d+)b')\n")
        parsed = raw_tree(src_path)
        assert parsed.is_ok
        tree, source, _language = parsed.danger_ok

        module = PythonAdapter().adapt(tree, source, "pat.py")
        assert module.module_regex_patterns == {"_RE": r"a(\d+)b"}

    # frob:ticket T-3473
    def test_adapt_ignores_non_regex_top_level_assignments(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/arch/_python.py::PythonAdapter.adapt kind="unit"
        # A plain constant, a computed pattern, and an aliased-import call
        # must all be silently absent -- fail-closed, never a wrong guess.
        from frob.arch._python import PythonAdapter
        from frob.lang import raw_tree

        src_path = tmp_path / "pat.py"
        src_path.write_text(
            "import re\n"
            "from re import compile as rc\n\n"
            "_NOT_A_PATTERN = 42\n"
            "_COMPUTED = re.compile(build_pattern())\n"
            "_ALIASED = rc(r'x(\\d+)')\n"
        )
        parsed = raw_tree(src_path)
        assert parsed.is_ok
        tree, source, _language = parsed.danger_ok

        module = PythonAdapter().adapt(tree, source, "pat.py")
        assert module.module_regex_patterns == {}

    # frob:ticket T-3474
    def test_adapt_tags_comprehension_branch_and_call_with_shared_id(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/arch/_python.py::PythonAdapter.adapt kind="unit"
        # The comprehension's output-expr call and its trailing if-clause
        # branch get the SAME non-None comprehension_id; a plain function-
        # body call/branch outside any comprehension stays None.
        from frob.arch._python import PythonAdapter
        from frob.lang import raw_tree

        src_path = tmp_path / "comp.py"
        src_path.write_text(
            "def f(entries):\n"
            "    if len(entries) == 0:\n"
            "        return []\n"
            "    return [int(e) for e in entries if e.isdigit() and True]\n"
        )
        parsed = raw_tree(src_path)
        assert parsed.is_ok
        tree, source, _language = parsed.danger_ok

        module = PythonAdapter().adapt(tree, source, "comp.py")
        func = module.functions[0]

        plain_branch = next(
            b for b in func.branches if "len(entries)" in b.condition_text
        )
        assert plain_branch.comprehension_id is None

        comp_call = next(c for c in func.calls if c.callee == "int")
        comp_branch = next(b for b in func.branches if "isdigit" in b.condition_text)
        assert comp_call.comprehension_id is not None
        assert comp_call.comprehension_id == comp_branch.comprehension_id



class TestTypeScriptAdapter:
    """T-0611: `frob.arch._typescript.TypeScriptAdapter` is the second
    `LanguageAdapter` implementation (after T-0610's `PythonAdapter`),
    built off `tree-sitter-typescript`. These tests hand-build small `.ts`
    fixtures covering every `NormalizedModule` entity kind, plus one
    stays-sane test on a more realistic multi-construct snippet."""

    def test_is_a_language_adapter(self) -> None:
        from frob.arch._normalized import LanguageAdapter
        from frob.arch._typescript import TypeScriptAdapter

        adapter = TypeScriptAdapter()
        assert isinstance(adapter, LanguageAdapter)
        assert adapter.language == "typescript"

    def _adapt(self, tmp_path: Path, source: str, filename: str = "mod.ts"):
        from frob.arch._typescript import TypeScriptAdapter
        from frob.lang import raw_tree

        path = tmp_path / filename
        path.write_text(source)
        parsed = raw_tree(path)
        assert parsed.is_ok
        tree, src, language = parsed.danger_ok
        assert language == "typescript"
        return TypeScriptAdapter().adapt(tree, src, filename)

    def test_adapt_imports(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            'import { Base } from "./base";\n'
            'import * as fs from "fs";\n'
            'import Default from "mod3";\n'
            'import "sideeffect";\n',
        )
        by_module = {i.module: i for i in module.imports}
        assert by_module["./base"].names == ["Base"]
        assert by_module["fs"].names == []
        assert by_module["mod3"].names == ["Default"]
        assert by_module["sideeffect"].names == []

    def test_adapt_class_bases_and_fields(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "class Base {}\n"
            "interface Greeter { greet(): string; }\n"
            "class Animal extends Base implements Greeter {\n"
            "  name: string;\n"
            "  private age: number = 0;\n"
            "  greet(): string { return this.name; }\n"
            "}\n",
        )
        classes = {c.name: c for c in module.classes}
        # T-0681: `interface_declaration` now maps onto `NormalizedClass`
        # too (mirroring `_kotlin.py`'s precedent), so `Greeter` shows up
        # here alongside the two real classes.
        assert set(classes) == {"Base", "Animal", "Greeter"}
        animal = classes["Animal"]
        assert animal.bases == ["Base", "Greeter"]
        fields = {f.name: f for f in animal.fields}
        assert fields["name"].type == "string"
        assert fields["age"].type == "number"

    def test_adapt_function_params_and_return_type(self, tmp_path: Path) -> None:
        from frob.arch._normalized import NormalizedParam

        module = self._adapt(
            tmp_path,
            "function add(x: number, y = 2): number {\n  return x + y;\n}\n",
        )
        assert len(module.functions) == 1
        fn = module.functions[0]
        assert fn.name == "add"
        assert fn.return_type == "number"
        assert fn.params[0] == NormalizedParam(
            name="x", type="number", has_default=False
        )
        assert fn.params[1].name == "y"
        assert fn.params[1].has_default is True
        assert fn.returns[0].value_text == "x + y"

    def test_adapt_arrow_function_bound_to_const(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "const double = (a: number): number => {\n  return a * 2;\n};\n",
        )
        funcs = {f.name: f for f in module.functions}
        assert "double" in funcs
        assert funcs["double"].params[0].name == "a"
        assert funcs["double"].returns[0].value_text == "a * 2"

    def test_adapt_branches_loops_calls_field_accesses(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "class Widget {\n"
            "  count: number = 0;\n"
            "  bump(flag: boolean): void {\n"
            "    if (this.count > 0 && flag) {\n"
            "      console.log(this.count);\n"
            "    }\n"
            "    for (let i = 0; i < 3; i++) {\n"
            "      this.count = this.count + i;\n"
            "    }\n"
            "  }\n"
            "}\n",
        )
        method = module.classes[0].methods[0]
        assert any(
            b.condition_text == "this.count > 0 && flag" for b in method.branches
        )
        assert any(loop.kind == "for" for loop in method.loops)
        assert any(c.callee == "console.log" for c in method.calls)
        writes = [
            fa for fa in method.field_accesses if fa.name == "count" and fa.is_write
        ]
        assert writes

    def test_adapt_for_of_and_ternary(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "function loopy(items: string[]): void {\n"
            "  for (const it of items) {\n"
            "    console.log(it);\n"
            "  }\n"
            '  const label = items.length > 0 ? "yes" : "no";\n'
            "  console.log(label);\n"
            "}\n",
        )
        fn = module.functions[0]
        assert any(loop.kind == "for" for loop in fn.loops)
        assert any(b.condition_text == "items.length > 0" for b in fn.branches)

    def test_adapt_raise_and_catch(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "function risky(): void {\n"
            "  try {\n"
            '    throw new RangeError("oops");\n'
            "  } catch (e) {\n"
            '    throw new Error("bad");\n'
            "  }\n"
            "}\n",
        )
        fn = module.functions[0]
        assert {r.exception_type for r in fn.raises} == {"RangeError", "Error"}
        assert len(fn.catches) == 1

    def test_adapt_override_modifier(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "class Base {\n"
            "  speak(): void {}\n"
            "}\n"
            "class Derived extends Base {\n"
            "  override speak(): void {}\n"
            "}\n",
        )
        derived = next(c for c in module.classes if c.name == "Derived")
        assert derived.methods[0].overrides == "speak"
        base = next(c for c in module.classes if c.name == "Base")
        assert base.methods[0].overrides is None

    def test_adapt_constructor_is_a_method(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "class Animal {\n"
            "  name: string;\n"
            "  constructor(name: string) {\n"
            "    this.name = name;\n"
            "  }\n"
            "}\n",
        )
        cls = module.classes[0]
        ctor = next(m for m in cls.methods if m.name == "constructor")
        assert ctor.is_method is True
        assert ctor.params[0].name == "name"

    def test_adapt_export_wrapped_declarations(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "export function exported(z: string): void {}\n"
            "export class ExportedClass {}\n",
        )
        assert {f.name for f in module.functions} == {"exported"}
        assert {c.name for c in module.classes} == {"ExportedClass"}

    def test_adapt_interface_declaration(self, tmp_path: Path) -> None:
        # T-0681: an interface becomes a `NormalizedClass` (mirroring
        # `_kotlin.py`'s precedent) -- bases from `extends`, fields from
        # property signatures, methods (bodyless) from method signatures.
        module = self._adapt(
            tmp_path,
            "interface Named { id: string; }\n"
            "interface Greeter extends Named {\n"
            "  loud?: boolean;\n"
            "  greet(msg: string): void;\n"
            "}\n",
        )
        classes = {c.name: c for c in module.classes}
        assert set(classes) == {"Named", "Greeter"}
        greeter = classes["Greeter"]
        assert greeter.bases == ["Named"]
        fields = {f.name: f for f in greeter.fields}
        assert fields["loud"].type == "boolean"
        methods = {m.name: m for m in greeter.methods}
        assert "greet" in methods
        greet = methods["greet"]
        assert greet.is_method is True
        assert greet.params[0].name == "msg"
        assert greet.return_type == "void"
        # An interface method has no implementation -- no body to walk.
        assert greet.body_line_count == 0
        assert greet.branches == []

    def test_adapt_enum_declaration(self, tmp_path: Path) -> None:
        # T-0681: an enum becomes a `NormalizedClass` with no bases/
        # methods (mirroring `_rust.py`'s `enum_item` precedent) -- each
        # member becomes a `NormalizedField` regardless of whether it
        # carries an explicit value.
        module = self._adapt(
            tmp_path,
            'enum Color {\n  Red,\n  Green = "green",\n  Blue = 3,\n}\n',
        )
        assert len(module.classes) == 1
        color = module.classes[0]
        assert color.name == "Color"
        assert color.bases == []
        assert color.methods == []
        assert [f.name for f in color.fields] == ["Red", "Green", "Blue"]

    def test_adapt_type_alias_declaration(self, tmp_path: Path) -> None:
        # T-0681: a type alias becomes a `NormalizedTypeAlias` on
        # `NormalizedModule.type_aliases` -- no fields/methods/members of
        # its own, unlike interface/enum, so no existing entity fits.
        module = self._adapt(
            tmp_path,
            "type ID = string;\ntype Result = string | number;\n",
        )
        aliases = {a.name: a for a in module.type_aliases}
        assert set(aliases) == {"ID", "Result"}
        assert aliases["ID"].target_text == "string"
        assert aliases["Result"].target_text == "string | number"

    def test_adapt_exported_interface_enum_type_alias(self, tmp_path: Path) -> None:
        # The T-0681 constructs unwrap an `export` wrapper the same way
        # `export class`/`export function` already do.
        module = self._adapt(
            tmp_path,
            "export interface Exported { z: boolean; }\n"
            "export enum ExportedEnum { A, B }\n"
            "export type ExportedAlias = number;\n",
        )
        assert {c.name for c in module.classes} == {"Exported", "ExportedEnum"}
        assert {a.name for a in module.type_aliases} == {"ExportedAlias"}

    def test_adapt_tsx_component(self, tmp_path: Path) -> None:
        # T-0681: a `.tsx` file parses through the `tsx` tree-sitter
        # grammar (still labeled `"typescript"`, see this adapter's
        # module docstring) -- a component function/arrow-function
        # returning JSX is represented as a normal `NormalizedFunction`,
        # with the JSX nodes inside its body contributing no new entity
        # kind but not breaking the existing event walk either (a
        # `member_expression` nested inside a `jsx_expression` is still
        # picked up by the branch condition it appears in).
        module = self._adapt(
            tmp_path,
            'import React from "react";\n'
            "\n"
            "interface Props {\n"
            "  name: string;\n"
            "}\n"
            "\n"
            "export function Greeting(props: Props) {\n"
            "  if (props.name) {\n"
            '    return <div className="hi">{props.name}</div>;\n'
            "  }\n"
            "  return <span/>;\n"
            "}\n"
            "\n"
            "export const Widget = (props: Props) => {\n"
            "  return <div>{props.name}</div>;\n"
            "};\n",
            filename="mod.tsx",
        )
        assert {c.name for c in module.classes} == {"Props"}
        funcs = {f.name: f for f in module.functions}
        assert set(funcs) == {"Greeting", "Widget"}
        assert funcs["Greeting"].branches
        assert funcs["Greeting"].params[0].name == "props"
        assert funcs["Widget"].params[0].name == "props"

        # Round-trips through pydantic (de)serialization like the other
        # entity kinds -- proves the new `NormalizedTypeAlias` field and
        # the interface/enum-as-`NormalizedClass` shapes are all
        # (de)serializable, not just constructible.
        from frob.arch._normalized import NormalizedModule

        restored = NormalizedModule.model_validate(module.model_dump())
        assert restored == module

    def test_adapt_stays_sane_on_realistic_snippet(self, tmp_path: Path) -> None:
        # A denser, more realistic TS module exercising every entity kind
        # at once (import, class w/ inheritance, constructor, override,
        # branches/loops/calls/field-accesses/raise/catch, a free function,
        # an arrow function) -- proves the adapter does not choke or
        # silently drop entities when they co-occur, the way a fixture
        # isolating one construct at a time cannot.
        module = self._adapt(
            tmp_path,
            'import { Base } from "./base";\n'
            "\n"
            "class Animal extends Base {\n"
            "  name: string;\n"
            "  private age: number = 0;\n"
            "\n"
            "  constructor(name: string, age = 1) {\n"
            "    super();\n"
            "    this.name = name;\n"
            "    this.age = age;\n"
            "  }\n"
            "\n"
            "  override speak(loud: boolean = false): void {\n"
            "    if (this.age > 5 && loud) {\n"
            "      console.log(this.name);\n"
            "    } else {\n"
            "      for (let i = 0; i < 3; i++) {\n"
            "        this.name = this.name + i;\n"
            "      }\n"
            "    }\n"
            "    try {\n"
            "      this.risky();\n"
            "    } catch (e) {\n"
            '      throw new Error("bad");\n'
            "    }\n"
            "  }\n"
            "\n"
            "  risky(): void {\n"
            '    throw new RangeError("oops");\n'
            "  }\n"
            "}\n"
            "\n"
            "function standalone(x: number, y = 2): number {\n"
            "  return x + y;\n"
            "}\n"
            "\n"
            "const arrowFn = (a: number): number => {\n"
            "  return a * 2;\n"
            "};\n",
        )
        assert module.language == "typescript"
        assert module.imports[0].module == "./base"
        cls = module.classes[0]
        assert cls.name == "Animal"
        assert cls.bases == ["Base"]
        methods = {m.name: m for m in cls.methods}
        assert set(methods) == {"constructor", "speak", "risky"}
        assert methods["speak"].overrides == "speak"
        assert methods["speak"].branches
        assert methods["speak"].loops
        assert methods["speak"].calls
        assert methods["speak"].field_accesses
        assert methods["speak"].raises[0].exception_type == "Error"
        assert methods["speak"].catches[0].line
        assert methods["risky"].raises[0].exception_type == "RangeError"
        funcs = {f.name: f for f in module.functions}
        assert set(funcs) == {"standalone", "arrowFn"}
        assert funcs["standalone"].params[1].has_default is True
        assert funcs["arrowFn"].returns[0].value_text == "a * 2"

        # Round-trips through pydantic (de)serialization, same as the
        # hand-built python NormalizedModule shape test (T-0609).
        from frob.arch._normalized import NormalizedModule

        restored = NormalizedModule.model_validate(module.model_dump())
        assert restored == module


class TestSharedCheckOnPythonAndTypeScript:
    """T-0611's acceptance criterion: a shared arch check written once
    against `NormalizedModule` fires identically on an equivalent python
    fixture (via `PythonAdapter`) and TypeScript fixture (via
    `TypeScriptAdapter`) -- no per-language branch in the check itself.
    Reuses `frob.arch._python`'s already-migrated (T-0610)
    `_iter_normalized_functions`/`_normalized_is_complex` helpers, which
    operate purely on `NormalizedModule`/`NormalizedFunction` and take no
    language-specific input."""

    _PY_LONG_FUNC = (
        "def configure_pipeline(a, b, c, d):\n"
        "    if a:\n"
        "        if b:\n"
        "            if c:\n"
        "                for i in range(d):\n"
        "                    if i:\n"
        "                        while i:\n"
        "                            if a and b:\n"
        "                                pass\n"
        "                            i -= 1\n"
        "    return a\n"
    )
    _TS_LONG_FUNC = (
        "function configurePipeline(a: boolean, b: boolean, c: boolean, d: number): boolean {\n"
        "  if (a) {\n"
        "    if (b) {\n"
        "      if (c) {\n"
        "        for (let i = 0; i < d; i++) {\n"
        "          if (i) {\n"
        "            while (i) {\n"
        "              if (a && b) {\n"
        "              }\n"
        "              i -= 1;\n"
        "            }\n"
        "          }\n"
        "        }\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "  return a;\n"
        "}\n"
    )

    def test_long_complex_function_flags_identically_across_languages(
        self, tmp_path: Path
    ) -> None:
        from frob.arch._python import (
            PythonAdapter,
            _iter_normalized_functions,
            _normalized_is_complex,
        )
        from frob.arch._typescript import TypeScriptAdapter
        from frob.lang import raw_tree

        py_path = tmp_path / "long_func.py"
        py_path.write_text(self._PY_LONG_FUNC)
        py_tree, py_src, py_lang = raw_tree(py_path).danger_ok
        assert py_lang == "python"
        py_module = PythonAdapter().adapt(py_tree, py_src, "long_func.py")

        ts_path = tmp_path / "long_func.ts"
        ts_path.write_text(self._TS_LONG_FUNC)
        ts_tree, ts_src, ts_lang = raw_tree(ts_path).danger_ok
        assert ts_lang == "typescript"
        ts_module = TypeScriptAdapter().adapt(ts_tree, ts_src, "long_func.ts")

        py_target = next(
            f
            for f, _prefix in _iter_normalized_functions(py_module)
            if f.name == "configure_pipeline"
        )
        ts_target = next(
            f
            for f, _prefix in _iter_normalized_functions(ts_module)
            if f.name == "configurePipeline"
        )

        # The SAME shared check function, unmodified, called on each
        # language's NormalizedFunction -- both must fire.
        assert _normalized_is_complex(py_target)
        assert _normalized_is_complex(ts_target)


class TestSharedCheckOnPythonAndRust:
    """T-0612's acceptance criterion: a shared arch check written once
    against `NormalizedModule` fires identically on an equivalent python
    fixture (via `PythonAdapter`) and rust fixture (via `RustAdapter`) --
    no per-language branch in the check itself. Reuses the same
    `_iter_normalized_functions`/`_normalized_is_complex` helpers
    `TestSharedCheckOnPythonAndTypeScript` already proves this against."""

    _PY_LONG_FUNC = TestSharedCheckOnPythonAndTypeScript._PY_LONG_FUNC
    _RUST_LONG_FUNC = (
        "fn configure_pipeline(a: bool, b: bool, c: bool, d: i32) -> bool {\n"
        "    if a {\n"
        "        if b {\n"
        "            if c {\n"
        "                for i in 0..d {\n"
        "                    if i > 0 {\n"
        "                        while i > 0 {\n"
        "                            if a && b {\n"
        "                            }\n"
        "                            i -= 1;\n"
        "                        }\n"
        "                    }\n"
        "                }\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "    a\n"
        "}\n"
    )

    def test_long_complex_function_flags_identically_across_languages(
        self, tmp_path: Path
    ) -> None:
        from frob.arch._python import (
            PythonAdapter,
            _iter_normalized_functions,
            _normalized_is_complex,
        )
        from frob.arch._rust import RustAdapter
        from frob.lang import raw_tree

        py_path = tmp_path / "long_func.py"
        py_path.write_text(self._PY_LONG_FUNC)
        py_tree, py_src, py_lang = raw_tree(py_path).danger_ok
        assert py_lang == "python"
        py_module = PythonAdapter().adapt(py_tree, py_src, "long_func.py")

        rust_path = tmp_path / "long_func.rs"
        rust_path.write_text(self._RUST_LONG_FUNC)
        rust_tree, rust_src, rust_lang = raw_tree(rust_path).danger_ok
        assert rust_lang == "rust"
        rust_module = RustAdapter().adapt(rust_tree, rust_src, "long_func.rs")

        py_target = next(
            f
            for f, _prefix in _iter_normalized_functions(py_module)
            if f.name == "configure_pipeline"
        )
        rust_target = next(
            f
            for f, _prefix in _iter_normalized_functions(rust_module)
            if f.name == "configure_pipeline"
        )

        # The SAME shared check function, unmodified, called on each
        # language's NormalizedFunction -- both must fire.
        assert _normalized_is_complex(py_target)
        assert _normalized_is_complex(rust_target)


class TestRustAdapter:
    """T-0612: `frob.arch._rust.RustAdapter` is the third `LanguageAdapter`
    implementation (after T-0610's `PythonAdapter`/T-0611's
    `TypeScriptAdapter`), built off `tree-sitter-rust`. These tests
    hand-build small `.rs` fixtures covering every `NormalizedModule`
    entity kind, plus one stays-sane test on a more realistic
    multi-construct snippet."""

    def test_is_a_language_adapter(self) -> None:
        from frob.arch._normalized import LanguageAdapter
        from frob.arch._rust import RustAdapter

        adapter = RustAdapter()
        assert isinstance(adapter, LanguageAdapter)
        assert adapter.language == "rust"

    def _adapt(self, tmp_path: Path, source: str, filename: str = "mod.rs"):
        from frob.arch._rust import RustAdapter
        from frob.lang import raw_tree

        path = tmp_path / filename
        path.write_text(source)
        parsed = raw_tree(path)
        assert parsed.is_ok
        tree, src, language = parsed.danger_ok
        assert language == "rust"
        return RustAdapter().adapt(tree, src, filename)

    def test_adapt_imports(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "use std::fmt;\n"
            "use std::collections::HashMap as Map;\n"
            "use std::io::{self, Read};\n"
            "use std::io::*;\n",
        )
        assert len(module.imports) == 4
        fmt_import = next(i for i in module.imports if i.module == "std::fmt")
        assert fmt_import.names == []
        map_import = next(
            i for i in module.imports if i.module == "std::collections::HashMap"
        )
        assert map_import.names == ["Map"]
        # Both `std::io` imports (the grouped list and the bare wildcard)
        # share the same module text but are distinct entries at different
        # lines -- one binds "Read", the other binds no individual name.
        io_imports = [i for i in module.imports if i.module == "std::io"]
        assert len(io_imports) == 2
        assert {tuple(i.names) for i in io_imports} == {("Read",), ()}

    def test_adapt_struct_named_and_tuple_fields(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "struct Point(i32, i32);\n"
            "struct Animal {\n"
            "    name: String,\n"
            "    age: u32,\n"
            "}\n",
        )
        classes = {c.name: c for c in module.classes}
        assert set(classes) == {"Point", "Animal"}
        point_fields = {f.name: f.type for f in classes["Point"].fields}
        assert point_fields == {"0": "i32", "1": "i32"}
        animal_fields = {f.name: f.type for f in classes["Animal"].fields}
        assert animal_fields == {"name": "String", "age": "u32"}

    def test_adapt_enum_variants_as_fields(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "enum Shape {\n"
            "    Circle(f64),\n"
            "    Square { side: f64 },\n"
            "    Empty,\n"
            "}\n",
        )
        shape = next(c for c in module.classes if c.name == "Shape")
        assert {f.name for f in shape.fields} == {"Circle", "Square", "Empty"}

    def test_adapt_enum_variant_payload_shapes(self, tmp_path: Path) -> None:
        # T-0743: NormalizedClass.variants carries the payload shape
        # NormalizedField alone cannot -- a tuple variant, a struct
        # variant, and a unit variant must be distinguishable, with their
        # payload field names/types intact.
        module = self._adapt(
            tmp_path,
            "enum Shape {\n"
            "    Circle(f64),\n"
            "    Square { side: f64 },\n"
            "    Empty,\n"
            "}\n",
        )
        shape = next(c for c in module.classes if c.name == "Shape")
        variants = {v.name: v for v in shape.variants}
        assert set(variants) == {"Circle", "Square", "Empty"}

        circle = variants["Circle"]
        assert circle.shape == "tuple"
        assert [(p.name, p.type) for p in circle.payload] == [("0", "f64")]

        square = variants["Square"]
        assert square.shape == "struct"
        assert [(p.name, p.type) for p in square.payload] == [("side", "f64")]

        empty = variants["Empty"]
        assert empty.shape == "unit"
        assert empty.payload == []

        # The pre-existing NormalizedField mapping is untouched (additive,
        # not a replacement) -- same assertion as
        # test_adapt_enum_variants_as_fields, re-checked alongside variants.
        assert {f.name for f in shape.fields} == {"Circle", "Square", "Empty"}

    def test_adapt_function_params_and_return_type(self, tmp_path: Path) -> None:
        from frob.arch._normalized import NormalizedParam

        module = self._adapt(
            tmp_path, "fn add(x: i32, y: i32) -> i32 {\n    x + y\n}\n"
        )
        assert len(module.functions) == 1
        fn = module.functions[0]
        assert fn.name == "add"
        assert fn.return_type == "i32"
        assert fn.params == [
            NormalizedParam(name="x", type="i32"),
            NormalizedParam(name="y", type="i32"),
        ]
        # Rust has no default-parameter syntax at all -- always False.
        assert all(p.has_default is False for p in fn.params)

    def test_adapt_trait_methods_and_impl_attach(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "trait Greet {\n"
            "    fn greet(&self) -> String;\n"
            "    fn default_greet(&self) -> String {\n"
            '        String::from("hi")\n'
            "    }\n"
            "}\n"
            "struct Animal { name: String }\n"
            "impl Animal {\n"
            "    fn new(name: String) -> Self {\n"
            "        Animal { name }\n"
            "    }\n"
            "}\n",
        )
        classes = {c.name: c for c in module.classes}
        greet = classes["Greet"]
        greet_methods = {m.name: m for m in greet.methods}
        assert set(greet_methods) == {"greet", "default_greet"}
        # `greet` (`function_signature_item`, no body) has no events/body.
        assert greet_methods["greet"].body_line_count == 0
        assert greet_methods["default_greet"].body_line_count > 0

        animal = classes["Animal"]
        new_method = next(m for m in animal.methods if m.name == "new")
        assert new_method.is_method is True
        assert new_method.overrides is None
        assert new_method.params[0].name == "name"

    def test_adapt_trait_impl_notes_trait_as_base_and_sets_overrides(
        self, tmp_path: Path
    ) -> None:
        module = self._adapt(
            tmp_path,
            "use std::fmt;\n"
            "struct Animal { name: String }\n"
            "impl fmt::Debug for Animal {\n"
            "    fn fmt(&self) -> String {\n"
            "        self.name.clone()\n"
            "    }\n"
            "}\n",
        )
        animal = next(c for c in module.classes if c.name == "Animal")
        assert animal.bases == ["fmt::Debug"]
        fmt_method = next(m for m in animal.methods if m.name == "fmt")
        assert fmt_method.overrides == "fmt"

    def test_adapt_branches_loops_calls_field_accesses(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "struct Widget { count: i32 }\n"
            "impl Widget {\n"
            "    fn bump(&mut self, flag: bool) {\n"
            "        if self.count > 0 && flag {\n"
            "            self.count.checked_add(1);\n"
            "        }\n"
            "        for i in 0..3 {\n"
            "            self.count = self.count + i;\n"
            "        }\n"
            "    }\n"
            "}\n",
        )
        method = module.classes[0].methods[0]
        assert any(
            b.condition_text == "self.count > 0 && flag" for b in method.branches
        )
        assert any(loop.kind == "for" for loop in method.loops)
        assert any(c.callee == "self.count.checked_add" for c in method.calls)
        writes = [
            fa for fa in method.field_accesses if fa.name == "count" and fa.is_write
        ]
        assert writes

    def test_adapt_method_chain_does_not_confuse_calls_with_field_accesses(
        self, tmp_path: Path
    ) -> None:
        # `self.name.clone().unwrap()` -- only `name` is a genuine field
        # read; `clone`/`unwrap` are method-dispatch targets of their own
        # call sites, not field accesses (T-0612 review fix).
        module = self._adapt(
            tmp_path,
            "struct Widget { name: String }\n"
            "impl Widget {\n"
            "    fn shout(&self) -> String {\n"
            "        self.name.clone().unwrap()\n"
            "    }\n"
            "}\n",
        )
        method = module.classes[0].methods[0]
        assert [fa.name for fa in method.field_accesses] == ["name"]
        assert "self.name.clone" in [c.callee for c in method.calls]
        assert "self.name.clone().unwrap" in [c.callee for c in method.calls]

    def test_adapt_match_arms_are_branches_and_loop_kinds(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "fn classify(n: i32) -> i32 {\n"
            "    match n {\n"
            "        0 => 0,\n"
            "        m if m > 10 => 1,\n"
            "        _ => 2,\n"
            "    }\n"
            "}\n"
            "fn loops() {\n"
            "    let mut i = 0;\n"
            "    while i < 3 {\n"
            "        i += 1;\n"
            "    }\n"
            "    loop {\n"
            "        break;\n"
            "    }\n"
            "}\n",
        )
        classify = next(f for f in module.functions if f.name == "classify")
        # Each match arm counts as its own branch (T-0612's explicit
        # divergence from `_python.py`'s deliberate match/case exclusion).
        assert len(classify.branches) == 3
        assert any(b.condition_text == "m if m > 10" for b in classify.branches)

        loopy = next(f for f in module.functions if f.name == "loops")
        assert {loop.kind for loop in loopy.loops} == {"while", "loop"}

    def test_adapt_panic_macro_and_unwrap_expect_are_raises(
        self, tmp_path: Path
    ) -> None:
        module = self._adapt(
            tmp_path,
            "fn risky(v: i32) -> i32 {\n"
            "    if v == 0 {\n"
            '        panic!("zero");\n'
            "    }\n"
            "    let a = maybe().unwrap();\n"
            '    let b = maybe().expect("missing");\n'
            "    a + b\n"
            "}\n",
        )
        fn = module.functions[0]
        assert {r.exception_type for r in fn.raises} == {"panic!", "unwrap", "expect"}

    def test_adapt_err_return_and_try_operator_are_raises(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "fn risky() -> Result<i32, String> {\n"
            "    let v = maybe()?;\n"
            '    if v == 0 {\n        return Err("zero".to_string());\n    }\n'
            "    Ok(v)\n"
            "}\n",
        )
        fn = module.functions[0]
        assert {r.exception_type for r in fn.raises} == {"?", "Err"}
        # `return Err(...)` is STILL its own `NormalizedReturn` too (T-0612's
        # "in addition to, never instead of" mapping decision).
        assert any(
            r.value_text is not None and r.value_text.startswith("Err(")
            for r in fn.returns
        )

    def test_adapt_result_match_err_arm_is_a_catch(self, tmp_path: Path) -> None:
        module = self._adapt(
            tmp_path,
            "fn handle(r: Result<i32, String>) -> i32 {\n"
            "    match r {\n"
            "        Ok(v) => v,\n"
            "        Err(e) => 0,\n"
            "    }\n"
            "}\n",
        )
        fn = module.functions[0]
        assert len(fn.catches) == 1
        assert fn.catches[0].exception_type == "Err"

    def test_adapt_stays_sane_on_realistic_snippet(self, tmp_path: Path) -> None:
        # A denser, more realistic rust module exercising every entity
        # kind at once (use imports, a trait, a struct with a trait impl
        # and an inherent impl, branches/loops/calls/field-accesses/panic/
        # Result-handling, a free function) -- proves the adapter does not
        # choke or silently drop entities when they co-occur.
        module = self._adapt(
            tmp_path,
            "use std::fmt;\n"
            "\n"
            "trait Greet {\n"
            "    fn greet(&self) -> String;\n"
            "}\n"
            "\n"
            "struct Animal {\n"
            "    name: String,\n"
            "    age: u32,\n"
            "}\n"
            "\n"
            "impl fmt::Debug for Animal {\n"
            "    fn fmt(&self) -> String {\n"
            "        self.name.clone()\n"
            "    }\n"
            "}\n"
            "\n"
            "impl Animal {\n"
            "    fn new(name: String, age: u32) -> Self {\n"
            "        Animal { name, age }\n"
            "    }\n"
            "\n"
            "    fn speak(&mut self, loud: bool) -> Result<String, String> {\n"
            "        if self.age > 5 && loud {\n"
            '            println!("{}", self.name);\n'
            "        } else {\n"
            "            for i in 0..3 {\n"
            '                self.name = format!("{}{}", self.name, i);\n'
            "            }\n"
            "        }\n"
            "        match self.age {\n"
            '            0 => println!("baby"),\n'
            '            n if n > 10 => panic!("too old"),\n'
            "            _ => {}\n"
            "        }\n"
            "        if self.age == 0 {\n"
            '            return Err("zero".to_string());\n'
            "        }\n"
            "        let v = self.risky()?;\n"
            "        Ok(self.name.clone())\n"
            "    }\n"
            "\n"
            "    fn risky(&self) -> Result<String, String> {\n"
            "        Ok(self.name.clone())\n"
            "    }\n"
            "}\n"
            "\n"
            "fn standalone(x: i32, y: i32) -> i32 {\n"
            "    x + y\n"
            "}\n",
        )
        assert module.language == "rust"
        assert module.imports[0].module == "std::fmt"
        classes = {c.name: c for c in module.classes}
        assert set(classes) == {"Greet", "Animal"}
        animal = classes["Animal"]
        assert animal.bases == ["fmt::Debug"]
        methods = {m.name: m for m in animal.methods}
        assert set(methods) == {"fmt", "new", "speak", "risky"}
        assert methods["fmt"].overrides == "fmt"
        assert methods["new"].overrides is None
        speak = methods["speak"]
        assert speak.branches
        assert speak.loops
        assert speak.calls
        assert speak.field_accesses
        assert "panic!" in {r.exception_type for r in speak.raises}
        assert "Err" in {r.exception_type for r in speak.raises}
        assert "?" in {r.exception_type for r in speak.raises}
        funcs = {f.name: f for f in module.functions}
        assert set(funcs) == {"standalone"}

        # Round-trips through pydantic (de)serialization, same as the
        # hand-built python/TypeScript `NormalizedModule` shape tests.
        from frob.arch._normalized import NormalizedModule

        restored = NormalizedModule.model_validate(module.model_dump())
        assert restored == module


class TestSharedCheckOnPythonAndKotlin:
    """T-0614's acceptance criterion: a shared arch check written once
    against `NormalizedModule` fires identically on an equivalent python
    fixture (via `PythonAdapter`) and kotlin fixture (via
    `KotlinAdapter`) -- no per-language branch in the check itself. Reuses
    the same `_iter_normalized_functions`/`_normalized_is_complex` helpers
    every other `TestSharedCheckOnPythonAnd*` class already proves this
    against."""

    _PY_LONG_FUNC = TestSharedCheckOnPythonAndTypeScript._PY_LONG_FUNC
    _KOTLIN_LONG_FUNC = (
        "fun configurePipeline(a: Boolean, b: Boolean, c: Boolean, d: Int): Boolean {\n"
        "    if (a) {\n"
        "        if (b) {\n"
        "            if (c) {\n"
        "                for (i in 0..d) {\n"
        "                    if (i > 0) {\n"
        "                        while (i > 0) {\n"
        "                            if (a && b) {\n"
        "                            }\n"
        "                        }\n"
        "                    }\n"
        "                }\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "    return a\n"
        "}\n"
    )

    def test_long_complex_function_flags_identically_across_languages(self) -> None:
        import tempfile

        from frob.arch._kotlin import KotlinAdapter
        from frob.arch._python import (
            PythonAdapter,
            _iter_normalized_functions,
            _normalized_is_complex,
        )
        from frob.lang import raw_tree
        from frob.lang._walk_kotlin import parse_kotlin

        with tempfile.TemporaryDirectory() as tmp:
            py_path = Path(tmp) / "long_func.py"
            py_path.write_text(self._PY_LONG_FUNC)
            py_tree, py_src, py_lang = raw_tree(py_path).danger_ok
            assert py_lang == "python"
            py_module = PythonAdapter().adapt(py_tree, py_src, "long_func.py")

        kt_src = self._KOTLIN_LONG_FUNC.encode()
        kt_tree = parse_kotlin(kt_src)
        assert not kt_tree.root_node.has_error
        kt_module = KotlinAdapter().adapt(kt_tree, kt_src, "long_func.kt")

        py_target = next(
            f
            for f, _prefix in _iter_normalized_functions(py_module)
            if f.name == "configure_pipeline"
        )
        kt_target = next(
            f
            for f, _prefix in _iter_normalized_functions(kt_module)
            if f.name == "configurePipeline"
        )

        # The SAME shared check function, unmodified, called on each
        # language's NormalizedFunction -- both must fire.
        assert _normalized_is_complex(py_target)
        assert _normalized_is_complex(kt_target)


class TestKotlinAdapter:
    """T-0614: `frob.arch._kotlin.KotlinAdapter` is the fourth
    `LanguageAdapter` implementation (after T-0610's `PythonAdapter`/
    T-0611's `TypeScriptAdapter`/T-0612's `RustAdapter`), built off
    `tree-sitter-kotlin`. These tests hand-build small kotlin snippets
    covering every `NormalizedModule` entity kind, plus one stays-sane
    test on a more realistic multi-construct snippet."""

    def test_is_a_language_adapter(self) -> None:
        from frob.arch._kotlin import KotlinAdapter
        from frob.arch._normalized import LanguageAdapter

        adapter = KotlinAdapter()
        assert isinstance(adapter, LanguageAdapter)
        assert adapter.language == "kotlin"

    def _adapt(self, source: str, filename: str = "mod.kt"):
        from frob.arch._kotlin import KotlinAdapter
        from frob.lang._walk_kotlin import parse_kotlin

        src = source.encode()
        tree = parse_kotlin(src)
        assert not tree.root_node.has_error
        return KotlinAdapter().adapt(tree, src, filename)

    def test_adapt_imports(self) -> None:
        module = self._adapt(
            "import java.util.List\n"
            "import kotlin.io.println as printLn\n"
            "import kotlin.collections.*\n"
        )
        assert len(module.imports) == 3
        plain = next(i for i in module.imports if i.module == "java.util.List")
        assert plain.names == []
        aliased = next(i for i in module.imports if i.module == "kotlin.io.println")
        assert aliased.names == ["printLn"]
        wildcard = next(i for i in module.imports if i.module == "kotlin.collections")
        assert wildcard.names == []

    def test_adapt_class_bases_fields_and_methods(self) -> None:
        module = self._adapt(
            "interface Speaker {\n"
            "    fun speak(): String\n"
            "}\n"
            "open class Animal(val name: String, age: Int) : Speaker {\n"
            '    var mood: String = "neutral"\n'
            "    fun greet(other: Animal) {}\n"
            "}\n"
        )
        classes = {c.name: c for c in module.classes}
        assert set(classes) == {"Speaker", "Animal"}
        # `interface` and `class` share one grammar node type, so an
        # interface's own bodyless method comes back as a NormalizedClass
        # method too.
        assert {m.name for m in classes["Speaker"].methods} == {"speak"}
        assert classes["Speaker"].methods[0].body_line_count == 0

        animal = classes["Animal"]
        assert animal.bases == ["Speaker"]
        # `name` (a `val` constructor parameter) is a field; `age` (a
        # plain constructor parameter, no `val`/`var`) is NOT -- kotlin's
        # own property-vs-parameter distinction.
        field_names = {f.name for f in animal.fields}
        assert field_names == {"name", "mood"}
        assert {m.name for m in animal.methods} == {"greet"}

    def test_adapt_data_class_constructor_properties(self) -> None:
        module = self._adapt("data class Point(val x: Int, val y: Int)\n")
        point = module.classes[0]
        assert point.name == "Point"
        assert {f.name: f.type for f in point.fields} == {"x": "Int", "y": "Int"}

    def test_adapt_sealed_class_with_no_body(self) -> None:
        module = self._adapt("sealed class Shape\n")
        shape = module.classes[0]
        assert shape.name == "Shape"
        assert shape.fields == []
        assert shape.methods == []

    def test_adapt_override_modifier(self) -> None:
        module = self._adapt(
            "open class Animal {\n"
            '    open fun speak(): String { return "..." }\n'
            "}\n"
            "class Dog : Animal() {\n"
            '    override fun speak(): String { return "Woof" }\n'
            "}\n"
        )
        classes = {c.name: c for c in module.classes}
        animal_speak = classes["Animal"].methods[0]
        dog_speak = classes["Dog"].methods[0]
        assert animal_speak.overrides is None
        assert dog_speak.overrides == "speak"

    def test_adapt_function_params_and_return_type(self) -> None:
        from frob.arch._normalized import NormalizedParam

        module = self._adapt(
            "fun add(x: Int, y: Int = 5): Int {\n    return x + y\n}\n"
        )
        assert len(module.functions) == 1
        fn = module.functions[0]
        assert fn.name == "add"
        assert fn.return_type == "Int"
        assert fn.params == [
            NormalizedParam(name="x", type="Int", has_default=False),
            NormalizedParam(name="y", type="Int", has_default=True),
        ]

    def test_adapt_branches_loops_calls_field_accesses(self) -> None:
        module = self._adapt(
            "class Widget(var count: Int) {\n"
            "    fun bump(flag: Boolean) {\n"
            "        if (this.count > 0 && flag) {\n"
            "            this.count = this.count + 1\n"
            "        }\n"
            "        for (i in 1..3) {\n"
            "            print(i)\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        method = module.classes[0].methods[0]
        assert any(
            b.condition_text == "this.count > 0 && flag" for b in method.branches
        )
        assert any(loop.kind == "for" for loop in method.loops)
        assert any(c.callee == "print" for c in method.calls)
        writes = [
            fa for fa in method.field_accesses if fa.name == "count" and fa.is_write
        ]
        reads = [
            fa for fa in method.field_accesses if fa.name == "count" and not fa.is_write
        ]
        assert writes
        assert reads

    def test_adapt_method_chain_does_not_confuse_calls_with_field_accesses(
        self,
    ) -> None:
        module = self._adapt(
            "class Widget(val name: String) {\n"
            "    fun shout(): String {\n"
            "        return this.name.uppercase()\n"
            "    }\n"
            "}\n"
        )
        method = module.classes[0].methods[0]
        assert [fa.name for fa in method.field_accesses] == ["name"]
        assert "this.name.uppercase" in [c.callee for c in method.calls]

    def test_adapt_when_entries_are_branches_and_loop_kinds(self) -> None:
        module = self._adapt(
            "fun classify(mood: String) {\n"
            "    when (mood) {\n"
            '        "happy" -> print("yay")\n'
            '        "sad" -> print("aw")\n'
            '        else -> print("meh")\n'
            "    }\n"
            "}\n"
            "fun loops() {\n"
            "    var i = 0\n"
            "    while (i < 3) {\n"
            "        i = i + 1\n"
            "    }\n"
            "    do {\n"
            "        i = i - 1\n"
            "    } while (i > 0)\n"
            "}\n"
        )
        classify = next(f for f in module.functions if f.name == "classify")
        # Each `when_entry` counts as its own branch (T-0614's explicit
        # divergence from `_python.py`'s deliberate match/case exclusion,
        # the same shape as `_rust.py`'s documented `match_arm` counting).
        assert len(classify.branches) == 3
        assert any(b.condition_text == "else" for b in classify.branches)

        loopy = next(f for f in module.functions if f.name == "loops")
        assert {loop.kind for loop in loopy.loops} == {"while", "do-while"}

    def test_adapt_throw_and_catch(self) -> None:
        module = self._adapt(
            "fun risky() {\n"
            "    try {\n"
            "        doIt()\n"
            "    } catch (e: RuntimeException) {\n"
            "        print(e)\n"
            "    }\n"
            '    throw RuntimeException("bad")\n'
            "}\n"
        )
        fn = module.functions[0]
        assert len(fn.catches) == 1
        assert fn.catches[0].exception_type == "RuntimeException"
        assert any(r.exception_type == "RuntimeException" for r in fn.raises)

    def test_adapt_stays_sane_on_realistic_snippet(self) -> None:
        # A denser, more realistic kotlin module exercising every entity
        # kind at once (imports, an interface, a class implementing it
        # with a property/override/branches/loops/calls/field-accesses/
        # when/try-catch/throw, a data class, a sealed class, a free
        # function) -- proves the adapter does not choke or silently drop
        # entities when they co-occur.
        module = self._adapt(
            "package com.example\n"
            "\n"
            "import java.util.List\n"
            "\n"
            "interface Speaker {\n"
            "    fun speak(): String\n"
            "}\n"
            "\n"
            "open class Animal(val name: String, age: Int) : Speaker {\n"
            '    var mood: String = "neutral"\n'
            "\n"
            "    override fun speak(): String {\n"
            '        if (this.name.length > 3 && this.mood == "happy") {\n'
            '            return "Woof"\n'
            "        } else {\n"
            '            return "meh"\n'
            "        }\n"
            "    }\n"
            "\n"
            "    fun greet(other: Animal) {\n"
            '        this.mood = "excited"\n'
            "        other.speak()\n"
            "        for (i in 1..3) {\n"
            "            print(i)\n"
            "        }\n"
            "        when (mood) {\n"
            '            "happy" -> print("yay")\n'
            '            else -> print("meh")\n'
            "        }\n"
            "        try {\n"
            "            risky()\n"
            "        } catch (e: RuntimeException) {\n"
            "            print(e)\n"
            "        }\n"
            '        throw RuntimeException("bad")\n'
            "    }\n"
            "}\n"
            "\n"
            "data class Point(val x: Int, val y: Int)\n"
            "\n"
            "sealed class Shape\n"
            "\n"
            "fun topLevel(a: Int, b: Int = 5): Int {\n"
            "    return a + b\n"
            "}\n"
        )
        assert module.language == "kotlin"
        assert module.imports[0].module == "java.util.List"
        classes = {c.name: c for c in module.classes}
        assert set(classes) == {"Speaker", "Animal", "Point", "Shape"}
        animal = classes["Animal"]
        assert animal.bases == ["Speaker"]
        methods = {m.name: m for m in animal.methods}
        assert set(methods) == {"speak", "greet"}
        assert methods["speak"].overrides == "speak"
        assert methods["greet"].overrides is None
        greet = methods["greet"]
        assert greet.loops
        assert greet.calls
        assert greet.field_accesses
        assert greet.branches
        assert greet.raises
        assert greet.catches
        funcs = {f.name: f for f in module.functions}
        assert set(funcs) == {"topLevel"}

        # Round-trips through pydantic (de)serialization, same as the
        # hand-built python/TypeScript/rust `NormalizedModule` shape tests.
        from frob.arch._normalized import NormalizedModule

        restored = NormalizedModule.model_validate(module.model_dump())
        assert restored == module


class TestFourWayCrossLanguageEquivalence:
    """T-0615: adapts `tests/fixtures/arch/{python,typescript,rust,kotlin}/
    equiv.*` (structurally equivalent fixtures) through all four
    `LanguageAdapter`s and asserts the shared-check + entity-shape
    equivalence the epic's acceptance criterion demands."""

    @pytest.fixture()
    def py_module(self):
        """Adapts the python equivalence fixture via `PythonAdapter`."""
        from frob.arch._python import PythonAdapter
        from frob.lang import raw_tree

        path = FIXTURES / "arch" / "python" / "equiv.py"
        tree, src, language = raw_tree(path).danger_ok
        assert language == "python"
        return PythonAdapter().adapt(tree, src, "equiv.py")

    @pytest.fixture()
    def ts_module(self):
        """Adapts the typescript equivalence fixture via `TypeScriptAdapter`."""
        from frob.arch._typescript import TypeScriptAdapter
        from frob.lang import raw_tree

        path = FIXTURES / "arch" / "typescript" / "equiv.ts"
        tree, src, language = raw_tree(path).danger_ok
        assert language == "typescript"
        return TypeScriptAdapter().adapt(tree, src, "equiv.ts")

    @pytest.fixture()
    def rust_module(self):
        """Adapts the rust equivalence fixture via `RustAdapter`."""
        from frob.arch._rust import RustAdapter
        from frob.lang import raw_tree

        path = FIXTURES / "arch" / "rust" / "equiv.rs"
        tree, src, language = raw_tree(path).danger_ok
        assert language == "rust"
        return RustAdapter().adapt(tree, src, "equiv.rs")

    # T-0615 N:1 equivalence fixture (kotlin side), INLINE rather than a
    # tracked `tests/fixtures/arch/kotlin/equiv.kt` file: `.kt` is not
    # `frob.lang`-registered at all (T-draft-a78fa200), so a real, tracked
    # `.kt` file in this repo's tree trips `gate:LANG`'s LANG002 (ERROR,
    # always, no waiver -- `docs/modules/lang.md`'s own "always" framing)
    # the moment it exists, regardless of what it is used for. Every other
    # `TestKotlinAdapter` test already builds kotlin sources inline for
    # exactly this reason; this fixture follows that same, established
    # pattern rather than introducing a new tracked `.kt` file. Same
    # structural shape as `equiv.py` / `equiv.ts` / `equiv.rs`: an
    # interface, a class implementing it with a field, an overriding
    # method (kotlin DOES have a static `override` modifier -- captured in
    # `NormalizedFunction.overrides`, same as TS), and a "dispatch" free
    # function using kotlin's own idiomatic dispatch construct: `when`.
    # `frob.arch._kotlin` deliberately counts EACH when-entry as its own
    # `NormalizedBranch` (T-0614's explicit divergence, the same shape as
    # rust's `match_arm` counting) -- so `dispatchKind` scores THREE
    # branches, same as rust's `match` and unlike python's ONE
    # (elif-folded) / TS's ZERO (switch not branch-producing).
    _KOTLIN_EQUIV_SOURCE = (
        "interface Creature {\n"
        "    fun speak(): String\n"
        "}\n"
        "\n"
        "class Animal(val name: String, val age: Int = 1) : Creature {\n"
        "    override fun speak(): String {\n"
        "        return name\n"
        "    }\n"
        "}\n"
        "\n"
        "fun configurePipeline(a: Boolean, b: Boolean, c: Boolean, d: Int): Boolean {\n"
        "    if (a) {\n"
        "        if (b) {\n"
        "            if (c) {\n"
        "                for (i in 0 until d) {\n"
        "                    if (i != 0) {\n"
        "                        var n = i\n"
        "                        while (n != 0) {\n"
        "                            if (a && b) {\n"
        "                            }\n"
        "                            n -= 1\n"
        "                        }\n"
        "                    }\n"
        "                }\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "    return a\n"
        "}\n"
        "\n"
        "fun dispatchKind(kind: String): Int {\n"
        "    return when (kind) {\n"
        '        "happy" -> 0\n'
        '        "sad" -> 1\n'
        "        else -> 2\n"
        "    }\n"
        "}\n"
    )

    @pytest.fixture()
    def kt_module(self):
        """Adapts the inline kotlin equivalence source via `KotlinAdapter`
        -- `.kt` is not wired into `frob.lang`'s central `raw_tree`
        dispatch yet (T-draft-a78fa200), so this goes through
        `parse_kotlin` directly, same as `TestKotlinAdapter`'s own
        `_adapt` helper."""
        from frob.arch._kotlin import KotlinAdapter
        from frob.lang._walk_kotlin import parse_kotlin

        src = self._KOTLIN_EQUIV_SOURCE.encode()
        tree = parse_kotlin(src)
        assert not tree.root_node.has_error
        return KotlinAdapter().adapt(tree, src, "equiv.kt")

    # -- (1) entity counts/kinds equivalence, with documented waivers -----

    def test_one_class_hierarchy_per_language(
        self, py_module, ts_module, rust_module, kt_module
    ) -> None:
        """Every language's fixture yields exactly one base + one derived
        class/struct/interface-impl pair, i.e. 2 `NormalizedClass` entries."""
        for module in (py_module, ts_module, rust_module, kt_module):
            assert len(module.classes) == 2, module.language

    def test_derived_class_has_the_field_and_one_method(
        self, py_module, ts_module, rust_module, kt_module
    ) -> None:
        """The derived class (Animal) carries a `name` field and its
        `speak` method in all four languages -- python included since
        T-0727 fixed `PythonAdapter._py_class_fields` to match the real
        (unwrapped) `assignment` node shape tree-sitter-python actually
        yields, closing what was previously a documented waiver."""
        for module in (py_module, ts_module, rust_module, kt_module):
            derived = next(c for c in module.classes if c.name == "Animal")
            field_names = {f.name for f in derived.fields}
            assert "name" in field_names, module.language
            method_names = {m.name for m in derived.methods}
            assert "speak" in method_names, module.language

    def test_override_captured_except_pythons_documented_waiver(
        self, py_module, ts_module, rust_module, kt_module
    ) -> None:
        """TS (`override` modifier), rust (trait-impl inference), and
        kotlin (`override` modifier) all set `NormalizedFunction.overrides`
        on the derived class's `speak` method. Python has NO static
        override keyword/annotation for `PythonAdapter` to read -- this is
        a documented WAIVER (`frob.arch._python` has no `overrides`
        machinery at all), not a missed mapping: python's `speak` still
        overrides `Creature.speak` at runtime, it is simply not STATICALLY
        observable the way the other three languages' grammars make it."""
        ts_speak = next(
            m
            for m in next(c for c in ts_module.classes if c.name == "Animal").methods
            if m.name == "speak"
        )
        assert ts_speak.overrides == "speak"

        rust_speak = next(
            m
            for m in next(c for c in rust_module.classes if c.name == "Animal").methods
            if m.name == "speak"
        )
        assert rust_speak.overrides == "speak"

        kt_speak = next(
            m
            for m in next(c for c in kt_module.classes if c.name == "Animal").methods
            if m.name == "speak"
        )
        assert kt_speak.overrides == "speak"

        # WAIVER: python's PythonAdapter never sets `overrides` -- assert
        # the documented absence explicitly rather than skipping the
        # language, so a future adapter change that starts (or a check that
        # starts silently assuming) python populates `overrides` is caught.
        py_speak = next(
            m
            for m in next(c for c in py_module.classes if c.name == "Animal").methods
            if m.name == "speak"
        )
        assert py_speak.overrides is None

    # -- (2) shared-check identical firing, four-way -----------------------

    def test_shared_complexity_check_fires_identically_four_ways(
        self, py_module, ts_module, rust_module, kt_module
    ) -> None:
        """`_iter_normalized_functions`/`_normalized_is_complex` -- migrated
        ONCE in T-0610 and reused unmodified by every pairwise adapter test
        -- must fire on the equivalent `configure_pipeline`/
        `configurePipeline` function in ALL FOUR languages, proving the
        shared check itself carries no per-language branch."""
        from frob.arch._python import _iter_normalized_functions, _normalized_is_complex

        targets = {
            "python": next(
                f
                for f, _prefix in _iter_normalized_functions(py_module)
                if f.name == "configure_pipeline"
            ),
            "typescript": next(
                f
                for f, _prefix in _iter_normalized_functions(ts_module)
                if f.name == "configurePipeline"
            ),
            "rust": next(
                f
                for f, _prefix in _iter_normalized_functions(rust_module)
                if f.name == "configure_pipeline"
            ),
            "kotlin": next(
                f
                for f, _prefix in _iter_normalized_functions(kt_module)
                if f.name == "configurePipeline"
            ),
        }
        for language, fn in targets.items():
            assert _normalized_is_complex(fn), language

    # -- (3) per-language dispatch-branch-count divergence, pinned --------

    def test_dispatch_branch_counts_pin_the_documented_per_language_divergence(
        self, py_module, ts_module, rust_module, kt_module
    ) -> None:
        """The SAME three-way dispatch (happy/sad/else) is expressed via
        python's if/elif chain, TS's `switch`, rust's `match`, and kotlin's
        `when` -- and each language's `NormalizedBranch` count for it is
        DIFFERENT by design, not by accident:

        - python: 1 branch (`tree-sitter-python` folds an entire
          if/elif/else chain into one `if_statement` node --
          `frob.arch._python`'s own `_BRANCH_NODE_TYPES` comment).
        - typescript: 0 branches (`switch_statement` is walked for nesting
          depth but is NOT one of `frob.arch._typescript`'s
          branch-producing node types).
        - rust: 3 branches (`frob.arch._rust` counts each `match_arm` as
          its own branch, T-0612's documented divergence).
        - kotlin: 3 branches (`frob.arch._kotlin` counts each `when_entry`
          as its own branch, T-0614's documented divergence, same shape as
          rust's).

        Pinning all four counts side by side means an adapter silently
        changing its dispatch-counting behavior in EITHER direction (an
        under-count regression, or an over-eager new over-count) fails
        this test loudly instead of drifting unnoticed."""
        py_dispatch = next(f for f in py_module.functions if f.name == "dispatch_kind")
        ts_dispatch = next(f for f in ts_module.functions if f.name == "dispatchKind")
        rust_dispatch = next(
            f for f in rust_module.functions if f.name == "dispatch_kind"
        )
        kt_dispatch = next(f for f in kt_module.functions if f.name == "dispatchKind")

        assert len(py_dispatch.branches) == 1
        assert len(ts_dispatch.branches) == 0
        assert len(rust_dispatch.branches) == 3
        assert len(kt_dispatch.branches) == 3

    def test_every_module_agrees_the_dispatch_function_exists_and_is_flat(
        self, py_module, ts_module, rust_module, kt_module
    ) -> None:
        """None of the four languages' dispatch function trips the
        complexity check -- a flat three-way dispatch (whatever its
        branch-count shape) is exactly the case `_normalized_is_complex`
        must NOT punish, matching each language's own long-function rule
        intent (T-0289's "big match/case is not the smell" rationale,
        which motivated python's match/case exclusion and generalizes
        here)."""
        from frob.arch._python import _iter_normalized_functions, _normalized_is_complex

        for module, name in (
            (py_module, "dispatch_kind"),
            (ts_module, "dispatchKind"),
            (rust_module, "dispatch_kind"),
            (kt_module, "dispatchKind"),
        ):
            fn = next(
                f for f, _prefix in _iter_normalized_functions(module) if f.name == name
            )
            assert not _normalized_is_complex(fn), module.language
