"""Tests for `frob.gates._fix_engine_sync.fix_sys_interface_canonical_order`
(T-1872): the Tier-A `interface=` canonical-order handler. Order-only is
the load-bearing property under test -- every case asserts the declared
name MULTISET is unchanged, only the ORDER moves."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from frob.gates._fix_engine_sync import fix_sys_interface_canonical_order
from frob.graph._models import GraphSnapshot

_STRATA_HEADER = "module test\n\n"

# T-1896: `fix_sys_interface_canonical_order` is typed to take a
# `GraphSnapshot` (Tier-A fix-handler signature uniformity, T-1872) even
# though its body never reads it (the handler re-reads the design tree
# itself) -- these tests previously passed `None`, which `ty` correctly
# flags as an invalid-argument-type since the param is not `GraphSnapshot |
# None`. An empty, otherwise-unused snapshot is the honest fix: it
# satisfies the real declared type without changing what the handler under
# test actually does.
_EMPTY_SNAPSHOT = GraphSnapshot(root="", symbols={}, edges=())


def _write_repo(root: Path, interface_block: str, py_source: str) -> None:
    """Lay out a minimal design/ + pkg/ tree: one node, one bound `.py`
    file, and `interface_block` as that node's raw `interface=[...]` body."""
    (root / "design").mkdir(parents=True)
    (root / "pkg").mkdir(parents=True)
    (root / "design" / "frob.strata").write_text(
        _STRATA_HEADER
        + "node core : trusted {\n"
        + '    code "pkg/**";\n'
        + f"    attr interface=[\n        {interface_block}\n    ];\n"
        + "}\n",
        encoding="utf-8",
    )
    (root / "pkg" / "mod.py").write_text(py_source, encoding="utf-8")


