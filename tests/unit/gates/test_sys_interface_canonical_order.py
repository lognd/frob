"""Tests for `frob.gates._fix_engine_sync.fix_sys_interface_canonical_order`
(T-1872): the Tier-A `interface=` canonical-order handler. Order-only is
the load-bearing property under test -- every case asserts the declared
name MULTISET is unchanged, only the ORDER moves."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from frob.gates._fix_engine_sync import fix_sys_interface_canonical_order

_STRATA_HEADER = 'module test\n\n'


def _write_repo(root: Path, interface_block: str, py_source: str) -> None:
    """Lay out a minimal design/ + pkg/ tree: one node, one bound `.py`
    file, and `interface_block` as that node's raw `interface=[...]` body."""
    (root / "design").mkdir(parents=True)
    (root / "pkg").mkdir(parents=True)
    (root / "design" / "frob.strata").write_text(
        _STRATA_HEADER
        + 'node core : trusted {\n'
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
        applied = fix_sys_interface_canonical_order(root, None)
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
        fix_sys_interface_canonical_order(root, None)
        text = (root / "design" / "frob.strata").read_text(encoding="utf-8")

        # Names live between the block's '[' and closing '];'.
        block = text.split("interface=[", 1)[1].split("];", 1)[0]
        after_names = [
            n.strip() for n in block.replace("\n", " ").split(",") if n.strip()
        ]
        assert Counter(after_names) == Counter(before_names)

        # Idempotent: a second run finds nothing left to reorder.
        applied_again = fix_sys_interface_canonical_order(root, None)
        assert applied_again == []
