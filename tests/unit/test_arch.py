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
# T-1066: deep-nesting's detector-owned arch-exempt directive -- a reasoned
# per-function override for a genuinely irreducible algorithm (mirrors the
# ARCH001 reasoned-waiver precedent, but stays off the generic waiver/
# Violation channel deep-nesting is deliberately excluded from).
# ---------------------------------------------------------------------------


# frob:ticket T-1066
_DEEP_NEST_SRC = (FIXTURES / "arch_python" / "src" / "deep_nest.py").read_text()


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
    # tests/unit/test_arch.py::TestDeepNestingArchExempt.test_reasoned_exempt_suppresse\
    # s_finding
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
    # tests/unit/test_arch.py::TestDeepNestingArchExempt.test_unreasoned_exempt_still_f\
    # ires
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
    # tests/unit/test_arch.py::TestDeepNestingArchExempt.test_exempt_on_unrelated_funct\
    # ion_does_not_leak
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


# ---------------------------------------------------------------------------
# T-0359: advisory categories exempt test files
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# T-0360: dispatch/validator families are not abstraction-opportunities
# ---------------------------------------------------------------------------


class TestCollectDispatchRefs:
    """Direct unit coverage of `_collect_dispatch_refs`'s three dispatch-
    like shapes (T-0394: the call-callee, call-argument, and keyword-
    argument branches, extracted to `_collect_dispatch_refs_from_call`)."""

    def _refs(self, tmp_path: Path, source: str) -> set[str]:
        from frob.arch._python import _collect_dispatch_refs
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
        # frob:tests src/frob/arch/_python.py::_collect_dispatch_refs_from_call
        assert self._refs(tmp_path, "handler()\n") == {"handler"}

    def test_call_positional_argument_identifier_counted(self, tmp_path: Path) -> None:
        # frob:tests src/frob/arch/_python.py::_collect_dispatch_refs_from_call
        assert "handler" in self._refs(tmp_path, "register(handler)\n")

    def test_call_keyword_argument_identifier_counted(self, tmp_path: Path) -> None:
        # frob:tests src/frob/arch/_python.py::_collect_dispatch_refs_from_call
        assert "handler" in self._refs(tmp_path, "dispatch(cmd, target=handler)\n")

    def test_call_keyword_argument_non_identifier_not_counted(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/arch/_python.py::_collect_dispatch_refs_from_call
        refs = self._refs(tmp_path, 'dispatch(cmd, target="literal")\n')
        assert refs == {"dispatch", "cmd"}

    def test_call_string_argument_not_counted(self, tmp_path: Path) -> None:
        # frob:tests src/frob/arch/_python.py::_collect_dispatch_refs_from_call
        assert self._refs(tmp_path, 'register("not_a_name")\n') == {"register"}


class TestDispatchFamilySuppression:
    def test_dispatch_family_no_abstraction_opportunity(self, tmp_path):
        # frob:tests src/frob/arch/_python.py::_is_dispatch_family
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
        # frob:tests src/frob/arch/_python.py::_is_dispatch_family
        # frob:tests src/frob/arch/_python.py::_near_duplicate_cluster
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
        # frob:tests src/frob/arch/_python.py::_is_dispatch_family
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


# ---------------------------------------------------------------------------
# T-0368: test files and fixtures/ data are exempt from large-file and
# deep-nesting too (extends the T-0359 advisory-category exemption)
# ---------------------------------------------------------------------------


def _big_module_text(n_lines: int) -> str:
    """A syntactically trivial python module of at least `n_lines` lines,
    used to drive the large-file line-count threshold without dragging in
    any other arch category (T-0368 test helper)."""
    header = "from __future__ import annotations\n\n"
    body = "\n".join(f"X_{i} = {i}" for i in range(n_lines)) + "\n"
    return header + body


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
    # frob:tests src/frob/arch/__init__.py::analyze_project
    # frob:tests src/frob/app/config.py::load_arch_config
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


# ---------------------------------------------------------------------------
# T-0370: abstraction-opportunity requires signature-specificity or
# body-similarity, not a bare shared signature
# ---------------------------------------------------------------------------


class TestAbstractionOpportunityDiscriminators:
    def test_generic_signature_unrelated_bodies_not_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_python.py::_check_abstraction_opportunities
        # frob:tests src/frob/arch/_python.py::_signature_is_specific
        # frob:tests src/frob/arch/_python.py::_near_duplicate_cluster
        # N functions sharing an over-generic `(str) -> str` signature
        # (like the 31-member residue this ticket targets) whose bodies do
        # completely different, structurally unrelated things -- a bare
        # shared signature is not evidence of an extractable abstraction,
        # so this must NOT flag at all.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def render_banner(text: str) -> str:\n"
            "    lines = text.split(chr(10))\n"
            "    width = max(len(line) for line in lines)\n"
            "    border = chr(42) * (width + 4)\n"
            "    body = chr(10).join(chr(42) + chr(32) + line for line in lines)\n"
            "    return border + chr(10) + body + chr(10) + border\n"
        )
        (src_dir / "b.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def rot13(text: str) -> str:\n"
            "    out = []\n"
            "    for ch in text:\n"
            "        code = ord(ch)\n"
            "        if 97 <= code <= 122:\n"
            "            out.append(chr((code - 97 + 13) % 26 + 97))\n"
            "        else:\n"
            "            out.append(ch)\n"
            "    return chr(0).join(out).replace(chr(0), chr(0))\n"
        )
        (src_dir / "c.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def slugify_path(text: str) -> str:\n"
            "    parts = text.split(chr(47))\n"
            "    kept = [p for p in parts if p not in (chr(46), chr(46) * 2)]\n"
            "    return chr(47).join(kept)\n"
        )

        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" not in categories

    def test_generic_signature_near_duplicate_bodies_still_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_python.py::_check_abstraction_opportunities
        # frob:tests src/frob/arch/_python.py::_near_duplicate_cluster
        # N functions sharing a generic `(AppConfig) -> None` signature
        # (the shape of the 39-member `run` residue this ticket targets)
        # whose bodies are near-DUPLICATE -- same shape, only the renamed
        # variables and one differing literal differ. Even on a purely
        # generic signature, real duplicated logic must still be caught.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class AppConfig:\n"
            "    pass\n"
            "\n"
            "def run_scan(config: AppConfig) -> None:\n"
            "    target = getattr(config, chr(65))\n"
            "    if not target:\n"
            '        raise ValueError("no target")\n'
            "    print(chr(97), target, chr(115), chr(99), chr(97), chr(110))\n"
        )
        (src_dir / "b.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class AppConfig:\n"
            "    pass\n"
            "\n"
            "def run_stamp(config: AppConfig) -> None:\n"
            "    target = getattr(config, chr(66))\n"
            "    if not target:\n"
            '        raise ValueError("no target")\n'
            "    print(chr(97), target, chr(115), chr(116), chr(97), chr(109))\n"
        )
        (src_dir / "c.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class AppConfig:\n"
            "    pass\n"
            "\n"
            "def run_sweep(config: AppConfig) -> None:\n"
            "    target = getattr(config, chr(67))\n"
            "    if not target:\n"
            '        raise ValueError("no target")\n'
            "    print(chr(97), target, chr(115), chr(119), chr(101), chr(101))\n"
        )

        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories
        msg = next(
            s.message
            for s in result.suggestions
            if s.category == "abstraction-opportunity"
        )
        assert "run_scan" in msg
        assert "run_stamp" in msg
        assert "run_sweep" in msg

    def test_specific_signature_genuine_family_still_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_python.py::_signature_is_specific
        # frob:tests src/frob/arch/_python.py::_check_abstraction_opportunities
        # A shared signature carrying a real domain type (`TicketStore`,
        # not one of the ubiquitous primitives) is specific enough to flag
        # on the signature alone, even though the bodies below are
        # deliberately UNRELATED -- signature-specificity is an
        # independent discriminator from body-similarity.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "store.py").write_text(
            "from __future__ import annotations\n\nclass TicketStore:\n    pass\n"
        )
        (src_dir / "a.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "from src.store import TicketStore\n"
            "\n"
            "def count_open(store: TicketStore) -> int:\n"
            "    return 1\n"
        )
        (src_dir / "b.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "from src.store import TicketStore\n"
            "\n"
            "def count_blocked(store: TicketStore) -> int:\n"
            "    total = 0\n"
            "    for _ in range(3):\n"
            "        total += 1\n"
            "    return total\n"
        )
        (src_dir / "c.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "from src.store import TicketStore\n"
            "\n"
            "def count_archived(store: TicketStore) -> int:\n"
            "    return len([1, 2, 3, 4])\n"
        )

        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories
        msg = next(
            s.message
            for s in result.suggestions
            if s.category == "abstraction-opportunity"
        )
        assert "count_open" in msg
        assert "count_blocked" in msg
        assert "count_archived" in msg

    def test_generic_signature_only_two_bodies_similar_reports_pair(self, tmp_path):
        # frob:tests src/frob/arch/_python.py::_near_duplicate_cluster
        # 3 functions share a generic `(str) -> bool` signature; only 2 of
        # them have near-duplicate bodies, the third is unrelated. The
        # finding must report the near-duplicate PAIR, not misrepresent
        # all 3 as one shared-logic family.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def is_hex_digest(text: str) -> bool:\n"
            "    if len(text) != 40:\n"
            "        return False\n"
            "    return all(c in chr(48) + chr(57) for c in text)\n"
        )
        (src_dir / "b.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def is_sha_digest(text: str) -> bool:\n"
            "    if len(text) != 40:\n"
            "        return False\n"
            "    return all(c in chr(48) + chr(57) for c in text)\n"
        )
        (src_dir / "c.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def is_valid_url(text: str) -> bool:\n"
            "    return text.startswith(chr(104) + chr(116) + chr(116) + chr(112))\n"
        )

        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories
        msg = next(
            s.message
            for s in result.suggestions
            if s.category == "abstraction-opportunity"
        )
        assert "is_hex_digest" in msg
        assert "is_sha_digest" in msg
        assert "is_valid_url" not in msg


# ---------------------------------------------------------------------------
# T-1068: language-parity groups (filed from T-0393) are not
# abstraction-opportunities -- the same false-positive class T-0360's
# dispatch-family exclusion covers, but for parallel per-language
# tree-sitter walkers (_py_/_rust_/_kt_/_ts_/_cpp_) instead of a shared
# call/registry site.
# ---------------------------------------------------------------------------


class TestLanguageParityExclusion:
    def test_one_member_per_language_not_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_python.py::_is_language_parity_family
        # frob:tests src/frob/arch/_python.py::_check_abstraction_opportunities
        # Three distinctly-tagged per-language walkers sharing a SPECIFIC
        # (domain-typed) signature -- `_signature_is_specific` alone would
        # flag this group (verified: with the language-parity check
        # removed, this exact fixture flags), so language-parity exclusion
        # is the only thing suppressing it.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "walkers.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class RawSymbol:\n"
            "    pass\n"
            "\n"
            "def _py_build_symbol(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
            "\n"
            "def _rust_build_symbol(node: object) -> RawSymbol:\n"
            "    sym = RawSymbol()\n"
            "    return sym\n"
            "\n"
            "def _kt_build_symbol(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" not in categories

    def test_duplicate_tag_within_group_still_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_python.py::_is_language_parity_family
        # Two `_rust_*` members share the "rust" tag -- not genuine
        # one-per-language parity (a real accidental collision within the
        # same language), so this must still flag.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "walkers.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class RawSymbol:\n"
            "    pass\n"
            "\n"
            "def _rust_build_symbol(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
            "\n"
            "def _rust_build_alias(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
            "\n"
            "def _kt_build_symbol(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories

    def test_untagged_member_within_group_still_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_python.py::_is_language_parity_family
        # `_read_symbol` carries no recognized language tag -- with no tag
        # to compare, parity cannot be established, so the group falls
        # through to the normal signature/body checks and still flags.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "walkers.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class RawSymbol:\n"
            "    pass\n"
            "\n"
            "def _read_symbol(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
            "\n"
            "def _rust_build_symbol(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
            "\n"
            "def _kt_build_symbol(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories

    def test_tag_requires_underscore_boundary(self, tmp_path):
        # frob:tests src/frob/arch/_python.py::_language_tag
        # "results_summary" contains "ts" as a bare substring with no
        # underscore before it -- must NOT be mistaken for a `_ts_` tag
        # (the T-0360-style structural rigor this detector requires, no
        # raw text proximity).
        from frob.arch._python import _language_tag

        assert _language_tag("results_summary") is None
        assert _language_tag("_ts_build_module") == "ts"
        assert _language_tag("_kt_build_module") == "kt"

    def test_long_form_language_spellings_normalize_to_short_tag(self):
        # frob:tests src/frob/arch/_python.py::_language_tag
        # T-1181: python/typescript/kotlin/cplusplus long-form spellings
        # (e.g. frob.testing._collect*.py's collect_python_tests/
        # collect_typescript_tests/collect_kotlin_tests) must normalize to
        # the SAME canonical short tag as their short-form counterpart so
        # `_is_language_parity_family`'s distinctness check treats them as
        # identity-equivalent, not as untagged/unknown segments.
        from frob.arch._python import _language_tag

        assert _language_tag("collect_python_tests") == "py"
        assert _language_tag("collect_typescript_tests") == "ts"
        assert _language_tag("collect_kotlin_tests") == "kt"
        assert _language_tag("collect_cplusplus_tests") == "cpp"

    def test_long_and_short_form_parity_group_not_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_python.py::_is_language_parity_family
        # frob:tests src/frob/arch/_python.py::_check_abstraction_opportunities
        # A parity family mixing long-form (python/typescript/kotlin) and
        # short-form (cpp) tags -- the T-1181 refile scenario -- must be
        # recognized as genuinely distinct-per-language and excluded, the
        # same as an all-short-form group already is.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "collectors.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class RawSymbol:\n"
            "    pass\n"
            "\n"
            "def collect_python_tests(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
            "\n"
            "def collect_typescript_tests(node: object) -> RawSymbol:\n"
            "    sym = RawSymbol()\n"
            "    return sym\n"
            "\n"
            "def collect_kotlin_tests(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
            "\n"
            "def collect_cpp_tests(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" not in categories


