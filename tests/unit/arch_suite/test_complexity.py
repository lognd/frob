"""Split from tests/unit/test_arch.py (T-1201)."""

from __future__ import annotations

import pytest

from tests.unit.arch_suite.conftest import (
    _DEEP_NEST_SRC,
    FIXTURES,
    HAS_ARCH,
    _big_module_text,
    analyze_project,
)

pytestmark = pytest.mark.skipif(not HAS_ARCH, reason="frob.arch not available")



class TestGodClass:
    def test_big_class_triggers_god_class(self):
        # Use a single-file path as root -- analyze_project walks the root dir
        root = FIXTURES / "arch_python" / "src"
        result = analyze_project(root)
        categories = {s.category for s in result.suggestions}
        assert "god-class" in categories

    def test_big_class_names_the_class(self):
        root = FIXTURES / "arch_python" / "src"
        result = analyze_project(root)
        god_class_issues = [s for s in result.suggestions if s.category == "god-class"]
        assert any("BigService" in s.message for s in god_class_issues)

    def test_simple_python_no_god_class(self):
        root = FIXTURES / "simple_python" / "src"
        result = analyze_project(root)
        categories = {s.category for s in result.suggestions}
        assert "god-class" not in categories


class TestLongFunction:
    def test_long_func_triggers_warning(self):
        root = FIXTURES / "arch_python" / "src"
        result = analyze_project(root)
        categories = {s.category for s in result.suggestions}
        assert "long-function" in categories

    def test_long_func_names_the_function(self):
        root = FIXTURES / "arch_python" / "src"
        result = analyze_project(root)
        long_issues = [s for s in result.suggestions if s.category == "long-function"]
        assert any("configure_pipeline" in s.message for s in long_issues)

    def test_simple_python_no_long_function(self):
        root = FIXTURES / "simple_python" / "src"
        result = analyze_project(root)
        categories = {s.category for s in result.suggestions}
        assert "long-function" not in categories


class TestDeepNesting:
    def test_deep_nest_triggers_suggestion(self):
        root = FIXTURES / "arch_python" / "src"
        result = analyze_project(root)
        categories = {s.category for s in result.suggestions}
        assert "deep-nesting" in categories

    def test_deep_nest_names_the_function(self):
        root = FIXTURES / "arch_python" / "src"
        result = analyze_project(root)
        nest_issues = [s for s in result.suggestions if s.category == "deep-nesting"]
        assert any("process_matrix" in s.message for s in nest_issues)

    def test_simple_python_no_deep_nesting(self):
        root = FIXTURES / "simple_python" / "src"
        result = analyze_project(root)
        categories = {s.category for s in result.suggestions}
        assert "deep-nesting" not in categories


# frob:ticket T-1066
class TestDeepNestingArchExempt:
    # frob:ticket T-1066
    def _analyze(self, tmp_path, source: str):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "deep_nest.py").write_text(source)
        return analyze_project(src_dir)

    # frob:ticket T-1066
    # frob:tests \
    # tests/unit/arch_suite/test_complexity.py::TestDeepNestingArchExempt.test_reasoned\
    # _exempt_suppresses_finding
    def test_reasoned_exempt_suppresses_finding(self, tmp_path):
        source = _DEEP_NEST_SRC.replace(
            "def process_matrix",
            '# arch-exempt: deep-nesting reason="textbook nested loop, test fixture"\n'
            "def process_matrix",
        )
        result = self._analyze(tmp_path, source)
        categories = {s.category for s in result.suggestions}
        assert "deep-nesting" not in categories

    # frob:ticket T-1066
    # frob:tests \
    # tests/unit/arch_suite/test_complexity.py::TestDeepNestingArchExempt.test_unreason\
    # ed_exempt_still_fires
    def test_unreasoned_exempt_still_fires(self, tmp_path):
        # No reason= -- must not match, same discipline frob:waive enforces
        # via WAIVE001 for the generic channel.
        source = _DEEP_NEST_SRC.replace(
            "def process_matrix", "# arch-exempt: deep-nesting\ndef process_matrix"
        )
        result = self._analyze(tmp_path, source)
        categories = {s.category for s in result.suggestions}
        assert "deep-nesting" in categories

    # frob:ticket T-1066
    # frob:tests \
    # tests/unit/arch_suite/test_complexity.py::TestDeepNestingArchExempt.test_exempt_o\
    # n_unrelated_function_does_not_leak
    def test_exempt_on_unrelated_function_does_not_leak(self, tmp_path):
        # The directive sits above an earlier, unrelated function -- a
        # blank/non-comment line breaks the leading-comment-block scan, so
        # it must not exempt process_matrix below it.
        source = (
            '# arch-exempt: deep-nesting reason="unrelated"\n'
            "def unrelated():\n"
            '    """Not the deeply-nested function."""\n'
            "    return 1\n\n\n" + _DEEP_NEST_SRC
        )
        result = self._analyze(tmp_path, source)
        nest_issues = [s for s in result.suggestions if s.category == "deep-nesting"]
        assert any("process_matrix" in s.message for s in nest_issues)


