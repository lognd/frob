"""Tests for frob.gates._docenum -- DOCENUM001 doc-claimed collection-member
drift gate (docs/modules/gates.md#docenum001-t-1227, T-1227).

Regression corpus: reconstructs the two historical `check.md _STAGE_GROUPS`
drift cases named in T-1227's acceptance criteria -- a stale claimed member
list must fire, the corrected list must pass.
"""
# frob:ticket T-1227

from __future__ import annotations

from pathlib import Path

from frob.gates._docenum import docenum001_gate
from frob.graph._models import Edge, EdgeKind, GraphSnapshot


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _snapshot(edges: tuple[Edge, ...]) -> GraphSnapshot:
    return GraphSnapshot(root=".", symbols={}, edges=edges)


def _enumerates_edge(
    target: str, members: str, *, src: str = "docs/x.md#anchor"
) -> Edge:
    return Edge(
        src=src,
        kind=EdgeKind.ENUMERATES,
        target=target,
        origin="docs/x.md:5",
        attrs={"members": members},
    )


class TestDocenum001Gate:
    def test_stale_claimed_list_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_docenum.py::docenum001_gate
        # Regression corpus case 1: the historical check.md _STAGE_GROUPS
        # drift -- doc claims a list missing a real member.
        _write(
            tmp_path,
            "check.py",
            '_STAGE_GROUPS = {"gates-fast": 1, "gates-native": 2, "ffi_boundary": 3}\n',
        )
        edges = (
            _enumerates_edge("check.py::_STAGE_GROUPS", "gates-fast,gates-native"),
        )
        violations = docenum001_gate(tmp_path, _snapshot(edges))
        rule_hits = [v for v in violations if v.rule == "DOCENUM001"]
        assert len(rule_hits) == 1
        assert "ffi_boundary" in rule_hits[0].message

    def test_corrected_claimed_list_passes(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_docenum.py::docenum001_gate
        # Regression corpus case 2: same collection, doc now corrected.
        _write(
            tmp_path,
            "check.py",
            '_STAGE_GROUPS = {"gates-fast": 1, "gates-native": 2, "ffi_boundary": 3}\n',
        )
        edges = (
            _enumerates_edge(
                "check.py::_STAGE_GROUPS", "gates-fast,gates-native,ffi_boundary"
            ),
        )
        violations = docenum001_gate(tmp_path, _snapshot(edges))
        assert violations == ()

    def test_stale_extra_claimed_member_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_docenum.py::docenum001_gate
        _write(tmp_path, "check.py", '_KINDS = {"a", "b"}\n')
        edges = (_enumerates_edge("check.py::_KINDS", "a,b,c"),)
        violations = docenum001_gate(tmp_path, _snapshot(edges))
        assert len(violations) == 1
        assert "stale/nonexistent" in violations[0].message
        assert "c" in violations[0].message

    def test_strenum_members_extracted(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_docenum.py::docenum001_gate
        _write(
            tmp_path,
            "kinds.py",
            "from enum import StrEnum\n\n\n"
            "class TicketKind(StrEnum):\n"
            '    FEATURE = "feature"\n'
            '    BUG = "bug"\n',
        )
        edges = (_enumerates_edge("kinds.py::TicketKind", "FEATURE,BUG"),)
        violations = docenum001_gate(tmp_path, _snapshot(edges))
        assert violations == ()

    def test_malformed_target_shape_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_docenum.py::docenum001_gate
        edges = (_enumerates_edge("not-a-symref", "a,b"),)
        violations = docenum001_gate(tmp_path, _snapshot(edges))
        assert len(violations) == 1
        assert "not a `path.py::Qualname`" in violations[0].message

    def test_unresolvable_shape_is_disclosed_not_silently_passed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_docenum.py::docenum001_gate
        # A shape this module cannot resolve (e.g. a computed value) must
        # WARN, never silently pass as "matches".
        _write(tmp_path, "weird.py", "_VALUE = compute_it()\n")
        edges = (_enumerates_edge("weird.py::_VALUE", "a,b"),)
        violations = docenum001_gate(tmp_path, _snapshot(edges))
        assert len(violations) == 1
        assert violations[0].severity.value == "warn"
        assert "cannot resolve" in violations[0].message

    def test_argparse_choices_members_extracted(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_docenum.py::docenum001_gate
        # T-1506: a qualname naming the enclosing parser-builder function
        # resolves to its one add_argument(choices=[...]) list.
        _write(
            tmp_path,
            "cli.py",
            "def _add_cycle_parser(sub) -> None:\n"
            '    cycle_p = sub.add_parser("cycle")\n'
            '    cycle_p.add_argument("cycle_path", metavar="path")\n'
            '    cycle_p.add_argument(\n'
            '        "--lang", dest="cycle_lang", choices=["python", "cpp", "c"]\n'
            "    )\n",
        )
        edges = (
            _enumerates_edge("cli.py::_add_cycle_parser", "python,cpp,c"),
        )
        violations = docenum001_gate(tmp_path, _snapshot(edges))
        assert violations == ()

    def test_argparse_choices_stale_claim_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_docenum.py::docenum001_gate
        _write(
            tmp_path,
            "cli.py",
            "def _add_cycle_parser(sub) -> None:\n"
            '    cycle_p = sub.add_parser("cycle")\n'
            '    cycle_p.add_argument(\n'
            '        "--lang", dest="cycle_lang", choices=["python", "cpp", "c"]\n'
            "    )\n",
        )
        edges = (_enumerates_edge("cli.py::_add_cycle_parser", "python,cpp"),)
        violations = docenum001_gate(tmp_path, _snapshot(edges))
        assert len(violations) == 1
        assert "c" in violations[0].message

    def test_argparse_multiple_choices_calls_is_ambiguous_punt(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_docenum.py::docenum001_gate
        # More than one add_argument(choices=[...]) call in the same
        # function is ambiguous -- punt (WARN), never guess which one the
        # qualname means.
        _write(
            tmp_path,
            "cli.py",
            "def _add_two_choices_parser(sub) -> None:\n"
            '    p = sub.add_parser("x")\n'
            '    p.add_argument("--a", choices=["one", "two"])\n'
            '    p.add_argument("--b", choices=["three", "four"])\n',
        )
        edges = (
            _enumerates_edge("cli.py::_add_two_choices_parser", "one,two"),
        )
        violations = docenum001_gate(tmp_path, _snapshot(edges))
        assert len(violations) == 1
        assert violations[0].severity.value == "warn"
        assert "cannot resolve" in violations[0].message
