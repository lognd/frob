# frob:ticket T-2532
"""WIRE001 dotted classmethod/staticmethod reach (T-2532): a classmethod's
or staticmethod's ONLY legal call shape in Python is dotted-qualified
(`ClassName.method_name(...)` or `instance.method_name(...)`) --
`_wire_reach_patterns`'s `call_pattern` used to explicitly EXCLUDE any
match preceded by a dot, making every genuine qualified call site
invisible to the reach scan and forcing a `frob:waive` for code that was
never actually unwired (the T-2530 `SealedGrantSet.from_root_node`
incident this ticket was filed from). Split into its own file rather than
folding into `tests/test_gates.py::TestWireGate`, mirroring
`tests/unit/test_wire_autouse_fixture.py`'s own precedent (a `tests/**`
lease held by a concurrent ticket at write time)."""

from __future__ import annotations

from pathlib import Path

from frob.gates._wire import wire_gate
from frob.gitio import Diff, Hunk
from frob.graph import build_graph
from frob.tickets import TicketQueue


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent directories -- shared
    scratch-repo helper mirroring `tests/test_gates.py::_write`."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _snapshot(root: Path):
    """Build a fresh `GraphSnapshot` over `root` -- shared scratch-repo
    helper mirroring `tests/test_gates.py::_snapshot`."""
    cache = root / ".frob" / "cache.db"
    return build_graph(root, cache).danger_ok


def _first_rule(violations, rule):
    """The first violation with `rule`, or None -- assertion convenience,
    mirroring `tests/test_gates.py::_first_rule`."""
    for v in violations:
        if v.rule == rule:
            return v
    return None


class TestWireGateDottedMethodReach:
    """T-2532: a real `ClassName.method(...)` call site (the only legal
    shape for a classmethod/staticmethod) must count as reached; a
    genuinely unwired method must still fire."""

    def test_classmethod_called_dotted_qualified_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach.test_classmethod_called_dotted_qualified_is_not_flagged  # noqa: E501
        # Positive control: a genuine classmethod, called exactly once,
        # only ever dotted-qualified (`SealedGrantSet.from_root_node(...)`,
        # the T-2530/T-2532 real-world shape) -- WIRE001 must not flag it.
        _write(
            tmp_path,
            "src/pkg/grants.py",
            "class SealedGrantSet:\n"
            "    @classmethod\n"
            "    def from_root_node(cls, node):\n"
            "        return cls()\n\n"
            "def _seed_grants_by_root_node(node):\n"
            "    return SealedGrantSet.from_root_node(node)\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if "from_root_node" in r.symref
        )
        diff = Diff(
            base="x", hunks=(Hunk(file="src/pkg/grants.py", span=record.span),)
        )
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert _first_rule(violations, "WIRE001") is None

    def test_genuinely_unwired_method_still_flagged(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach.test_genuinely_unwired_method_still_flagged  # noqa: E501
        # Negative control: a method with no caller ANYWHERE -- neither
        # bare nor dotted-qualified -- must still fire. The T-2532 fix
        # must not widen the escape into a blanket exemption for every
        # method.
        _write(
            tmp_path,
            "src/pkg/orphan.py",
            "class Orphan:\n"
            "    @staticmethod\n"
            "    def never_called():\n"
            "        return 1\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if "never_called" in r.symref
        )
        diff = Diff(
            base="x", hunks=(Hunk(file="src/pkg/orphan.py", span=record.span),)
        )
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert _first_rule(violations, "WIRE001") is not None

    def test_similarly_named_dotted_call_does_not_false_positive_reach(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach.test_similarly_named_dotted_call_does_not_false_positive_reach  # noqa: E501
        # Positive control, the other direction: a DIFFERENT method whose
        # short name is a superstring of the target's (`other_never_
        # called`) must not count as a reach for `never_called` -- the
        # widened pattern must not turn into a bare substring match.
        _write(
            tmp_path,
            "src/pkg/orphan2.py",
            "class Orphan:\n"
            "    @staticmethod\n"
            "    def never_called():\n"
            "        return 1\n\n"
            "class Other:\n"
            "    @staticmethod\n"
            "    def other_never_called():\n"
            "        return 2\n\n"
            "def use_other():\n"
            "    return Other.other_never_called()\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r
            for r in snap.symbols.values()
            if r.symref.endswith(".never_called") or r.symref.endswith(":never_called")
        )
        diff = Diff(
            base="x", hunks=(Hunk(file="src/pkg/orphan2.py", span=record.span),)
        )
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert _first_rule(violations, "WIRE001") is not None