class TestLargeFile:
    def test_large_test_file_not_flagged(self, tmp_path):
        # frob:tests src/frob/arch/__init__.py::analyze_project
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_big.py").write_text(_big_module_text(600))

        result = analyze_project(tests_dir)
        categories = {s.category for s in result.suggestions}
        assert "large-file" not in categories

    def test_large_src_file_still_flagged(self, tmp_path):
        # frob:tests src/frob/arch/__init__.py::analyze_project
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "big.py").write_text(_big_module_text(600))

        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "large-file" in categories

    def test_fixtures_json_not_flagged(self, tmp_path):
        # frob:tests src/frob/arch/__init__.py::_is_fixture_data_file
        fixtures_dir = tmp_path / "tests" / "fixtures"
        fixtures_dir.mkdir(parents=True)
        payload = "\n".join(f'  "k{i}": {i},' for i in range(600))
        (fixtures_dir / "corpus.json").write_text("{\n" + payload + "\n}\n")

        result = analyze_project(tmp_path)
        categories = {s.category for s in result.suggestions}
        assert "large-file" not in categories

    def test_large_json_data_not_flagged(self, tmp_path):
        # T-0372: a generated/data JSON file has no tree-sitter grammar --
        # it is not a "code module" arch's size heuristic is meant to judge.
        # frob:tests src/frob/arch/__init__.py::analyze_project
        payload = "\n".join(f'  "k{i}": {i},' for i in range(1000))
        (tmp_path / "big.json").write_text("{\n" + payload + "\n}\n")

        result = analyze_project(tmp_path)
        categories = {s.category for s in result.suggestions}
        assert "large-file" not in categories

    def test_large_md_ledger_not_flagged(self, tmp_path):
        # T-0372: a ticket-ledger-style markdown file (e.g. tickets-archive.md)
        # has no tree-sitter grammar and should not be judged as an
        # over-large code module.
        # frob:tests src/frob/arch/__init__.py::analyze_project
        (tmp_path / "big.md").write_text(
            "\n".join(f"## Entry {i}\n\nsome ledger text\n" for i in range(1000))
        )

        result = analyze_project(tmp_path)
        categories = {s.category for s in result.suggestions}
        assert "large-file" not in categories

    def test_large_py_src_still_flagged(self, tmp_path):
        # T-0372: real source (has a tree-sitter grammar) must never be
        # exempted by this data-file skip.
        # frob:tests src/frob/arch/__init__.py::analyze_project
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "huge.py").write_text(_big_module_text(1000))

        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "large-file" in categories

    # frob:ticket T-0373
    # frob:ticket T-1424
    # frob:tests src/frob/arch/__init__.py::analyze_project
    # frob:tests src/frob/repo_meta.py::load_arch_config
    def test_calibrated_frob_toml_threshold_suppresses_600_line_flag(self, tmp_path):
        """T-0373: a 600-line file is flagged at analyze_project's own
        500-line default but NOT once frob.toml's [arch] max_file_lines=800
        (via load_arch_config) is threaded through -- the calibration the
        gate now honors."""
        from frob.app.config import load_arch_config

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "big.py").write_text(_big_module_text(600))
        (tmp_path / "frob.toml").write_text("[arch]\nmax_file_lines = 800\n")

        default_result = analyze_project(src_dir)
        assert "large-file" in {s.category for s in default_result.suggestions}

        calibrated_result = analyze_project(src_dir, **load_arch_config(tmp_path))
        assert "large-file" not in {s.category for s in calibrated_result.suggestions}


class TestDeepNestingExemption:
    def test_deeply_nested_test_file_no_finding(self, tmp_path):
        # frob:tests src/frob/arch/__init__.py::analyze_project
        nest_src = (FIXTURES / "arch_python" / "src" / "deep_nest.py").read_text()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_deep_nest.py").write_text(nest_src)

        result = analyze_project(tests_dir)
        categories = {s.category for s in result.suggestions}
        assert "deep-nesting" not in categories

    def test_equivalent_src_file_still_flagged(self, tmp_path):
        # frob:tests src/frob/arch/__init__.py::analyze_project
        nest_src = (FIXTURES / "arch_python" / "src" / "deep_nest.py").read_text()
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "deep_nest.py").write_text(nest_src)

        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "deep-nesting" in categories
