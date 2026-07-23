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
        assert set(classes) == {"Base", "Animal"}
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
        self, ts_module, rust_module, kt_module
    ) -> None:
        """The derived class (Animal) carries a `name` field and its
        `speak` method in TS/rust/kotlin, all three of which capture
        class-level annotated / constructor-set fields via their adapter.
        Python is asserted separately below (see
        `test_python_field_detection_is_a_documented_waiver`) since
        `PythonAdapter` does not capture this shape at all today."""
        for module in (ts_module, rust_module, kt_module):
            derived = next(c for c in module.classes if c.name == "Animal")
            field_names = {f.name for f in derived.fields}
            assert "name" in field_names, module.language
            method_names = {m.name for m in derived.methods}
            assert "speak" in method_names, module.language

    def test_python_field_detection_is_a_documented_waiver(self, py_module) -> None:
        """WAIVER (T-draft-d49c456f, filed out of T-0615's scope):
        `PythonAdapter._py_class_fields` never actually matches a
        class-level annotated field's real grammar shape (the assignment
        node arrives directly, not `expression_statement`-wrapped, as the
        filed ticket's repro shows) -- so `Animal.fields` comes back EMPTY
        for python even though the SAME fixture shape (`name: str` at
        class level) is captured by TS/rust/kotlin. Asserted explicitly
        here, not skipped, so a future fix to `_py_class_fields` is
        caught by this test needing an update rather than silently
        passing either way."""
        derived = next(c for c in py_module.classes if c.name == "Animal")
        assert derived.fields == []
        method_names = {m.name for m in derived.methods}
        assert "speak" in method_names

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

    def test_pool_inside_pool_fires_on_real_repo_run_combined_jobs(self):
        """Acceptance: the check fires on `src/frob/gates/_run_combined_jobs`
        as it exists TODAY -- T-0581 fixed the runtime ordering (submit
        before the thread pool opens, `mp_context=spawn`), but the
        STRUCTURAL co-occurrence this syntactic check flags is still
        present and is meant to stay flagged (an intentional, waived
        finding), proving the detector fires on real code, not only a
        fixture."""
        root = Path(__file__).parent.parent.parent / "src" / "frob" / "gates"
        result = analyze_project(root)
        hits = [
            s
            for s in result.suggestions
            if s.category == "pool-inside-pool"
            and s.symref == "__init__.py::_run_combined_jobs"
        ]
        assert len(hits) == 1
        assert hits[0].severity == "warning"

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
