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


class TestDocenum001UndocumentedMembers:
    """T-2664: a claimed member with no table row/heading anywhere in the
    doc file is a separate WARN finding from the member-list-mismatch
    check above -- covers both directions plus the pre-existing mismatch
    check still firing unchanged."""

    def test_claimed_member_with_no_doc_row_fires_warn(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_docenum.py::docenum001_gate
        _write(tmp_path, "code.py", '_RULES = {"AAA001": 1, "BBB002": 2}\n')
        _write(
            tmp_path,
            "docs/x.md",
            "# Rules\n\n"
            "| Rule | Fails when |\n"
            "|---|---|\n"
            "| AAA001 | thing happens |\n",
        )
        edges = (_enumerates_edge("code.py::_RULES", "AAA001,BBB002"),)
        violations = docenum001_gate(tmp_path, _snapshot(edges))
        # member list itself matches exactly -- no mismatch finding.
        assert not [v for v in violations if "member list" in v.message]
        undoc = [v for v in violations if "no resolvable documentation" in v.message]
        assert len(undoc) == 1
        assert undoc[0].severity.value == "warn"
        assert "BBB002" in undoc[0].message
        assert "AAA001" not in undoc[0].message

    def test_claimed_member_with_doc_row_does_not_fire(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_docenum.py::docenum001_gate
        _write(tmp_path, "code.py", '_RULES = {"AAA001": 1, "BBB002": 2}\n')
        _write(
            tmp_path,
            "docs/x.md",
            "# Rules\n\n"
            "| Rule | Fails when |\n"
            "|---|---|\n"
            "| AAA001 | thing happens |\n"
            "| BBB002 | other thing happens |\n",
        )
        edges = (_enumerates_edge("code.py::_RULES", "AAA001,BBB002"),)
        violations = docenum001_gate(tmp_path, _snapshot(edges))
        assert violations == ()

    def test_documented_via_heading_section_does_not_fire(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_docenum.py::docenum001_gate
        # Combined-id headings (this file's own catalog shape, e.g.
        # "## AFFECT001 AFFECT002 (T-0628)") must also count as
        # documentation, not just a table row.
        _write(tmp_path, "code.py", '_RULES = {"AAA001": 1, "BBB002": 2}\n')
        _write(
            tmp_path,
            "docs/x.md",
            "# Rules\n\n## AAA001 BBB002 (T-0000)\n\nProse.\n",
        )
        edges = (_enumerates_edge("code.py::_RULES", "AAA001,BBB002"),)
        violations = docenum001_gate(tmp_path, _snapshot(edges))
        assert violations == ()

    def test_member_mismatch_still_fires_alongside_undocumented(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_docenum.py::docenum001_gate
        # Existing ERROR-severity mismatch detection is unchanged by the
        # new WARN check -- both can fire on the same edge independently.
        _write(tmp_path, "code.py", '_RULES = {"AAA001": 1, "BBB002": 2}\n')
        _write(
            tmp_path,
            "docs/x.md",
            "# Rules\n\n| Rule | Fails when |\n|---|---|\n| AAA001 | x |\n",
        )
        edges = (_enumerates_edge("code.py::_RULES", "AAA001"),)
        violations = docenum001_gate(tmp_path, _snapshot(edges))
        rules_by_severity = {v.severity.value for v in violations}
        assert "error" in rules_by_severity
        mismatch = [v for v in violations if "member list" in v.message]
        assert len(mismatch) == 1
        assert "BBB002" in mismatch[0].message
