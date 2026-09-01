"""Split from tests/unit/test_arch.py (T-1201)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.arch_suite.conftest import FIXTURES, HAS_ARCH, analyze_project

pytestmark = pytest.mark.skipif(not HAS_ARCH, reason="frob.arch not available")


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


class TestTestFileExemption:
    def test_test_file_no_long_function_or_god_class(self, tmp_path):
        # frob:tests src/frob/arch/__init__.py::analyze_project
        # Same long-AND-complex-function/big-class content the arch_python
        # fixture uses to trigger long-function/god-class, but placed under
        # a tests/ dir with a test_*.py name -- must not fire, since a
        # fixture-parametrized test body's shape is the nature of tests,
        # not production-architecture debt.
        long_func_src = (FIXTURES / "arch_python" / "src" / "long_func.py").read_text()
        big_class_src = (FIXTURES / "arch_python" / "src" / "big_class.py").read_text()
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_long_func.py").write_text(long_func_src)
        (tests_dir / "test_big_class.py").write_text(big_class_src)

        result = analyze_project(tests_dir)
        categories = {s.category for s in result.suggestions}
        assert "long-function" not in categories
        assert "god-class" not in categories
        assert "abstraction-opportunity" not in categories

    def test_equivalent_src_file_still_flagged(self, tmp_path):
        # frob:tests src/frob/arch/__init__.py::analyze_project
        # Control: the identical content, same tmp root, but under src/ with
        # a non-test name -- production-architecture debt still fires.
        long_func_src = (FIXTURES / "arch_python" / "src" / "long_func.py").read_text()
        big_class_src = (FIXTURES / "arch_python" / "src" / "big_class.py").read_text()
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "long_func.py").write_text(long_func_src)
        (src_dir / "big_class.py").write_text(big_class_src)

        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "long-function" in categories
        assert "god-class" in categories


class TestCollectDispatchRefs:
    """Direct unit coverage of `_collect_dispatch_refs`'s three dispatch-
    like shapes (T-0394: the call-callee, call-argument, and keyword-
    argument branches, extracted to `_collect_dispatch_refs_from_call`)."""

    def _refs(self, tmp_path: Path, source: str) -> set[str]:
        from frob.arch._abstraction import _collect_dispatch_refs
        from frob.lang import raw_tree

        path = tmp_path / "mod.py"
        path.write_text(source)
        parsed = raw_tree(path)
        assert parsed.is_ok
        tree, _source, _language = parsed.danger_ok
        out: set[str] = set()
        _collect_dispatch_refs(tree.root_node, out)
        return out

    def test_call_callee_identifier_counted(self, tmp_path: Path) -> None:
        # frob:tests src/frob/arch/_abstraction.py::_collect_dispatch_refs_from_call
        assert self._refs(tmp_path, "handler()\n") == {"handler"}

    def test_call_positional_argument_identifier_counted(self, tmp_path: Path) -> None:
        # frob:tests src/frob/arch/_abstraction.py::_collect_dispatch_refs_from_call
        assert "handler" in self._refs(tmp_path, "register(handler)\n")

    def test_call_keyword_argument_identifier_counted(self, tmp_path: Path) -> None:
        # frob:tests src/frob/arch/_abstraction.py::_collect_dispatch_refs_from_call
        assert "handler" in self._refs(tmp_path, "dispatch(cmd, target=handler)\n")

    def test_call_keyword_argument_non_identifier_not_counted(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/arch/_abstraction.py::_collect_dispatch_refs_from_call
        refs = self._refs(tmp_path, 'dispatch(cmd, target="literal")\n')
        assert refs == {"dispatch", "cmd"}

    def test_call_string_argument_not_counted(self, tmp_path: Path) -> None:
        # frob:tests src/frob/arch/_abstraction.py::_collect_dispatch_refs_from_call
        assert self._refs(tmp_path, 'register("not_a_name")\n') == {"register"}


class TestDispatchFamilySuppression:
    def test_dispatch_family_no_abstraction_opportunity(self, tmp_path):
        # frob:tests src/frob/arch/_abstraction.py::_is_dispatch_family
        # Three same-signature handlers all registered in one command table
        # in the SAME file -- an intentional dispatch family, not a missing
        # abstraction: the shared signature IS the contract that lets the
        # table call them uniformly.
        #
        # T-0370 reviewer-caught regression: this fixture's second
        # parameter is deliberately typed `RunnerConfig` (a domain type,
        # NOT one of `_GENERIC_TYPE_NAMES`), and the handler bodies are
        # substantial (>=8 normalized tokens) but mutually DISSIMILAR
        # (well below the 0.9 near-duplicate ratio -- each does genuinely
        # different work). That means `_signature_is_specific` alone would
        # flag this group -- `_is_dispatch_family` is the ONLY thing
        # suppressing it, so the test genuinely regresses if dispatch-
        # family suppression breaks (verified by hand: forcing
        # `_is_dispatch_family` to return `False` makes this test fail).
        # A `dict`-typed 2nd param (the original fixture) is GENERIC, so
        # the group was ALSO gated by body-similarity -- with `pass`-only
        # bodies that gate was never cleared either way, and the test
        # stayed green even with `_is_dispatch_family` broken.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "runner.py").write_text(
            "from __future__ import annotations\n"
            "from pathlib import Path\n"
            "\n"
            "class RunnerConfig:\n"
            "    pass\n"
            "\n"
            "def _run_scan(root: Path, cfg: RunnerConfig) -> None:\n"
            "    found = []\n"
            "    for entry in root.iterdir():\n"
            "        if entry.suffix == cfg.ext:\n"
            "            found.append(entry)\n"
            "    cfg.scanned = found\n"
            "\n"
            "def _run_stamp(root: Path, cfg: RunnerConfig) -> None:\n"
            "    marker = root / cfg.stamp_name\n"
            "    marker.write_text(str(cfg.version))\n"
            "    cfg.stamped_at = marker\n"
            "\n"
            "def _run_sweep(root: Path, cfg: RunnerConfig) -> None:\n"
            "    removed = 0\n"
            "    for child in root.glob(cfg.pattern):\n"
            "        child.unlink()\n"
            "        removed += 1\n"
            "    cfg.removed = removed\n"
            "\n"
            "_COMMANDS = {\n"
            '    "scan": _run_scan,\n'
            '    "stamp": _run_stamp,\n'
            '    "sweep": _run_sweep,\n'
            "}\n"
        )

        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" not in categories

    def test_accidental_same_signature_still_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_abstraction.py::_is_dispatch_family
        # frob:tests src/frob/arch/_abstraction.py::_near_duplicate_cluster
        # Three same-(generic)-signature functions with NO common
        # caller/registry anywhere AND structurally near-duplicate bodies
        # (validate-then-transform, differing only in which str method is
        # called) -- accidental parallel structure with real duplicated
        # logic behind it (T-0370: a generic `(str) -> str` signature alone
        # is no longer enough, so the bodies must actually carry the
        # near-duplicate signal this test means to exercise).
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def normalize_alpha(text: str) -> str:\n"
            "    cleaned = text.strip()\n"
            "    if not cleaned:\n"
            '        raise ValueError("empty")\n'
            "    return cleaned\n"
        )
        (src_dir / "b.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def normalize_beta(text: str) -> str:\n"
            "    cleaned = text.lower()\n"
            "    if not cleaned:\n"
            '        raise ValueError("empty")\n'
            "    return cleaned\n"
        )
        (src_dir / "c.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def normalize_gamma(text: str) -> str:\n"
            "    cleaned = text.title()\n"
            "    if not cleaned:\n"
            '        raise ValueError("empty")\n'
            "    return cleaned\n"
        )

        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories
        msg = next(
            s.message
            for s in result.suggestions
            if s.category == "abstraction-opportunity"
        )
        assert "normalize_alpha" in msg
        assert "normalize_beta" in msg
        assert "normalize_gamma" in msg

    def test_init_reexport_does_not_suppress(self, tmp_path):
        # frob:tests src/frob/arch/__init__.py::_is_init_file
        # Reviewer-demonstrated false-suppression path: three near-
        # duplicate-bodied (T-0370: generic `(str) -> str` alone is no
        # longer enough) same-signature functions each imported and listed
        # in an __init__.py's __all__ -- a plain re-export, not a dispatch
        # site. Must still flag: an ordinary re-export list is not a common
        # caller/registry.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def normalize_alpha(text: str) -> str:\n"
            "    cleaned = text.strip()\n"
            "    if not cleaned:\n"
            '        raise ValueError("empty")\n'
            "    return cleaned\n"
        )
        (src_dir / "b.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def normalize_beta(text: str) -> str:\n"
            "    cleaned = text.lower()\n"
            "    if not cleaned:\n"
            '        raise ValueError("empty")\n'
            "    return cleaned\n"
        )
        (src_dir / "c.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def normalize_gamma(text: str) -> str:\n"
            "    cleaned = text.title()\n"
            "    if not cleaned:\n"
            '        raise ValueError("empty")\n'
            "    return cleaned\n"
        )
        (src_dir / "__init__.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "from .a import normalize_alpha\n"
            "from .b import normalize_beta\n"
            "from .c import normalize_gamma\n"
            "\n"
            '__all__ = ["normalize_alpha", "normalize_beta", "normalize_gamma"]\n'
        )

        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories
        msg = next(
            s.message
            for s in result.suggestions
            if s.category == "abstraction-opportunity"
        )
        assert "normalize_alpha" in msg
        assert "normalize_beta" in msg
        assert "normalize_gamma" in msg

    def test_test_file_co_mention_does_not_suppress(self, tmp_path):
        # frob:tests src/frob/arch/_abstraction.py::_is_dispatch_family
        # Reviewer-demonstrated false-suppression path: a test file that
        # imports and CALLS all three near-duplicate-bodied (T-0370)
        # same-signature functions (each name appears as a real call). A
        # test asserting against three such helpers is not a dispatch site
        # either -- test files are excluded from the corpus entirely.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def normalize_alpha(text: str) -> str:\n"
            "    cleaned = text.strip()\n"
            "    if not cleaned:\n"
            '        raise ValueError("empty")\n'
            "    return cleaned\n"
        )
        (src_dir / "b.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def normalize_beta(text: str) -> str:\n"
            "    cleaned = text.lower()\n"
            "    if not cleaned:\n"
            '        raise ValueError("empty")\n'
            "    return cleaned\n"
        )
        (src_dir / "c.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def normalize_gamma(text: str) -> str:\n"
            "    cleaned = text.title()\n"
            "    if not cleaned:\n"
            '        raise ValueError("empty")\n'
            "    return cleaned\n"
        )
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_normalize.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "from src.a import normalize_alpha\n"
            "from src.b import normalize_beta\n"
            "from src.c import normalize_gamma\n"
            "\n"
            "def test_all_three():\n"
            '    assert normalize_alpha("x") == "x"\n'
            '    assert normalize_beta("X") == "x"\n'
            '    assert normalize_gamma("x") == "X"\n'
        )

        result = analyze_project(tmp_path)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories
        msg = next(
            s.message
            for s in result.suggestions
            if s.category == "abstraction-opportunity"
        )
        assert "normalize_alpha" in msg
        assert "normalize_beta" in msg
        assert "normalize_gamma" in msg
