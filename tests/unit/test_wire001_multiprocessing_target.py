"""T-3576: `_write_journal_and_block`'s own `frob:waive WIRE001` (`tests/
unit/test_fix_engine_journal.py`, filed by T-3558) reasoned that WIRE001's
call-graph analyzer "does not resolve a target= reference the way it
resolves a direct call" for `multiprocessing.Process(target=X, ...)`/
`ctx.Process(target=X, ...)`. Investigation (T-3576) found this is
already the generic keyword-argument-value shape T-2778 landed
(`_wire_reach_patterns`'s `keyword_arg_pattern`, gated to `kind ==
SymbolKind.FUNCTION`) -- `target=X` is textually indistinguishable from
any other `name=X` keyword argument, so the analyzer already resolves it
correctly with NO detector change needed. This file locks that in with
an explicit fixture naming the shape by name (must-fire/must-stay-quiet,
this repo's own detector-change discipline), since no existing test
named `multiprocessing.Process`/`target=` specifically before this --
the T-2778 fixtures cover the general keyword-argument shape only.
`_write_journal_and_block`'s own now-redundant waiver was removed in the
same change. Kept in a separate file per this repo's own precedent
(`test_wire001_callback_keyword_argument.py`'s own module docstring:
avoid editing a file under another ticket's live lease when a disjoint
file will do)."""

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


class TestWire001MultiprocessingProcessTarget:
    """Acceptance: a fresh private FUNCTION whose only reference anywhere
    is `multiprocessing.Process(target=...)` (or a context's own
    `ctx.Process(target=...)`) must NOT fire WIRE001; a function with no
    such caller anywhere still fires -- the fix (already-generic since
    T-2778) narrows the false positive, it does not disable the gate."""

    def test_function_passed_as_process_target_kwarg_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_wire001_multiprocessing_target.py::TestWire001MultiprocessingProcessTarget.test_function_passed_as_process_target_kwarg_is_not_flagged  # noqa: E501
        """A brand-new private function passed only as `multiprocessing.
        Process(target=...)`'s own keyword argument (never `_worker(`)
        to a same-module caller must NOT fire WIRE001 -- the exact
        `_write_journal_and_block`/T-3558 shape."""
        _write(
            tmp_path,
            "src/a.py",
            "from __future__ import annotations\n\n"
            "import multiprocessing\n\n\n"
            "def _worker(x: int) -> None:\n"
            "    print(x)\n\n\n"
            "def spawn(x: int) -> None:\n"
            "    proc = multiprocessing.Process(target=_worker, args=(x,))\n"
            "    proc.start()\n"
            "    proc.join()\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if r.id.qualname.endswith("_worker")
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "_worker" in v.message for v in violations
        )

    def test_function_passed_as_context_process_target_kwarg_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_wire001_multiprocessing_target.py::TestWire001MultiprocessingProcessTarget.test_function_passed_as_context_process_target_kwarg_is_not_flagged  # noqa: E501
        """Same shape via `multiprocessing.get_context(...).Process(
        target=...)` -- the exact receiver `_write_journal_and_block`'s
        real caller uses (`ctx.Process(target=..., args=(...))`), not
        the bare `multiprocessing.Process` spelling."""
        _write(
            tmp_path,
            "src/b.py",
            "from __future__ import annotations\n\n"
            "import multiprocessing\n\n\n"
            "def _worker(x: int) -> None:\n"
            "    print(x)\n\n\n"
            "def spawn(x: int) -> None:\n"
            "    ctx = multiprocessing.get_context('spawn')\n"
            "    proc = ctx.Process(\n"
            "        target=_worker, args=(x,)\n"
            "    )\n"
            "    proc.start()\n"
            "    proc.join()\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if r.id.qualname.endswith("_worker")
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/b.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "_worker" in v.message for v in violations
        )

    def test_function_with_no_process_target_caller_anywhere_still_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_wire001_multiprocessing_target.py::TestWire001MultiprocessingProcessTarget.test_function_with_no_process_target_caller_anywhere_still_flagged  # noqa: E501
        """Positive control (must-still-fire): a genuinely unwired
        private function -- no `Process(target=...)` (or any other)
        reference anywhere outside its own tests -- still fires WIRE001.
        The multiprocessing.Process shape rescues a real caller, it does
        not exempt every function."""
        _write(
            tmp_path,
            "src/c.py",
            "from __future__ import annotations\n\n\n"
            "def _never_called() -> int:\n"
            "    return 1\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if r.id.qualname.endswith("_never_called")
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/c.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert any(
            v.rule == "WIRE001" and "_never_called" in v.message for v in violations
        )
