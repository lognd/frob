"""T-2778: WIRE001's text-scan reach check
(`frob.gates._wire._wire_reach_patterns`) only recognized call-shaped
(`short(`), fixed-marker/job-table/dict-table by-reference, ErrorSet
member-access, and property-attribute-access usages of a newly-added
symbol. A private top-level FUNCTION passed by name as an ORDINARY call's
keyword-argument value (`on_tick=_print_tick`) is a fifth by-reference
shape none of those matched -- so a real, live callback (`scripts.
wait_for_land_slot._print_tick`, passed as `wait_for_slot`'s `on_tick=`
argument on every `--verbose` run) false-positived WIRE001, worked
around with a WIRE001 waiver naming this ticket as its follow-up until
this landed.

This file proves the fix (`wrapper_pattern`'s new keyword-argument-value
alternative, `_wire_reach_patterns`): a fresh FUNCTION passed as a
keyword-argument value elsewhere is rescued, a FUNCTION with no such
caller anywhere still fires (T-2451/T-1831/T-1820-shaped anchors must
stay correctly flagged), and -- the anti-abuse control the T-1831 anchor
specifically requires -- a CLASS passed the identical way is NOT
rescued, since the new alternative is gated to `kind ==
SymbolKind.FUNCTION` only. Kept in a separate file per this repo's own
precedent (`test_wire001_property_attribute_access.py`'s own module
docstring: avoid editing a file under another ticket's live lease when a
disjoint file will do)."""

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


class TestWire001CallbackKeywordArgument:
    """Acceptance: a fresh private FUNCTION passed as a keyword-argument
    value is rescued from WIRE001; one with no such caller anywhere, and
    a CLASS passed the identical way, still fire -- the fix narrows the
    false positive, it does not disable the gate."""

    # frob:ticket T-2778
    def test_function_passed_as_keyword_argument_value_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_wire001_callback_keyword_argument.py::TestWire001CallbackKeyw\
        # ordArgument.test_function_passed_as_keyword_argument_value_is_not_flagged
        """(MUST FAIL FIRST on pre-T-2778 main): a brand-new private
        function passed only as a keyword-argument value (never
        `_print_tick(`) to a same-module caller must NOT fire WIRE001 --
        the exact `_print_tick`/`wait_for_slot(on_tick=...)` shape
        T-2775 hit."""
        _write(
            tmp_path,
            "src/a.py",
            "from __future__ import annotations\n\n\n"
            "def _print_tick(reading: int, elapsed: float) -> None:\n"
            "    print(reading, elapsed)\n\n\n"
            "def run_loop(on_tick) -> None:\n"
            "    on_tick(1, 2.0)\n\n\n"
            "def main(verbose: bool) -> None:\n"
            "    run_loop(on_tick=_print_tick if verbose else None)\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if r.id.qualname.endswith("_print_tick")
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "_print_tick" in v.message for v in violations
        )

    # frob:ticket T-2778
    def test_function_with_no_caller_anywhere_still_flagged_positive_control(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_wire001_callback_keyword_argument.py::TestWire001CallbackKeyw\
        # ordArgument.test_function_with_no_caller_anywhere_still_flagged_positive_cont\
        # rol
        """Positive control (must-still-pass): a genuinely unwired
        private function -- no keyword-argument-value (or any other)
        reference anywhere outside its own tests -- still fires WIRE001.
        The fix rescues a real callback-argument caller, it does not
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

    # frob:ticket T-2778
    def test_class_passed_as_keyword_argument_value_still_flagged_anchor_control(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_wire001_callback_keyword_argument.py::TestWire001CallbackKeyw\
        # ordArgument.test_class_passed_as_keyword_argument_value_still_flagged_anchor_\
        # control
        """Anti-abuse control the T-1831 anchor requires: a CLASS passed
        as a keyword-argument value (`formatter_class=_GroupedHelpFormatter`'s
        own shape) must NOT be rescued by this fix -- the new keyword-
        argument-value alternative is gated to `kind ==
        SymbolKind.FUNCTION` specifically so a CLASS wired only this way
        keeps firing WIRE001, exactly as T-1831 (queued forever on
        purpose) requires."""
        _write(
            tmp_path,
            "src/c.py",
            "from __future__ import annotations\n\n\n"
            "import argparse\n\n\n"
            "class _GroupedHelpFormatter(argparse.HelpFormatter):\n"
            "    pass\n\n\n"
            "def build_parser() -> argparse.ArgumentParser:\n"
            "    return argparse.ArgumentParser(\n"
            "        formatter_class=_GroupedHelpFormatter\n"
            "    )\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r
            for r in snap.symbols.values()
            if r.id.qualname.endswith("_GroupedHelpFormatter")
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/c.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert any(
            v.rule == "WIRE001" and "_GroupedHelpFormatter" in v.message
            for v in violations
        )
