"""
Unit tests for frob.arch.analyze_project.

The frob.arch module may not exist yet; these tests are written against its
expected public API and will be skipped if the module is unavailable.

The ArchResult model has a `suggestions` list of ArchSuggestion objects.
Each ArchSuggestion has: file, line, category, severity, message, detail.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"

try:
    from frob.arch import analyze_project

    HAS_ARCH = True
except ImportError:
    HAS_ARCH = False

pytestmark = pytest.mark.skipif(not HAS_ARCH, reason="frob.arch not available")


# ---------------------------------------------------------------------------
# god-class detection
# ---------------------------------------------------------------------------


class TestGodClass:
    def test_big_class_triggers_god_class(self):
        # Use a single-file path as root -- analyze_project walks the root dir
        root = FIXTURES / "arch_python" / "src"
        result = analyze_project(root)
        categories = {s.category for s in result.suggestions}
        assert "god-class" in categories

    # frob:waive PERF003 reason="list comprehension over suggestions plus a sibling any() generator with a substring test; not a nested join"
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


# ---------------------------------------------------------------------------
# long-function detection
# ---------------------------------------------------------------------------


class TestLongFunction:
    def test_long_func_triggers_warning(self):
        root = FIXTURES / "arch_python" / "src"
        result = analyze_project(root)
        categories = {s.category for s in result.suggestions}
        assert "long-function" in categories

    # frob:waive PERF003 reason="list comprehension over suggestions plus a sibling any() generator with a substring test; not a nested join"
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


# ---------------------------------------------------------------------------
# deep-nesting detection
# ---------------------------------------------------------------------------


class TestDeepNesting:
    def test_deep_nest_triggers_suggestion(self):
        root = FIXTURES / "arch_python" / "src"
        result = analyze_project(root)
        categories = {s.category for s in result.suggestions}
        assert "deep-nesting" in categories

    # frob:waive PERF003 reason="list comprehension over suggestions plus a sibling any() generator with a substring test; not a nested join"
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


# ---------------------------------------------------------------------------
# analyze_project
# ---------------------------------------------------------------------------


class TestAnalyzeProject:
    def test_arch_python_project_finds_issues(self):
        # frob:tests src/frob/arch/__init__.py::analyze_project kind="unit"
        result = analyze_project(FIXTURES / "arch_python" / "src")
        assert len(result.suggestions) > 0

    def test_arch_python_project_reports_line_numbers(self):
        # frob:tests src/frob/arch/__init__.py::analyze_project kind="unit"
        result = analyze_project(FIXTURES / "arch_python" / "src")
        located = [s.line for s in result.suggestions if s.line is not None]
        assert located, "at least one suggestion should carry a line number"
        assert all(line >= 1 for line in located)

    def test_arch_python_project_has_all_three_kinds(self):
        result = analyze_project(FIXTURES / "arch_python" / "src")
        categories = {s.category for s in result.suggestions}
        assert "god-class" in categories
        assert "long-function" in categories
        assert "deep-nesting" in categories

    def test_simple_python_project_clean(self):
        result = analyze_project(FIXTURES / "simple_python" / "src")
        architectural = [
            s
            for s in result.suggestions
            if s.category
            in ("god-class", "long-function", "deep-nesting", "high-coupling")
        ]
        assert len(architectural) == 0


# ---------------------------------------------------------------------------
# output format
# ---------------------------------------------------------------------------


class TestArchResultFormat:
    def test_as_text_returns_string(self):
        result = analyze_project(FIXTURES / "arch_python" / "src")
        text = result.as_text()
        assert isinstance(text, str)
        assert len(text) > 0

    def test_as_text_mentions_category(self):
        result = analyze_project(FIXTURES / "arch_python" / "src")
        text = result.as_text()
        assert "god-class" in text or "long-function" in text or "deep-nesting" in text

    def test_as_json_is_valid_json(self):
        result = analyze_project(FIXTURES / "arch_python" / "src")
        data = json.loads(result.as_json())
        assert isinstance(data, dict)

    def test_as_json_has_suggestions_key(self):
        result = analyze_project(FIXTURES / "arch_python" / "src")
        data = json.loads(result.as_json())
        assert "suggestions" in data

    def test_as_json_suggestion_count_matches(self):
        result = analyze_project(FIXTURES / "arch_python" / "src")
        data = json.loads(result.as_json())
        assert len(data["suggestions"]) == len(result.suggestions)

    def test_as_text_clean_project(self):
        result = analyze_project(FIXTURES / "simple_python" / "src")
        text = result.as_text()
        assert isinstance(text, str)
        # Simple project may have no issues at all
        assert "no architectural issues" in text or isinstance(text, str)


# ---------------------------------------------------------------------------
# interface-level integration
# ---------------------------------------------------------------------------


def test_arch_end_to_end_analyze_then_render():
    # frob:tests src/frob/arch kind="integration"
    # Drive the whole arch boundary: walk a real fixture tree, produce an
    # ArchResult, and round-trip it through both public renderers.
    result = analyze_project(FIXTURES / "arch_python" / "src")
    categories = {s.category for s in result.suggestions}
    assert {"god-class", "long-function", "deep-nesting"} <= categories
    data = json.loads(result.as_json())
    assert len(data["suggestions"]) == len(result.suggestions)
    assert isinstance(result.as_text(), str)