class TestSysInterfaceCanonicalOrder:
    """GIVEN/WHEN/THEN acceptance for T-1872's canonical-order handler."""

    # frob:tests \
    # tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonical\
    # Order.test_groups_by_kind_then_alpha
    def test_groups_by_kind_then_alpha(self, tmp_path: Path) -> None:
        """Classes first, then functions, then constants -- alphabetical
        within each group -- resolved against the node's bound code, not
        lexical casing (SYMBOLIC NEVER LEXICAL, T-1662)."""
        root = tmp_path / "repo"
        _write_repo(
            root,
            "zeta, Alpha, BETA_CONST, helper_fn,",
            "class Alpha:\n    pass\n\n"
            "def zeta():\n    pass\n\n"
            "def helper_fn():\n    pass\n\n"
            "BETA_CONST = 1\n",
        )
        applied = fix_sys_interface_canonical_order(root, _EMPTY_SNAPSHOT)
        assert len(applied) == 1
        assert applied[0].rule == "SYS-IFACE-ORDER"

        text = (root / "design" / "frob.strata").read_text(encoding="utf-8")
        assert "Alpha, helper_fn, zeta, BETA_CONST," in text

    # frob:tests \
    # tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonical\
    # Order.test_order_only_multiset_preserved_and_idempotent
    def test_order_only_multiset_preserved_and_idempotent(self, tmp_path: Path) -> None:
        """The declared name multiset (INCLUDING a duplicate -- T-1871's
        PARSE ERROR was dropped, so a duplicate can still exist on disk)
        is byte-identical before and after, and a second run is a no-op."""
        root = tmp_path / "repo"
        before_names = ["zeta", "Alpha", "Alpha", "helper_fn", "BETA_CONST"]
        _write_repo(
            root,
            ", ".join(before_names) + ",",
            "class Alpha:\n    pass\n\n"
            "def zeta():\n    pass\n\n"
            "def helper_fn():\n    pass\n\n"
            "BETA_CONST = 1\n",
        )
        fix_sys_interface_canonical_order(root, _EMPTY_SNAPSHOT)
        text = (root / "design" / "frob.strata").read_text(encoding="utf-8")

        # Names live between the block's '[' and closing '];'.
        block = text.split("interface=[", 1)[1].split("];", 1)[0]
        after_names = [
            n.strip() for n in block.replace("\n", " ").split(",") if n.strip()
        ]
        assert Counter(after_names) == Counter(before_names)

        # Idempotent: a second run finds nothing left to reorder.
        applied_again = fix_sys_interface_canonical_order(root, _EMPTY_SNAPSHOT)
        assert applied_again == []

    # frob:tests \
    # tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonical\
    # Order.test_empty_interface_one_line_form_is_not_read_as_a_name
    def test_empty_interface_one_line_form_is_not_read_as_a_name(
        self, tmp_path: Path
    ) -> None:
        """T-1900: `attr interface=[];` (the one-line empty form
        `_render_interface_block` itself emits) must be left byte-
        identical -- the handler must NOT read the literal `[]` token as
        a declared name called `[]` and re-expand it into an invalid
        multi-line block."""
        root = tmp_path / "repo"
        root.mkdir()
        (root / "design").mkdir()
        (root / "pkg").mkdir()
        strata_text = (
            _STRATA_HEADER
            + "node core : trusted {\n"
            + '    code "pkg/**";\n'
            + "    attr interface=[];\n"
            + "}\n"
        )
        (root / "design" / "frob.strata").write_text(strata_text, encoding="utf-8")
        (root / "pkg" / "mod.py").write_text("X = 1\n", encoding="utf-8")

        applied = fix_sys_interface_canonical_order(root, None)
        assert applied == []

        after = (root / "design" / "frob.strata").read_text(encoding="utf-8")
        assert after == strata_text
        assert "attr interface=[];" in after

    # frob:tests \
    # tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonical\
    # Order.test_round_trip_every_node_shape_reparses
    def test_round_trip_every_node_shape_reparses(self, tmp_path: Path) -> None:
        """Round-trip over every node shape (compact multi-name, legacy
        one-name-per-line, and the empty case) -- the rewritten
        `design/frob.strata` must still PARSE via strata-core afterward."""
        from frob.strata._parse import parse_module

        root = tmp_path / "repo"
        root.mkdir()
        (root / "design").mkdir()
        (root / "pkg").mkdir()
        strata_text = (
            _STRATA_HEADER
            + "node core : trusted {\n"
            + '    code "pkg/core.py";\n'
            + "    attr interface=[\n        zeta, Alpha,\n    ];\n"
            + "}\n\n"
            + "node legacy : trusted {\n"
            + '    code "pkg/legacy.py";\n'
            + "    attr interface=only_fn;\n"
            + "}\n\n"
            + "node empty : trusted {\n"
            + '    code "pkg/empty.py";\n'
            + "    attr interface=[];\n"
            + "}\n"
        )
        (root / "design" / "frob.strata").write_text(strata_text, encoding="utf-8")
        (root / "pkg" / "core.py").write_text(
            "class Alpha:\n    pass\n\ndef zeta():\n    pass\n", encoding="utf-8"
        )
        (root / "pkg" / "legacy.py").write_text(
            "def only_fn():\n    pass\n", encoding="utf-8"
        )
        (root / "pkg" / "empty.py").write_text("Y = 1\n", encoding="utf-8")

        fix_sys_interface_canonical_order(root, None)
        after = (root / "design" / "frob.strata").read_text(encoding="utf-8")
        result = parse_module(after)
        assert result.is_ok, result.err

    # frob:tests \
    # tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonical\
    # Order.test_rewrite_that_would_not_parse_is_refused
    def test_rewrite_that_would_not_parse_is_refused(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """T-1900 part 3: even when the multiset guard passes, a rewrite
        whose rendered text fails to re-parse must be refused (`lines`
        left unchanged) rather than written -- simulated by forcing
        `_iface_rewrite_parses` to report failure."""
        from frob.gates import _fix_engine_sync

        root = tmp_path / "repo"
        _write_repo(
            root,
            "zeta, Alpha,",
            "class Alpha:\n    pass\n\ndef zeta():\n    pass\n",
        )
        before = (root / "design" / "frob.strata").read_text(encoding="utf-8")

        monkeypatch.setattr(
            _fix_engine_sync, "_iface_rewrite_parses", lambda lines: False
        )
        applied = fix_sys_interface_canonical_order(root, None)
        assert applied == []

        after = (root / "design" / "frob.strata").read_text(encoding="utf-8")
        assert after == before