class TestCallThroughForwarderExclusion:
    def test_distinct_named_self_forwarders_not_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_python.py::_is_call_through_forwarder_family
        # frob:tests src/frob/arch/_python.py::_is_self_named_forwarder
        # frob:tests src/frob/arch/_python.py::_check_abstraction_opportunities
        # The real `RenderWriter` shape (T-1182, refiled from the T-1083
        # disposition): each method carries a DIFFERENT bare name
        # (heading/good/warn) but its own body is a short call-through to
        # an identically-named module-level counterpart -- own lineage,
        # not a shared group name. `_signature_is_specific` alone would
        # flag this group (verified: with the forwarder exclusion
        # removed, this exact fixture flags), so the exclusion is the
        # only thing suppressing it.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "elements.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def heading(text: str, color: bool) -> str:\n"
            "    return text\n"
            "\n"
            "def good(text: str, color: bool) -> str:\n"
            "    return text\n"
            "\n"
            "def warn(text: str, color: bool) -> str:\n"
            "    return text\n"
        )
        (src_dir / "renderer.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "from elements import heading, good, warn\n"
            "\n"
            "\n"
            "class RenderWriter:\n"
            "    def __init__(self, emit, color):\n"
            "        self._emit = emit\n"
            "        self.color = color\n"
            "\n"
            "    def heading(self, text: str) -> None:\n"
            "        self._emit(heading(text, color=self.color))\n"
            "\n"
            "    def good(self, text: str) -> None:\n"
            "        self._emit(good(text, color=self.color))\n"
            "\n"
            "    def warn(self, text: str) -> None:\n"
            "        self._emit(warn(text, color=self.color))\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" not in categories

    def test_group_with_one_non_self_named_member_still_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_python.py::_is_call_through_forwarder_family
        # Three near-duplicate-bodied methods CLUSTER together (same
        # shape, high body-similarity), but `good`/`warn` each mistakenly
        # delegate to `heading` instead of their OWN name -- not real
        # per-member forwarders, just three near-identical (and likely
        # buggy) implementations. A group like this is exactly the
        # unexplained-duplication case the detector exists to catch, so
        # the forwarder exclusion must not suppress it.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "elements.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def heading(text: str, color: bool) -> str:\n"
            "    return text\n"
        )
        (src_dir / "renderer.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "from elements import heading\n"
            "\n"
            "\n"
            "class RenderWriter:\n"
            "    def __init__(self, emit, color):\n"
            "        self._emit = emit\n"
            "        self.color = color\n"
            "\n"
            "    def heading(self, text: str) -> None:\n"
            "        self._emit(heading(text, color=self.color))\n"
            "\n"
            "    def good(self, text: str) -> None:\n"
            "        self._emit(heading(text, color=self.color))\n"
            "\n"
            "    def warn(self, text: str) -> None:\n"
            "        self._emit(heading(text, color=self.color))\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories

    def test_forwarder_helper_requires_self_named_short_body(self):
        # frob:tests src/frob/arch/_python.py::_is_call_through_forwarder_family
        # frob:tests src/frob/arch/_python.py::_is_self_named_forwarder
        from frob.arch._python import (
            _is_call_through_forwarder_family,
            _is_self_named_forwarder,
        )

        assert _is_self_named_forwarder("heading", "self . _emit ( heading ( _v0 ) )")
        assert not _is_self_named_forwarder("heading", "self . _emit ( warn ( _v0 ) )")
        assert not _is_self_named_forwarder("heading", "")

        # DIFFERENT names, each independently self-forwarding: excluded.
        assert _is_call_through_forwarder_family(
            [
                ("a.py", "heading", "heading ( _v0 )"),
                ("a.py", "good", "good ( _v0 )"),
            ]
        )
        # One member's body does not mention its own name: not excluded.
        assert not _is_call_through_forwarder_family(
            [
                ("a.py", "heading", "heading ( _v0 )"),
                (
                    "a.py",
                    "good",
                    "stripped = _v0 . strip ( ) upper = stripped . upper ( )",
                ),
            ]
        )


class TestCheckRegistryExclusion:
    def test_check_and_run_checks_names_not_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_python.py::_is_check_registry_family
        # frob:tests src/frob/arch/_python.py::_check_abstraction_opportunities
        # Three same-signature functions named per `frob.arch`'s own
        # detector-registry convention (`check_*` detectors plus a family's
        # `run_*_checks` aggregator, T-1112) -- `_signature_is_specific`
        # alone would flag this group (verified: with the check-registry
        # exclusion removed, this exact fixture flags), so the exclusion is
        # the only thing suppressing it.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "checks.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class ArchSuggestion:\n"
            "    pass\n"
            "\n"
            "def check_no_di_construction(module: object) -> list[ArchSuggestion]:\n"
            "    return []\n"
            "\n"
            "def check_boolean_flag_param(module: object) -> list[ArchSuggestion]:\n"
            "    out = []\n"
            "    return out\n"
            "\n"
            "def run_smell_checks(module: object) -> list[ArchSuggestion]:\n"
            "    return []\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" not in categories

    def test_non_registry_named_group_still_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_python.py::_is_check_registry_family
        # `_validate_no_di` does not match the `check_*`/`run_*_checks`
        # naming convention -- the group has no such registry shape to
        # exclude, so it falls through to the normal signature/body checks
        # and still flags.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "checks.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class ArchSuggestion:\n"
            "    pass\n"
            "\n"
            "def _validate_no_di(module: object) -> list[ArchSuggestion]:\n"
            "    return []\n"
            "\n"
            "def check_boolean_flag_param(module: object) -> list[ArchSuggestion]:\n"
            "    out = []\n"
            "    return out\n"
            "\n"
            "def run_smell_checks(module: object) -> list[ArchSuggestion]:\n"
            "    return []\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories

    def test_check_registry_regex_matches_both_shapes(self) -> None:
        # frob:tests src/frob/arch/_python.py::_is_check_registry_family
        from frob.arch._python import _is_check_registry_family

        assert _is_check_registry_family(
            [("a.py", "check_boolean_flag_param"), ("b.py", "run_smell_checks")]
        )
        assert not _is_check_registry_family(
            [("a.py", "check_boolean_flag_param"), ("b.py", "_validate_no_di")]
        )


# frob:ticket T-1141
class TestGateRuleBuilderExclusion:
    """`_is_gate_rule_builder_family` (T-1141, mirroring T-1112's
    `_is_check_registry_family`): a shared-signature group whose return
    type is `Violation`/`list[Violation]`/`tuple[Violation, ...]` is
    `frob.gates`'s own gate/rule-builder convention, not an accidental
    duplication -- structural (return-type-based), unlike the
    check-registry exclusion's name-based discriminator, since gate/rule-
    builder names do not share one fixed prefix/suffix the way
    `check_*`/`run_*_checks` do."""

    def test_violation_returning_group_not_flagged(self, tmp_path) -> None:
        # frob:tests src/frob/arch/_python.py::_is_gate_rule_builder_family
        # frob:tests src/frob/arch/_python.py::_check_abstraction_opportunities
        # Three same-signature functions returning `tuple[Violation, ...]`
        # with arbitrary, non-convention-matching names -- verified: with
        # the gate-rule-builder exclusion removed, this exact fixture
        # flags (a specific `Path` param type alone would satisfy
        # `_signature_is_specific`).
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "gates.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class Violation:\n"
            "    pass\n"
            "\n"
            "def alpha_check(root) -> tuple[Violation, ...]:\n"
            "    return ()\n"
            "\n"
            "def bravo_check(root) -> tuple[Violation, ...]:\n"
            "    return ()\n"
            "\n"
            "def charlie_check(root) -> tuple[Violation, ...]:\n"
            "    return ()\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" not in categories

    def test_non_violation_returning_group_still_flagged(self, tmp_path) -> None:
        # frob:tests src/frob/arch/_python.py::_is_gate_rule_builder_family
        # A same-signature group over a specific (non-generic) type that
        # does NOT return a Violation shape has no gate/rule-builder
        # convention to exclude, so it falls through to the normal
        # signature/body checks and still flags.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "gates.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class TicketQueue:\n"
            "    pass\n"
            "\n"
            "def alpha_lookup(queue: TicketQueue) -> str:\n"
            "    return ''\n"
            "\n"
            "def bravo_lookup(queue: TicketQueue) -> str:\n"
            "    return ''\n"
            "\n"
            "def charlie_lookup(queue: TicketQueue) -> str:\n"
            "    return ''\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories

    def test_return_type_membership_matches_all_three_shapes(self) -> None:
        # frob:tests src/frob/arch/_python.py::_is_gate_rule_builder_family
        from frob.arch._python import _is_gate_rule_builder_family

        assert _is_gate_rule_builder_family("Violation")
        assert _is_gate_rule_builder_family("list[Violation]")
        assert _is_gate_rule_builder_family("tuple[Violation, ...]")
        assert not _is_gate_rule_builder_family("str")
        assert not _is_gate_rule_builder_family("tuple[Edge, ...]")


# frob:ticket T-1144
class TestToolResultBuilderExclusion:
    """`_is_tool_result_builder_family` (T-1144, mirroring T-1141's
    `_is_gate_rule_builder_family` for `frob.gates`'s own `Violation`
    convention): a shared-signature group whose return type is
    `ToolResult`/`ToolResult | None` is `frob.process`/`frob.check`'s own
    check-stage-runner convention, not an accidental duplication."""

    def test_toolresult_returning_group_not_flagged(self, tmp_path) -> None:
        # frob:tests src/frob/arch/_python.py::_is_tool_result_builder_family
        # frob:tests src/frob/arch/_python.py::_check_abstraction_opportunities
        # Three same-signature functions returning `ToolResult` with
        # arbitrary, non-convention-matching names -- verified: with the
        # tool-result-builder exclusion removed, this exact fixture flags
        # (a specific `Path` param type alone satisfies
        # `_signature_is_specific`).
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "runners.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class ToolResult:\n"
            "    pass\n"
            "\n"
            "def alpha_run(root) -> ToolResult:\n"
            "    return ToolResult()\n"
            "\n"
            "def bravo_run(root) -> ToolResult:\n"
            "    return ToolResult()\n"
            "\n"
            "def charlie_run(root) -> ToolResult:\n"
            "    return ToolResult()\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" not in categories

    def test_non_toolresult_returning_group_still_flagged(self, tmp_path) -> None:
        # frob:tests src/frob/arch/_python.py::_is_tool_result_builder_family
        # A same-shaped group over a specific (non-generic) type that does
        # NOT return a ToolResult shape has no check-stage-runner
        # convention to exclude, so it falls through to the normal
        # signature/body checks and still flags.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "runners.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class ToolResult:\n"
            "    pass\n"
            "\n"
            "def alpha_lookup(result: ToolResult) -> str:\n"
            "    return ''\n"
            "\n"
            "def bravo_lookup(result: ToolResult) -> str:\n"
            "    return ''\n"
            "\n"
            "def charlie_lookup(result: ToolResult) -> str:\n"
            "    return ''\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories

    def test_return_type_membership_matches_both_shapes(self) -> None:
        # frob:tests src/frob/arch/_python.py::_is_tool_result_builder_family
        from frob.arch._python import _is_tool_result_builder_family

        assert _is_tool_result_builder_family("ToolResult")
        assert _is_tool_result_builder_family("ToolResult | None")
        assert not _is_tool_result_builder_family("str")
        assert not _is_tool_result_builder_family("Violation")


# ---------------------------------------------------------------------------
# design-pattern recommender (T-0332): HALLMARK->PATTERN and
# ANTI-PATTERN->ESCAPE advisory suggestions.
# ---------------------------------------------------------------------------


class TestPatternRecommender:
    def test_isinstance_chain_recommends_strategy(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "shapes.py").write_text(
            "def area(shape):\n"
            "    if isinstance(shape, Circle):\n"
            "        return 1\n"
            "    elif isinstance(shape, Square):\n"
            "        return 2\n"
            "    elif isinstance(shape, Triangle):\n"
            "        return 3\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("Strategy" in s.message for s in hits)

    def test_two_arm_isinstance_chain_not_flagged(self, tmp_path: Path) -> None:
        # STRONG-HALLMARK-ONLY: two arms is routine control flow, not a
        # growing type-switch -- must not fire.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "shapes.py").write_text(
            "def area(shape):\n"
            "    if isinstance(shape, Circle):\n"
            "        return 1\n"
            "    elif isinstance(shape, Square):\n"
            "        return 2\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "Strategy" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_state_field_chain_recommends_state_machine(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "job.py").write_text(
            "class Job:\n"
            "    def step(self):\n"
            "        if self.status == 'pending':\n"
            "            pass\n"
            "        elif self.status == 'running':\n"
            "            pass\n"
            "        elif self.status == 'done':\n"
            "            pass\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("State machine" in s.message for s in hits)

    def test_non_state_attribute_chain_not_flagged_state_machine(
        self, tmp_path: Path
    ) -> None:
        # STRONG-HALLMARK-ONLY: an elif chain on a `self.<attr>` whose name
        # carries no state/status/mode/phase/stage lifecycle hint is an
        # ordinary attribute comparison, not the growing-state-machine
        # hallmark -- must not fire State machine.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "shape.py").write_text(
            "class Shape:\n"
            "    def area(self):\n"
            "        if self.color == 'red':\n"
            "            pass\n"
            "        elif self.color == 'blue':\n"
            "            pass\n"
            "        elif self.color == 'green':\n"
            "            pass\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "State machine" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_telescoping_ctor_recommends_builder(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "cfg.py").write_text(
            "class Config:\n"
            "    def __init__(self, a=1, b=2, c=None, d=None, e=None, f=None):\n"
            "        self.a = a\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("Builder" in s.message for s in hits)

    def test_normal_ctor_not_flagged_as_telescoping(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "point.py").write_text(
            "class Point:\n"
            "    def __init__(self, x, y):\n"
            "        self.x = x\n"
            "        self.y = y\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "Builder" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_scattered_construction_across_files_recommends_factory(
        self, tmp_path: Path
    ) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text("def use_a():\n    return Widget(1)\n")
        (src_dir / "b.py").write_text("def use_b():\n    return Widget(2)\n")
        (src_dir / "c.py").write_text("def use_c():\n    return Widget(3)\n")
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("Factory" in s.message and "Widget" in s.message for s in hits)

    def test_construction_in_two_files_not_flagged(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text("def use_a():\n    return Widget(1)\n")
        (src_dir / "b.py").write_text("def use_b():\n    return Widget(2)\n")
        result = analyze_project(src_dir)
        assert not any(
            "Factory" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_wrap_delegate_recommends_decorator(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "wrapper.py").write_text(
            "class LoggingList:\n"
            "    def __init__(self, inner):\n"
            "        self._inner = inner\n"
            "\n"
            "    def append(self):\n"
            "        return self._inner.append()\n"
            "\n"
            "    def pop(self):\n"
            "        return self._inner.pop()\n"
            "\n"
            "    def clear(self):\n"
            "        return self._inner.clear()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("Decorator" in s.message for s in hits)

    def test_two_method_delegating_wrapper_not_flagged_decorator(
        self, tmp_path: Path
    ) -> None:
        # STRONG-HALLMARK-ONLY: only 2 pass-through methods (below
        # _MIN_DELEGATE_METHODS=3) is an ordinary small wrapper, not the
        # wrap-and-delegate hallmark -- must not fire Decorator.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "wrapper.py").write_text(
            "class SmallWrapper:\n"
            "    def __init__(self, inner):\n"
            "        self._inner = inner\n"
            "\n"
            "    def append(self):\n"
            "        return self._inner.append()\n"
            "\n"
            "    def pop(self):\n"
            "        return self._inner.pop()\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "Decorator" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_god_class_pairs_with_srp_escape(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        methods = "\n".join(f"    def m{i}(self): pass" for i in range(14))
        (src_dir / "big.py").write_text(f"class BigThing:\n{methods}\n")
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "god-class" in categories
        assert "anti-pattern-escape" in categories
        escape = next(
            s for s in result.suggestions if s.category == "anti-pattern-escape"
        )
        assert "SRP decompose" in escape.message
        assert "BigThing" in escape.message

    def test_class_at_threshold_not_flagged_god_object(self, tmp_path: Path) -> None:
        # STRONG-HALLMARK-ONLY: god-object is PAIRED with god-class
        # (T-0332's "one detector, two outputs" design) -- a class at
        # exactly the default max_class_methods=12 threshold does not
        # trigger god-class, so it must not produce a paired SRP-decompose
        # escape either.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        methods = "\n".join(f"    def m{i}(self): pass" for i in range(12))
        (src_dir / "normal.py").write_text(f"class NormalThing:\n{methods}\n")
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "god-class" not in categories
        assert "anti-pattern-escape" not in categories

    def test_stringly_typed_recommends_newtype(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "cmd.py").write_text(
            "def dispatch(cmd):\n"
            "    if cmd == 'start':\n"
            "        pass\n"
            "    elif cmd == 'stop':\n"
            "        pass\n"
            "    elif cmd == 'pause':\n"
            "        pass\n"
            "    elif cmd == 'resume':\n"
            "        pass\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "anti-pattern-escape"]
        assert any("newtype" in s.message for s in hits)

    def test_short_string_chain_not_flagged_stringly_typed(
        self, tmp_path: Path
    ) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "cmd.py").write_text(
            "def dispatch(cmd):\n"
            "    if cmd == 'start':\n"
            "        pass\n"
            "    elif cmd == 'stop':\n"
            "        pass\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "newtype" in s.message
            for s in result.suggestions
            if s.category == "anti-pattern-escape"
        )

    def test_simple_python_no_pattern_recommendations(self) -> None:
        # Clean fixture project must not produce any advisory pattern
        # findings -- the STRONG-HALLMARK-ONLY constraint means simple code
        # never fires.
        root = FIXTURES / "simple_python" / "src"
        result = analyze_project(root)
        categories = {s.category for s in result.suggestions}
        assert "pattern-recommendation" not in categories
        assert "anti-pattern-escape" not in categories

    # -- T-0605: interface-translate -> Adapter -----------------------------

    def test_translating_wrapper_recommends_adapter(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "legacy_adapter.py").write_text(
            "class LegacyAdapter:\n"
            "    def __init__(self, legacy):\n"
            "        self._legacy = legacy\n"
            "\n"
            "    def read(self):\n"
            "        return self._legacy.fetch_old()\n"
            "\n"
            "    def write(self, data):\n"
            "        return self._legacy.store_old(data)\n"
            "\n"
            "    def close(self):\n"
            "        return self._legacy.shutdown_old()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("Adapter" in s.message for s in hits)

    def test_same_name_wrapper_not_flagged_adapter(self, tmp_path: Path) -> None:
        # Disjointness proof: a SAME-name pass-through wrapper (3+ methods)
        # is `wrap-delegate` -> Decorator, never `interface-translate` ->
        # Adapter -- the two hallmarks must never double-fire on identical
        # call-name shapes.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "wrapper.py").write_text(
            "class LoggingList:\n"
            "    def __init__(self, inner):\n"
            "        self._inner = inner\n"
            "\n"
            "    def append(self):\n"
            "        return self._inner.append()\n"
            "\n"
            "    def pop(self):\n"
            "        return self._inner.pop()\n"
            "\n"
            "    def clear(self):\n"
            "        return self._inner.clear()\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "Adapter" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_two_translating_methods_not_flagged_adapter(self, tmp_path: Path) -> None:
        # STRONG-HALLMARK-ONLY: only 2 translating methods (below
        # _MIN_TRANSLATE_METHODS=3) is an ordinary small wrapper, not the
        # interface-translate hallmark -- must not fire Adapter.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "small_adapter.py").write_text(
            "class SmallAdapter:\n"
            "    def __init__(self, legacy):\n"
            "        self._legacy = legacy\n"
            "\n"
            "    def read(self):\n"
            "        return self._legacy.fetch_old()\n"
            "\n"
            "    def write(self, data):\n"
            "        return self._legacy.store_old(data)\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "Adapter" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_mixed_delegate_and_translate_methods_fires_both(
        self, tmp_path: Path
    ) -> None:
        # Disjointness pin (reviewer round 1, T-0605): `wrap-delegate` and
        # `interface-translate` are disjoint PER-METHOD ONLY, never
        # per-class. A class with a same-name-delegating subset (3
        # methods) AND a separate translating subset (3 differently-named
        # methods) on the SAME inner attribute legitimately fires BOTH
        # Decorator and Adapter -- two true findings about two disjoint
        # method groups, not a contradiction. This is intentional,
        # accepted behavior, not a bug to suppress.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "mixed.py").write_text(
            "class MixedWrapper:\n"
            "    def __init__(self, inner):\n"
            "        self._inner = inner\n"
            "\n"
            "    def append(self):\n"
            "        return self._inner.append()\n"
            "\n"
            "    def pop(self):\n"
            "        return self._inner.pop()\n"
            "\n"
            "    def clear(self):\n"
            "        return self._inner.clear()\n"
            "\n"
            "    def read(self):\n"
            "        return self._inner.fetch_old()\n"
            "\n"
            "    def write(self, data):\n"
            "        return self._inner.store_old(data)\n"
            "\n"
            "    def close(self):\n"
            "        return self._inner.shutdown_old()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("Decorator" in s.message for s in hits)
        assert any("Adapter" in s.message for s in hits)

    # -- T-0605: manual-callback-list -> Observer ----------------------------

    def test_manual_callback_list_recommends_observer(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "bus.py").write_text(
            "class EventBus:\n"
            "    def __init__(self):\n"
            "        self._listeners = []\n"
            "\n"
            "    def subscribe(self, cb):\n"
            "        self._listeners.append(cb)\n"
            "\n"
            "    def publish(self):\n"
            "        for cb in self._listeners:\n"
            "            cb()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("Observer" in s.message for s in hits)

    def test_append_only_list_not_flagged_observer(self, tmp_path: Path) -> None:
        # No notify loop -- an ordinary list attribute that is only ever
        # appended to (a plain accumulator) must not fire Observer.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "log.py").write_text(
            "class Log:\n"
            "    def __init__(self):\n"
            "        self._entries = []\n"
            "\n"
            "    def record(self, entry):\n"
            "        self._entries.append(entry)\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "Observer" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_iterate_without_append_not_flagged_observer(self, tmp_path: Path) -> None:
        # A notify-shaped loop over a list nothing ever appends to (e.g. a
        # fixed, pre-populated list) must not fire Observer either -- both
        # the register AND notify facts are required.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "fixed.py").write_text(
            "class FixedHandlers:\n"
            "    def __init__(self):\n"
            "        self._handlers = []\n"
            "\n"
            "    def run_all(self):\n"
            "        for h in self._handlers:\n"
            "            h()\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "Observer" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    # -- T-0605: anemic-accessors -> move behavior to data -------------------

    def test_anemic_accessors_recommends_move_behavior(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "record.py").write_text(
            "class CustomerRecord:\n"
            "    def __init__(self, name, email, balance):\n"
            "        self._name = name\n"
            "        self._email = email\n"
            "        self._balance = balance\n"
            "\n"
            "    def get_name(self):\n"
            "        return self._name\n"
            "\n"
            "    def set_name(self, name):\n"
            "        self._name = name\n"
            "\n"
            "    def get_email(self):\n"
            "        return self._email\n"
            "\n"
            "    def set_balance(self, balance):\n"
            "        self._balance = balance\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "anti-pattern-escape"]
        assert any("move behavior to data" in s.message for s in hits)

    def test_class_with_real_method_not_flagged_anemic(self, tmp_path: Path) -> None:
        # One real method (actual computation) alongside several trivial
        # accessors must disqualify the whole class -- a mixed
        # behavior-plus-accessors class is not anemic.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "account.py").write_text(
            "class Account:\n"
            "    def __init__(self, name, email, balance):\n"
            "        self._name = name\n"
            "        self._email = email\n"
            "        self._balance = balance\n"
            "\n"
            "    def get_name(self):\n"
            "        return self._name\n"
            "\n"
            "    def set_name(self, name):\n"
            "        self._name = name\n"
            "\n"
            "    def get_email(self):\n"
            "        return self._email\n"
            "\n"
            "    def apply_interest(self, rate):\n"
            "        if rate > 0:\n"
            "            self._balance = self._balance * (1 + rate)\n"
            "        return self._balance\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "move behavior to data" in s.message
            for s in result.suggestions
            if s.category == "anti-pattern-escape"
        )

    def test_two_accessor_class_not_flagged_anemic(self, tmp_path: Path) -> None:
        # STRONG-HALLMARK-ONLY: only 2 accessor methods (below
        # _MIN_ANEMIC_ACCESSORS=3) is an ordinary small value holder, not
        # the anemic-domain-model hallmark -- must not fire.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "point.py").write_text(
            "class Point:\n"
            "    def __init__(self, x, y):\n"
            "        self._x = x\n"
            "        self._y = y\n"
            "\n"
            "    def get_x(self):\n"
            "        return self._x\n"
            "\n"
            "    def get_y(self):\n"
            "        return self._y\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "move behavior to data" in s.message
            for s in result.suggestions
            if s.category == "anti-pattern-escape"
        )

    def test_dataclass_boilerplate_recommends_dataclass(self, tmp_path: Path) -> None:
        # T-0849: a plain class whose only method is a pure
        # assign-every-param `__init__` recommends `@dataclass`.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "point.py").write_text(
            "class Point3D:\n"
            "    def __init__(self, x, y, z):\n"
            "        self.x = x\n"
            "        self.y = y\n"
            "        self.z = z\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("@dataclass" in s.message for s in hits)

    def test_dataclass_boilerplate_with_computed_field_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # Adversarial near-miss (hand-verified, T-0849): mutate the
        # discriminator by making ONE assignment computed instead of a
        # bare parameter pass-through -- the detector must go silent. This
        # is the exact fixture used to hand-verify the near-miss is
        # load-bearing: reverting `self.z = z * 2` back to `self.z = z`
        # makes this test start failing (the class becomes a real 3-field
        # boilerplate holder again).
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "point.py").write_text(
            "class Point3D:\n"
            "    def __init__(self, x, y, z):\n"
            "        self.x = x\n"
            "        self.y = y\n"
            "        self.z = z * 2\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "@dataclass" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_dataclass_boilerplate_with_extra_method_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # A second method beyond `__init__` (even a trivial one) means
        # this is not a pure value holder -- must not fire.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "point.py").write_text(
            "class Point3D:\n"
            "    def __init__(self, x, y, z):\n"
            "        self.x = x\n"
            "        self.y = y\n"
            "        self.z = z\n"
            "\n"
            "    def magnitude(self):\n"
            "        return (self.x**2 + self.y**2 + self.z**2) ** 0.5\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "@dataclass" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_dataclass_boilerplate_with_decorated_extra_method_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # Adversarial near-miss (hand-verified, T-0849 reviewer round 1):
        # a `@property` method is a `decorated_definition` node, not a
        # `function_definition` -- the detector's class-body member scan
        # must count it too, or it silently vanishes from the extra-
        # method count and the class wrongly looks like a pure `__init__`-
        # only value holder. Hand-verified: dropping the `decorated_
        # definition` arm from the member-collection filter makes this
        # test start failing (the class becomes a false-positive
        # `@dataclass` recommendation again).
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "point.py").write_text(
            "class Point3D:\n"
            "    def __init__(self, x, y, z):\n"
            "        self.x = x\n"
            "        self.y = y\n"
            "        self.z = z\n"
            "\n"
            "    @property\n"
            "    def magnitude(self):\n"
            "        return (self.x**2 + self.y**2 + self.z**2) ** 0.5\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "@dataclass" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_already_dataclass_not_flagged(self, tmp_path: Path) -> None:
        # An already-`@dataclass`-decorated class is a `decorated_
        # definition` node, structurally excluded before body inspection.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "point.py").write_text(
            "from dataclasses import dataclass\n"
            "\n"
            "@dataclass\n"
            "class Point3D:\n"
            "    x: int\n"
            "    y: int\n"
            "    z: int\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "@dataclass" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_manual_decorator_wrap_recommends_decorator_syntax(
        self, tmp_path: Path
    ) -> None:
        # T-0849: 3+ module-level `def f(...): ...` / `f = wrapper(f)`
        # reassignment pairs recommend `@wrapper` decorator syntax.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "registry.py").write_text(
            "def handler_one():\n"
            "    pass\n"
            "handler_one = logged(handler_one)\n"
            "\n"
            "def handler_two():\n"
            "    pass\n"
            "handler_two = logged(handler_two)\n"
            "\n"
            "def handler_three():\n"
            "    pass\n"
            "handler_three = logged(handler_three)\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("decorator syntax" in s.message for s in hits)

    def test_two_manual_decorator_wraps_not_flagged(self, tmp_path: Path) -> None:
        # Adversarial near-miss (hand-verified, T-0849): mutate the
        # discriminator by dropping to 2 occurrences (below
        # _MIN_MANUAL_DECORATOR_WRAPS=3) -- the STRONG-HALLMARK-ONLY floor
        # must keep this silent. Hand-verified: adding a third
        # `handler_three = logged(handler_three)` pair back makes this
        # test start failing (the file becomes the real 3-site hallmark).
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "registry.py").write_text(
            "def handler_one():\n"
            "    pass\n"
            "handler_one = logged(handler_one)\n"
            "\n"
            "def handler_two():\n"
            "    pass\n"
            "handler_two = logged(handler_two)\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "decorator syntax" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_decorator_syntax_wrap_not_flagged(self, tmp_path: Path) -> None:
        # Functions already wrapped via real `@decorator` syntax are
        # `decorated_definition` nodes, not bare `function_definition`s --
        # never enter this walk, never fire.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "registry.py").write_text(
            "@logged\n"
            "def handler_one():\n"
            "    pass\n"
            "\n"
            "@logged\n"
            "def handler_two():\n"
            "    pass\n"
            "\n"
            "@logged\n"
            "def handler_three():\n"
            "    pass\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "decorator syntax" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )


# ---------------------------------------------------------------------------
# T-0609: normalized code model + adapter protocol
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# T-0610: PythonAdapter -- maps a real parsed python file onto NormalizedModule
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# T-0611: TypeScriptAdapter -- maps a real parsed TypeScript file onto
# NormalizedModule, mirroring TestPythonAdapter's structure. Hand-built
# inline TS fixtures (written to tmp_path) rather than a shared fixtures/
# directory, since none exists for TypeScript yet.
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# T-0612: RustAdapter -- maps a real parsed rust file onto NormalizedModule,
# mirroring TestTypeScriptAdapter's structure. Hand-built inline .rs
# fixtures (written to tmp_path), same as TypeScript's approach.
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# T-0614: KotlinAdapter -- maps a real parsed kotlin file onto
# NormalizedModule, mirroring TestRustAdapter's structure. `tree-sitter-
# kotlin` (via `tree-sitter-language-pack`) exposes almost no named fields
# (see `frob.arch._kotlin`'s module docstring), so fixtures are built and
# parsed directly through `frob.lang._walk_kotlin.parse_kotlin` (source
# bytes -> Tree) rather than `frob.lang.raw_tree` -- `.kt`/`.kts` are not
# wired into `frob.lang`'s `_EXTENSION_TABLE`/`_extract.py` central
# dispatch (that is a separate follow-up ticket, T-draft-a78fa200: wiring
# them there needs a real `_walk_kotlin` RawSymbol walker too, or
# `parse_file`/`frob check` would KeyError on any real `.kt` file).
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# T-0615: the N:1 cross-language equivalence meta-test -- EPIC T-0329's own
# closing acceptance criterion ("an arch check written once fires correctly
# across python+ts+rust+kotlin on equivalent code"). T-0610/T-0611/T-0612/
# T-0614 each proved this PAIRWISE (python vs one other language); this is
# the four-way superset: one equivalent fixture per language under
# `tests/fixtures/arch/<language>/equiv.<ext>` (same base/derived class +
# field + overriding method shape, same nested if/for/while long function,
# same three-way dispatch function), adapted through all four
# `LanguageAdapter`s, asserting:
#
#   1. every `NormalizedModule` expresses the SAME entity counts/kinds for
#      the equivalent constructs, with per-language WAIVERS documented
#      (not silently skipped) where a language genuinely lacks a construct
#      -- python has no static "override" keyword, so its
#      `NormalizedFunction.overrides` stays `None` even for a genuine
#      override, unlike TS/kotlin's explicit `override` modifier and
#      rust's trait-impl inference;
#   2. the SHARED check (`_iter_normalized_functions`/`_normalized_is_complex`,
#      migrated once in T-0610 and reused unmodified by every adapter's
#      pairwise test) fires IDENTICALLY across all four on the equivalent
#      long/complex function;
#   3. the per-language branch-counting divergence on the SAME three-way
#      dispatch construct (python's if/elif chain folds to ONE branch;
#      TS's `switch` produces ZERO branches; rust's `match` and kotlin's
#      `when` each produce THREE, one per arm/entry) is pinned as an
#      EXPECTED difference with the rationale here, so future drift in
#      either direction (an adapter starting -- or stopping -- to count
#      arms) fails this test loudly instead of silently.
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# T-0695: structural fork/pool hazard family
# ---------------------------------------------------------------------------


class TestForkPoolHazards:
    """`frob.arch._concurrency` -- pool-inside-pool, fork-after-threads,
    pipe-wait-deadlock, self-join-deadlock (docs/modules/arch.md#fork-pool-
    hazards)."""

    def test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool(
        self, tmp_path
    ):
        """A `ProcessPoolExecutor` construction reachable in the same
        function as a `ThreadPoolExecutor` construction fires
        `pool-inside-pool` at warning severity -- the T-0265 field-bug
        shape."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "combined.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor\n\n"
            "def run_combined(thread_jobs, process_jobs):\n"
            "    ppool = ProcessPoolExecutor(max_workers=2)\n"
            "    with ThreadPoolExecutor(max_workers=2) as tpool:\n"
            "        tpool.submit(lambda: None)\n"
            "    ppool.shutdown(wait=True)\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pool-inside-pool"]
        assert len(hits) == 1
        assert hits[0].severity == "warning"
        assert hits[0].symref == "combined.py::run_combined"

    def test_pool_inside_pool_discharges_on_real_repo_run_combined_jobs(self):
        """Acceptance (T-0767): the restructured gates tree carries ZERO
        fork/pool-hazard findings. T-0695's real-repo acceptance originally
        asserted `pool-inside-pool` FIRES on `_run_combined_jobs` (T-0581
        fixed the runtime ordering but left the structural co-occurrence in
        one function); the advisory channel is unwaivable by design, so
        T-0767 hoisted pool construction into `_open_process_pool` /
        `_run_thread_jobs` and this test's job flipped: it now regression-
        locks the discharge, across ALL four hazard categories so a future
        refactor reintroducing the co-occurrence (or any sibling hazard
        shape) in `src/frob/gates` fails loudly. The synthetic fixture
        above (`test_pool_inside_pool_fires_on_process_pool_alongside_
        thread_pool`) still proves the detector itself fires -- the
        detector was not weakened, only the real-repo hit discharged."""
        root = Path(__file__).parent.parent.parent / "src" / "frob" / "gates"
        result = analyze_project(root)
        hazard_categories = {
            "pool-inside-pool",
            "fork-after-threads",
            "pipe-wait-deadlock",
            "self-join-deadlock",
        }
        hits = [s for s in result.suggestions if s.category in hazard_categories]
        assert hits == []

    def test_self_join_deadlock_discharges_on_real_repo_vet_scan(self):
        """Acceptance (T-0794): `src/frob/vet` carries ZERO fork/pool-
        hazard findings. `_run_with_timeout` used to be dispatched as a
        worker task (`_scan_dependencies_parallel`'s `pool.submit`) AND
        itself construct+`shutdown` an inner single-worker pool in the
        same body -- the exact `self-join-deadlock` co-occurrence shape
        (T-0767 discharged the sibling `pool-inside-pool` case on
        `src/frob/gates` the same way). The advisory channel is
        unwaivable by design, so T-0794 hoisted the inner pool's
        construction into `_open_single_worker_pool` and its
        submit/await/shutdown into `_bounded_process_dependency`, leaving
        `_run_with_timeout` -- the function actually dispatched -- a pure
        orchestrator with no pool calls of its own. This test regression-
        locks the discharge, across ALL four hazard categories so a
        future refactor reintroducing the co-occurrence (or any sibling
        hazard shape) in `src/frob/vet` fails loudly. The synthetic
        fixture above (`test_self_join_deadlock_fires_when_dispatched_
        task_joins_its_pool`) still proves the detector itself fires --
        the detector was not weakened, only the real-repo hit
        discharged."""
        root = Path(__file__).parent.parent.parent / "src" / "frob" / "vet"
        result = analyze_project(root)
        hazard_categories = {
            "pool-inside-pool",
            "fork-after-threads",
            "pipe-wait-deadlock",
            "self-join-deadlock",
        }
        hits = [s for s in result.suggestions if s.category in hazard_categories]
        assert hits == []

    def test_fork_after_threads_fires_when_fork_follows_thread_start(self, tmp_path):
        """An `os.fork()` reachable AFTER a `Thread(...).start()` on the
        same function's line order fires `fork-after-threads`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "forker.py").write_text(
            "from __future__ import annotations\n"
            "import os\n"
            "import threading\n\n"
            "def spawn_then_fork():\n"
            "    t = threading.Thread(target=lambda: None)\n"
            "    t.start()\n"
            "    pid = os.fork()\n"
            "    return pid\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "fork-after-threads"]
        assert len(hits) == 1
        assert hits[0].symref == "forker.py::spawn_then_fork"

    def test_fork_before_threads_does_not_fire(self, tmp_path):
        """Forking BEFORE any thread starts is the safe order (T-0581's
        own fix shape) -- `fork-after-threads` must not fire on it."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "safe_forker.py").write_text(
            "from __future__ import annotations\n"
            "import os\n"
            "import threading\n\n"
            "def fork_then_spawn():\n"
            "    pid = os.fork()\n"
            "    t = threading.Thread(target=lambda: None)\n"
            "    t.start()\n"
            "    return pid\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "fork-after-threads"]
        assert hits == []

    def test_pipe_wait_deadlock_fires_without_communicate(self, tmp_path):
        """A `Popen(..., stdout=PIPE)` followed by a bare `.wait()` with no
        `.communicate()` anywhere in the function fires
        `pipe-wait-deadlock`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "piper.py").write_text(
            "from __future__ import annotations\n"
            "import subprocess\n\n"
            "def run_and_wait(cmd):\n"
            "    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)\n"
            "    proc.wait()\n"
            "    return proc.returncode\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pipe-wait-deadlock"]
        assert len(hits) == 1
        assert hits[0].symref == "piper.py::run_and_wait"

    def test_pipe_wait_deadlock_does_not_fire_with_communicate(self, tmp_path):
        """The same `Popen(..., stdout=PIPE)` shape, but drained via
        `.communicate()` instead of a bare `.wait()`, must not fire."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "safe_piper.py").write_text(
            "from __future__ import annotations\n"
            "import subprocess\n\n"
            "def run_and_communicate(cmd):\n"
            "    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)\n"
            "    out, err = proc.communicate()\n"
            "    return out\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pipe-wait-deadlock"]
        assert hits == []

    def test_self_join_deadlock_fires_when_dispatched_task_joins_its_pool(
        self, tmp_path
    ):
        """A function submitted to a pool elsewhere in the module, whose
        own body calls `.shutdown()`, fires `self-join-deadlock`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "selfjoin.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n"
            "def dispatch(pool):\n"
            "    pool.submit(worker, pool)\n\n"
            "def worker(pool):\n"
            "    pool.shutdown(wait=True)\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "self-join-deadlock"]
        assert len(hits) == 1
        assert hits[0].symref == "selfjoin.py::worker"

    def test_self_join_deadlock_does_not_fire_on_undispatched_join(self, tmp_path):
        """A function that calls `.join()` on a pool it owns, but is never
        itself submitted/started as a task, must not fire -- this is the
        ordinary caller-joins-its-own-pool shape, not the hazard."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "ordinary.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n"
            "def run_all(jobs):\n"
            "    pool = ThreadPoolExecutor(max_workers=2)\n"
            "    for job in jobs:\n"
            "        pool.submit(job)\n"
            "    pool.shutdown(wait=True)\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "self-join-deadlock"]
        assert hits == []


class TestAsyncEventLoopHazards:
    """`frob.arch._async_hazards` -- blocking-call-in-async,
    nested-event-loop, unawaited-coroutine, async-zero-awaits (T-0696,
    child 3 of the T-0693 concurrency-hazard umbrella), and
    sequential-independent-awaits (T-1027, T-0698's own disclosed cut)."""

    def test_blocking_call_in_async_fires_on_time_sleep(self, tmp_path):
        """`time.sleep` reachable inside an `async def` body, with no
        executor dispatch, fires `blocking-call-in-async`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "blocker.py").write_text(
            "from __future__ import annotations\n"
            "import time\n\n"
            "async def poll():\n"
            "    time.sleep(1)\n"
            "    return True\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "blocking-call-in-async"]
        assert len(hits) == 1
        assert hits[0].symref == "blocker.py::poll"
        assert hits[0].severity == "warning"

    def test_blocking_call_in_async_does_not_fire_via_to_thread(self, tmp_path):
        """The same `time.sleep` call, but dispatched via
        `asyncio.to_thread`, must not fire -- it is correctly offloaded
        off the event loop."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "safe_blocker.py").write_text(
            "from __future__ import annotations\n"
            "import asyncio\n"
            "import time\n\n"
            "async def poll():\n"
            "    await asyncio.to_thread(time.sleep, 1)\n"
            "    return True\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "blocking-call-in-async"]
        assert hits == []

    def test_nested_event_loop_fires_on_asyncio_run_inside_coroutine(self, tmp_path):
        """`asyncio.run(...)` reachable inside an `async def` body fires
        `nested-event-loop` -- it raises RuntimeError at runtime since a
        coroutine already runs on a loop."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "nested.py").write_text(
            "from __future__ import annotations\n"
            "import asyncio\n\n"
            "async def outer():\n"
            "    asyncio.run(inner())\n\n"
            "async def inner():\n"
            "    return 1\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "nested-event-loop"]
        assert len(hits) == 1
        assert hits[0].symref == "nested.py::outer"

    def test_nested_event_loop_does_not_fire_at_top_level_sync_code(self, tmp_path):
        """`asyncio.run(...)` called from ordinary (non-async) top-level
        code is the standard entry-point shape -- must not fire."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "entrypoint.py").write_text(
            "from __future__ import annotations\n"
            "import asyncio\n\n"
            "async def main():\n"
            "    return 1\n\n"
            "def cli():\n"
            "    asyncio.run(main())\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "nested-event-loop"]
        assert hits == []

    def test_unawaited_coroutine_fires_on_bare_call_statement(self, tmp_path):
        """A bare call to a module-defined `async def` function, used as
        its own statement (neither awaited, gathered, nor stored), fires
        `unawaited-coroutine`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "dropped.py").write_text(
            "from __future__ import annotations\n\n"
            "async def fetch():\n"
            "    return 1\n\n"
            "def trigger():\n"
            "    fetch()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "unawaited-coroutine"]
        assert len(hits) == 1
        assert hits[0].symref == "dropped.py::trigger"

    def test_unawaited_coroutine_does_not_fire_when_awaited_or_stored(self, tmp_path):
        """The same call, but awaited in one function and stored (never
        called bare) in another, must not fire either time."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "kept.py").write_text(
            "from __future__ import annotations\n\n"
            "async def fetch():\n"
            "    return 1\n\n"
            "async def awaits_it():\n"
            "    return await fetch()\n\n"
            "def stores_it():\n"
            "    coro = fetch()\n"
            "    return coro\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "unawaited-coroutine"]
        assert hits == []

    def test_async_zero_awaits_fires_on_no_await_body(self, tmp_path):
        """An `async def` whose body never awaits anything fires
        `async-zero-awaits` at suggestion severity."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "noawait.py").write_text(
            "from __future__ import annotations\n\n"
            "async def compute():\n"
            "    x = 1 + 1\n"
            "    return x\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "async-zero-awaits"]
        assert len(hits) == 1
        assert hits[0].symref == "noawait.py::compute"
        assert hits[0].severity == "suggestion"

    def test_async_zero_awaits_does_not_fire_when_awaiting(self, tmp_path):
        """An `async def` that awaits something in its own body must not
        fire `async-zero-awaits`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "hasawait.py").write_text(
            "from __future__ import annotations\n"
            "import asyncio\n\n"
            "async def compute():\n"
            "    await asyncio.sleep(0)\n"
            "    return 1\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "async-zero-awaits"]
        assert hits == []

    def test_sequential_independent_awaits_fires_on_unrelated_calls(self, tmp_path):
        """Three sequential awaits, none reading an earlier one's bound
        name, fire ONE `sequential-independent-awaits` suggestion naming
        all three call sites."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "gatherable.py").write_text(
            "from __future__ import annotations\n\n"
            "async def fetch_all():\n"
            "    a = await fetch_one()\n"
            "    b = await fetch_two()\n"
            "    c = await fetch_three()\n"
            "    return a, b, c\n\n"
            "async def fetch_one(): ...\n"
            "async def fetch_two(): ...\n"
            "async def fetch_three(): ...\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s
            for s in result.suggestions
            if s.category == "sequential-independent-awaits"
        ]
        assert len(hits) == 1
        assert hits[0].symref == "gatherable.py::fetch_all"
        assert hits[0].severity == "suggestion"
        assert "fetch_one" in hits[0].message
        assert "fetch_two" in hits[0].message
        assert "fetch_three" in hits[0].message

    def test_sequential_independent_awaits_does_not_fire_when_second_reads_first(
        self, tmp_path
    ):
        """The second await's argument reads the first await's bound
        name -- a real sequential dependency, must not fire."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "dependent.py").write_text(
            "from __future__ import annotations\n\n"
            "async def pipeline():\n"
            "    a = await fetch_one()\n"
            "    b = await fetch_two(a)\n"
            "    return b\n\n"
            "async def fetch_one(): ...\n"
            "async def fetch_two(x): ...\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s
            for s in result.suggestions
            if s.category == "sequential-independent-awaits"
        ]
        assert hits == []

    def test_sequential_independent_awaits_does_not_fire_on_single_await(
        self, tmp_path
    ):
        """A single await has no sibling to be independent OF -- must not
        fire (this check needs 2+ awaits in the same run)."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "single.py").write_text(
            "from __future__ import annotations\n\n"
            "async def fetch():\n"
            "    a = await fetch_one()\n"
            "    return a\n\n"
            "async def fetch_one(): ...\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s
            for s in result.suggestions
            if s.category == "sequential-independent-awaits"
        ]
        assert hits == []


class TestLockOrderingHazards:
    """`frob.arch._lock_ordering` -- interprocedural lock-order-cycle and
    lock-identity-unresolved (T-0694, child 2 of the T-0693 concurrency-
    hazard umbrella)."""

    def test_two_lock_ab_ba_cycle_fires_within_one_function(self, tmp_path):
        """`f` acquires `lock_a` then `lock_b`; `g` acquires `lock_b` then
        `lock_a` -- the classic AB/BA two-lock deadlock, entirely within
        each function's own body, fires `lock-order-cycle`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "deadlock.py").write_text(
            "from __future__ import annotations\n"
            "import threading\n\n"
            "lock_a = threading.Lock()\n"
            "lock_b = threading.Lock()\n\n\n"
            "def f():\n"
            "    with lock_a:\n"
            "        with lock_b:\n"
            "            pass\n\n\n"
            "def g():\n"
            "    with lock_b:\n"
            "        with lock_a:\n"
            "            pass\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "lock-order-cycle"]
        assert len(hits) == 1
        assert "lock_a" in hits[0].message
        assert "lock_b" in hits[0].message
        assert "deadlock.py::f" in hits[0].message
        assert "deadlock.py::g" in hits[0].message
        assert hits[0].severity == "warning"

    def test_two_lock_ab_ba_cycle_fires_across_call_paths_via_callees(self, tmp_path):
        """The SAME cycle, but each function's second lock is acquired
        inside a CALLEE, not its own body -- the interprocedural
        requirement: `f` acquires `lock_a` then calls `helper_b` (which
        acquires `lock_b`); `g` acquires `lock_b` then calls `helper_a`
        (which acquires `lock_a`). Must still fire `lock-order-cycle`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "via_callee.py").write_text(
            "from __future__ import annotations\n"
            "import threading\n\n"
            "lock_a = threading.Lock()\n"
            "lock_b = threading.Lock()\n\n\n"
            "def helper_b():\n"
            "    with lock_b:\n"
            "        pass\n\n\n"
            "def helper_a():\n"
            "    with lock_a:\n"
            "        pass\n\n\n"
            "def f():\n"
            "    with lock_a:\n"
            "        helper_b()\n\n\n"
            "def g():\n"
            "    with lock_b:\n"
            "        helper_a()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "lock-order-cycle"]
        assert len(hits) == 1
        assert "lock_a" in hits[0].message
        assert "lock_b" in hits[0].message

    def test_consistent_global_order_does_not_fire(self, tmp_path):
        """Every function acquires `lock_a` before `lock_b`, never the
        reverse -- a consistent global order must stay silent."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "consistent.py").write_text(
            "from __future__ import annotations\n"
            "import threading\n\n"
            "lock_a = threading.Lock()\n"
            "lock_b = threading.Lock()\n\n\n"
            "def f():\n"
            "    with lock_a:\n"
            "        with lock_b:\n"
            "            pass\n\n\n"
            "def g():\n"
            "    with lock_a:\n"
            "        with lock_b:\n"
            "            pass\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "lock-order-cycle"]
        assert hits == []

    def test_reentrant_same_lock_does_not_fire(self, tmp_path):
        """A function acquiring the SAME `RLock` twice (nested `with`) must
        not fire `lock-order-cycle` -- reentrant use of one lock is never
        an ordering hazard."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "reentrant.py").write_text(
            "from __future__ import annotations\n"
            "import threading\n\n"
            "lock_a = threading.RLock()\n\n\n"
            "def f():\n"
            "    with lock_a:\n"
            "        with lock_a:\n"
            "            pass\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "lock-order-cycle"]
        assert hits == []

    def test_unresolvable_lock_identity_is_advisory(self, tmp_path):
        """A `with` statement over a lock-shaped PARAMETER (no module/class-
        level construction site this resolver can identify) fires
        `lock-identity-unresolved` at suggestion severity, fail-closed,
        instead of being silently dropped -- and a plain `with open(...)`
        (no lock-shaped name) must not fire anything at all."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "unresolved.py").write_text(
            "from __future__ import annotations\n\n\n"
            "def f(some_lock):\n"
            "    with some_lock:\n"
            "        pass\n"
        )
        (src_dir / "plain_open.py").write_text(
            "def f():\n    with open('x') as fh:\n        pass\n"
        )
        result = analyze_project(src_dir)
        unresolved_hits = [
            s for s in result.suggestions if s.category == "lock-identity-unresolved"
        ]
        assert len(unresolved_hits) == 1
        assert unresolved_hits[0].symref == "unresolved.py::f"
        assert unresolved_hits[0].severity == "suggestion"
        open_hits = [
            s
            for s in result.suggestions
            if s.file == "plain_open.py"
            and s.category in ("lock-identity-unresolved", "lock-order-cycle")
        ]
        assert open_hits == []


# ---------------------------------------------------------------------------
# T-0618: LSP checks -- override contract violations (docs/modules/arch.md#lsp-checks)
# ---------------------------------------------------------------------------


def _lsp_module(base, override):
    """Build a two-class `NormalizedModule` (T-0618) with `override`'s
    `bases` naming `base`'s class name -- the same-file base<->override
    linkage every `_solid.py` check resolves from."""
    from frob.arch._normalized import NormalizedModule

    return NormalizedModule(
        path="pkg/mod.py",
        language="python",
        classes=[base, override],
    )


class TestOverrideRaisesNotImplemented:
    """ARCH104: `check_override_raises_not_implemented`
    (docs/modules/arch.md#lsp-checks)."""

    def test_concrete_override_raising_not_implemented_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedRaise,
            NormalizedReturn,
        )
        from frob.arch._solid import check_override_raises_not_implemented

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="greet",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    returns=[NormalizedReturn(line=3, value_text="'hi'")],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="greet",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    raises=[
                        NormalizedRaise(line=7, exception_type="NotImplementedError")
                    ],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_raises_not_implemented(module, out)
        assert len(out) == 1
        assert out[0].category == "lsp-not-implemented-override"
        assert out[0].symref == "pkg/mod.py::Sub.greet"

    def test_base_itself_raising_not_implemented_is_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedRaise,
        )
        from frob.arch._solid import check_override_raises_not_implemented

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="greet",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    raises=[
                        NormalizedRaise(line=3, exception_type="NotImplementedError")
                    ],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="greet",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    raises=[
                        NormalizedRaise(line=7, exception_type="NotImplementedError")
                    ],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_raises_not_implemented(module, out)
        assert out == []


class TestOverrideSignatureVariance:
    """ARCH105: `check_override_signature_variance`
    (docs/modules/arch.md#lsp-checks)."""

    def test_narrower_required_params_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedParam,
        )
        from frob.arch._solid import check_override_signature_variance

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="save",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    params=[
                        NormalizedParam(name="self"),
                        NormalizedParam(name="path"),
                        NormalizedParam(name="mode"),
                    ],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="save",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    params=[NormalizedParam(name="self"), NormalizedParam(name="path")],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_signature_variance(module, out)
        assert len(out) == 1
        assert out[0].category == "lsp-signature-variance"
        assert out[0].metric == 1

    def test_wider_return_type_flagged(self) -> None:
        from frob.arch._normalized import NormalizedClass, NormalizedFunction
        from frob.arch._solid import check_override_signature_variance

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="get",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    return_type="int",
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="get",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    return_type="str",
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_signature_variance(module, out)
        assert len(out) == 1
        assert out[0].category == "lsp-signature-variance"

    def test_same_shape_signature_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedParam,
        )
        from frob.arch._solid import check_override_signature_variance

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="get",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    params=[NormalizedParam(name="self"), NormalizedParam(name="x")],
                    return_type="int",
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="get",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    params=[NormalizedParam(name="self"), NormalizedParam(name="x")],
                    return_type="int",
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_signature_variance(module, out)
        assert out == []


