"""T-2931: WIRE001's text-scan reach check
(`frob.gates._wire._wire_reach_patterns`) recognized several bare-name
by-reference shapes (`_WRAPPER_MARKER_NAMES`, dict-table values, a
keyword-argument value) but none of them can match a DOTTED marker call
-- `wrapper_pattern`'s bare-name alternative explicitly excludes a
dot-preceded match (`(?<![A-Za-z0-9_.])`). `atexit.register(_target,
...)` (the stdlib's own dynamic-dispatch callback registry, T-2645's
`_scratch_file_for_suffix`/`_remove_scratch_file`) is exactly this
shape: a private FUNCTION whose only caller is `atexit.register`, never
a call token this text scan could otherwise see -- false-positived
WIRE001, worked around with a per-site waiver directive (naming this
ticket as its follow-up) until this landed.

This file proves the fix (`_DOTTED_WRAPPER_MARKERS`/`_wire_reach_
patterns`'s new dotted-wrapper alternative): a fresh FUNCTION registered
only via `atexit.register` is rescued, a FUNCTION with no such caller
anywhere still fires, and -- the anti-abuse control this repo's other
by-reference fixes each carry (T-1831/T-2778's own anchors) -- a CLASS
registered the identical way is NOT rescued, since the new alternative
is gated to `kind == SymbolKind.FUNCTION` only. Kept in a separate file
per this repo's own precedent (`test_wire001_callback_keyword_
argument.py`'s own module docstring: avoid editing a file under another
ticket's live lease when a disjoint file will do)."""

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


class TestWire001AtexitRegister:
    """Acceptance: a fresh private FUNCTION registered only via
    `atexit.register` is rescued from WIRE001; one with no such caller
    anywhere, and a CLASS registered the identical way, still fire --
    the fix narrows the false positive, it does not disable the gate."""

    # frob:ticket T-2931
    def test_function_registered_via_atexit_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_wire001_atexit_register.py::TestWire001AtexitRegister.test_fu\
        # nction_registered_via_atexit_is_not_flagged
        """(MUST FAIL FIRST on pre-T-2931 main): a brand-new private
        function whose only reference anywhere is
        `atexit.register(_remove_scratch_file, path)` must NOT fire
        WIRE001 -- the exact `_scratch_file_for_suffix`/`_remove_scratch_
        file` shape T-2645 hit."""
        _write(
            tmp_path,
            "src/a.py",
            "from __future__ import annotations\n\n\n"
            "def _remove_scratch_file(path: str) -> None:\n"
            "    import contextlib\n"
            "    import os\n\n"
            "    with contextlib.suppress(OSError):\n"
            "        os.unlink(path)\n\n\n"
            "def register_cleanup(path: str) -> None:\n"
            "    import atexit\n\n"
            "    atexit.register(_remove_scratch_file, path)\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r
            for r in snap.symbols.values()
            if r.id.qualname.endswith("_remove_scratch_file")
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "_remove_scratch_file" in v.message
            for v in violations
        )

    # frob:ticket T-2931
    def test_function_with_no_caller_anywhere_still_flagged_positive_control(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_wire001_atexit_register.py::TestWire001AtexitRegister.test_fu\
        # nction_with_no_caller_anywhere_still_flagged_positive_control
        """Positive control (must-still-pass): a genuinely unwired
        private function -- no `atexit.register` (or any other)
        reference anywhere outside its own tests -- still fires WIRE001.
        The fix rescues a real `atexit.register` caller, it does not
        exempt every function."""
        _write(
            tmp_path,
            "src/b.py",
            "from __future__ import annotations\n\n\n"
            "def _never_called() -> int:\n"
            "    return 1\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if r.id.qualname.endswith("_never_called")
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/b.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert any(
            v.rule == "WIRE001" and "_never_called" in v.message for v in violations
        )

    # frob:ticket T-2931
    def test_class_registered_via_atexit_still_flagged_anchor_control(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_wire001_atexit_register.py::TestWire001AtexitRegister.test_cl\
        # ass_registered_via_atexit_still_flagged_anchor_control
        """Anti-abuse control (matching T-1831/T-2778's own anchors): a
        CLASS registered via `atexit.register` must NOT be rescued by
        this fix -- the new dotted-wrapper alternative is gated to
        `kind == SymbolKind.FUNCTION` specifically, no evidenced CLASS
        instance of this shape exists, and widening past FUNCTION would
        just be guessing."""
        _write(
            tmp_path,
            "src/c.py",
            "from __future__ import annotations\n\n\n"
            "class _Closer:\n"
            "    def __init__(self) -> None:\n"
            "        pass\n\n\n"
            "def register_closer() -> None:\n"
            "    import atexit\n\n"
            "    atexit.register(_Closer)\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if r.id.qualname.endswith("_Closer")
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/c.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert any(
            v.rule == "WIRE001" and "_Closer" in v.message for v in violations
        )
