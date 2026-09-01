from pathlib import Path

import pytest


class TestClosedWorldAccounting:
    """T-0158 addendum 2 remainder / T-0180: closed-world import
    accounting -- every import resolves to registry/no-capability/vetted,
    or the loud unknown fallthrough."""

    def _site_packages(self, tmp_path: Path) -> Path:
        site_packages = tmp_path / ".venv" / "lib" / "python3.11" / "site-packages"
        site_packages.mkdir(parents=True)
        return site_packages

    def test_walk_python_imports_collects_absolute_imports_only(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_closedworld.py::walk_python_imports kind="unit"
        from frob.vet._closedworld import walk_python_imports

        pkg_dir = tmp_path / "some_pkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text(
            "import os\n"
            "import requests.sessions\n"
            "from json import loads\n"
            "from . import helper\n"
            "from .sub import thing\n"
        )
        roots = walk_python_imports(pkg_dir)
        assert roots == frozenset({"os", "requests", "json"})

    def test_walk_python_imports_skips_unparseable_files(self, tmp_path: Path) -> None:
        from frob.vet._closedworld import walk_python_imports

        pkg_dir = tmp_path / "broken_pkg"
        pkg_dir.mkdir()
        (pkg_dir / "good.py").write_text("import sys\n")
        (pkg_dir / "bad.py").write_text("def f(:\n  this is not python\n")
        assert walk_python_imports(pkg_dir) == frozenset({"sys"})

    def test_resolve_import_registry_match(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_closedworld.py::resolve_import kind="unit"
        from frob.vet._closedworld import resolve_import

        result = resolve_import(
            "subprocess", root=tmp_path, cache_path=tmp_path / ".frob" / "vet.db"
        )
        assert result.resolution == "registry"

    def test_resolve_import_registry_match_via_pypi_name_override(
        self, tmp_path: Path
    ) -> None:
        # python-dotenv's DANGEROUS_OPERATIONS library field is the PyPI
        # distribution name "python-dotenv", not the import root "dotenv" --
        # the override table must bridge that.
        from frob.vet._closedworld import resolve_import

        result = resolve_import(
            "dotenv", root=tmp_path, cache_path=tmp_path / ".frob" / "vet.db"
        )
        assert result.resolution == "registry"

    def test_resolve_import_no_capability_match(self, tmp_path: Path) -> None:
        from frob.vet._closedworld import resolve_import

        result = resolve_import(
            "collections", root=tmp_path, cache_path=tmp_path / ".frob" / "vet.db"
        )
        assert result.resolution == "no-capability"

    def test_resolve_import_vetted_via_local_source_scan_and_cache(
        self, tmp_path: Path
    ) -> None:
        site_packages = self._site_packages(tmp_path)
        dep_dir = site_packages / "leaf_dep"
        dep_dir.mkdir()
        (dep_dir / "__init__.py").write_text("import subprocess\n")

        cache_path = tmp_path / ".frob" / "vet.db"
        from frob.vet._cache import _latest_verdict
        from frob.vet._closedworld import resolve_import

        result = resolve_import("leaf_dep", root=tmp_path, cache_path=cache_path)
        assert result.resolution == "vetted"
        # second call must hit the cache, not rescan
        cached = _latest_verdict(cache_path, "pypi", "leaf_dep")
        assert cached is not None
        result2 = resolve_import("leaf_dep", root=tmp_path, cache_path=cache_path)
        assert result2.resolution == "vetted"
        assert result2.detail.startswith("cached verdict")

    def test_resolve_import_unknown_when_unresolvable(self, tmp_path: Path) -> None:
        from frob.vet._closedworld import resolve_import

        result = resolve_import(
            "totally_unresolvable_pkg_xyz",
            root=tmp_path,
            cache_path=tmp_path / ".frob" / "vet.db",
        )
        assert result.resolution == "unknown"

    def test_closed_world_accounting_source_unavailable(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_closedworld.py::closed_world_accounting kind="unit"
        from frob.vet._closedworld import closed_world_accounting

        acc = closed_world_accounting(
            tmp_path,
            "pypi",
            "no-such-package",
            "1.0.0",
            cache_path=tmp_path / ".frob" / "vet.db",
        )
        assert acc.source_available is False
        assert acc.resolutions == ()
        assert acc.closed is False
        assert "source unavailable" in acc.accounting_line()

    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.registry_count \
    # kind="unit"
    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.no_capability_count \
    # kind="unit"
    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.vetted_count kind="unit"
    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.unknown_count \
    # kind="unit"
    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.accounting_line \
    # kind="unit"
    def test_closed_world_accounting_full_pass(self, tmp_path: Path) -> None:
        site_packages = self._site_packages(tmp_path)
        pkg_dir = site_packages / "top_pkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text(
            "import subprocess\n"
            "import collections\n"
            "import totally_unresolvable_pkg_xyz\n"
        )

        from frob.vet._closedworld import closed_world_accounting

        acc = closed_world_accounting(
            tmp_path,
            "pypi",
            "top_pkg",
            "1.0.0",
            cache_path=tmp_path / ".frob" / "vet.db",
        )
        assert acc.source_available is True
        assert acc.registry_count == 1
        assert acc.no_capability_count == 1
        assert acc.unknown_count == 1
        assert acc.closed is False
        assert "1 registry op(s)" in acc.accounting_line()
        assert "1 unknown" in acc.accounting_line()

    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.closed kind="unit"
    def test_closed_world_accounting_closed_when_no_unknowns(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting kind="unit"
        site_packages = self._site_packages(tmp_path)
        pkg_dir = site_packages / "clean_pkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("import subprocess\nimport collections\n")

        from frob.vet._closedworld import closed_world_accounting

        acc = closed_world_accounting(
            tmp_path,
            "pypi",
            "clean_pkg",
            "1.0.0",
            cache_path=tmp_path / ".frob" / "vet.db",
        )
        assert acc.unknown_count == 0
        assert acc.closed is True

    def test_import_resolution_model_fields(self) -> None:
        # frob:tests src/frob/vet/_models.py::ImportResolution kind="unit"
        from frob.vet._models import ImportResolution

        r = ImportResolution(import_name="os", resolution="no-capability")
        assert r.import_name == "os"
        assert r.resolution == "no-capability"
        assert r.detail == ""


# frob:ticket T-1505
class TestOpaqueIndirectionGate:
    """T-0665: fail-closed runtime-resolved capability-indirection
    obligation -- `frob.vet._capability._opaque_indirection_findings` and
    `frob.gates._opaque.opaque_gate`'s literal/non-literal split, the
    coordinator-signed category-1 boundary."""

    def test_python_getattr_non_literal_name_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text("getattr(subprocess, name)(x)\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "getattr" for f in findings)

    def test_python_getattr_literal_name_does_not_fire(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # Coordinator sign-off: "literal-key lookups that resolve
        # statically belong to the ordinary resolver path, not this gate."
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text('getattr(subprocess, "run")(x)\n')
        findings = _opaque_indirection_findings(pkg)
        assert not any(f.construct_name == "getattr" for f in findings)

    def test_python_eval_always_fires_regardless_of_argument(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # eval/exec have literal_arg_index=None -- always opaque, no
        # literal split is possible for arbitrary evaluated source text.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text('eval("1 + 1")\n')
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "eval" for f in findings)

    def test_python_import_module_non_literal_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text("importlib.import_module(mod_name).run(x)\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "importlib.import_module" for f in findings)

    def test_typescript_dynamic_import_non_literal_specifier_fires(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import(modName).then(m => m.exec(x));\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "dynamic import()" for f in findings)

    def test_typescript_dynamic_import_literal_specifier_does_not_fire(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text('import("./known-module").then(m => m.run());\n')
        findings = _opaque_indirection_findings(pkg)
        assert not any(f.construct_name == "dynamic import()" for f in findings)

    def test_c_dlsym_non_literal_symbol_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "void g() { void (*f)(const char*) = dlsym(handle, name); f(x); }\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "dlsym" for f in findings)

    def test_c_dlsym_literal_symbol_does_not_fire(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            'void g() { void (*f)(const char*) = dlsym(handle, "run_cmd"); f(x); }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert not any(f.construct_name == "dlsym" for f in findings)

    def test_kotlin_class_forname_always_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            'fun run(cls: String) { Class.forName(cls).getMethod("m").invoke(t) }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "Class.forName" for f in findings)

    def test_rust_libloading_get_fires_only_when_file_uses_libloading(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # The bare `.get(` needle is deliberately broad -- gated to files
        # that actually import libloading, so an ordinary HashMap::get in
        # an unrelated rust file never trips this.
        from frob.vet._capability_scan import _opaque_indirection_findings

        with_lib = tmp_path / "with_lib.rs"
        with_lib.write_text(
            "use libloading::Library;\n"
            'fn g(lib: &Library) { let f = lib.get(b"run_cmd").unwrap(); f(x); }\n'
        )
        assert any(
            f.construct_name == "libloading symbol lookup"
            for f in _opaque_indirection_findings(with_lib)
        )

        without_lib = tmp_path / "without_lib.rs"
        without_lib.write_text(
            'fn g(m: &std::collections::HashMap<String, i32>) { m.get("x"); }\n'
        )
        assert not any(
            f.construct_name == "libloading symbol lookup"
            for f in _opaque_indirection_findings(without_lib)
        )

    def test_finding_inside_comment_span_does_not_fire(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text("# eval(x) is just an example in a comment\n")
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()

    def test_finding_inside_string_literal_does_not_fire(self, tmp_path: Path) -> None:
        # frob:tests \
        # src/frob/vet/_capability_scan.py::_byte_offset_inside_string_literal \
        # kind="unit"
        # The single-largest false-positive class the T-0665 first-turn-on
        # measurement found: this module's OWN registry constants (e.g.
        # `needle="getattr("`) tripping their own obligation.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text('NEEDLE = "getattr("\n')
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()

    def test_arg_looks_literal_rejects_fstring_interpolation(self) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_arg_looks_literal kind="unit"
        # Kills the f-string-interpolation carve-out: an f-string WITH a
        # `{...}` interpolation is NOT a plain literal even though it
        # starts with a quote character.
        from frob.vet._capability_scan import _arg_looks_literal

        assert _arg_looks_literal(b'"run"') is True
        assert _arg_looks_literal(b'f"{name}"') is False
        assert _arg_looks_literal(b"name") is False

    def test_split_top_level_args_balances_nested_parens(self) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_split_top_level_args kind="unit"
        from frob.vet._capability_scan import _split_top_level_args

        raw = b"getattr(foo(1, 2), name)) trailing"
        # start right after "getattr("
        args = _split_top_level_args(raw, len(b"getattr("))
        assert args == [b"foo(1, 2)", b" name"]

    def test_split_top_level_args_returns_none_when_unterminated(self) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_split_top_level_args kind="unit"
        # Fail-closed: an unterminated call (truncated file / match found
        # inside an unhandled construct) returns None, which the caller
        # treats as "argument unknown" and fires rather than silently
        # passing.
        from frob.vet._capability_scan import _split_top_level_args

        assert _split_top_level_args(b"getattr(foo, name", len(b"getattr(")) is None

    def test_opaque_gate_emits_warn_severity_violation(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_opaque.py::opaque_gate kind="unit"
        import subprocess as sp

        from frob.findings import Severity
        from frob.gates._opaque import opaque_gate

        sp.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        pkg = tmp_path / "pkg.py"
        pkg.write_text("getattr(subprocess, name)(x)\n")
        sp.run(["git", "add", "pkg.py"], cwd=tmp_path, capture_output=True, check=True)

        violations = opaque_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "OPAQUE001"
        # T-1185: promoted WARN -> ERROR now that every named site is
        # fixed-or-waived repo-wide (promote-at-zero posture).
        assert violations[0].severity == Severity.ERROR
        assert violations[0].file == "pkg.py"

    def test_opaque_gate_no_findings_on_empty_tracked_set(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_opaque.py::opaque_gate kind="unit"
        from frob.gates._opaque import opaque_gate

        assert opaque_gate(tmp_path) == ()

    def test_waived_finding_is_suppressed_and_reason_recorded(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_opaque.py::opaque_gate kind="unit"
        # Acceptance criterion [1]: "Given the same construct with a
        # reasoned waiver, when checked, then it passes and the waiver
        # reason is recorded" -- the generic frob:waive engine
        # (frob.gates._apply_waivers) applies to OPAQUE001 the same way
        # it does to every other rule id, once the gate emits a real
        # Violation for it (this test proves that end to end).
        import subprocess as sp

        from frob.gates import _apply_waivers  # noqa: PLC0415 - internal, test-only
        from frob.gates._opaque import opaque_gate
        from frob.graph import build_graph

        sp.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            '# frob:waive OPAQUE001 reason="name is a trusted enum member, '
            'not attacker input"\n'
            "getattr(subprocess, name)(x)\n"
        )
        sp.run(["git", "add", "pkg.py"], cwd=tmp_path, capture_output=True, check=True)

        violations = opaque_gate(tmp_path)
        assert len(violations) == 1

        cache = tmp_path / ".frob" / "cache.db"
        snap = build_graph(tmp_path, cache).danger_ok
        kept, waived = _apply_waivers(violations, snap)
        assert kept == ()
        assert len(waived) == 1
        assert waived[0].waived is not None
        assert "trusted enum member" in waived[0].waived.reason

    def test_opaque_violation_carries_symref(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_opaque.py::opaque_gate kind="unit"
        # T-1659: OPAQUE001's Violation used to leave `symref` unset, which
        # made every `frob:waive OPAQUE001` match by FILE SCOPE
        # (`_match_waiver`'s symref-less branch) instead of the specific
        # function it was written above -- the same DEAD001/T-1652 hole.
        import subprocess as sp

        from frob.gates._opaque import opaque_gate

        sp.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        pkg = tmp_path / "pkg.py"
        pkg.write_text("def handler(name, x):\n    getattr(subprocess, name)(x)\n")
        sp.run(["git", "add", "pkg.py"], cwd=tmp_path, capture_output=True, check=True)

        violations = opaque_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].symref == "pkg.py::handler"

    def test_opaque_waiver_scoped_to_symbol_not_whole_file(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_opaque.py::opaque_gate kind="unit"
        # T-1659: a `frob:waive OPAQUE001` written above ONE function in a
        # multi-function file must NOT forgive a sibling function's own
        # OPAQUE001 finding -- pre-fix, both fell back to file-scope
        # matching and a single waiver silently covered every finding in
        # the file (the DEAD001/T-1652 shape this ticket audits for).
        import subprocess as sp

        from frob.gates import _apply_waivers  # noqa: PLC0415 - internal, test-only
        from frob.gates._opaque import opaque_gate
        from frob.graph import build_graph

        sp.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            '# frob:waive OPAQUE001 reason="waived is a trusted enum member"\n'
            "def waived(name, x):\n"
            "    getattr(subprocess, name)(x)\n"
            "\n"
            "\n"
            "def unwaived(name, x):\n"
            "    getattr(subprocess, name)(x)\n"
        )
        sp.run(["git", "add", "pkg.py"], cwd=tmp_path, capture_output=True, check=True)

        violations = opaque_gate(tmp_path)
        assert len(violations) == 2

        cache = tmp_path / ".frob" / "cache.db"
        snap = build_graph(tmp_path, cache).danger_ok
        kept, waived = _apply_waivers(violations, snap)
        assert len(kept) == 1
        assert kept[0].symref == "pkg.py::unwaived"
        assert len(waived) == 1
        assert waived[0].symref == "pkg.py::waived"

    # -- T-1659: semantic (AST-based) narrowing of the needle scan itself,
    # following the coordinator's "decide from semantics, never a lexical
    # match" directive -- these lock the exact false-positive shapes the
    # T-1659 symref-narrowing audit surfaced: `monkeypatch.setattr(...)`/
    # `model.eval(...)` (dotted attribute access, not the bare builtin),
    # `test_..._exec(...)`/`_mutation_for_eval(...)` (the needle landing
    # mid-token inside a longer identifier), and `sys.modules["x"]` read
    # (not the assignment-target WRITE the taxonomy row means) -- while a
    # genuine bare call of each kind still fires.

    def test_dotted_setattr_call_does_not_fire(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text('monkeypatch.setattr("frob.gates._x", lambda root: None)\n')
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()

    def test_dotted_eval_method_call_does_not_fire(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text("result = model.eval(assignment)\n")
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()

    def test_identifier_ending_in_builtin_name_does_not_fire(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text("def _mutation_for_eval(x):\n    return x\n")
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()

    def test_bare_setattr_call_still_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text("setattr(obj, name, value)\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "setattr" for f in findings)

    def test_sys_modules_read_does_not_fire(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text('mod = sys.modules["frob.strata._facts"]\n')
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()

    def test_sys_modules_write_still_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text('sys.modules["fake"] = FakeModule()\n')
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "sys.modules replacement" for f in findings)

    # -- T-0666: litmus fixtures for taxonomy runtime-opaque rows that have
    # NO entry in `RUNTIME_OPAQUE_CONSTRUCTS`/`OPAQUE_SOURCE_INVISIBLE` yet
    # (no detector, no fail-closed obligation, no excuse-registration).
    # Each of these locks the CURRENT honest gap -- `_opaque_indirection_
    # findings` returns no finding for the construct -- rather than leaving
    # the taxonomy row unregistered. This is real, un-addressed surface
    # against T-0339's acceptance [1] ("every runtime-opaque construct
    # FAILS CLOSED"); T-1047 (filed alongside this ticket's Done report)
    # tracks closing each of these by extending `RUNTIME_OPAQUE_CONSTRUCTS`
    # or, where the construct is genuinely source-invisible, adding a
    # REG011 excuse to `OPAQUE_SOURCE_INVISIBLE`.

    def test_python_exec_always_fires_regardless_of_argument(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "exec" row -- distinct construct_name from "eval" above;
        # RUNTIME_OPAQUE_CONSTRUCTS registers it separately (literal_arg_
        # index=None), so it should always fire, same shape as eval.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text('exec("import subprocess")\n')
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "exec" for f in findings)

    def test_python_dunder_import_computed_name_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "`__import__` with computed module name" row.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text("__import__(mod_name).run(x)\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "__import__" for f in findings)

    def test_python_setattr_monkeypatch_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "monkeypatch / module attribute mutation" row.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text("setattr(subprocess, name, real_run)\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "setattr" for f in findings)

    def test_python_container_dynamic_key_not_addressed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "callable in a container, dynamic key" row (also covers
        # the sibling "computed member access, non-constant key" row --
        # identical `container[expr](...)` shape): `handlers[key](x)`.
        # Closed by T-1051's `RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS`
        # generalized `subscript_call` detector (`_structural_opaque_
        # findings`) -- T-1047 left this unaddressed since the fixed-
        # needle+literal-arg architecture cannot express a non-constant
        # SUBSCRIPT shape, only a fixed call-name substring.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text('handlers = {"a": subprocess.run}\nhandlers[key](x)\n')
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "container dynamic-key call" for f in findings)

    def test_python_container_literal_key_call_not_addressed_by_structural_gate(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_subscript_key_looks_literal \
        # kind="unit"
        # No-regression guard for the new structural detector: a LITERAL-
        # keyed subscript call (`handlers["a"](x)`) is the ORDINARY
        # resolver's job per T-0665's literal/non-literal split, not this
        # fail-closed obligation -- must not double-fire.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text('handlers = {"a": subprocess.run}\nhandlers["a"](x)\n')
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()

    def test_opaque_structural_construct_is_frozen(self) -> None:
        # frob:waive COV006 reason="confirmed exercised: the test mutates \
        # RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS[0], an instance of the bound class -- \
        # the best-effort callgraph only sees name( call tokens, not indexed-constant \
        # attribute mutation; same disposition as the evasion-taxonomy meta-test \
        # COV006 waivers"
        # frob:tests \
        # src/frob/vet/_capability_registry/_schemas.py::_OpaqueStructuralConstruct \
        # kind="unit"
        # T-1051: `_OpaqueStructuralConstruct.model_config = ConfigDict(
        # frozen=True)` (same immutability posture as `_OpaqueConstruct`
        # above it) must actually reject a post-construction mutation --
        # kills the `frozen=True` -> `frozen=False` mutant TEST016 flagged
        # with zero coverage.
        import pydantic

        from frob.vet._capability_registry import RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS

        entry = RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS[0]
        with pytest.raises(pydantic.ValidationError):
            entry.construct_name = "mutated"

    def test_python_functools_partial_dynamic_target_fires(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "`functools.partial`/decorator indirection with dynamic
        # target" row -- closed by T-1047 (RUNTIME_OPAQUE_CONSTRUCTS now
        # registers a `functools.partial(` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text("functools.partial(resolve_target())(x)\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "functools.partial" for f in findings)

    def test_python_dunder_getattr_class_interception_fires(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "class `__getattr__`/`__getattribute__` interception"
        # row -- closed by T-1047 (a `def __getattr__(` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "class Proxy:\n"
            "    def __getattr__(self, name):\n"
            "        return subprocess.run\nobj = Proxy()\nobj.run(x)\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "__getattr__ interception" for f in findings)

    def test_python_sys_modules_replacement_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "direct `sys.modules` replacement" row (added in the
        # taxonomy doc's Phase 2 pass) -- closed by T-1047 (a
        # `sys.modules[` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            'sys.modules["subprocess"] = fake_module\n'
            "import subprocess\nsubprocess.run(x)\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "sys.modules replacement" for f in findings)

    def test_typescript_computed_member_non_constant_key_not_addressed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "computed member access, non-constant key" row -- closed
        # by T-1051's generalized `subscript_call` structural detector
        # (`_structural_opaque_findings`), the same shape T-1047 could not
        # express with a fixed needle.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("cp[key](x);\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "container dynamic-key call" for f in findings)

    def test_typescript_global_this_bracket_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "`globalThis[name]`" row -- closed by T-1047 (a
        # `globalThis[` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("globalThis[name](x);\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "globalThis[name]" for f in findings)

    def test_typescript_reflect_apply_dynamic_target_fires(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "`Reflect.get`/`Reflect.apply` with dynamic target" row
        # -- closed by T-1047 (`Reflect.get(`/`Reflect.apply(` needles).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("Reflect.apply(Reflect.get(cp, key), null, [x]);\n")
        findings = _opaque_indirection_findings(pkg)
        names = {f.construct_name for f in findings}
        assert "Reflect.get" in names
        assert "Reflect.apply" in names

    def test_typescript_proxy_interception_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "`Proxy` interception (`get`/`apply` traps)" row --
        # closed by T-1047 (a `new Proxy(` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("new Proxy(cp, { get(){ return cp.exec; } }).run(x);\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "Proxy interception" for f in findings)

    def test_typescript_container_dynamic_key_not_addressed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "callable in container, dynamic key" row -- closed by
        # T-1051's generalized `subscript_call` structural detector.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("handlers[key](x);\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "container dynamic-key call" for f in findings)

    def test_typescript_monkeypatch_module_namespace_fires(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "monkeypatch / property mutation on module namespace
        # object" row -- closed by T-1047 (a `require.cache[` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("require.cache[id].exports.exec = realExec;\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "monkeypatch module namespace" for f in findings)

    def test_c_array_nonconstant_index_not_addressed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "function pointer read via array/struct with non-
        # constant index/selector" row. The ORDINARY resolver still proves
        # this stays UNDETECTED as a resolution
        # (`test_array_fn_ptr_nonconstant_index_not_detected`, unchanged --
        # that is a SEPARATE, still-open gap in the ordinary resolver's own
        # points-to); this fixture proves the fail-closed OBLIGATION gate
        # now catches it via T-1051's generalized `subscript_call`
        # structural detector, closing THIS row.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "void (*tbl[])(const char*) = { system };\n"
            'void g(int user_selected_index) { tbl[user_selected_index]("sh"); }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(
            f.construct_name == "array-index function-pointer dispatch"
            for f in findings
        )

    def test_c_integer_cast_to_function_pointer_not_addressed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "function pointer cast from an integer/opaque value" row
        # -- closed by T-1051's `explicit_fnptr_cast_call` structural
        # detector (`((RET(*)(ARGS))expr)(...)`).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.c"
        pkg.write_text('void g(long addr) { ((void(*)(const char*))addr)("sh"); }\n')
        findings = _opaque_indirection_findings(pkg)
        assert any(
            f.construct_name == "integer-cast to function pointer" for f in findings
        )

    def test_c_void_star_backcast_not_addressed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "function pointer through `void*` indirection and
        # back-cast" row -- closed by T-1051's `named_type_cast_call`
        # structural detector (`((TypeName)expr)(...)`).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "typedef void (*Handler)(const char*);\n"
            'void g() { void *p = get_handler(); ((Handler)p)("sh"); }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(
            f.construct_name == "void* back-cast to function pointer" for f in findings
        )

    def test_cpp_array_runtime_index_not_addressed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "function pointer through array/vector with runtime
        # index" row -- closed by T-1051's `subscript_call` structural
        # detector (same shape as the sibling C row above, `.cpp`
        # extension exercises the identical `language="c-cpp"` bucket).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "void g(int user_idx) {\n"
            "    void (*handlers[])(const char*) = { system };\n"
            '    handlers[user_idx]("sh");\n'
            "}\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(
            f.construct_name == "array-index function-pointer dispatch"
            for f in findings
        )

    def test_cpp_pointer_to_member_call_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # frob:ticket T-1505
        # T-1063/T-1505 residue: taxonomy "member-function pointer bound to
        # a named member" row (`auto p = &Ops::run; (obj.*p)(x);`) --
        # `test_member_function_pointer_bound_to_named_member_not_detected`
        # (above, `TestCapabilityScanCppTaxonomyClosureResolution`) already
        # locks the ORDINARY resolver's honest non-resolution; this fixture
        # proves the fail-closed OBLIGATION gate now catches the same site
        # via the new `cpp_pointer_to_member_call` structural detector.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "struct Ops { static void run(const char*); };\n"
            "void g() {\n"
            "    auto p = &Ops::run;\n"
            '    (Ops::*p)("sh");\n'
            "}\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "pointer-to-member call" for f in findings)

    def test_cpp_reinterpret_cast_to_function_pointer_fires(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "`reinterpret_cast` from an integer/opaque handle" row
        # -- closed by T-1047 (a `reinterpret_cast<` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "typedef void (*Handler)(const char*);\n"
            'void g(long addr) { reinterpret_cast<Handler>(addr)("sh"); }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(
            f.construct_name == "reinterpret_cast to function pointer" for f in findings
        )

    def test_cpp_rtti_driven_dispatch_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "RTTI-driven dispatch (`typeid`/`dynamic_cast`)" row --
        # closed by T-1047 (a `typeid(` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "void g(Base *obj) {\n"
            '    if (typeid(*obj) == typeid(Derived)) { system("sh"); }\n'
            "}\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "RTTI-driven dispatch" for f in findings)

    def test_rust_trait_object_dynamic_dispatch_not_addressed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "trait-object dynamic dispatch" row. Bounded-polymorphism
        # dispatch through a statically-enumerable impl set is explicitly
        # OUT of this gate's scope by design (`_opaque.py`'s own module
        # docstring) -- but no `frob:enforces`/registry cross-check
        # currently distinguishes "bounded, in-repo impl set" from "open,
        # plugin-arriving" trait objects for Rust specifically the way the
        # gate's docstring claims is handled; this fixture records the
        # current as-built behavior (silent) rather than asserting the
        # nuanced claim is fully implemented -- see T-1047.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "trait Spawn { fn spawn(&self, x: &str); }\n"
            "fn g(s: &dyn Spawn, x: &str) { s.spawn(x); }\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()

    def test_rust_extern_ffi_symbol_excused_source_invisible(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_opaque.py::OPAQUE_SOURCE_INVISIBLE \
        # kind="unit"
        # taxonomy "`extern` block FFI symbol binding resolved by the
        # dynamic linker" row. Same source-invisible shape as the C
        # weak-symbol row `OPAQUE_SOURCE_INVISIBLE` already excuses (T-0665)
        # -- closed by T-1047: a dedicated rust `extern`-block excuse entry
        # now exists (distinct from the vtable-patch entry). No finding
        # fires (source-invisible, category-3 per T-0665 doctrine) but the
        # accountability record is asserted, not silent non-detection.
        from frob.vet._capability_registry import OPAQUE_SOURCE_INVISIBLE
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'extern "C" { fn run_cmd(s: *const i8); }\n'
            "fn g(x: *const i8) { unsafe { run_cmd(x); } }\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()
        rust_excuses = [e for e in OPAQUE_SOURCE_INVISIBLE if e.language == "rust"]
        assert any("extern" in e.reason for e in rust_excuses)

    def test_rust_function_pointer_in_container_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "function pointer stored in and read from a container"
        # row -- closed by T-1047 (a `Vec<fn(` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            'fn g(i: usize, v: Vec<fn(&str)>) { v[i]("sh"); }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(
            f.construct_name == "function pointer in container" for f in findings
        )

    def test_rust_boxed_dyn_fn_runtime_selected_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "`Box<dyn Fn>` built from a runtime-selected source" row
        # -- closed by T-1047 (a `Box<dyn Fn` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "fn g(cond: bool, a: fn(&str), b: fn(&str), x: &str) {\n"
            "    let f: Box<dyn Fn(&str)> = if cond { Box::new(a) } else { Box::new(b) };\n"
            "    f(x);\n"
            "}\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "Box<dyn Fn> runtime-selected" for f in findings)

    def test_rust_macro_rules_dangerous_body_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # frob:ticket T-1505
        # T-1063/T-1505 residue: taxonomy "`macro_rules!` expansion
        # emitting a fixed call" row --
        # `test_macro_rules_expansion_emitting_fixed_call_not_detected`
        # (above, `TestCapabilityScanRustBindingResolution`) already locks
        # the ORDINARY resolver's honest non-resolution; this fixture
        # proves the fail-closed OBLIGATION gate now catches the same site
        # via the new `rust_macro_invisible_call` structural detector,
        # needle-gated on the macro's OWN body (through the `Command as C`
        # alias) so an ordinary, harmless local macro never fires -- see
        # `test_rust_macro_rules_benign_body_not_addressed` below.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            'macro_rules! run { ($x:expr) => { C::new("sh").arg($x).spawn() } }\n'
            'fn f() { run!("x"); }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(
            f.construct_name == "macro_rules! expansion emitting a fixed call"
            for f in findings
        )

    def test_rust_macro_rules_benign_body_not_addressed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # frob:ticket T-1505
        # The needle-gate's own negative case: a locally-defined macro
        # whose body contains nothing registry-dangerous (ordinary parser/
        # DSL boilerplate, the common real-world shape -- this repo's own
        # `strata-core/src/parse/lexer.rs` defines dozens) must NOT fire,
        # or every such macro in this repo's own corpus would falsely
        # trip the fail-closed obligation on every `frob check` run.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "macro_rules! double { ($x:expr) => { $x * 2 } }\n"
            "fn f() { let y = double!(3); }\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert not any(
            f.construct_name == "macro_rules! expansion emitting a fixed call"
            for f in findings
        )

    def test_rust_proc_macro_synthesized_call_excused_source_invisible(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_opaque.py::OPAQUE_SOURCE_INVISIBLE \
        # kind="unit"
        # taxonomy "procedural / derive macros synthesizing a call from
        # external input" row -- mirrors the `macro_rules!` resolver gap
        # `test_macro_rules_expansion_emitting_fixed_call_not_detected`
        # already locks for the ordinary resolver (that resolver-level
        # gap remains open, tracked separately). This is the fail-closed-
        # obligation-gate sibling: closed by T-1047 with a dedicated rust
        # proc-macro excuse entry (category-3, source-invisible -- the
        # expansion never appears in this file's text at all).
        from frob.vet._capability_registry import OPAQUE_SOURCE_INVISIBLE
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.rs"
        pkg.write_text("#[derive(RunFromAttribute)]\nstruct Job;\n")
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()
        rust_excuses = [e for e in OPAQUE_SOURCE_INVISIBLE if e.language == "rust"]
        assert any("proc" in e.reason or "macro" in e.reason for e in rust_excuses)

    def test_kotlin_function_value_in_container_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "function value stored in and read from a container" row
        # -- closed by T-1047 (a `]!!(` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            'val handlers: Map<String, (String) -> Unit> = mapOf("a" to ::ProcessBuilder)\n'
            'fun g(key: String) { handlers[key]!!("sh") }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "function value in container" for f in findings)

    def test_kotlin_delegated_property_by_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "delegated property / `by` indirection resolving at
        # runtime" row -- closed by T-1047 (a `by lazy {` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            "val f: (String) -> Unit by lazy { ::ProcessBuilder }\n"
            'fun g() { f("sh") }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "delegated property by" for f in findings)

    def test_kotlin_dynamic_classloading_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "dynamic classloading (`URLClassLoader` etc.)" row --
        # closed by T-1047 (a `URLClassLoader(` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            "fun g(clsName: String) {\n"
            "    val cls = URLClassLoader(arrayOf()).loadClass(clsName)\n"
            "}\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "dynamic classloading" for f in findings)

    def test_kotlin_kcallable_call_always_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "`KFunction`/`KCallable.call` obtained dynamically" row
        # -- RUNTIME_OPAQUE_CONSTRUCTS registers a separate "KCallable.call"
        # entry (deliberately broad `.call(` needle, literal_arg_index=
        # None) from the "Class.forName" entry above.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            "fun g(methodName: String, target: Any, x: String) {\n"
            "    val f = target::class.members.first { it.name == methodName }\n"
            "    f.call(x)\n"
            "}\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "KCallable.call" for f in findings)

    def test_kotlin_operator_invoke_instance_call_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # frob:ticket T-1505
        # T-1063/T-1505 residue: taxonomy "`operator fun invoke` making an
        # object directly callable" row --
        # `test_operator_fun_invoke_making_object_directly_callable_not_detected`
        # (above, `TestCapabilityScanKotlinTaxonomyClosureResolution`)
        # already locks the ORDINARY resolver's honest non-resolution (no
        # receiver-instance points-to); this fixture proves the fail-
        # closed OBLIGATION gate now catches the SAME construct-then-call
        # shape via the new `kotlin_operator_invoke_call` structural
        # detector.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            "import java.lang.Runtime\n"
            "class Handler { operator fun invoke(x: String) { "
            "Runtime.getRuntime() } }\n"
            'fun g() { val h = Handler(); h("sh") }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(
            f.construct_name == "operator fun invoke instance call" for f in findings
        )

    def test_typescript_eval_always_fires_regardless_of_argument(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "`eval`" row (TS/JS's own copy of the construct Python's
        # `eval` row above already locks a sibling fixture for) --
        # RUNTIME_OPAQUE_CONSTRUCTS registers a separate `language=
        # "typescript"` "eval" entry (literal_arg_index=None), so this row
        # needs its own litmus rather than reusing Python's.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("eval(\"require('child_process').exec(x)\");\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "eval" for f in findings)

    def test_typescript_function_constructor_always_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "`new Function(...)`" row.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            'new Function("x", "return require(\'child_process\').exec(x)")(x);\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "Function constructor" for f in findings)

    def test_c_weak_symbol_override_excused_source_invisible(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_opaque.py::OPAQUE_SOURCE_INVISIBLE \
        # kind="unit"
        # taxonomy "weak-symbol override resolved by the linker/loader" row
        # (C). Unlike the other C runtime rows, this one is DELIBERATELY
        # not a fixture-with-a-finding: the T-0665 sign-off excuses it via
        # a REG011-compliant "none -- <explanation>" disposition in
        # `OPAQUE_SOURCE_INVISIBLE` rather than a detector, since no
        # per-source-file scan can see linker-level symbol interposition.
        # This litmus locks that the excuse entry itself still exists
        # (a REG011 accountability record, not silence).
        from frob.vet._capability_registry import OPAQUE_SOURCE_INVISIBLE

        c_cpp_excuses = [e for e in OPAQUE_SOURCE_INVISIBLE if e.language == "c-cpp"]
        assert len(c_cpp_excuses) == 1
        assert "weak-symbol" in c_cpp_excuses[0].reason

    def test_rust_runtime_vtable_patch_excused_source_invisible(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_opaque.py::OPAQUE_SOURCE_INVISIBLE \
        # kind="unit"
        # Rust's own `OPAQUE_SOURCE_INVISIBLE` entries: a runtime vtable
        # patch (unsafe raw-pointer rewrite of a trait object's vtable
        # slot), plus, as of T-1047, a dedicated `extern` FFI symbol
        # excuse and a proc-macro-expansion excuse (each its own entry,
        # each its own reason -- REG011 per-entry accountability, not a
        # shared blanket rust exemption). This litmus locks that the
        # vtable-patch excuse specifically still exists among however
        # many rust entries there are, so a future edit cannot silently
        # drop it.
        from frob.vet._capability_registry import OPAQUE_SOURCE_INVISIBLE

        rust_excuses = [e for e in OPAQUE_SOURCE_INVISIBLE if e.language == "rust"]
        assert len(rust_excuses) == 3
        vtable_excuses = [e for e in rust_excuses if "vtable" in e.reason]
        assert len(vtable_excuses) == 1
        assert "vtable" in rust_excuses[0].reason

    def test_cpp_virtual_dispatch_bounded_polymorphism_no_finding(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings \
        # kind="unit"
        # taxonomy "virtual dispatch through a base pointer" row.
        # `_opaque.py`'s own module docstring carves BOUNDED POLYMORPHISM
        # (ordinary virtual dispatch whose implementation set is statically
        # enumerable in-repo) OUT of this gate's scope by design -- not a
        # gap, a deliberate exclusion, since the may-analysis is sound over
        # the statically-visible override set. This litmus locks that
        # design intent: an ordinary virtual call produces no
        # opaque-indirection finding.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "struct Base { virtual void run(const char*) = 0; };\n"
            "struct Derived : Base { void run(const char* x) override { system(x); } };\n"
            "void g(Base *base, const char *x) { base->run(x); }\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()


class TestEvasionTaxonomyExhaustiveness:
    """T-0666: cross-language exhaustiveness meta-test. Parses
    `docs/design/capability-evasion-taxonomy.md`'s per-language tables AT
    TEST TIME (not a hardcoded copy of the row counts) and asserts every
    row maps to >=1 registered litmus fixture via
    `frob.vet._evasion_coverage._EVASION_LITMUS_MAP` -- the explicit,
    greppable, statically-checkable registration T-0666's own acceptance
    criteria require. Validates BOTH directions (the "dangling test refs"
    check): (1) the doc's row COUNT per (language, category) never exceeds
    the map's registered litmus COUNT for that pair (a new taxonomy row
    added with no matching new fixture fails the build, acceptance [1]);
    (2) every dotted `Class.method` path the map lists actually resolves
    to a real test defined in this file (a stale/renamed reference fails
    the build too, not silently passes)."""

    _TAXONOMY_DOC = (
        Path(__file__).resolve().parent.parent.parent
        / "docs"
        / "design"
        / "capability-evasion-taxonomy.md"
    )

    @staticmethod
    def _doc_row_counts() -> dict[tuple[str, str], int]:
        # frob:tests \
        # tests/vet_suite/test_opaque_indirection.py::TestEvasionTaxonomyExhaustivenes\
        # s kind="unit"
        """Parse the taxonomy doc's `## <Language>` sections at call time,
        counting `| static |...` and `| runtime |...` table rows under
        each heading -- the doc IS the denominator, never a hardcoded
        number in this test module."""
        from frob.vet._evasion_coverage import _DOC_HEADING_TO_LANGUAGE_KEY

        text = TestEvasionTaxonomyExhaustiveness._TAXONOMY_DOC.read_text()
        counts: dict[tuple[str, str], int] = {}
        current_key: str | None = None
        for line in text.splitlines():
            if line.startswith("## "):
                heading = line[3:].strip()
                current_key = _DOC_HEADING_TO_LANGUAGE_KEY.get(heading)
                continue
            if current_key is None:
                continue
            if line.startswith("| static |"):
                counts[(current_key, "static")] = (
                    counts.get((current_key, "static"), 0) + 1
                )
            elif line.startswith("| runtime |"):
                counts[(current_key, "runtime")] = (
                    counts.get((current_key, "runtime"), 0) + 1
                )
        return counts

    def test_every_doc_heading_recognized(self) -> None:
        # frob:tests src/frob/vet/_evasion_coverage.py::_DOC_HEADING_TO_LANGUAGE_KEY \
        # kind="unit"
        # frob:waive COV006 reason="T-1024: genuinely read directly by this test (dict \
        # subscript/iteration/membership, not a call), which frob.graph.callgraph's \
        # best-effort reachability heuristic cannot see"
        # Dangling-heading check: every `## <Language>` heading actually
        # present in the taxonomy doc must be a key
        # `_DOC_HEADING_TO_LANGUAGE_KEY` recognizes -- a renamed heading
        # (e.g. "TypeScript / JavaScript" -> "TypeScript/JavaScript") would
        # otherwise silently drop that language's rows from the count
        # entirely rather than failing loudly.
        from frob.vet._evasion_coverage import _DOC_HEADING_TO_LANGUAGE_KEY

        text = self._TAXONOMY_DOC.read_text()
        doc_headings = {
            line[3:].strip() for line in text.splitlines() if line.startswith("## ")
        }
        # The doc also carries non-language headings (Purpose, Combined
        # coverage table, Honesty and sourcing) -- only assert every
        # KNOWN-LANGUAGE heading this map claims to cover is genuinely
        # present verbatim (the reverse of "every doc heading is mapped").
        for heading in _DOC_HEADING_TO_LANGUAGE_KEY:
            assert heading in doc_headings, (
                f"_DOC_HEADING_TO_LANGUAGE_KEY claims heading {heading!r} "
                "but it is not present verbatim in "
                "capability-evasion-taxonomy.md -- stale mapping"
            )

    def test_every_litmus_path_resolves_to_a_real_test(self) -> None:
        # frob:tests src/frob/vet/_evasion_coverage.py::_EVASION_LITMUS_MAP kind="unit"
        # frob:waive COV006 reason="T-1024: genuinely read directly by this test (dict \
        # subscript/iteration/membership, not a call), which frob.graph.callgraph's \
        # best-effort reachability heuristic cannot see"
        # Dangling-ref check (direction 2): every "Class.method" string in
        # _EVASION_LITMUS_MAP must be a REAL class+method actually defined
        # SOMEWHERE in the tests/vet_suite/ package -- a typo'd or
        # renamed-but-not-updated reference fails loudly rather than
        # silently claiming coverage that does not exist. Uses `ast`
        # (static, no pytest-collect dependency) so this check has no
        # test-runner-ordering hazard. T-3593: the litmus fixtures used to
        # all live in this one file's monofile predecessor
        # (tests/test_vet.py); the per-gate-family split scattered them
        # across sibling modules in this same package, so the search must
        # cover the whole package, not just this file.
        import ast

        from frob.vet._evasion_coverage import _EVASION_LITMUS_MAP

        package_dir = Path(__file__).resolve().parent
        real: set[str] = set()
        for module_path in package_dir.glob("*.py"):
            tree = ast.parse(module_path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for child in node.body:
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            real.add(f"{node.name}.{child.name}")

        missing: list[str] = []
        for (language, category), paths in _EVASION_LITMUS_MAP.items():
            for path in paths:
                if path not in real:
                    missing.append(f"{language}/{category}: {path}")
        assert not missing, (
            "_EVASION_LITMUS_MAP references test(s) that do not exist in "
            f"tests/vet_suite/: {missing}"
        )

    def test_every_taxonomy_row_has_sufficient_registered_litmus_coverage(
        self,
    ) -> None:
        # frob:tests src/frob/vet/_evasion_coverage.py::_EVASION_LITMUS_MAP kind="unit"
        # frob:waive COV006 reason="T-1024: genuinely read directly by this test (dict \
        # subscript/iteration/membership, not a call), which frob.graph.callgraph's \
        # best-effort reachability heuristic cannot see"
        # Acceptance [0]: "given the full evasion taxonomy denominator,
        # when the meta-test runs, then every entry maps to >=1 registered
        # litmus fixture." Acceptance [1]: "given a new taxonomy entry
        # added with no fixture, when the meta-test runs, then it fails
        # the build" -- this is the count-floor check that makes that
        # true: the doc's own row count per (language, category), parsed
        # fresh every run, must never exceed the number of litmus paths
        # registered for that pair.
        from frob.vet._evasion_coverage import _EVASION_LITMUS_MAP

        doc_counts = self._doc_row_counts()
        shortfalls: list[str] = []
        for key, doc_count in doc_counts.items():
            registered = len(_EVASION_LITMUS_MAP.get(key, ()))
            if registered < doc_count:
                shortfalls.append(
                    f"{key[0]}/{key[1]}: doc has {doc_count} row(s), only "
                    f"{registered} litmus path(s) registered in "
                    "_EVASION_LITMUS_MAP -- add the missing fixture(s)"
                )
        assert not shortfalls, "\n".join(shortfalls)

    def test_map_has_no_orphaned_language_category_pairs(self) -> None:
        # frob:tests src/frob/vet/_evasion_coverage.py::_EVASION_LITMUS_MAP kind="unit"
        # frob:waive COV006 reason="T-1024: genuinely read directly by this test (dict \
        # subscript/iteration/membership, not a call), which frob.graph.callgraph's \
        # best-effort reachability heuristic cannot see"
        # Reverse sanity: every (language, category) key in
        # _EVASION_LITMUS_MAP must correspond to a pair the doc actually has
        # at least one row for -- catches a typo'd language/category key
        # in the map itself (e.g. "kotln" or "statc") that would otherwise
        # silently register litmus paths nothing ever cross-checks.
        from frob.vet._evasion_coverage import _EVASION_LITMUS_MAP

        doc_counts = self._doc_row_counts()
        orphaned = [key for key in _EVASION_LITMUS_MAP if key not in doc_counts]
        assert not orphaned, (
            f"_EVASION_LITMUS_MAP has key(s) with no matching doc rows: {orphaned}"
        )

    def test_combined_registered_total_matches_112_entry_denominator(self) -> None:
        # frob:tests src/frob/vet/_evasion_coverage.py::_EVASION_LITMUS_MAP kind="unit"
        # frob:waive COV006 reason="T-1024: genuinely read directly by this test (dict \
        # subscript/iteration/membership, not a call), which frob.graph.callgraph's \
        # best-effort reachability heuristic cannot see"
        # T-0339's own framing (and `docs/design/registry/evasion.yaml`'s
        # 112 EVA-<LANG>-<S|R><NN> ids, reconciled in
        # `docs/design/registry/RECONCILIATION.md`) name 112 as the
        # working denominator. This locks that _EVASION_LITMUS_MAP's total
        # registered litmus count is >= 112 -- never fewer than the
        # reconciled registry total, even though (per this test class's
        # own module docstring) the taxonomy doc's OWN raw table-row count
        # is higher for python's two extra rows found this pass (see this
        # ticket's Done report for the doc-vs-registry count-mismatch
        # finding, filed as a documentation-accuracy follow-up rather than
        # resolved here since docs/design/capability-evasion-taxonomy.md
        # is outside T-0666's declared scope).
        from frob.vet._evasion_coverage import _EVASION_LITMUS_MAP

        total = sum(len(v) for v in _EVASION_LITMUS_MAP.values())
        assert total >= 112, (
            f"_EVASION_LITMUS_MAP total registered litmus paths ({total}) is "
            "below the 112-entry reconciled denominator"
        )


# frob:ticket T-1433
class TestOperationEntryMatchesFallthrough:
    """T-1465: `_operation_entry_matches` must return `False`
    (not implicitly `None`, ty's invalid-return-type finding) for an
    entry with no `needles` whose `function_or_pattern` is not a
    Python bare-`compile(` special case -- the fallthrough branch."""

    # frob:ticket T-1433
    def test_no_needles_and_not_bare_compile_returns_false(self) -> None:
        # frob:tests src/frob/vet/_capability_core.py::_operation_entry_matches \
        # kind="unit"
        from frob.vet._capability_core import _operation_entry_matches
        from frob.vet._capability_registry._schemas import _DangerousOperation

        entry = _DangerousOperation(
            language="python",
            library="os",
            function_or_pattern="os.system(",
            capability_kind="exec",
            rationale="test fixture",
            safer_alternative="subprocess.run",
            severity="high",
            needles=(),
        )
        result = _operation_entry_matches(entry, b"nothing relevant here", ())
        assert result is False


class TestNeedleMatchesResolvedTokenBoundary:
    """T-2507: `_needle_matches_resolved` compares RESOLVED dotted
    identities as dotted-segment sequences with boundary equality, not
    substring containment. The falsifiable proof that the fix is real
    (not cosmetic): with segment comparison, a needle's trailing
    punctuation ("subprocess.", "os.system(") is REDUNDANT -- dropping it
    must not change a single verdict below. Every pair in this class is
    run BOTH with and without its registry punctuation and must agree."""

    # frob:ticket T-2507

    def test_module_prefix_matches_with_and_without_trailing_dot(self) -> None:
        # frob:tests src/frob/vet/_capability_core.py::_needle_matches_resolved \
        # kind="unit"
        from frob.vet._capability_core import _needle_matches_resolved

        assert _needle_matches_resolved("subprocess.", "subprocess.run") is True
        assert _needle_matches_resolved("subprocess", "subprocess.run") is True
        assert _needle_matches_resolved("subprocess.", "subprocess.Popen") is True
        assert _needle_matches_resolved("subprocess", "subprocess.Popen") is True

    def test_call_target_matches_with_and_without_trailing_paren(self) -> None:
        # frob:tests src/frob/vet/_capability_core.py::_needle_matches_resolved \
        # kind="unit"
        from frob.vet._capability_core import _needle_matches_resolved

        assert _needle_matches_resolved("os.system(", "os.system") is True
        assert _needle_matches_resolved("os.system", "os.system") is True

    def test_bare_identifier_matches_with_and_without_trailing_paren(self) -> None:
        # frob:tests src/frob/vet/_capability_core.py::_needle_matches_resolved \
        # kind="unit"
        from frob.vet._capability_core import _needle_matches_resolved

        assert _needle_matches_resolved("Popen(", "subprocess.Popen") is True
        assert _needle_matches_resolved("Popen", "subprocess.Popen") is True
        assert _needle_matches_resolved("Popen(", "Popen") is True
        assert _needle_matches_resolved("Popen", "Popen") is True

    def test_family_prefix_still_reaches_sibling_family(self) -> None:
        """`"os.exec"` (no trailing marker) is a deliberate family prefix
        meant to reach `os.execv`/`os.execve`/etc -- unaffected by the
        punctuation-drop property since it never had trailing punctuation
        to drop; kept here as the still-intentional loose case."""
        # frob:tests src/frob/vet/_capability_core.py::_needle_matches_resolved \
        # kind="unit"
        from frob.vet._capability_core import _needle_matches_resolved

        assert _needle_matches_resolved("os.exec", "os.execv") is True
        assert _needle_matches_resolved("os.exec", "os.execve") is True

    def test_no_false_positive_on_module_name_substring(self) -> None:
        """The exact false positive named in T-2507's own body: needle
        `"net"` must NOT substring-hit `"netrc"`/`"network_helper"` --
        the class of bug this ticket exists to close."""
        # frob:tests src/frob/vet/_capability_core.py::_needle_matches_resolved \
        # kind="unit"
        from frob.vet._capability_core import _needle_matches_resolved

        assert _needle_matches_resolved("net", "netrc") is False
        assert _needle_matches_resolved("net", "network_helper") is False
        assert _needle_matches_resolved("net.", "netrc") is False

    def test_no_false_positive_on_call_target_substring(self) -> None:
        """The other T-2507 example: needle `"os.system("` must not
        substring-hit an unrelated `"myos.system"` -- true with or
        without the trailing call-paren, since the leading segment
        `"myos"` never equals `"os"` exactly."""
        # frob:tests src/frob/vet/_capability_core.py::_needle_matches_resolved \
        # kind="unit"
        from frob.vet._capability_core import _needle_matches_resolved

        assert _needle_matches_resolved("os.system(", "myos.system") is False
        assert _needle_matches_resolved("os.system", "myos.system") is False

    def test_no_false_positive_on_bare_identifier_substring(self) -> None:
        # frob:tests src/frob/vet/_capability_core.py::_needle_matches_resolved \
        # kind="unit"
        from frob.vet._capability_core import _needle_matches_resolved

        assert _needle_matches_resolved("Popen(", "NotPopen") is False
        assert _needle_matches_resolved("Popen", "NotPopenEither") is False

    def test_module_prefix_does_not_match_unrelated_leading_segment(self) -> None:
        # frob:tests src/frob/vet/_capability_core.py::_needle_matches_resolved \
        # kind="unit"
        from frob.vet._capability_core import _needle_matches_resolved

        assert _needle_matches_resolved("subprocess.", "subprocess2.run") is False
        assert _needle_matches_resolved("subprocess", "subprocess2.run") is False
