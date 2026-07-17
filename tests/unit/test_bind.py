"""Unit tests for frob.bind: BIND-comment scanning and mismatch detection."""

from __future__ import annotations

from frob.bind import check, scan_bindings, scan_sources


def test_scan_bindings_finds_cpp_and_rust(tmp_path):
    # frob:tests src/frob/bind/__init__.py::scan_bindings kind="unit"
    (tmp_path / "glue.cpp").write_text(
        '// BIND: int add(int a, int b)\nint add(int a, int b) { return a + b; }\n'
    )
    (tmp_path / "glue.rs").write_text(
        "// BIND: fn sub(a: i32, b: i32) -> i32\nfn sub(a: i32, b: i32) -> i32 { a - b }\n"
    )
    decls = scan_bindings(tmp_path)
    kinds = {d.kind for d in decls}
    assert kinds == {"pybind11", "pyo3"}
    assert any("add" in d.signature for d in decls)
    assert any("sub" in d.signature for d in decls)


def test_scan_sources_finds_header_and_rust(tmp_path):
    # frob:tests src/frob/bind/__init__.py::scan_sources kind="unit"
    (tmp_path / "glue.h").write_text("int add(int a, int b);\n")
    (tmp_path / "glue.rs").write_text(
        "#[pyfunction]\nfn sub(a: i32, b: i32) -> i32 { a - b }\n"
    )
    decls = scan_sources(tmp_path)
    kinds = {d.kind for d in decls}
    assert "cpp_header" in kinds
    assert "rust" in kinds
    assert any("add" in d.signature for d in decls)


def test_check_reports_mismatch_for_unbound_binding(tmp_path):
    (tmp_path / "glue.cpp").write_text(
        '// BIND: int mystery(int x)\nint mystery(int x) { return x; }\n'
    )
    mismatches = check(tmp_path)
    assert len(mismatches) == 1
    assert "mystery" in mismatches[0].issue