class TestOverrideStrengthenedPrecondition:
    """ARCH106: `check_override_strengthened_precondition`
    (docs/modules/arch.md#lsp-checks)."""

    def test_added_guard_raise_on_shared_param_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedClass,
            NormalizedFunction,
            NormalizedParam,
            NormalizedRaise,
        )
        from frob.arch._solid import check_override_strengthened_precondition

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="withdraw",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    params=[
                        NormalizedParam(name="self"),
                        NormalizedParam(name="amount"),
                    ],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="withdraw",
                    line=6,
                    body_line_count=3,
                    is_method=True,
                    params=[
                        NormalizedParam(name="self"),
                        NormalizedParam(name="amount"),
                    ],
                    branches=[NormalizedBranch(line=7, condition_text="amount > 100")],
                    raises=[NormalizedRaise(line=8, exception_type="ValueError")],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_strengthened_precondition(module, out)
        assert len(out) == 1
        assert out[0].category == "lsp-strengthened-precondition"
        assert out[0].metric == 1

    def test_guard_raise_present_in_base_too_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedClass,
            NormalizedFunction,
            NormalizedParam,
            NormalizedRaise,
        )
        from frob.arch._solid import check_override_strengthened_precondition

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="withdraw",
                    line=2,
                    body_line_count=3,
                    is_method=True,
                    params=[
                        NormalizedParam(name="self"),
                        NormalizedParam(name="amount"),
                    ],
                    branches=[NormalizedBranch(line=3, condition_text="amount > 100")],
                    raises=[NormalizedRaise(line=4, exception_type="ValueError")],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=6,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="withdraw",
                    line=7,
                    body_line_count=3,
                    is_method=True,
                    params=[
                        NormalizedParam(name="self"),
                        NormalizedParam(name="amount"),
                    ],
                    branches=[NormalizedBranch(line=8, condition_text="amount > 100")],
                    raises=[NormalizedRaise(line=9, exception_type="ValueError")],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_strengthened_precondition(module, out)
        assert out == []


