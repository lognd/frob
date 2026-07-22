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

    # frob:waive DUP001 reason="parallel test methods within test_arch.py \
    # (2 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case coverage; extracting would obscure per-case intent"
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

    # frob:waive DUP001 reason="parallel test methods within test_arch.py \
    # (2 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case coverage; extracting would obscure per-case intent"
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

    # frob:waive DUP001 reason="parallel test methods within test_arch.py \
    # (2 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case coverage; extracting would obscure per-case intent"
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

    # frob:waive DUP001 reason="parallel test methods within test_arch.py \
    # (2 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case coverage; extracting would obscure per-case intent"
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

    # frob:waive DUP001 reason="parallel test methods within test_arch.py \
    # (2 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case coverage; extracting would obscure per-case intent"
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

    # frob:waive DUP001 reason="parallel test methods within test_arch.py \
    # (2 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case coverage; extracting would obscure per-case intent"
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
