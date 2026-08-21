"""T-2753: WIRE001's text-scan reach check
(`frob.gates._wire._is_reached_outside_diff_tests`) only rescued an
AUTOUSE pytest fixture (`_is_autouse_pytest_fixture`, T-1510) outright --
`_new_callable_records` never even asked whether it was reachable. A
non-autouse fixture consumed via pytest's ordinary dependency-injection
shape (declared as a test/fixture function's own PARAMETER, e.g. `def
test_x(self, outside_view):`) went through the ordinary call-shaped scan
instead, which can never match it: a consumed fixture is never followed
by a call token. `tests/unit/test_app_runners_batch6.py::
_real_console_handlers` carried exactly this waiver (T-2743's SC004
disposition) until this ticket's own land removed it -- the fix below
makes it unnecessary.

This file proves the fix (`_is_pytest_fixture`/
`_is_fixture_consumed_as_parameter`): a fresh non-autouse fixture named
as a parameter by some OTHER function (same file, a sibling test file,
or a file that imports it directly, T-2492's own cross-module fixture-
import precedent) is rescued, while one nothing ever requests still
fires -- the fix narrows the false positive, it does not exempt every
fixture outright. Kept in a separate file per this repo's own precedent
(`test_wire001_property_attribute_access.py`'s own module docstring:
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


class TestWire001FixtureParameterAccess:
    """Acceptance: a fresh non-autouse fixture consumed as a test/fixture
    function's own parameter is rescued from WIRE001, same-file or
    cross-file; a fixture nothing ever requests, and an ordinary new
    function, still fire -- the fix narrows the false positive, it does
    not disable the gate."""

    # frob:ticket T-2753
    def test_fixture_consumed_by_a_test_in_the_same_file_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParame\
        # terAccess.test_fixture_consumed_by_a_test_in_the_same_file_is_not_flagged
        """(MUST FAIL FIRST on pre-T-2753 main): a brand-new non-autouse
        `@pytest.fixture` named as a parameter by a `test_*` function in
        the SAME file must NOT fire WIRE001 -- the exact
        `_real_console_handlers`/`TestFmtRunnerJsonGuard` shape T-2492
        hit, now generalized."""
        _write(
            tmp_path,
            "tests/test_a.py",
            "import pytest\n\n\n"
            "@pytest.fixture\n"
            "def outside_view():\n"
            "    return object()\n\n\n"
            "def test_uses_it(outside_view) -> None:\n"
            "    assert outside_view is not None\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "outside_view" in r.symref)
        diff = Diff(base="x", hunks=(Hunk(file="tests/test_a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "outside_view" in v.message for v in violations
        )

    # frob:ticket T-2753
    def test_fixture_consumed_by_a_test_in_a_different_file_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParame\
        # terAccess.test_fixture_consumed_by_a_test_in_a_different_file_is_not_flagged
        """Cross-file: a fixture imported into a SIBLING test module and
        named there as a parameter -- T-2492's own cross-module fixture-
        import precedent (`test_app_runners_json_guard_t2492.py` imports
        `_real_console_handlers` from `test_app_runners_batch6.py`) --
        must also be rescued."""
        _write(
            tmp_path,
            "tests/_fixtures.py",
            "import pytest\n\n\n"
            "@pytest.fixture\n"
            "def shared_view():\n"
            "    return object()\n",
        )
        _write(
            tmp_path,
            "tests/test_b.py",
            "from tests._fixtures import shared_view  # noqa: F401\n\n\n"
            "def test_uses_it(shared_view) -> None:\n"
            "    assert shared_view is not None\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "shared_view" in r.symref)
        diff = Diff(
            base="x", hunks=(Hunk(file="tests/_fixtures.py", span=record.span),)
        )
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "shared_view" in v.message for v in violations
        )

    # frob:ticket T-2753
    def test_fixture_consumed_only_by_another_fixture_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParame\
        # terAccess.test_fixture_consumed_only_by_another_fixture_is_not_flagged
        """A fixture requested by ANOTHER fixture's own parameter list
        (not a `test_*` function directly) is also dependency-injection
        consumption, not a call -- must be rescued the same way."""
        _write(
            tmp_path,
            "tests/test_c.py",
            "import pytest\n\n\n"
            "@pytest.fixture\n"
            "def base_view():\n"
            "    return object()\n\n\n"
            "@pytest.fixture\n"
            "def derived_view(base_view):\n"
            "    return base_view\n\n\n"
            "def test_uses_it(derived_view) -> None:\n"
            "    assert derived_view is not None\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "base_view" in r.symref)
        diff = Diff(base="x", hunks=(Hunk(file="tests/test_c.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "base_view" in v.message for v in violations
        )

    # frob:ticket T-2753
    def test_fixture_with_no_consumer_anywhere_still_flagged_positive_control(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParame\
        # terAccess.test_fixture_with_no_consumer_anywhere_still_flagged_positive_contr\
        # ol
        """Positive control (must-still-pass): a genuinely unrequested
        non-autouse fixture -- no function anywhere names it as a
        parameter -- still fires WIRE001. The fix rescues a real
        consumer, it does not exempt every fixture outright."""
        _write(
            tmp_path,
            "tests/test_d.py",
            "import pytest\n\n\n"
            "@pytest.fixture\n"
            "def unused_view():\n"
            "    return object()\n\n\n"
            "def test_something_else() -> None:\n"
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "unused_view" in r.symref)
        diff = Diff(base="x", hunks=(Hunk(file="tests/test_d.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert any(
            v.rule == "WIRE001" and "unused_view" in v.message for v in violations
        )

    # frob:ticket T-2753
    def test_ordinary_new_function_still_flagged_positive_control(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParame\
        # terAccess.test_ordinary_new_function_still_flagged_positive_control
        """Second positive control: an ordinary (non-fixture) new function
        with no caller outside its own tests still fires WIRE001 -- the
        fixture-parameter rescue is gated on `_is_pytest_fixture`, so a
        plain function whose NAME happens to be passed as some other
        function's parameter (not a fixture-decorated one) is NOT newly
        rescued by this fix."""
        _write(
            tmp_path,
            "src/e.py",
            "def own_obligations_clean() -> bool:\n    return True\n",
        )
        _write(
            tmp_path,
            "tests/test_e.py",
            "def test_own_obligations_clean() -> None:\n"
            "    assert own_obligations_clean()\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if "own_obligations_clean" in r.symref
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/e.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert any(
            v.rule == "WIRE001" and "own_obligations_clean" in v.message
            for v in violations
        )