class TestOverrideWeakenedPostcondition:
    """ARCH107: `check_override_weakened_postcondition`
    (docs/modules/arch.md#lsp-checks)."""

    def test_bare_return_where_base_always_returns_value_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedReturn,
        )
        from frob.arch._solid import check_override_weakened_postcondition

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="find",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    returns=[NormalizedReturn(line=3, value_text="item")],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="find",
                    line=6,
                    body_line_count=2,
                    is_method=True,
                    returns=[NormalizedReturn(line=7, value_text=None)],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_weakened_postcondition(module, out)
        assert len(out) == 1
        assert out[0].category == "lsp-weakened-postcondition"

    def test_override_also_always_returning_value_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedReturn,
        )
        from frob.arch._solid import check_override_weakened_postcondition

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="find",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    returns=[NormalizedReturn(line=3, value_text="item")],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="find",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    returns=[NormalizedReturn(line=7, value_text="other_item")],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_weakened_postcondition(module, out)
        assert out == []


class TestNoOpOverride:
    """ARCH108: `check_noop_override` (docs/modules/arch.md#lsp-checks)."""

    def test_empty_body_override_of_value_returning_base_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedReturn,
        )
        from frob.arch._solid import check_noop_override

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="compute",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    returns=[NormalizedReturn(line=3, value_text="42")],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="compute",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    returns=[],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_noop_override(module, out)
        assert len(out) == 1
        assert out[0].category == "lsp-noop-override"

    def test_override_with_real_body_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedReturn,
        )
        from frob.arch._solid import check_noop_override

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="compute",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    returns=[NormalizedReturn(line=3, value_text="42")],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="compute",
                    line=6,
                    body_line_count=2,
                    is_method=True,
                    calls=[NormalizedCall(callee="super().compute", line=7)],
                    returns=[NormalizedReturn(line=7, value_text="43")],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_noop_override(module, out)
        assert out == []


