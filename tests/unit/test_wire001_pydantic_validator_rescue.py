"""T-2325: WIRE001's own gate logic rescued an autouse pytest fixture
(`_is_autouse_pytest_fixture`, T-1510) but did not rescue a pydantic
`@field_validator`/`@model_validator` (`_is_pydantic_validator`, T-1652)
even though `frob.gates._waive`'s WAIVE008 already ASSUMED it did (its
own `_wire001_symbol_now_rescued` helper calls both predicates). Net
effect before this fix: a fresh pydantic validator with no explicit
outside caller false-positived WIRE001 (real, unwaived error) if left
bare, and false-positived WAIVE008 ("this waiver suppresses nothing,
remove it") if a `frob:waive WIRE001` was added instead -- no way to
cleanly satisfy both checks for this shape.

This file proves the fix: `_new_callable_records` (WIRE001's own new-
symbol proxy) now excludes a pydantic validator the same way it already
excludes an autouse fixture, mirroring the existing
`test_shared_test_fixture_called_from_a_sibling_test_file_is_not_flagged`/
`test_new_public_function_with_no_caller_is_flagged` precedents in
tests/test_gates.py::TestWireGate -- kept in a separate file rather than
added there directly, per this repo's own guidance to avoid editing a
file under another ticket's live lease when a disjoint file will do."""

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


class TestWire001PydanticValidatorRescue:
    """Acceptance: a fresh pydantic validator is rescued from WIRE001,
    and an ordinary new function with no such decorator still fires --
    the fix narrows the false-positive, it does not disable the gate."""

    # frob:ticket T-2325
    def test_fresh_model_validator_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_wire001_pydantic_validator_rescue.py::TestWire001PydanticVali\
        # datorRescue.test_fresh_model_validator_is_not_flagged
        """(MUST FAIL FIRST on pre-T-2325 main): a brand-new pydantic
        `@model_validator(mode="after")` method with no caller outside
        its own tests must NOT fire WIRE001 -- pydantic's own dispatch
        reaches it dynamically, the same dynamic-dispatch shape an
        autouse fixture already gets rescued for."""
        _write(
            tmp_path,
            "src/a.py",
            "from __future__ import annotations\n"
            "from pydantic import BaseModel, model_validator\n\n\n"
            "class Widget(BaseModel):\n"
            "    model_config = {}\n\n"
            "    name: str\n\n"
            '    @model_validator(mode="after")\n'
            '    def _validate_name_nonempty(self) -> "Widget":\n'
            "        if not self.name.strip():\n"
            '            raise ValueError("name must be non-empty")\n'
            "        return self\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if "_validate_name_nonempty" in r.symref
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "_validate_name_nonempty" in v.message
            for v in violations
        )

    # frob:ticket T-2325
    def test_fresh_field_validator_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_wire001_pydantic_validator_rescue.py::TestWire001PydanticVali\
        # datorRescue.test_fresh_field_validator_is_not_flagged
        """Same rescue for the other pydantic validator decorator shape,
        `@field_validator`."""
        _write(
            tmp_path,
            "src/b.py",
            "from __future__ import annotations\n"
            "from pydantic import BaseModel, field_validator\n\n\n"
            "class Gadget(BaseModel):\n"
            "    model_config = {}\n\n"
            "    label: str\n\n"
            '    @field_validator("label")\n'
            "    @classmethod\n"
            "    def _validate_label_nonempty(cls, value: str) -> str:\n"
            "        if not value.strip():\n"
            '            raise ValueError("label must be non-empty")\n'
            "        return value\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if "_validate_label_nonempty" in r.symref
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/b.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "_validate_label_nonempty" in v.message
            for v in violations
        )

    # frob:ticket T-2325
    def test_ordinary_new_function_still_flagged_positive_control(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_wire001_pydantic_validator_rescue.py::TestWire001PydanticVali\
        # datorRescue.test_ordinary_new_function_still_flagged_positive_control
        """Positive control (must-still-pass): an ordinary new function
        with no pydantic decorator and no caller outside its own test
        still fires WIRE001 -- the fix narrows the rescue to the
        pydantic-validator shape specifically, it does not disable
        WIRE001 generally. Mirrors tests/test_gates.py::TestWireGate::
        test_new_public_function_with_no_caller_is_flagged."""
        _write(
            tmp_path,
            "src/c.py",
            "def own_obligations_clean() -> bool:\n    return True\n",
        )
        _write(
            tmp_path,
            "tests/test_c.py",
            "def test_own_obligations_clean() -> None:\n"
            "    assert own_obligations_clean()\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if "own_obligations_clean" in r.symref
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/c.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert any(
            v.rule == "WIRE001" and "own_obligations_clean" in v.message
            for v in violations
        )
