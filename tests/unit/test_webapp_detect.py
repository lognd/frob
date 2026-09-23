"""frob.webapp._detect coverage: one positive-control fixture per framework.

frob:ticket T-5302
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.webapp import FrameworkKind, detect_frameworks

_FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "webapp"

_CASES = [
    ("nextjs", FrameworkKind.NEXTJS),
    ("vite", FrameworkKind.VITE),
    ("django", FrameworkKind.DJANGO),
    ("flask", FrameworkKind.FLASK),
    ("fastapi", FrameworkKind.FASTAPI),
    ("rails", FrameworkKind.RAILS),
    ("laravel", FrameworkKind.LARAVEL),
    ("sveltekit", FrameworkKind.SVELTEKIT),
    ("astro", FrameworkKind.ASTRO),
]


@pytest.mark.parametrize("fixture_dir,expected", _CASES)
# frob:tests src/frob/webapp/_detect.py::detect_frameworks kind="unit"
# frob:tests src/frob/webapp/_detect.py::FrameworkKind kind="unit"
def test_detect_frameworks_positive_control(fixture_dir: str, expected: FrameworkKind):
    """MUST-FIRE: each framework's fixture dir detects as exactly that one framework."""
    root = _FIXTURE_ROOT / fixture_dir
    assert detect_frameworks(root) == frozenset({expected})


# frob:tests src/frob/webapp/_detect.py::detect_frameworks kind="unit"
def test_detect_frameworks_plain_python_cli_is_empty():
    """MUST-FIRE: a plain Python CLI repo with no framework markers detects nothing --
    the empty-set short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF rule relies on."""
    root = _FIXTURE_ROOT / "plain_python_cli"
    assert detect_frameworks(root) == frozenset()


# frob:tests src/frob/webapp/_detect.py::detect_frameworks kind="unit"
def test_detect_frameworks_missing_root_is_empty(tmp_path: Path):
    """A root with no files at all detects nothing (no crash on absent manifests)."""
    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    assert detect_frameworks(empty_root) == frozenset()