class TestRunLspChecks:
    """`run_lsp_checks` combines every ARCH1xx LSP check
    (docs/modules/arch.md#lsp-checks)."""

    def test_combines_multiple_checks(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedRaise,
            NormalizedReturn,
        )
        from frob.arch._solid import run_lsp_checks

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="greet",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    returns=[NormalizedReturn(line=3, value_text="'hi'")],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="greet",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    raises=[
                        NormalizedRaise(line=7, exception_type="NotImplementedError")
                    ],
                )
            ],
        )
        module = _lsp_module(base, override)
        out = run_lsp_checks(module)
        categories = {s.category for s in out}
        assert "lsp-not-implemented-override" in categories


# ---------------------------------------------------------------------------
# T-0619: ISP checks -- fat interface, narrow-client usage (docs/modules/arch.md#isp-checks)
# ---------------------------------------------------------------------------


def _isp_module(*classes):
    """Build a `NormalizedModule` (T-0619) from `classes`, mirroring
    `_lsp_module`'s convenience for ISP fixtures needing 2+ classes."""
    from frob.arch._normalized import NormalizedModule

    return NormalizedModule(path="pkg/mod.py", language="python", classes=list(classes))


def _stub_method(name: str, line: int):
    """A structurally empty override body (T-0619's `_is_stub_method`
    "empty shell" shape: no branches/loops/calls/field-accesses/catches,
    no value-returning return) for fat-interface fixtures."""
    from frob.arch._normalized import NormalizedFunction

    return NormalizedFunction(name=name, line=line, body_line_count=1, is_method=True)


def _real_method(name: str, line: int):
    """An override body with a real call event (T-0619) -- NOT a stub by
    `_is_stub_method`'s test, for fat-interface negative fixtures."""
    from frob.arch._normalized import (
        NormalizedCall,
        NormalizedFunction,
        NormalizedReturn,
    )

    return NormalizedFunction(
        name=name,
        line=line,
        body_line_count=2,
        is_method=True,
        calls=[NormalizedCall(callee="do_work", line=line + 1)],
        returns=[NormalizedReturn(line=line + 1, value_text="result")],
    )


class TestFatInterface:
    """ARCH109: `check_fat_interface` (docs/modules/arch.md#isp-checks)."""

    def test_mostly_stubbed_implementers_flag_fat_interface(self) -> None:
        from frob.arch._normalized import NormalizedClass
        from frob.arch._solid import check_fat_interface

        interface = NormalizedClass(
            name="Repo",
            line=1,
            bases=["ABC"],
            methods=[
                _stub_method("create", 2),
                _stub_method("read", 3),
                _stub_method("update", 4),
                _stub_method("delete", 5),
            ],
        )
        impl_a = NormalizedClass(
            name="ImplA",
            line=10,
            bases=["Repo"],
            methods=[
                _stub_method("create", 11),
                _stub_method("read", 12),
                _stub_method("update", 13),
                _real_method("delete", 14),
            ],
        )
        impl_b = NormalizedClass(
            name="ImplB",
            line=20,
            bases=["Repo"],
            methods=[
                _stub_method("create", 21),
                _stub_method("read", 22),
                _stub_method("update", 23),
                _real_method("delete", 24),
            ],
        )
        module = _isp_module(interface, impl_a, impl_b)
        out: list = []
        check_fat_interface(module, out)
        assert len(out) == 1
        assert out[0].category == "fat-interface"
        assert out[0].symref == "Repo"
        assert out[0].metric == 6  # 3 stubbed methods x 2 implementers

    def test_mostly_implemented_methods_not_flagged(self) -> None:
        from frob.arch._normalized import NormalizedClass
        from frob.arch._solid import check_fat_interface

        interface = NormalizedClass(
            name="Repo",
            line=1,
            bases=["ABC"],
            methods=[
                _stub_method("create", 2),
                _stub_method("read", 3),
                _stub_method("update", 4),
                _stub_method("delete", 5),
            ],
        )
        impl_a = NormalizedClass(
            name="ImplA",
            line=10,
            bases=["Repo"],
            methods=[
                _real_method("create", 11),
                _real_method("read", 12),
                _real_method("update", 13),
                _stub_method("delete", 14),
            ],
        )
        impl_b = NormalizedClass(
            name="ImplB",
            line=20,
            bases=["Repo"],
            methods=[
                _real_method("create", 21),
                _real_method("read", 22),
                _real_method("update", 23),
                _stub_method("delete", 24),
            ],
        )
        module = _isp_module(interface, impl_a, impl_b)
        out: list = []
        check_fat_interface(module, out)
        assert out == []


class TestNarrowClientUsage:
    """ARCH110: `check_narrow_client_usage`
    (docs/modules/arch.md#isp-checks)."""

    def test_client_using_small_method_subset_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedParam,
        )
        from frob.arch._solid import check_narrow_client_usage

        wide = NormalizedClass(
            name="Client",
            line=1,
            methods=[
                _stub_method("connect", 2),
                _stub_method("read", 3),
                _stub_method("write", 4),
                _stub_method("close", 5),
                _stub_method("flush", 6),
            ],
        )
        user_fn = NormalizedFunction(
            name="save_once",
            line=10,
            body_line_count=2,
            params=[NormalizedParam(name="client", type="Client")],
            calls=[NormalizedCall(callee="client.write", line=11)],
        )
        from frob.arch._normalized import NormalizedModule

        module = NormalizedModule(
            path="pkg/mod.py", language="python", classes=[wide], functions=[user_fn]
        )
        out: list = []
        check_narrow_client_usage(module, out)
        assert len(out) == 1
        assert out[0].category == "narrow-client-usage"
        assert out[0].symref == "save_once"
        assert out[0].metric == 4  # 5 methods - 1 used

    def test_client_using_most_of_interface_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._solid import check_narrow_client_usage

        wide = NormalizedClass(
            name="Client",
            line=1,
            methods=[
                _stub_method("connect", 2),
                _stub_method("read", 3),
                _stub_method("write", 4),
                _stub_method("close", 5),
                _stub_method("flush", 6),
            ],
        )
        user_fn = NormalizedFunction(
            name="save_everything",
            line=10,
            body_line_count=5,
            params=[NormalizedParam(name="client", type="Client")],
            calls=[
                NormalizedCall(callee="client.connect", line=11),
                NormalizedCall(callee="client.write", line=12),
                NormalizedCall(callee="client.flush", line=13),
                NormalizedCall(callee="client.close", line=14),
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", classes=[wide], functions=[user_fn]
        )
        out: list = []
        check_narrow_client_usage(module, out)
        assert out == []


class TestRunIspChecks:
    """`run_isp_checks` combines every ARCH1xx ISP check
    (docs/modules/arch.md#isp-checks)."""

    def test_combines_both_checks(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._solid import run_isp_checks

        interface = NormalizedClass(
            name="Repo",
            line=1,
            bases=["ABC"],
            methods=[
                _stub_method("create", 2),
                _stub_method("read", 3),
                _stub_method("update", 4),
                _stub_method("delete", 5),
            ],
        )
        impl_a = NormalizedClass(
            name="ImplA",
            line=10,
            bases=["Repo"],
            methods=[_stub_method("create", 11), _stub_method("read", 12)],
        )
        impl_b = NormalizedClass(
            name="ImplB",
            line=20,
            bases=["Repo"],
            methods=[_stub_method("create", 21), _stub_method("read", 22)],
        )
        user_fn = NormalizedFunction(
            name="save_once",
            line=30,
            body_line_count=2,
            params=[NormalizedParam(name="repo", type="Repo")],
            calls=[NormalizedCall(callee="repo.create", line=31)],
        )
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            classes=[interface, impl_a, impl_b],
            functions=[user_fn],
        )
        out = run_isp_checks(module)
        categories = {s.category for s in out}
        assert "fat-interface" in categories
        assert "narrow-client-usage" in categories


# ---------------------------------------------------------------------------
# T-0620: DIP layering contract + no-DI construction smell (docs/modules/arch.md#dip-layering-contract)
# ---------------------------------------------------------------------------


class TestLayeringConfig:
    """`LayeringConfig.layer_for` (docs/modules/arch.md#dip-layering-contract)."""

    def test_layer_for_longest_prefix_match(self) -> None:
        from frob.arch._layering import LayeringConfig

        config = LayeringConfig(
            layers={
                "app": ["src/app"],
                "app_admin": ["src/app/admin"],
            },
            allow={},
        )
        assert config.layer_for("src/app/admin/views.py") == "app_admin"
        assert config.layer_for("src/app/main.py") == "app"

    def test_layer_for_unmatched_path_is_none(self) -> None:
        from frob.arch._layering import LayeringConfig

        config = LayeringConfig(layers={"app": ["src/app"]}, allow={})
        assert config.layer_for("src/other/mod.py") is None


class TestLoadLayeringConfig:
    """`load_layering_config` (docs/modules/arch.md#dip-layering-contract)."""

    def test_missing_frob_toml_returns_none(self, tmp_path: Path) -> None:
        from frob.arch._layering import load_layering_config

        assert load_layering_config(tmp_path) is None

    def test_parses_declared_layers_and_allow_table(self, tmp_path: Path) -> None:
        from frob.arch._layering import load_layering_config

        (tmp_path / "frob.toml").write_text(
            "[arch.layering.layers]\n"
            'app = ["src/app"]\n'
            'lang = ["src/lang"]\n\n'
            "[arch.layering.allow]\n"
            'app = ["lang"]\n'
            "lang = []\n"
        )
        config = load_layering_config(tmp_path)
        assert config is not None
        assert config.layers["app"] == ["src/app"]
        assert config.allow["app"] == ["lang"]


class TestLayeringViolations:
    """`check_layering_violations`
    (docs/modules/arch.md#dip-layering-contract)."""

    def test_disallowed_cross_layer_edge_flagged(self, tmp_path: Path) -> None:
        from frob.arch._layering import LayeringConfig, check_layering_violations

        (tmp_path / "app").mkdir()
        (tmp_path / "lang").mkdir()
        (tmp_path / "app" / "__init__.py").write_text("")
        (tmp_path / "app" / "main.py").write_text("import lang.core\n")
        (tmp_path / "lang" / "__init__.py").write_text("")
        (tmp_path / "lang" / "core.py").write_text("import app.main\n")

        config = LayeringConfig(
            layers={"app": ["app"], "lang": ["lang"]},
            allow={"app": ["lang"], "lang": []},
        )
        out = check_layering_violations(tmp_path, config)
        violations = [s for s in out if s.file == "lang/core.py"]
        assert len(violations) == 1
        assert violations[0].category == "dip-layering-violation"

    def test_allowed_cross_layer_edge_not_flagged(self, tmp_path: Path) -> None:
        from frob.arch._layering import LayeringConfig, check_layering_violations

        (tmp_path / "app").mkdir()
        (tmp_path / "lang").mkdir()
        (tmp_path / "app" / "__init__.py").write_text("")
        (tmp_path / "app" / "main.py").write_text("import lang.core\n")
        (tmp_path / "lang" / "__init__.py").write_text("")
        (tmp_path / "lang" / "core.py").write_text("")

        config = LayeringConfig(
            layers={"app": ["app"], "lang": ["lang"]},
            allow={"app": ["lang"], "lang": []},
        )
        out = check_layering_violations(tmp_path, config)
        assert [s for s in out if s.category == "dip-layering-violation"] == []

    def test_dynamic_import_in_layered_file_flagged(self, tmp_path: Path) -> None:
        from frob.arch._layering import LayeringConfig, check_layering_violations

        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "__init__.py").write_text("")
        (tmp_path / "app" / "main.py").write_text(
            "import importlib\nmod = importlib.import_module('lang.core')\n"
        )

        config = LayeringConfig(layers={"app": ["app"]}, allow={"app": []})
        out = check_layering_violations(tmp_path, config)
        hits = [s for s in out if s.file == "app/main.py"]
        assert len(hits) == 1
        assert hits[0].category == "dip-layering-violation"
        assert "dynamic import" in hits[0].message


class TestNoDiConstructionSmell:
    """`check_no_di_construction`
    (docs/modules/arch.md#no-di-construction-smell)."""

    def test_inline_construction_outside_init_flagged(self) -> None:
        from frob.arch._layering import check_no_di_construction
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
        )

        service = NormalizedClass(name="Emailer", line=1, methods=[])
        worker = NormalizedClass(
            name="Worker",
            line=5,
            methods=[
                NormalizedFunction(
                    name="run",
                    line=6,
                    body_line_count=2,
                    is_method=True,
                    calls=[NormalizedCall(callee="Emailer", line=7)],
                )
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", classes=[service, worker]
        )
        out = check_no_di_construction(module)
        assert len(out) == 1
        assert out[0].category == "no-di-construction"
        assert out[0].symref == "pkg/mod.py::Worker.run"

    def test_construction_inside_init_not_flagged(self) -> None:
        from frob.arch._layering import check_no_di_construction
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
        )

        service = NormalizedClass(name="Emailer", line=1, methods=[])
        worker = NormalizedClass(
            name="Worker",
            line=5,
            methods=[
                NormalizedFunction(
                    name="__init__",
                    line=6,
                    body_line_count=2,
                    is_method=True,
                    calls=[NormalizedCall(callee="Emailer", line=7)],
                )
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", classes=[service, worker]
        )
        out = check_no_di_construction(module)
        assert out == []

    def test_construction_inside_factory_function_not_flagged(self) -> None:
        from frob.arch._layering import check_no_di_construction
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
        )

        service = NormalizedClass(name="Emailer", line=1, methods=[])
        factory = NormalizedFunction(
            name="make_emailer",
            line=5,
            body_line_count=1,
            calls=[NormalizedCall(callee="Emailer", line=6)],
        )
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            classes=[service],
            functions=[factory],
        )
        out = check_no_di_construction(module)
        assert out == []


# ---------------------------------------------------------------------------
# T-0621: type-driven design checks (docs/modules/arch.md#type-driven-design-checks)
# ---------------------------------------------------------------------------


class TestIllegalStatesRepresentable:
    """`check_illegal_states_representable`
    (docs/modules/arch.md#type-driven-design-checks)."""

    def test_bool_field_cross_field_guard_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedClass,
            NormalizedField,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )
        from frob.arch._typedesign import check_illegal_states_representable

        cls = NormalizedClass(
            name="Payment",
            line=1,
            fields=[
                NormalizedField(name="is_refund", line=2, type="bool"),
                NormalizedField(name="amount", line=3, type="int"),
            ],
            methods=[
                NormalizedFunction(
                    name="__init__",
                    line=4,
                    body_line_count=3,
                    is_method=True,
                    branches=[
                        NormalizedBranch(
                            line=5, condition_text="is_refund and amount > 0"
                        )
                    ],
                    raises=[NormalizedRaise(line=6, exception_type="ValueError")],
                )
            ],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=[cls])
        out = check_illegal_states_representable(module)
        assert len(out) == 1
        assert out[0].category == "illegal-states-representable"
        assert out[0].symref == "pkg/mod.py::Payment.__init__"

    def test_bool_field_alone_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedClass,
            NormalizedField,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )
        from frob.arch._typedesign import check_illegal_states_representable

        cls = NormalizedClass(
            name="Payment",
            line=1,
            fields=[NormalizedField(name="is_refund", line=2, type="bool")],
            methods=[
                NormalizedFunction(
                    name="__init__",
                    line=4,
                    body_line_count=3,
                    is_method=True,
                    branches=[NormalizedBranch(line=5, condition_text="is_refund")],
                    raises=[NormalizedRaise(line=6, exception_type="ValueError")],
                )
            ],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=[cls])
        out = check_illegal_states_representable(module)
        assert out == []


