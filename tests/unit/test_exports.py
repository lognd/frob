"""Unit tests for frob.exports."""

from pathlib import Path

from frob.exports import (
    ExportsError,
    ExportsResult,
    ModuleExports,
    exports_consumers,
    exports_package,
)


class TestExportsPackage:
    def _make_pkg(self, tmp_path: Path, files: dict[str, str]) -> Path:
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        for name, src in files.items():
            (pkg / name).write_text(src)
        return pkg

    def test_basic_public_symbols(self, tmp_path):
        # frob:tests src/frob/exports/__init__.py::exports_package kind="unit"
        pkg = self._make_pkg(
            tmp_path,
            {
                "alpha.py": "def foo(): ...\ndef bar(): ...\n",
            },
        )
        result = exports_package(pkg)
        assert result.is_ok
        er = result.danger_ok
        assert len(er.modules) == 1
        assert "foo" in er.modules[0].symbols
        assert "bar" in er.modules[0].symbols

    def test_private_excluded_by_default(self, tmp_path):
        pkg = self._make_pkg(
            tmp_path,
            {
                "mod.py": "def public(): ...\ndef _private(): ...\n",
            },
        )
        result = exports_package(pkg)
        assert result.is_ok
        syms = result.danger_ok.modules[0].symbols
        assert "public" in syms
        assert "_private" not in syms

    def test_private_included_with_flag(self, tmp_path):
        pkg = self._make_pkg(
            tmp_path,
            {
                "mod.py": "def public(): ...\ndef _private(): ...\n",
            },
        )
        result = exports_package(pkg, include_private=True)
        assert result.is_ok
        syms = result.danger_ok.modules[0].symbols
        assert "_private" in syms

    def test_exclude_module(self, tmp_path):
        pkg = self._make_pkg(
            tmp_path,
            {
                "alpha.py": "def foo(): ...\n",
                "beta.py": "def bar(): ...\n",
            },
        )
        result = exports_package(pkg, exclude_modules=["beta"])
        assert result.is_ok
        mods = {m.module for m in result.danger_ok.modules}
        assert not any("beta" in m for m in mods)
        assert any("alpha" in m for m in mods)

    def test_not_a_directory(self, tmp_path):
        f = tmp_path / "single.py"
        f.write_text("def x(): ...\n")
        result = exports_package(f)
        assert result.is_err
        assert result.danger_err == ExportsError.NotADirectory

    def test_no_source_files(self, tmp_path):
        pkg = tmp_path / "empty"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        result = exports_package(pkg)
        assert result.is_err
        assert result.danger_err == ExportsError.NoSourceFiles

    def test_as_text_output(self, tmp_path):
        pkg = self._make_pkg(
            tmp_path,
            {
                "mod.py": "def Alpha(): ...\ndef Beta(): ...\n",
            },
        )
        result = exports_package(pkg)
        text = result.danger_ok.as_text()
        assert "from mypkg.mod import" in text
        assert "__all__" in text
        assert "Alpha" in text

    def test_as_text_skips_module_with_no_symbols(self):
        # frob:tests src/frob/exports/__init__.py::ExportsResult.as_text kind="unit"
        # `exports_package` never produces a zero-symbol `ModuleExports`
        # (`_module_exports` filters it to `None` first) -- but `as_text`
        # is public API over `ExportsResult`, which a caller can build
        # directly, so construct one by hand to exercise `as_text`'s "not
        # mod.symbols -- continue" branch: no `from empty import ...` line
        # should be emitted for it.
        result = ExportsResult(
            package_dir="mypkg",
            modules=[
                ModuleExports(module="mypkg.alpha", symbols=["foo"]),
                ModuleExports(module="mypkg.empty", symbols=[]),
            ],
        )
        text = result.as_text()
        assert "from mypkg.alpha import" in text
        assert "mypkg.empty" not in text

    def test_as_text_aliases_duplicate_symbol_names(self, tmp_path):
        # frob:tests src/frob/exports/__init__.py::ExportsResult.as_text kind="unit"
        # Two modules exporting the same symbol name exercise `as_text`'s
        # duplicate-aliasing branch (`mod_short_symbol` aliasing), not just
        # the no-duplicates path every other as_text test takes.
        pkg = self._make_pkg(
            tmp_path,
            {
                "alpha.py": "def widget(): ...\n",
                "beta.py": "def widget(): ...\n",
            },
        )
        result = exports_package(pkg)
        text = result.danger_ok.as_text()
        assert "widget as alpha_widget" in text
        assert "widget as beta_widget" in text
        assert '"alpha_widget"' in text
        assert '"beta_widget"' in text

    def test_classes_included(self, tmp_path):
        pkg = self._make_pkg(
            tmp_path,
            {
                "models.py": "class Foo:\n    pass\n\nclass Bar:\n    pass\n",
            },
        )
        result = exports_package(pkg)
        syms = result.danger_ok.modules[0].symbols
        assert "Foo" in syms
        assert "Bar" in syms


