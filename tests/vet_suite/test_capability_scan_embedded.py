from pathlib import Path


class TestEmbeddedCodeCapability:
    """T-0244: HTML/JS string literals embedded in python source (the
    malmberg pilot P3 dashboard-as-a-string shape) -- fail-closed
    `embedded_code` declaration plus best-effort typescript-needle
    re-scan of the region's own text."""

    def test_embedded_html_script_string_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0244: a large HTML/JS-shaped string literal inside a python
        # module (the malmberg pilot P3 shape) surfaces `embedded_code`
        # AND, since the embedded script itself calls `eval(`, the
        # typescript-needle re-scan's `eval` hit too.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "dashboard.py"
        padding = "x" * 40
        pkg.write_text(
            "DASHBOARD_HTML = '''\n"
            "<!doctype html>\n"
            "<html><body>\n"
            "<script>\n"
            f"// {padding}\n"
            f"// {padding}\n"
            "function render(payload) { eval(payload); }\n"
            "document.getElementById('root').innerHTML = render();\n"
            "</script>\n"
            "</body></html>\n"
            "'''\n"
        )
        capabilities = scan_file_capabilities(pkg)
        assert "embedded_code" in capabilities
        assert "eval" in capabilities

    def test_embedded_code_region_below_size_threshold_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0244: a short string that merely mentions an HTML tag (e.g. an
        # error message fragment) must not fire -- the heuristic requires
        # both the size floor and a signal token, not either alone.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("MSG = 'invalid <script> tag in input'\n")
        assert "embedded_code" not in scan_file_capabilities(pkg)

    def test_embedded_code_declared_even_when_content_opaque_to_needles(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0244 fail-closed guarantee: a large embedded HTML region whose
        # content matches no specific typescript needle (plain markup, no
        # script) still declares `embedded_code` -- the region is never
        # silently passed just because the best-effort re-scan is empty.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        filler = "\n".join(f"<div>row {i}</div>" for i in range(20))
        pkg.write_text(
            f"PAGE_HTML = '''\n<html><body>\n{filler}\n</body></html>\n'''\n"
        )
        capabilities = scan_file_capabilities(pkg)
        assert "embedded_code" in capabilities

    def test_embedded_code_regions_scanned_via_operations(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        # T-0244: _scan_file_operations names the specific typescript
        # DANGEROUS_OPERATIONS entry that fired inside the embedded region,
        # not just the bare "eval" capability kind.
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "dashboard.py"
        padding = "x" * 80
        pkg.write_text(
            "DASHBOARD_HTML = '''\n"
            "<!doctype html>\n"
            "<script>\n"
            f"// {padding}\n"
            f"// {padding}\n"
            "function render(payload) { eval(payload); }\n"
            "</script>\n"
            "'''\n"
        )
        ops = _scan_file_operations(pkg)
        assert any(
            op.capability_kind == "eval" and op.language == "typescript" for op in ops
        )