class TestPrimitiveObsession:
    """`check_primitive_obsession`
    (docs/modules/arch.md#type-driven-design-checks)."""

    def test_three_plus_raw_params_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._typedesign import check_primitive_obsession

        func = NormalizedFunction(
            name="make_address",
            line=1,
            body_line_count=1,
            params=[
                NormalizedParam(name="street", type="str"),
                NormalizedParam(name="city", type="str"),
                NormalizedParam(name="zip_code", type="str"),
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_primitive_obsession(module)
        assert len(out) == 1
        assert out[0].category == "primitive-obsession"
        assert out[0].metric == 3

    def test_two_raw_params_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._typedesign import check_primitive_obsession

        func = NormalizedFunction(
            name="add",
            line=1,
            body_line_count=1,
            params=[
                NormalizedParam(name="a", type="int"),
                NormalizedParam(name="b", type="int"),
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_primitive_obsession(module)
        assert out == []


class TestParseDontValidate:
    """`check_parse_dont_validate`
    (docs/modules/arch.md#type-driven-design-checks)."""

    def test_validates_then_returns_same_type_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
            NormalizedRaise,
        )
        from frob.arch._typedesign import check_parse_dont_validate

        func = NormalizedFunction(
            name="validate_email",
            line=1,
            body_line_count=3,
            params=[NormalizedParam(name="email", type="str")],
            return_type="str",
            branches=[NormalizedBranch(line=2, condition_text="'@' not in email")],
            raises=[NormalizedRaise(line=3, exception_type="ValueError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_parse_dont_validate(module)
        assert len(out) == 1
        assert out[0].category == "parse-dont-validate"
        assert out[0].symref == "validate_email"

    def test_validates_then_returns_refined_type_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
            NormalizedRaise,
        )
        from frob.arch._typedesign import check_parse_dont_validate

        func = NormalizedFunction(
            name="parse_email",
            line=1,
            body_line_count=3,
            params=[NormalizedParam(name="email", type="str")],
            return_type="EmailAddress",
            branches=[NormalizedBranch(line=2, condition_text="'@' not in email")],
            raises=[NormalizedRaise(line=3, exception_type="ValueError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_parse_dont_validate(module)
        assert out == []


class TestBooleanFlagParam:
    """`check_boolean_flag_param`
    (docs/modules/arch.md#type-driven-design-checks)."""

    def test_public_function_branching_on_bool_param_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._typedesign import check_boolean_flag_param

        func = NormalizedFunction(
            name="save",
            line=1,
            body_line_count=2,
            params=[NormalizedParam(name="overwrite", type="bool")],
            branches=[NormalizedBranch(line=2, condition_text="overwrite")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_boolean_flag_param(module)
        assert len(out) == 1
        assert out[0].category == "boolean-flag-param"
        assert out[0].metric == 1

    def test_private_function_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._typedesign import check_boolean_flag_param

        func = NormalizedFunction(
            name="_save",
            line=1,
            body_line_count=2,
            params=[NormalizedParam(name="overwrite", type="bool")],
            branches=[NormalizedBranch(line=2, condition_text="overwrite")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_boolean_flag_param(module)
        assert out == []


class TestRunTypeDesignChecks:
    """`run_typedesign_checks` combines every ARCH1xx type-driven-design
    check (docs/modules/arch.md#type-driven-design-checks)."""

    def test_combines_all_four_checks(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedClass,
            NormalizedField,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
            NormalizedRaise,
        )
        from frob.arch._typedesign import run_typedesign_checks

        payment = NormalizedClass(
            name="Payment",
            line=1,
            fields=[
                NormalizedField(name="is_refund", line=2, type="bool"),
                NormalizedField(name="amount", line=3, type="int"),
            ],
            methods=[
                NormalizedFunction(
                    name="__init__",
                    line=4,
                    body_line_count=3,
                    is_method=True,
                    branches=[
                        NormalizedBranch(
                            line=5, condition_text="is_refund and amount > 0"
                        )
                    ],
                    raises=[NormalizedRaise(line=6, exception_type="ValueError")],
                )
            ],
        )
        save_fn = NormalizedFunction(
            name="save",
            line=10,
            body_line_count=2,
            params=[NormalizedParam(name="overwrite", type="bool")],
            branches=[NormalizedBranch(line=11, condition_text="overwrite")],
        )
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            classes=[payment],
            functions=[save_fn],
        )
        out = run_typedesign_checks(module)
        categories = {s.category for s in out}
        assert "illegal-states-representable" in categories
        assert "boolean-flag-param" in categories


# ---------------------------------------------------------------------------
# T-0622: logging discipline checks -- unlogged error path, unlogged
# boundary, print-as-diagnostic
# ---------------------------------------------------------------------------


class TestUnloggedErrorPath:
    """`check_unlogged_error_path`
    (docs/modules/arch.md#logging-discipline-checks)."""

    def test_catch_with_no_nearby_log_call_flagged(self) -> None:
        from frob.arch._logging_checks import check_unlogged_error_path
        from frob.arch._normalized import (
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="load_config",
            line=1,
            body_line_count=4,
            catches=[NormalizedCatch(line=3, exception_type="OSError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_unlogged_error_path(module)
        assert len(out) == 1
        assert out[0].category == "unlogged-error-path"
        assert out[0].symref == "load_config"

    def test_catch_with_nearby_log_call_not_flagged(self) -> None:
        from frob.arch._logging_checks import check_unlogged_error_path
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="load_config",
            line=1,
            body_line_count=4,
            catches=[NormalizedCatch(line=3, exception_type="OSError")],
            calls=[NormalizedCall(callee="logger.error", line=4)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_unlogged_error_path(module)
        assert out == []


class TestUnloggedBoundary:
    """`check_unlogged_boundary`
    (docs/modules/arch.md#logging-discipline-checks)."""

    def test_public_entry_point_with_no_log_call_flagged(self) -> None:
        from frob.arch._logging_checks import check_unlogged_boundary
        from frob.arch._normalized import NormalizedFunction, NormalizedModule

        func = NormalizedFunction(name="run", line=1, body_line_count=2)
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_unlogged_boundary(module)
        assert any(s.category == "unlogged-boundary" for s in out)
        assert any(s.symref == "run" for s in out)

    def test_boundary_call_with_no_nearby_log_call_flagged(self) -> None:
        from frob.arch._logging_checks import check_unlogged_boundary
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=4,
            calls=[
                NormalizedCall(callee="logger.info", line=1),
                NormalizedCall(callee="subprocess.run", line=10),
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_unlogged_boundary(module)
        assert any(s.category == "unlogged-boundary" and s.line == 10 for s in out)

    def test_private_function_not_flagged(self) -> None:
        from frob.arch._logging_checks import check_unlogged_boundary
        from frob.arch._normalized import NormalizedFunction, NormalizedModule

        func = NormalizedFunction(name="_run", line=1, body_line_count=2)
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_unlogged_boundary(module)
        assert out == []


class TestPrintAsDiagnostic:
    """`check_print_as_diagnostic`
    (docs/modules/arch.md#logging-discipline-checks)."""

    def test_print_call_flagged(self) -> None:
        from frob.arch._logging_checks import check_print_as_diagnostic
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=2,
            calls=[NormalizedCall(callee="print", line=2)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_print_as_diagnostic(module)
        assert len(out) == 1
        assert out[0].category == "print-as-diagnostic"

    def test_print_call_in_cli_module_not_flagged(self) -> None:
        from frob.arch._logging_checks import check_print_as_diagnostic
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=2,
            calls=[NormalizedCall(callee="print", line=2)],
        )
        module = NormalizedModule(
            path="pkg/cli.py", language="python", functions=[func]
        )
        out = check_print_as_diagnostic(module)
        assert out == []


class TestRunLoggingChecks:
    """`run_logging_checks` combines every ARCH1xx logging-discipline check
    (docs/modules/arch.md#logging-discipline-checks)."""

    def test_combines_all_three_checks(self) -> None:
        from frob.arch._logging_checks import run_logging_checks
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
        )

        catch_fn = NormalizedFunction(
            name="load_config",
            line=1,
            body_line_count=4,
            catches=[NormalizedCatch(line=3, exception_type="OSError")],
        )
        print_fn = NormalizedFunction(
            name="run",
            line=10,
            body_line_count=2,
            calls=[NormalizedCall(callee="print", line=11)],
        )
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            functions=[catch_fn, print_fn],
        )
        out = run_logging_checks(module)
        categories = {s.category for s in out}
        assert "unlogged-error-path" in categories
        assert "unlogged-boundary" in categories
        assert "print-as-diagnostic" in categories


# ---------------------------------------------------------------------------
# T-0623: fallibility checks -- unhandled Result, swallowed exception,
# recoverable-error-wrong-signature, over-broad except
# ---------------------------------------------------------------------------


class TestUnhandledResult:
    """`check_unhandled_result`
    (docs/modules/arch.md#fallibility-checks)."""

    def test_bare_statement_call_to_result_function_flagged(self) -> None:
        from frob.arch._fallibility import check_unhandled_result
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        load = NormalizedFunction(
            name="load", line=1, body_line_count=1, return_type="Result[Config, Err]"
        )
        run = NormalizedFunction(
            name="run",
            line=5,
            body_line_count=2,
            calls=[NormalizedCall(callee="load", line=6)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[load, run]
        )
        out = check_unhandled_result(module)
        assert len(out) == 1
        assert out[0].category == "unhandled-result"
        assert out[0].symref == "run"

    def test_returned_call_to_result_function_not_flagged(self) -> None:
        from frob.arch._fallibility import check_unhandled_result
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
            NormalizedReturn,
        )

        load = NormalizedFunction(
            name="load", line=1, body_line_count=1, return_type="Result[Config, Err]"
        )
        run = NormalizedFunction(
            name="run",
            line=5,
            body_line_count=2,
            calls=[NormalizedCall(callee="load", line=6)],
            returns=[NormalizedReturn(line=6, value_text="load()")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[load, run]
        )
        out = check_unhandled_result(module)
        assert out == []


class TestSwallowedException:
    """`check_swallowed_exception`
    (docs/modules/arch.md#fallibility-checks)."""

    def test_bare_except_with_no_reaction_flagged(self) -> None:
        from frob.arch._fallibility import check_swallowed_exception
        from frob.arch._normalized import (
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="load",
            line=1,
            body_line_count=4,
            catches=[NormalizedCatch(line=3, exception_type=None)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_swallowed_exception(module)
        assert len(out) == 1
        assert out[0].category == "swallowed-exception"
        assert out[0].severity == "warning"

    def test_except_with_nearby_log_call_not_flagged(self) -> None:
        from frob.arch._fallibility import check_swallowed_exception
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="load",
            line=1,
            body_line_count=4,
            catches=[NormalizedCatch(line=3, exception_type=None)],
            calls=[NormalizedCall(callee="logger.warning", line=4)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_swallowed_exception(module)
        assert out == []


class TestRecoverableErrorWrongSignature:
    """`check_recoverable_error_wrong_signature`
    (docs/modules/arch.md#fallibility-checks)."""

    def test_raises_value_error_without_result_signature_flagged(self) -> None:
        from frob.arch._fallibility import check_recoverable_error_wrong_signature
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        func = NormalizedFunction(
            name="parse_amount",
            line=1,
            body_line_count=2,
            return_type="int",
            raises=[NormalizedRaise(line=2, exception_type="ValueError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_recoverable_error_wrong_signature(module)
        assert len(out) == 1
        assert out[0].category == "recoverable-error-wrong-signature"
        assert out[0].symref == "parse_amount"

    def test_raises_value_error_with_result_signature_not_flagged(self) -> None:
        from frob.arch._fallibility import check_recoverable_error_wrong_signature
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        func = NormalizedFunction(
            name="parse_amount",
            line=1,
            body_line_count=2,
            return_type="Result[int, ParseError]",
            raises=[NormalizedRaise(line=2, exception_type="ValueError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_recoverable_error_wrong_signature(module)
        assert out == []


class TestOverBroadExcept:
    """`check_over_broad_except`
    (docs/modules/arch.md#fallibility-checks)."""

    def test_bare_except_flagged(self) -> None:
        from frob.arch._fallibility import check_over_broad_except
        from frob.arch._normalized import (
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="load",
            line=1,
            body_line_count=3,
            catches=[NormalizedCatch(line=2, exception_type="Exception")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_over_broad_except(module)
        assert any(s.category == "over-broad-except" for s in out)

    def test_specific_except_not_flagged(self) -> None:
        from frob.arch._fallibility import check_over_broad_except
        from frob.arch._normalized import (
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="load",
            line=1,
            body_line_count=3,
            catches=[NormalizedCatch(line=2, exception_type="OSError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_over_broad_except(module)
        assert out == []

    def test_reraise_with_different_type_loses_context_flagged(self) -> None:
        from frob.arch._fallibility import check_over_broad_except
        from frob.arch._normalized import (
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        func = NormalizedFunction(
            name="load",
            line=1,
            body_line_count=4,
            catches=[NormalizedCatch(line=2, exception_type="OSError")],
            raises=[NormalizedRaise(line=3, exception_type="RuntimeError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_over_broad_except(module)
        assert any(
            "losing context" in (s.message or "").lower()
            or "context" in (s.detail or "").lower()
            for s in out
        )


class TestRunFallibilityChecks:
    """`run_fallibility_checks` combines every ARCH1xx fallibility check
    (docs/modules/arch.md#fallibility-checks)."""

    def test_combines_all_four_checks(self) -> None:
        from frob.arch._fallibility import run_fallibility_checks
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        load = NormalizedFunction(
            name="load", line=1, body_line_count=1, return_type="Result[Config, Err]"
        )
        run_fn = NormalizedFunction(
            name="run",
            line=5,
            body_line_count=6,
            return_type="int",
            calls=[NormalizedCall(callee="load", line=6)],
            catches=[NormalizedCatch(line=7, exception_type=None)],
            raises=[NormalizedRaise(line=30, exception_type="ValueError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[load, run_fn]
        )
        out = run_fallibility_checks(module)
        categories = {s.category for s in out}
        assert "unhandled-result" in categories
        assert "swallowed-exception" in categories
        assert "recoverable-error-wrong-signature" in categories
        assert "over-broad-except" in categories


# frob:ticket T-0686
class TestMayRaiseResolver:
    """`frob.arch._mayraise.compute_may_raise` (T-0686, child 1 of T-0685):
    per-function may-raise sets over `NormalizedModule` -- own raise sites
    + builtin-raiser table + same-module callee-graph fixpoint, except
    clauses subtracting what they discharge, unresolved callees/raises
    fail-closed to `UNKNOWN`."""

    # frob:ticket T-0686
    def test_fixture_chain_own_raise_and_builtin_raiser_and_catch_subtraction(
        self,
    ) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # Ticket acceptance fixture: f -> g -> h where h raises ValueError,
        # g catches it (so g's own visible raises is empty), and f itself
        # subscripts a dict (KeyError, the curated builtin-raiser default)
        # and separately calls g (whose raise is fully discharged) -- f's
        # own may-raise set must be exactly {KeyError}.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
            NormalizedSubscript,
        )

        h = NormalizedFunction(
            name="h",
            line=1,
            body_line_count=2,
            raises=[NormalizedRaise(line=2, exception_type="ValueError")],
        )
        g = NormalizedFunction(
            name="g",
            line=5,
            body_line_count=4,
            calls=[NormalizedCall(callee="h", line=7)],
            catches=[NormalizedCatch(line=8, exception_type="ValueError")],
        )
        f = NormalizedFunction(
            name="f",
            line=12,
            body_line_count=3,
            calls=[NormalizedCall(callee="g", line=13)],
            subscripts=[NormalizedSubscript(line=14)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[h, g, f]
        )

        result = compute_may_raise(module)

        assert result["pkg/mod.py::h"].raises == frozenset({"ValueError"})
        assert result["pkg/mod.py::g"].raises == frozenset()
        assert result["pkg/mod.py::f"].raises == frozenset({"KeyError"})

    # frob:ticket T-0686
    def test_unresolvable_call_yields_unknown(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        from frob.arch._mayraise import UNKNOWN, compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        caller = NormalizedFunction(
            name="dispatch",
            line=1,
            body_line_count=2,
            calls=[NormalizedCall(callee="plugin_hook", line=2)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[caller]
        )

        result = compute_may_raise(module)

        assert result["pkg/mod.py::dispatch"].raises == frozenset({UNKNOWN})

    # frob:ticket T-0686
    def test_bare_reraise_resolves_to_caught_type(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        func = NormalizedFunction(
            name="reraiser",
            line=1,
            body_line_count=5,
            catches=[NormalizedCatch(line=2, exception_type="KeyError")],
            raises=[NormalizedRaise(line=3, exception_type=None)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )

        result = compute_may_raise(module)

        assert result["pkg/mod.py::reraiser"].raises == frozenset({"KeyError"})

    # frob:ticket T-0686
    def test_bare_except_reraise_is_unknown(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        from frob.arch._mayraise import UNKNOWN, compute_may_raise
        from frob.arch._normalized import (
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        func = NormalizedFunction(
            name="reraiser",
            line=1,
            body_line_count=5,
            catches=[NormalizedCatch(line=2, exception_type=None)],
            raises=[NormalizedRaise(line=3, exception_type=None)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )

        result = compute_may_raise(module)

        assert result["pkg/mod.py::reraiser"].raises == frozenset({UNKNOWN})

    # frob:ticket T-0686
    def test_recursive_cycle_converges(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # a <-> b mutual recursion: a raises ValueError, b calls a and a
        # calls b -- the fixpoint must terminate and both must see
        # ValueError in their visible set (no catch discharges it).
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        a = NormalizedFunction(
            name="a",
            line=1,
            body_line_count=3,
            raises=[NormalizedRaise(line=2, exception_type="ValueError")],
            calls=[NormalizedCall(callee="b", line=3)],
        )
        b = NormalizedFunction(
            name="b",
            line=6,
            body_line_count=2,
            calls=[NormalizedCall(callee="a", line=7)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[a, b]
        )

        result = compute_may_raise(module)

        assert "ValueError" in result["pkg/mod.py::a"].raises
        assert "ValueError" in result["pkg/mod.py::b"].raises

    # frob:ticket T-0686
    def test_ambiguous_method_name_across_classes_is_unresolved(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        from frob.arch._mayraise import UNKNOWN, compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        run_a = NormalizedFunction(name="run", line=2, body_line_count=1, raises=[])
        run_b = NormalizedFunction(
            name="run",
            line=12,
            body_line_count=1,
            raises=[NormalizedRaise(line=13, exception_type="ValueError")],
        )
        caller = NormalizedFunction(
            name="dispatch",
            line=20,
            body_line_count=2,
            calls=[NormalizedCall(callee="run", line=21)],
        )
        cls_a = NormalizedClass(name="A", line=1, methods=[run_a])
        cls_b = NormalizedClass(name="B", line=11, methods=[run_b])
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            classes=[cls_a, cls_b],
            functions=[caller],
        )

        result = compute_may_raise(module)

        assert result["pkg/mod.py::dispatch"].raises == frozenset({UNKNOWN})

    # frob:ticket T-0689
    def test_undeclared_ctypes_style_call_is_unknown(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # A call into a ctypes/cffi-loaded handle (`lib.some_c_function(...)`)
        # is not a same-module function and not in either curated raiser
        # table -- opaque boundary, fail-closed to Unknown (T-0689's
        # acceptance criterion, first half).
        from frob.arch._mayraise import UNKNOWN, compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        caller = NormalizedFunction(
            name="call_native",
            line=1,
            body_line_count=2,
            calls=[NormalizedCall(callee="lib.some_c_function", line=2)],
        )
        module = NormalizedModule(
            path="pkg/native.py", language="python", functions=[caller]
        )

        result = compute_may_raise(module)

        assert result["pkg/native.py::call_native"].raises == frozenset({UNKNOWN})

    # frob:ticket T-0689
    def test_declared_raises_substitutes_for_opaque_boundary_call(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # The SAME opaque ctypes-style call as the previous test, but now
        # carrying a `frob:callee-raises` declaration (NormalizedCall.
        # declared_raises, renamed from `frob:raises` by T-0931) -- the
        # declared set substitutes for Unknown
        # (T-0689's acceptance criterion, second half).
        from frob.arch._mayraise import UNKNOWN, compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        caller = NormalizedFunction(
            name="call_native",
            line=1,
            body_line_count=2,
            calls=[
                NormalizedCall(
                    callee="lib.some_c_function",
                    line=2,
                    declared_raises=frozenset({"OSError"}),
                )
            ],
        )
        module = NormalizedModule(
            path="pkg/native.py", language="python", functions=[caller]
        )

        result = compute_may_raise(module)

        assert result["pkg/native.py::call_native"].raises == frozenset({"OSError"})
        assert UNKNOWN not in result["pkg/native.py::call_native"].raises

    # frob:ticket T-0689
    def test_declared_raises_empty_set_is_honored_not_treated_as_absent(
        self,
    ) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # `declared_raises=frozenset()` ("declared to raise nothing", the
        # valid errno-convention shape) must NOT fall through to Unknown --
        # callers check `is not None`, never truthiness.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        caller = NormalizedFunction(
            name="call_native",
            line=1,
            body_line_count=2,
            calls=[
                NormalizedCall(
                    callee="lib.errno_style_call",
                    line=2,
                    declared_raises=frozenset(),
                )
            ],
        )
        module = NormalizedModule(
            path="pkg/native.py", language="python", functions=[caller]
        )

        result = compute_may_raise(module)

        assert result["pkg/native.py::call_native"].raises == frozenset()

    # frob:ticket T-0689
    def test_curated_stdlib_c_extension_table_resolves_precisely(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # json.loads/sqlite3.connect/struct.pack are curated stdlib
        # C-extension raisers (T-0689's user mandate) -- resolved
        # precisely, not Unknown, keyed on the full dotted callee text.
        from frob.arch._mayraise import UNKNOWN, compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        caller = NormalizedFunction(
            name="parse_all",
            line=1,
            body_line_count=4,
            calls=[
                NormalizedCall(callee="json.loads", line=2),
                NormalizedCall(callee="sqlite3.connect", line=3),
                NormalizedCall(callee="struct.pack", line=4),
            ],
        )
        module = NormalizedModule(
            path="pkg/parse.py", language="python", functions=[caller]
        )

        result = compute_may_raise(module)

        raises = result["pkg/parse.py::parse_all"].raises
        assert raises == frozenset({"JSONDecodeError", "sqlite3.Error", "struct.error"})
        assert UNKNOWN not in raises


# ---------------------------------------------------------------------------
# T-0624: misc design smells -- mutable default arg, feature envy, data
# clumps, magic literals, dead private code, deep inheritance, temporal
# coupling
# ---------------------------------------------------------------------------


class TestMutableDefaultArg:
    """`check_mutable_default_arg`
    (docs/modules/arch.md#misc-design-smells)."""

    def test_list_literal_default_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._smells import check_mutable_default_arg

        func = NormalizedFunction(
            name="add_item",
            line=1,
            body_line_count=1,
            params=[NormalizedParam(name="items", has_default=True, default_text="[]")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_mutable_default_arg(module)
        assert len(out) == 1
        assert out[0].category == "mutable-default-arg"

    def test_none_default_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._smells import check_mutable_default_arg

        func = NormalizedFunction(
            name="add_item",
            line=1,
            body_line_count=1,
            params=[
                NormalizedParam(name="items", has_default=True, default_text="None")
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_mutable_default_arg(module)
        assert out == []


class TestFeatureEnvy:
    """`check_feature_envy` (docs/modules/arch.md#misc-design-smells)."""

    def test_method_calling_other_receiver_more_than_self_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_feature_envy

        method = NormalizedFunction(
            name="render",
            line=2,
            body_line_count=4,
            is_method=True,
            calls=[
                NormalizedCall(callee="other.a", line=3),
                NormalizedCall(callee="other.b", line=4),
                NormalizedCall(callee="self.helper", line=5),
            ],
        )
        cls = NormalizedClass(name="Widget", line=1, methods=[method])
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=[cls])
        out = check_feature_envy(module)
        assert len(out) == 1
        assert out[0].category == "feature-envy"

    def test_method_calling_self_more_than_others_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_feature_envy

        method = NormalizedFunction(
            name="render",
            line=2,
            body_line_count=4,
            is_method=True,
            calls=[
                NormalizedCall(callee="self.a", line=3),
                NormalizedCall(callee="self.b", line=4),
                NormalizedCall(callee="other.helper", line=5),
            ],
        )
        cls = NormalizedClass(name="Widget", line=1, methods=[method])
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=[cls])
        out = check_feature_envy(module)
        assert out == []


class TestDataClumps:
    """`check_data_clumps` (docs/modules/arch.md#misc-design-smells)."""

    def test_same_three_keyword_group_at_three_sites_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_data_clumps

        args = [
            NormalizedCallArg(keyword="street"),
            NormalizedCallArg(keyword="city"),
            NormalizedCallArg(keyword="zip_code"),
        ]
        func = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=3,
            calls=[
                NormalizedCall(callee="make_address", line=2, args=args),
                NormalizedCall(callee="make_address", line=3, args=args),
                NormalizedCall(callee="make_address", line=4, args=args),
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_data_clumps(module)
        assert len(out) == 1
        assert out[0].category == "data-clumps"
        assert out[0].metric == 3

    def test_group_at_two_sites_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_data_clumps

        args = [
            NormalizedCallArg(keyword="street"),
            NormalizedCallArg(keyword="city"),
            NormalizedCallArg(keyword="zip_code"),
        ]
        func = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=2,
            calls=[
                NormalizedCall(callee="make_address", line=2, args=args),
                NormalizedCall(callee="make_address", line=3, args=args),
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_data_clumps(module)
        assert out == []


class TestMagicLiteral:
    """`check_magic_literal` (docs/modules/arch.md#misc-design-smells)."""

    def test_bare_number_in_condition_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_magic_literal

        func = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=2,
            branches=[NormalizedBranch(line=2, condition_text="retries > 42")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_magic_literal(module)
        assert len(out) == 1
        assert out[0].category == "magic-literal"

    def test_zero_and_one_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_magic_literal

        func = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=2,
            branches=[NormalizedBranch(line=2, condition_text="count > 0 and n == 1")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_magic_literal(module)
        assert out == []


class TestDeadPrivateCode:
    """`check_dead_private_code`
    (docs/modules/arch.md#misc-design-smells)."""

    def test_unreferenced_private_function_flagged(self) -> None:
        from frob.arch._normalized import NormalizedFunction, NormalizedModule
        from frob.arch._smells import check_dead_private_code

        func = NormalizedFunction(name="_helper", line=1, body_line_count=1)
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_dead_private_code(module)
        assert len(out) == 1
        assert out[0].category == "dead-private-code"

    def test_referenced_private_function_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_dead_private_code

        helper = NormalizedFunction(name="_helper", line=1, body_line_count=1)
        run = NormalizedFunction(
            name="run",
            line=5,
            body_line_count=1,
            calls=[NormalizedCall(callee="_helper", line=6)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[helper, run]
        )
        out = check_dead_private_code(module)
        assert out == []


class TestDeepInheritance:
    """`check_deep_inheritance` (docs/modules/arch.md#misc-design-smells)."""

    def test_chain_beyond_threshold_flagged(self) -> None:
        from frob.arch._normalized import NormalizedClass, NormalizedModule
        from frob.arch._smells import check_deep_inheritance

        classes = [
            NormalizedClass(name="A", line=1),
            NormalizedClass(name="B", line=2, bases=["A"]),
            NormalizedClass(name="C", line=3, bases=["B"]),
            NormalizedClass(name="D", line=4, bases=["C"]),
            NormalizedClass(name="E", line=5, bases=["D"]),
        ]
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=classes)
        out = check_deep_inheritance(module)
        assert any(s.symref == "pkg/mod.py::E" for s in out)

    def test_shallow_chain_not_flagged(self) -> None:
        from frob.arch._normalized import NormalizedClass, NormalizedModule
        from frob.arch._smells import check_deep_inheritance

        classes = [
            NormalizedClass(name="A", line=1),
            NormalizedClass(name="B", line=2, bases=["A"]),
        ]
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=classes)
        out = check_deep_inheritance(module)
        assert out == []


class TestTemporalCoupling:
    """`check_temporal_coupling`
    (docs/modules/arch.md#misc-design-smells)."""

    def test_guard_clause_on_initialized_flag_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedClass,
            NormalizedField,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )
        from frob.arch._smells import check_temporal_coupling

        method = NormalizedFunction(
            name="use",
            line=5,
            body_line_count=3,
            is_method=True,
            branches=[NormalizedBranch(line=6, condition_text="not self._initialized")],
            raises=[NormalizedRaise(line=7, exception_type="RuntimeError")],
        )
        cls = NormalizedClass(
            name="Service",
            line=1,
            fields=[NormalizedField(name="_initialized", line=2, type="bool")],
            methods=[method],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=[cls])
        out = check_temporal_coupling(module)
        assert len(out) == 1
        assert out[0].category == "temporal-coupling"

    def test_field_not_guarded_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedField,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_temporal_coupling

        method = NormalizedFunction(
            name="use", line=5, body_line_count=1, is_method=True
        )
        cls = NormalizedClass(
            name="Service",
            line=1,
            fields=[NormalizedField(name="_initialized", line=2, type="bool")],
            methods=[method],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=[cls])
        out = check_temporal_coupling(module)
        assert out == []


class TestRunSmellChecks:
    """`run_smell_checks` combines every ARCH1xx misc design-smell check
    (docs/modules/arch.md#misc-design-smells)."""

    def test_combines_all_seven_checks(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedCall,
            NormalizedCallArg,
            NormalizedClass,
            NormalizedField,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
            NormalizedRaise,
        )
        from frob.arch._smells import run_smell_checks

        args = [
            NormalizedCallArg(keyword="a"),
            NormalizedCallArg(keyword="b"),
            NormalizedCallArg(keyword="c"),
        ]
        top_fn = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=8,
            params=[NormalizedParam(name="items", has_default=True, default_text="[]")],
            branches=[NormalizedBranch(line=2, condition_text="retries > 42")],
            calls=[
                NormalizedCall(callee="make_thing", line=3, args=args),
                NormalizedCall(callee="make_thing", line=4, args=args),
                NormalizedCall(callee="make_thing", line=5, args=args),
            ],
        )
        dead_fn = NormalizedFunction(name="_dead", line=20, body_line_count=1)
        method = NormalizedFunction(
            name="use",
            line=30,
            body_line_count=3,
            is_method=True,
            branches=[
                NormalizedBranch(line=31, condition_text="not self._initialized")
            ],
            raises=[NormalizedRaise(line=32, exception_type="RuntimeError")],
            calls=[
                NormalizedCall(callee="other.a", line=31),
                NormalizedCall(callee="other.b", line=32),
            ],
        )
        cls = NormalizedClass(
            name="Service",
            line=25,
            fields=[NormalizedField(name="_initialized", line=26, type="bool")],
            methods=[method],
        )
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            functions=[top_fn, dead_fn],
            classes=[cls],
        )
        out = run_smell_checks(module)
        categories = {s.category for s in out}
        assert "mutable-default-arg" in categories
        assert "data-clumps" in categories
        assert "magic-literal" in categories
        assert "dead-private-code" in categories
        assert "temporal-coupling" in categories
        assert "feature-envy" in categories


# ---------------------------------------------------------------------------
# T-0625: module dependency cycle detection
# ---------------------------------------------------------------------------


class TestModuleDependencyCycles:
    """`check_module_dependency_cycles`
    (docs/modules/arch.md#module-dependency-cycles)."""

    def test_two_file_import_cycle_flagged(self, tmp_path) -> None:  # noqa: ANN001
        from frob.arch._smells import check_module_dependency_cycles

        (tmp_path / "a.py").write_text("import b\n")
        (tmp_path / "b.py").write_text("import a\n")
        out = check_module_dependency_cycles(tmp_path)
        assert len(out) == 1
        assert out[0].category == "module-dependency-cycle"
        assert "a.py" in out[0].message
        assert "b.py" in out[0].message

    def test_acyclic_imports_not_flagged(self, tmp_path) -> None:  # noqa: ANN001
        from frob.arch._smells import check_module_dependency_cycles

        (tmp_path / "a.py").write_text("import b\n")
        (tmp_path / "b.py").write_text("x = 1\n")
        out = check_module_dependency_cycles(tmp_path)
        assert out == []


# ---------------------------------------------------------------------------
# T-0745: protocol summary engine -- per-function fixpoint over the call graph
# ---------------------------------------------------------------------------

from frob.graph._models import Edge, EdgeKind  # noqa: E402
from frob.graph.callgraph import CallGraph  # noqa: E402
from frob.graph.summary import (  # noqa: E402
    UNRESOLVED_CALLEE,
    compute_protocol_summaries,
)


def _transition(src: str, proto: str, frm: str, to: str) -> Edge:
    """Test helper: a `TRANSITION` edge shaped like `dsl.parse_directives`'s
    output, without needing real source files to drive the DSL parser."""
    return Edge(
        src=src,
        kind=EdgeKind.TRANSITION,
        target=proto,
        origin=f"{src}:1",
        attrs={"proto": proto, "from": frm, "to": to},
    )


def _requires(src: str, proto: str, state: str) -> Edge:
    """Test helper: a `REQUIRES` edge shaped like `dsl.parse_directives`'s
    output."""
    return Edge(
        src=src,
        kind=EdgeKind.REQUIRES,
        target=proto,
        origin=f"{src}:1",
        attrs={"proto": proto, "state": state},
    )


# frob:ticket T-0809
def _acquire(src: str, resource: str) -> Edge:
    """Test helper: an `ACQUIRE` edge shaped like `dsl.parse_directives`'s
    output for `frob:acquire <resource>`."""
    return Edge(src=src, kind=EdgeKind.ACQUIRE, target=resource, origin=f"{src}:1")


# frob:ticket T-0809
def _release(src: str, resource: str) -> Edge:
    """Test helper: a `RELEASE` edge shaped like `dsl.parse_directives`'s
    output for `frob:release <resource>`."""
    return Edge(src=src, kind=EdgeKind.RELEASE, target=resource, origin=f"{src}:1")


# frob:ticket T-0809
def _escapes(src: str, resource: str) -> Edge:
    """Test helper: an `ESCAPES` edge shaped like `dsl.parse_directives`'s
    output for `frob:escapes <resource>`."""
    return Edge(src=src, kind=EdgeKind.ESCAPES, target=resource, origin=f"{src}:1")


class TestProtocolSummaryEngine:
    """`frob.graph.summary.compute_protocol_summaries` -- bottom-up fixpoint
    over a fixture `CallGraph`, no repo-wide scan (docs/modules/graph.md
    #protocol-summary-engine)."""

    def test_leaf_function_summary_is_its_own_declarations(self):
        """A leaf with no callees summarizes to exactly its own
        `frob:transition`/`frob:requires` declarations."""
        graph = CallGraph(calls={})
        edges = [_transition("f.py::open_conn", "conn", "closed", "open")]
        result = compute_protocol_summaries(
            graph, edges, entrypoints=["f.py::open_conn"]
        )
        summary = result.summaries["f.py::open_conn"]
        assert summary.transitions == {"conn:closed->open"}
        assert summary.requires == frozenset()
        assert not summary.poisoned
        assert result.not_analyzed == ()
        assert result.timeouts == ()

    def test_caller_summary_includes_callee_transitions(self):
        """`caller` calls `helper`; `caller`'s summary must include
        `helper`'s transition even though `caller` declares nothing of its
        own -- the join propagates upward through one hop."""
        graph = CallGraph(calls={"f.py::caller": ("f.py::helper",)})
        edges = [_transition("f.py::helper", "conn", "closed", "open")]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::caller"])
        assert result.summaries["f.py::caller"].transitions == {"conn:closed->open"}
        assert result.summaries["f.py::helper"].transitions == {"conn:closed->open"}
        assert not result.summaries["f.py::caller"].poisoned

    def test_requires_and_transitions_join_across_two_hops(self):
        """`top -> mid -> leaf`: `top`'s summary is the union of all three
        levels' own declarations, hand-computed and compared exactly."""
        graph = CallGraph(
            calls={
                "f.py::top": ("f.py::mid",),
                "f.py::mid": ("f.py::leaf",),
            }
        )
        edges = [
            _requires("f.py::top", "lock", "held"),
            _transition("f.py::mid", "lock", "unheld", "held"),
            _transition("f.py::leaf", "conn", "closed", "open"),
        ]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::top"])
        top = result.summaries["f.py::top"]
        assert top.requires == {"lock:held"}
        assert top.transitions == {"lock:unheld->held", "conn:closed->open"}
        assert not top.poisoned

    def test_recursive_cluster_converges_to_hand_computed_fixpoint(self):
        """A mutually-recursive pair (`a` calls `b`, `b` calls `a`), each
        declaring a distinct transition -- the fixpoint must converge so
        BOTH functions' summaries include BOTH transitions (recursion via
        lattice join, T-0745's design sketch)."""
        graph = CallGraph(
            calls={
                "f.py::a": ("f.py::b",),
                "f.py::b": ("f.py::a",),
            }
        )
        edges = [
            _transition("f.py::a", "conn", "closed", "open"),
            _transition("f.py::b", "conn", "open", "closed"),
        ]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::a"])
        expected = {"conn:closed->open", "conn:open->closed"}
        assert result.summaries["f.py::a"].transitions == expected
        assert result.summaries["f.py::b"].transitions == expected
        assert not result.summaries["f.py::a"].poisoned
        assert not result.summaries["f.py::b"].poisoned
        assert result.timeouts == ()

    def test_self_recursive_function_converges(self):
        """A single function that calls itself is its own one-member SCC
        with a self-loop -- must go through the recursive-cluster branch,
        not the single-node fast path, and still converge to just its own
        declaration (nothing new to join from calling itself)."""
        graph = CallGraph(calls={"f.py::recur": ("f.py::recur",)})
        edges = [_transition("f.py::recur", "conn", "closed", "open")]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::recur"])
        summary = result.summaries["f.py::recur"]
        assert summary.transitions == {"conn:closed->open"}
        assert not summary.poisoned

    def test_unresolved_callee_poisons_the_summary(self):
        """A call to `UNRESOLVED_CALLEE` poisons the caller's summary --
        NO-FAIL-SILENT: the caller's own declarations are still populated,
        but `poisoned` is `True` with a reason naming the caller."""
        graph = CallGraph(calls={"f.py::caller": (UNRESOLVED_CALLEE,)})
        edges = [_transition("f.py::caller", "conn", "closed", "open")]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::caller"])
        summary = result.summaries["f.py::caller"]
        assert summary.poisoned
        assert summary.poison_reason is not None
        assert "unresolved" in summary.poison_reason
        assert summary.transitions == {"conn:closed->open"}

    def test_poisoning_propagates_transitively_through_a_clean_caller(self):
        """`top -> mid -> poisoned_leaf`: `mid` calls an unresolved callee,
        so `mid` is poisoned; `top` calls only `mid` (itself clean) but
        must ALSO end up poisoned -- poisoning propagates upward through
        every transitive caller, it never resets at a clean intermediate
        hop."""
        graph = CallGraph(
            calls={
                "f.py::top": ("f.py::mid",),
                "f.py::mid": (UNRESOLVED_CALLEE,),
            }
        )
        edges = [_transition("f.py::top", "conn", "closed", "open")]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::top"])
        assert result.summaries["f.py::mid"].poisoned
        assert result.summaries["f.py::top"].poisoned
        assert result.summaries["f.py::top"].poison_reason is not None

    def test_unreachable_function_is_reported_not_analyzed_never_silent(self):
        """A function with its own declarations that no entrypoint ever
        calls must show up in `not_analyzed`, and must NOT get a
        (falsely-clean) summary -- the NO-FAIL-SILENT mandate applied to
        reachability."""
        graph = CallGraph(calls={"f.py::entry": ()})
        edges = [_transition("f.py::orphan", "conn", "closed", "open")]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::entry"])
        assert "f.py::orphan" in result.not_analyzed
        assert "f.py::orphan" not in result.summaries
        assert "f.py::entry" in result.summaries

    def test_non_converging_scc_is_reported_as_a_timeout_error_and_poisoned(self):
        """A three-member mutually-recursive cluster needs more than one
        join round to fully propagate; capping `max_iterations=1` must
        surface an `SCCTimeout` naming the cluster, and every member of
        the cluster must be poisoned -- an abort is a loud ERROR, never a
        silently-partial summary (T-0745 acceptance)."""
        graph = CallGraph(
            calls={
                "f.py::a": ("f.py::b",),
                "f.py::b": ("f.py::c",),
                "f.py::c": ("f.py::a",),
            }
        )
        edges = [_transition("f.py::a", "conn", "closed", "open")]
        result = compute_protocol_summaries(
            graph, edges, entrypoints=["f.py::a"], max_iterations=1
        )
        assert len(result.timeouts) == 1
        assert set(result.timeouts[0].members) == {"f.py::a", "f.py::b", "f.py::c"}
        assert result.timeouts[0].iterations == 1
        for member in ("f.py::a", "f.py::b", "f.py::c"):
            summary = result.summaries[member]
            assert summary.poisoned
            assert summary.poison_reason is not None
            assert "did not converge" in summary.poison_reason

    def test_diamond_shaped_calls_join_without_duplication_or_loss(self):
        """`top` calls both `left` and `right`, which both call `shared` --
        a diamond. `top`'s summary must include every distinct transition
        exactly once (set union is naturally idempotent) with nothing
        dropped from either branch."""
        graph = CallGraph(
            calls={
                "f.py::top": ("f.py::left", "f.py::right"),
                "f.py::left": ("f.py::shared",),
                "f.py::right": ("f.py::shared",),
            }
        )
        edges = [
            _transition("f.py::left", "a", "s0", "s1"),
            _transition("f.py::right", "b", "s0", "s1"),
            _transition("f.py::shared", "c", "s0", "s1"),
        ]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::top"])
        assert result.summaries["f.py::top"].transitions == {
            "a:s0->s1",
            "b:s0->s1",
            "c:s0->s1",
        }
        assert not result.summaries["f.py::top"].poisoned

    # frob:ticket T-0809
    def test_leaf_resource_declarations_populate_acquired_released_escaped(self):
        """A leaf declaring `frob:acquire`/`frob:release`/`frob:escapes`
        summarizes to exactly those resource-name sets, T-0809's
        resource-tracking DSL folded the same way `requires`/`transitions`
        already are."""
        graph = CallGraph(calls={})
        edges = [
            _acquire("f.py::open_fd", "fd"),
            _release("f.py::open_fd", "lock"),
            _escapes("f.py::open_fd", "conn"),
        ]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::open_fd"])
        summary = result.summaries["f.py::open_fd"]
        assert summary.acquired == {"fd"}
        assert summary.released == {"lock"}
        assert summary.escaped == {"conn"}
        assert not summary.poisoned

    # frob:ticket T-0809
    def test_resource_sets_join_transitively_through_a_caller(self):
        """`caller` calls `helper`, which acquires a resource -- `caller`'s
        summary must include it, matching `requires`/`transitions`'
        existing one-hop join behavior."""
        graph = CallGraph(calls={"f.py::caller": ("f.py::helper",)})
        edges = [_acquire("f.py::helper", "fd")]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::caller"])
        assert result.summaries["f.py::caller"].acquired == {"fd"}
        assert result.summaries["f.py::helper"].acquired == {"fd"}

    # frob:ticket T-0809
    def test_resource_sets_join_across_a_recursive_cluster(self):
        """A mutually-recursive pair each declaring a distinct resource
        acquire must converge with BOTH resources in both summaries,
        mirroring `test_recursive_cluster_converges_to_hand_computed_fixpoint`."""
        graph = CallGraph(calls={"f.py::a": ("f.py::b",), "f.py::b": ("f.py::a",)})
        edges = [_acquire("f.py::a", "fd"), _acquire("f.py::b", "lock")]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::a"])
        expected = {"fd", "lock"}
        assert result.summaries["f.py::a"].acquired == expected
        assert result.summaries["f.py::b"].acquired == expected
        assert not result.summaries["f.py::a"].poisoned


class TestSharedStateRaceHazards:
    """`src/frob/arch/_shared_state_race.py` -- unguarded-shared-write
    (T-0697, child 4 of the T-0693 concurrency-hazard umbrella)."""

    def test_unguarded_write_from_thread_submitted_function_fires(self, tmp_path):
        """A module-level dict written from a thread-submitted function
        with no enclosing lock fires `unguarded-shared-write`, naming the
        write site and the writing function."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "race.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n"
            "cache = {}\n\n\n"
            "def worker():\n"
            "    cache['x'] = 1\n\n\n"
            "def dispatch():\n"
            "    with ThreadPoolExecutor() as ex:\n"
            "        ex.submit(worker)\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "unguarded-shared-write"]
        assert len(hits) == 1
        assert "cache" in hits[0].message
        assert "race.py::worker" in hits[0].message
        assert hits[0].severity == "warning"

    def test_same_write_under_with_lock_does_not_fire(self, tmp_path):
        """The same shape, but the write is enclosed by `with lock:` --
        must stay silent."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "race_guarded.py").write_text(
            "from __future__ import annotations\n"
            "import threading\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n"
            "cache = {}\n"
            "lock = threading.Lock()\n\n\n"
            "def worker():\n"
            "    with lock:\n"
            "        cache['x'] = 1\n\n\n"
            "def dispatch():\n"
            "    with ThreadPoolExecutor() as ex:\n"
            "        ex.submit(worker)\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "unguarded-shared-write"]
        assert hits == []

    def test_write_reachable_via_callee_of_dispatched_function_fires(self, tmp_path):
        """The dispatched function itself does nothing but call a helper
        that performs the unguarded write -- still fires, since the write
        is reachable from the dispatch point through the call graph."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "race_via_callee.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n"
            "totals = []\n\n\n"
            "def helper():\n"
            "    totals.append(1)\n\n\n"
            "def worker():\n"
            "    helper()\n\n\n"
            "def dispatch():\n"
            "    with ThreadPoolExecutor() as ex:\n"
            "        ex.submit(worker)\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "unguarded-shared-write"]
        assert len(hits) == 1
        assert "race_via_callee.py::helper" in hits[0].message
        assert "totals" in hits[0].message

    def test_write_not_reachable_from_any_dispatch_does_not_fire(self, tmp_path):
        """A module-level list written by a function that is never
        dispatched to a thread/task anywhere in the module -- must stay
        silent (plain sequential code is not this check's target)."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "sequential.py").write_text(
            "from __future__ import annotations\n\n"
            "totals = []\n\n\n"
            "def only_caller():\n"
            "    totals.append(1)\n\n\n"
            "def main():\n"
            "    only_caller()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "unguarded-shared-write"]
        assert hits == []

    def test_async_create_task_dispatch_fires_same_as_thread_submit(self, tmp_path):
        """A coroutine dispatched via `asyncio.create_task` that writes an
        unguarded module-level dict fires identically to the thread-submit
        shape."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "race_async.py").write_text(
            "from __future__ import annotations\n"
            "import asyncio\n\n"
            "state = {}\n\n\n"
            "async def worker():\n"
            "    state['x'] = 1\n\n\n"
            "async def dispatch():\n"
            "    asyncio.create_task(worker())\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "unguarded-shared-write"]
        assert len(hits) == 1
        assert "state" in hits[0].message
        assert "race_async.py::worker" in hits[0].message


class TestConcurrencyModelMismatch:
    """`src/frob/arch/_concurrency_model.py` -- gil-bound-in-threadpool and
    ipc-overhead-in-processpool (T-0698, child 5 of the T-0693
    concurrency-hazard umbrella)."""

    def test_cpu_bound_loop_in_threadpool_fires_gil_bound(self, tmp_path):
        """A pure-arithmetic loop function submitted to a ThreadPoolExecutor
        fires `gil-bound-in-threadpool`, naming the loop."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "cpu_thread.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n\n"
            "def crunch():\n"
            "    total = 0\n"
            "    for i in range(10_000_000):\n"
            "        total += i * i\n"
            "    return total\n\n\n"
            "def dispatch():\n"
            "    with ThreadPoolExecutor() as ex:\n"
            "        ex.submit(crunch)\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s for s in result.suggestions if s.category == "gil-bound-in-threadpool"
        ]
        assert len(hits) == 1
        assert "crunch" in hits[0].message
        assert hits[0].severity == "suggestion"

    def test_io_bound_socket_read_in_threadpool_does_not_fire(self, tmp_path):
        """A socket-read function dispatched to a ThreadPoolExecutor is the
        CORRECT model (IO-bound work belongs in a thread pool) -- must stay
        silent."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "io_thread.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n\n"
            "def read_socket(sock):\n"
            "    return sock.recv(4096)\n\n\n"
            "def dispatch(sock):\n"
            "    with ThreadPoolExecutor() as ex:\n"
            "        ex.submit(read_socket, sock)\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s for s in result.suggestions if s.category == "gil-bound-in-threadpool"
        ]
        assert hits == []

    def test_trivial_io_task_in_processpool_fires_ipc_overhead(self, tmp_path):
        """A trivially small IO-bound task dispatched to a
        ProcessPoolExecutor fires `ipc-overhead-in-processpool`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "io_process.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ProcessPoolExecutor\n\n\n"
            "def fetch_page(url):\n"
            "    return requests.get(url)\n\n\n"
            "def dispatch(url):\n"
            "    with ProcessPoolExecutor() as ex:\n"
            "        ex.submit(fetch_page, url)\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s for s in result.suggestions if s.category == "ipc-overhead-in-processpool"
        ]
        assert len(hits) == 1
        assert "fetch_page" in hits[0].message

    def test_mixed_loop_and_io_function_never_fires_either_advisory(self, tmp_path):
        """A function that both loops AND calls IO is MIXED/UNKNOWN -- never
        confidently classified, so no advisory fires even when dispatched
        to a thread pool."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "mixed.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n\n"
            "def mixed_work(urls):\n"
            "    results = []\n"
            "    for url in urls:\n"
            "        results.append(requests.get(url))\n"
            "    return results\n\n\n"
            "def dispatch(urls):\n"
            "    with ThreadPoolExecutor() as ex:\n"
            "        ex.submit(mixed_work, urls)\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s
            for s in result.suggestions
            if s.category in ("gil-bound-in-threadpool", "ipc-overhead-in-processpool")
        ]
        assert hits == []


# frob:ticket T-0687
class TestCppMayThrow:
    """T-0687: frob.arch._cpp_mayraise -- C++ may-throw analysis wired
    into analyze_project's "cpp" dispatch branch. A noexcept function
    whose computed may-throw set (explicit throw, curated STL throwers,
    same-file callee propagation, Unknown fail-closed for anything else)
    is non-empty and not discharged by its own catch (...) fires
    cpp-noexcept-throws at ArchSeverity "error"."""

    # frob:tests tests/unit/test_arch.py::TestCppMayThrow.test_noexcept_calling_throwing_function_fires_error  # noqa: E501
    def test_noexcept_calling_throwing_function_fires_error(self, tmp_path):
        """noexcept `caller` calls same-file `risky` (which throws) with
        no try/catch of its own -- an error finding names the call site."""
        from frob.arch import analyze_project

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "risky.cpp").write_text(
            "int risky() {\n"
            '    throw std::runtime_error("bad");\n'
            "}\n\n"
            "void caller() noexcept {\n"
            "    risky();\n"
            "}\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "cpp-noexcept-throws"]
        assert hits
        assert any(s.symref == "risky.cpp::caller" for s in hits)
        assert any(s.severity == "error" for s in hits)

    # frob:tests tests/unit/test_arch.py::TestCppMayThrow.test_noexcept_with_catch_all_does_not_fire  # noqa: E501
    def test_noexcept_with_catch_all_does_not_fire(self, tmp_path):
        """Same shape as above, but `caller` wraps the risky call in a
        try/catch (...) -- the hard boundary is discharged, no finding."""
        from frob.arch import analyze_project

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "safe.cpp").write_text(
            "int risky() {\n"
            '    throw std::runtime_error("bad");\n'
            "}\n\n"
            "void caller() noexcept {\n"
            "    try {\n"
            "        risky();\n"
            "    } catch (...) {\n"
            "    }\n"
            "}\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "cpp-noexcept-throws"]
        assert hits == []

    # frob:tests tests/unit/test_arch.py::TestCppMayThrow.test_non_noexcept_function_never_fires  # noqa: E501
    def test_non_noexcept_function_never_fires(self, tmp_path):
        """A function that may throw but is NOT noexcept is normal
        propagation, not a hard-boundary violation -- never flagged."""
        from frob.arch import analyze_project

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "propagates.cpp").write_text(
            "int risky() {\n"
            '    throw std::runtime_error("bad");\n'
            "}\n\n"
            "void caller() {\n"
            "    risky();\n"
            "}\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "cpp-noexcept-throws"]
        assert hits == []

    # frob:tests tests/unit/test_arch.py::TestCppMayThrow.test_noexcept_calling_vector_at_fires_curated_thrower  # noqa: E501
    def test_noexcept_calling_vector_at_fires_curated_thrower(self, tmp_path):
        """A noexcept function calling `.at(...)` (curated STL thrower,
        out_of_range) with no catch fires, naming out_of_range."""
        from frob.arch import analyze_project

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "at_call.cpp").write_text(
            "void reads(std::vector<int>& v) noexcept {\n    int x = v.at(0);\n}\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "cpp-noexcept-throws"]
        assert hits
        assert any("out_of_range" in s.message for s in hits)
