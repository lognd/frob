"""Unit tests for T-0617's OCP checks (`frob.arch._ocp`): type-dispatch
smell and non-exhaustive enum match.

Deliberately a SEPARATE file from `tests/unit/test_arch.py` (concurrent
sibling tickets T-0615/T-0616 also touch arch tests; new checks get a new
test file rather than contending on a shared one), following that file's
own convention: drive everything through the public `analyze_project`
entry point and inspect `ArchResult.suggestions`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from frob.arch import analyze_project

    HAS_ARCH = True
except ImportError:
    HAS_ARCH = False

pytestmark = pytest.mark.skipif(not HAS_ARCH, reason="frob.arch not available")


class TestTypeDispatchSmell:
    """OCP: an isinstance-chain reuses T-0332's `type-switch` detector
    (`frob.arch._patterns.iter_type_switch_chains`) and is ALSO reported as
    an OCP violation, not just a pattern recommendation."""

    # frob:waive DUP001 reason="parallel test methods within test_arch_ocp.py (2 sites) sharing an \
    # arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_isinstance_chain_flags_ocp_violation(self, tmp_path: Path) -> None:
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
        hits = [s for s in result.suggestions if s.category == "type-dispatch-smell"]
        assert len(hits) == 1
        assert "OCP" in hits[0].message
        assert hits[0].symref == "shapes.py::area"
        assert hits[0].metric == 3

    def test_same_chain_also_still_recommends_strategy(self, tmp_path: Path) -> None:
        # One detector, two outputs (T-0332/T-0617): the SAME isinstance
        # chain fires both the pre-existing pattern-recommendation AND the
        # new OCP smell -- reuse, not replacement.
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
        categories = {s.category for s in result.suggestions}
        assert "pattern-recommendation" in categories
        assert "type-dispatch-smell" in categories

    # frob:waive DUP001 reason="parallel test methods within test_arch_ocp.py (7 sites) sharing an \
    # arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_two_arm_isinstance_chain_not_flagged(self, tmp_path: Path) -> None:
        # STRONG-HALLMARK-ONLY (inherited from the reused T-0332 detector):
        # two arms is routine control flow, not a growing type-switch.
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
        hits = [s for s in result.suggestions if s.category == "type-dispatch-smell"]
        assert hits == []


class TestNonExhaustiveEnumMatch:
    """OCP: a `match`/`case` over a locally-known enum missing a member and
    carrying no wildcard/default arm."""

    # frob:waive DUP001 reason="parallel test methods within test_arch_ocp.py (2 sites) sharing an \
    # arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_missing_member_flagged(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "colors.py").write_text(
            "from enum import Enum\n\n"
            "class Color(Enum):\n"
            "    RED = 1\n"
            "    GREEN = 2\n"
            "    BLUE = 3\n\n"
            "def name_of(c: Color) -> str:\n"
            "    match c:\n"
            "        case Color.RED:\n"
            "            return 'r'\n"
            "        case Color.GREEN:\n"
            "            return 'g'\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s for s in result.suggestions if s.category == "non-exhaustive-enum-match"
        ]
        assert len(hits) == 1
        assert "BLUE" in hits[0].message
        assert hits[0].symref == "colors.py::name_of"
        assert hits[0].metric == 1

    # frob:waive DUP001 reason="parallel test methods within test_arch_ocp.py (7 sites) sharing an \
    # arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_exhaustive_match_not_flagged(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "colors.py").write_text(
            "from enum import Enum\n\n"
            "class Color(Enum):\n"
            "    RED = 1\n"
            "    GREEN = 2\n\n"
            "def name_of(c: Color) -> str:\n"
            "    match c:\n"
            "        case Color.RED:\n"
            "            return 'r'\n"
            "        case Color.GREEN:\n"
            "            return 'g'\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s for s in result.suggestions if s.category == "non-exhaustive-enum-match"
        ]
        assert hits == []

    # frob:waive DUP001 reason="parallel test methods within test_arch_ocp.py (7 sites) sharing an \
    # arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_wildcard_default_suppresses_finding(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "colors.py").write_text(
            "from enum import Enum\n\n"
            "class Color(Enum):\n"
            "    RED = 1\n"
            "    GREEN = 2\n"
            "    BLUE = 3\n\n"
            "def name_of(c: Color) -> str:\n"
            "    match c:\n"
            "        case Color.RED:\n"
            "            return 'r'\n"
            "        case _:\n"
            "            return 'other'\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s for s in result.suggestions if s.category == "non-exhaustive-enum-match"
        ]
        assert hits == []

    # frob:waive DUP001 reason="parallel test methods within test_arch_ocp.py (7 sites) sharing an \
    # arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_capture_default_suppresses_finding(self, tmp_path: Path) -> None:
        # A bare-name capture pattern (`case other:`) is also a default arm.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "colors.py").write_text(
            "from enum import Enum\n\n"
            "class Color(Enum):\n"
            "    RED = 1\n"
            "    GREEN = 2\n"
            "    BLUE = 3\n\n"
            "def name_of(c: Color) -> str:\n"
            "    match c:\n"
            "        case Color.RED:\n"
            "            return 'r'\n"
            "        case other:\n"
            "            return str(other)\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s for s in result.suggestions if s.category == "non-exhaustive-enum-match"
        ]
        assert hits == []

    # frob:waive DUP001 reason="parallel test methods within test_arch_ocp.py (7 sites) sharing an \
    # arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_non_enum_class_match_not_flagged(self, tmp_path: Path) -> None:
        # No local Enum-family class at all -- fail toward silence, not a
        # false-positive on a non-enum tagged-union-shaped match.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "shapes.py").write_text(
            "def name_of(c):\n"
            "    match c:\n"
            "        case Shape.CIRCLE:\n"
            "            return 'circle'\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s for s in result.suggestions if s.category == "non-exhaustive-enum-match"
        ]
        assert hits == []

    # frob:waive DUP001 reason="parallel test methods within test_arch_ocp.py (7 sites) sharing an \
    # arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_union_pattern_covers_multiple_members(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "colors.py").write_text(
            "from enum import Enum\n\n"
            "class Color(Enum):\n"
            "    RED = 1\n"
            "    GREEN = 2\n"
            "    BLUE = 3\n\n"
            "def name_of(c: Color) -> str:\n"
            "    match c:\n"
            "        case Color.RED | Color.GREEN | Color.BLUE:\n"
            "            return 'known'\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s for s in result.suggestions if s.category == "non-exhaustive-enum-match"
        ]
        assert hits == []

    # frob:waive DUP001 reason="parallel test methods within test_arch_ocp.py (7 sites) sharing an \
    # arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_unresolvable_pattern_shape_not_flagged(self, tmp_path: Path) -> None:
        # A qualifier naming a DIFFERENT class than any known local enum
        # makes the match unresolvable from this file alone -- silence.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "colors.py").write_text(
            "from enum import Enum\n\n"
            "class Color(Enum):\n"
            "    RED = 1\n"
            "    GREEN = 2\n\n"
            "def name_of(c):\n"
            "    match c:\n"
            "        case OtherThing.RED:\n"
            "            return 'r'\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s for s in result.suggestions if s.category == "non-exhaustive-enum-match"
        ]
        assert hits == []
