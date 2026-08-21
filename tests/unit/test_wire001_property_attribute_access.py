"""T-2746: WIRE001's text-scan reach check
(`frob.gates._wire._wire_reach_patterns`) only recognized call-shaped
(`short(`) and by-reference (wrapper marker / dict-table value /
ErrorSet member-access) usages of a newly-added symbol. A `@property`'s
ONLY legal Python access shape is bare attribute access with NO trailing
call parens (`graph.degraded_languages`, never
`graph.degraded_languages()`), which none of the existing patterns
matched -- so a brand-new `@property` false-positived WIRE001 on its
first real, non-test caller, forcing a waiver every time.

Found while landing T-2700: `DependencyGraph.degraded_languages`
(src/frob/cycle/graph.py) was read via plain attribute access by
`find_cycles` in the SAME file, one line below the property's own
definition, and WIRE001 still fired.

This file proves the fix (`_is_property`/`_wire_reach_patterns`'s new
`property_access_pattern`): a fresh `@property` with a genuine
attribute-access caller elsewhere is rescued, while a `@property` with
NO caller anywhere still fires -- the fix narrows the false positive, it
does not exempt every property outright. Kept in a separate file per
this repo's own precedent (`test_wire001_pydantic_validator_rescue.py`'s
own module docstring: avoid editing a file under another ticket's live
lease when a disjoint file will do)."""

from __future__ import annotations

from pathlib import Path

from frob.gates._wire import wire_gate
from frob.gitio import Diff, Hunk
from frob.graph import build_graph
from frob.tickets import TicketQueue


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs -- local copy of
    tests/test_gates.py's own `_write` helper (same reasoning as this
    file's own module docstring: avoid touching a leased file)."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _snapshot(root: Path):
    """Build a graph snapshot for `root` -- local copy of
    tests/test_gates.py's own `_snapshot` helper."""
    cache = root / ".frob" / "cache.db"
    return build_graph(root, cache).danger_ok


class TestWire001PropertyAttributeAccess:
    """Acceptance: a fresh `@property` with a genuine attribute-access
    caller is rescued from WIRE001; one with no caller anywhere, and an
    ordinary new method, still fire -- the fix narrows the false
    positive, it does not disable the gate."""

    # frob:ticket T-2746
    def test_property_read_via_attribute_access_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttr\
        # ibuteAccess.test_property_read_via_attribute_access_is_not_flagged
        """(MUST FAIL FIRST on pre-T-2746 main): a brand-new `@property`
        read only via bare attribute access (never `short(`) by a
        SEPARATE caller must NOT fire WIRE001 -- the exact
        `DependencyGraph.degraded_languages`/`find_cycles` shape T-2700
        hit."""
        _write(
            tmp_path,
            "src/a.py",
            "from __future__ import annotations\n\n\n"
            "class Widget:\n"
            "    def __init__(self) -> None:\n"
            '        self._label = "x"\n\n'
            "    @property\n"
            "    def label(self) -> str:\n"
            "        return self._label\n\n\n"
            "def describe(widget: Widget) -> str:\n"
            "    return widget.label\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if r.id.qualname.endswith("Widget.label")
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "Widget.label" in v.message for v in violations
        )

    # frob:ticket T-2746
    def test_property_with_no_caller_anywhere_still_flagged_positive_control(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttr\
        # ibuteAccess.test_property_with_no_caller_anywhere_still_flagged_positive_cont\
        # rol
        """Positive control (must-still-pass): a genuinely unwired
        `@property` -- no attribute-access reader anywhere outside its
        own tests -- still fires WIRE001. The fix rescues a real
        attribute-access caller, it does not exempt every property."""
        _write(
            tmp_path,
            "src/b.py",
            "from __future__ import annotations\n\n\n"
            "class Gadget:\n"
            "    def __init__(self) -> None:\n"
            "        self._size = 1\n\n"
            "    @property\n"
            "    def size(self) -> int:\n"
            "        return self._size\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if r.id.qualname.endswith("Gadget.size")
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/b.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert any(
            v.rule == "WIRE001" and "Gadget.size" in v.message for v in violations
        )

    # frob:ticket T-2746
    def test_ordinary_new_method_still_flagged_positive_control(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttr\
        # ibuteAccess.test_ordinary_new_method_still_flagged_positive_control
        """Second positive control: an ordinary (non-`@property`) new
        method with no caller outside its own tests still fires WIRE001
        -- `property_access_pattern` is gated on `_is_property`, so a
        plain method's own by-reference callback usage
        (`obj.method`, no parens) is NOT newly rescued by this fix."""
        _write(
            tmp_path,
            "src/c.py",
            "from __future__ import annotations\n\n\n"
            "class Thing:\n"
            "    def run(self) -> int:\n"
            "        return 1\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if r.id.qualname.endswith("Thing.run")
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/c.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert any(v.rule == "WIRE001" and "Thing.run" in v.message for v in violations)