class TestExportsConsumers:
    """T-0858: exports_consumers folds the xref-sunset's surviving
    "who imports this symbol" question into the exports library surface."""

    def test_finds_import_consumer(self, tmp_path):
        # frob:tests src/frob/exports/__init__.py::exports_consumers kind="unit"
        (tmp_path / "producer.py").write_text("def widget(): ...\n")
        (tmp_path / "consumer.py").write_text(
            "from producer import widget\n\nwidget()\n"
        )
        result = exports_consumers("widget", tmp_path)
        assert result.is_ok
        files = {c.file for c in result.danger_ok.consumers}
        assert "consumer.py" in files

    def test_excludes_prose_mention(self, tmp_path):
        # frob:tests src/frob/exports/__init__.py::exports_consumers kind="unit"
        (tmp_path / "producer.py").write_text("def widget(): ...\n")
        (tmp_path / "notes.py").write_text(
            "# see widget for details, but this file does not import it\n"
        )
        result = exports_consumers("widget", tmp_path)
        assert result.is_ok
        files = {c.file for c in result.danger_ok.consumers}
        assert "notes.py" not in files

    def test_no_source_files(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        result = exports_consumers("widget", empty)
        assert result.is_err
        assert result.danger_err == ExportsError.NoSourceFiles

    def test_as_text_output(self, tmp_path):
        (tmp_path / "producer.py").write_text("def widget(): ...\n")
        (tmp_path / "consumer.py").write_text("from producer import widget\n")
        result = exports_consumers("widget", tmp_path)
        text = result.danger_ok.as_text()
        assert "widget" in text
        assert "consumer.py" in text

    def test_as_json_output(self, tmp_path):
        (tmp_path / "producer.py").write_text("def widget(): ...\n")
        (tmp_path / "consumer.py").write_text("from producer import widget\n")
        result = exports_consumers("widget", tmp_path)
        js = result.danger_ok.as_json()
        assert "widget" in js
        assert "consumer.py" in js


class TestFrobExportsPolicyResidue:
    """T-0871: real-repo proof that `frob-exports` reports zero missing
    public symbols for the 9 packages this ticket's scope covers -- every
    remaining missing symbol was resolved as a deliberate export
    (`__init__.py` import + `__all__` entry) or a demotion to private
    (leading underscore, referrers fixed), never a blanket waiver."""

    _PACKAGES = (
        "src/frob",
        "src/frob/arch",
        "src/frob/lang",
        "src/frob/mutate",
        "src/frob/perf",
        "src/frob/scaffold",
        "src/frob/serve",
        "src/frob/testing",
        "src/frob/vet",
    )

    def _missing(self, pkg_dir: Path) -> list[str]:
        """Every `module.symbol` in `pkg_dir` not textually referenced in
        its own `__init__.py` -- the same substring check `frob check`'s
        `frob-exports` tool uses (`frob.check._python._missing_exports`)."""
        result = exports_package(pkg_dir, include_private=False)
        assert result.is_ok, result.err
        er = result.danger_ok
        init_src = (pkg_dir / "__init__.py").read_text(encoding="utf-8")
        missing = []
        for mod in er.modules:
            for sym in mod.symbols:
                if sym not in init_src:
                    missing.append(f"{mod.module}.{sym}")
        return missing

    # frob:tests tests/unit/test_exports.py::TestFrobExportsPolicyResidue.test_all_nine_packages_report_zero_missing_symbols kind="unit"  # noqa: E501
    def test_all_nine_packages_report_zero_missing_symbols(self):
        repo_root = Path(__file__).resolve().parents[2]
        offenders: dict[str, list[str]] = {}
        for rel in self._PACKAGES:
            pkg_dir = repo_root / rel
            missing = self._missing(pkg_dir)
            if missing:
                offenders[rel] = missing
        assert offenders == {}, (
            f"frob-exports still reports missing symbols: {offenders}"
        )
