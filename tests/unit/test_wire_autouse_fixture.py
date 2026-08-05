# frob:ticket T-1510
"""WIRE001 autouse-pytest-fixture exemption (T-1510): a new
`@pytest.fixture(autouse=True)`-decorated function has no direct-call
token anywhere in the tree -- pytest's own fixture-injection machinery
reaches it implicitly for every test in scope -- so WIRE001 must not
flag it as an unwired new symbol. Split into its own file rather than
`tests/test_gates.py::TestWireGate` because that file's `tests/**` lease
was held by a concurrent in-progress ticket at the time this was
written (T-1510's Done report)."""

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


class TestWireGateAutouseFixtureExemption:
    """T-1510: WIRE001 must treat a new autouse pytest fixture as reached,
    not as an unwired new symbol -- while an ordinary new private helper
    with the same "no direct caller" shape still fires normally."""

    def test_new_autouse_fixture_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_wire_autouse_fixture.py::TestWireGateAutouseFixtureExemption.test_new_autouse_fixture_is_not_flagged  # noqa: E501
        _write(
            tmp_path,
            "tests/test_a.py",
            "import pytest\n\n"
            "@pytest.fixture(autouse=True)\n"
            "def _npx_available(monkeypatch) -> None:\n"
            "    monkeypatch.setattr('shutil.which', lambda name: '/usr/bin/npx')\n\n"
            "def test_something() -> None:\n"
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "_npx_available" in r.symref)
        diff = Diff(base="x", hunks=(Hunk(file="tests/test_a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert _first_rule(violations, "WIRE001") is None

    def test_new_plain_test_helper_with_no_caller_is_still_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_wire_autouse_fixture.py::TestWireGateAutouseFixtureExemption.test_new_plain_test_helper_with_no_caller_is_still_flagged  # noqa: E501
        # Negative control: a non-fixture private helper defined in a test
        # file, never called by any test, still fires -- the autouse
        # exemption must not swallow ordinary dead code just because it
        # lives in a test file.
        _write(
            tmp_path,
            "tests/test_b.py",
            "def _unused_helper() -> bool:\n    return True\n\n"
            "def test_something() -> None:\n    assert True\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "_unused_helper" in r.symref)
        diff = Diff(base="x", hunks=(Hunk(file="tests/test_b.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        v = _first_rule(violations, "WIRE001")
        assert v is not None
        assert "_unused_helper" in v.message

    def test_non_autouse_fixture_with_no_caller_is_still_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_wire_autouse_fixture.py::TestWireGateAutouseFixtureExemption.test_non_autouse_fixture_with_no_caller_is_still_flagged  # noqa: E501
        # Negative control: a `@pytest.fixture` WITHOUT autouse=True is a
        # normal fixture, reached only by a test that names it as a
        # parameter -- WIRE001's text scan cannot see that either, so it
        # is deliberately still flagged (out of scope for this ticket,
        # which is about the AUTOUSE shape specifically).
        _write(
            tmp_path,
            "tests/test_c.py",
            "import pytest\n\n"
            "@pytest.fixture\n"
            "def _explicit_fixture():\n    return 1\n\n"
            "def test_something() -> None:\n    assert True\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if "_explicit_fixture" in r.symref
        )
        diff = Diff(base="x", hunks=(Hunk(file="tests/test_c.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        v = _first_rule(violations, "WIRE001")
        assert v is not None
        assert "_explicit_fixture" in v.message
