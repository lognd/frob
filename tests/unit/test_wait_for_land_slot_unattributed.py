"""T-2807 evidence: `wait_for_land_slot.py`'s new unattributed-land-process
probe, kept in its own file rather than `tests/unit/test_coordinator_
scripts.py` (leased by a concurrent ticket at the time this was written).

Mirrors that file's own loading convention (`tests.unit.conftest._load_
script`) so both `fleet_status.py` and `wait_for_land_slot.py` are ordinary
importable Python here too -- no subprocess needed for the pure logic.
"""

from __future__ import annotations

from tests.unit.conftest import _load_script

wait_for_land_slot = _load_script("wait_for_land_slot")


def _row(argv: str) -> dict:
    """A minimal `land_process_rows()`-shaped row carrying just the `argv`
    field `probe_unattributed_land_process` reads."""
    return {"pid": 1, "etimes": 5, "cputime": "00:00:01", "argv": argv}


class TestProbeUnattributedLandProcess:
    """`probe_unattributed_land_process`: the T-2807 fix itself."""

    def test_true_when_a_row_has_no_parseable_ticket_id(self) -> None:
        """A live `frob ticket land` process whose argv carries no
        `T-####` token (e.g. a `--queue`/`--drain` batch invocation) --
        exactly the row `land_invocations()` silently drops -- must be
        reported as an unattributed land in progress."""
        rows = [_row("uv run frob ticket land --queue --worktree /repo")]
        assert (
            wait_for_land_slot.probe_unattributed_land_process(rows) is True
        )

    def test_false_when_every_row_has_a_ticket_id(self) -> None:
        """A normal, fully-attributed `frob ticket land T-1234` row must
        not be reported as unattributed -- it is already correctly
        counted by the plain `LANDS IN FLIGHT` reading."""
        rows = [_row("uv run frob ticket land T-1234 --worktree /repo")]
        assert (
            wait_for_land_slot.probe_unattributed_land_process(rows) is False
        )

    def test_false_when_no_rows_at_all(self) -> None:
        """No live land processes at all: never reported as unattributed
        (an empty scan is not evidence of an unattributed one)."""
        assert wait_for_land_slot.probe_unattributed_land_process([]) is False


class TestWaitForSlotUnattributedGate:
    """`wait_for_slot`'s new `unattributed_probe` gate -- the two T-2807
    positive controls, both directions."""

    def test_unattributed_land_process_blocks_an_otherwise_free_slot(
        self,
    ) -> None:
        """T-2807 positive control (direction 1, the repro itself): the
        text probe reads a genuinely free `LANDS IN FLIGHT: 0` (as it did
        in the live incident), but `unattributed_probe` reports `True`
        (planting the startup-window/unparseable-id case) -- `wait_for_
        slot` must NOT report a free slot, and must time out with
        `EXIT_TIMEOUT` (a real condition was measured, just never
        satisfied), never `EXIT_SLOT_FREE`."""
        ticks: list[tuple[int | None, float]] = []

        def _fake_probe(command: list[str]) -> int | None:
            return 0

        original = wait_for_land_slot.probe_lands_in_flight
        try:
            wait_for_land_slot.probe_lands_in_flight = _fake_probe  # type: ignore[assignment]  # ty: ignore[unresolved-attribute]  # noqa: E501
            exit_code, summary = wait_for_land_slot.wait_for_slot(
                command=["irrelevant"],
                max_in_flight=0,
                timeout_s=0.05,
                poll_interval_s=0.01,
                sleep=lambda _s: None,
                now=_counter(),
                on_tick=lambda reading, elapsed: ticks.append((reading, elapsed)),
                unattributed_probe=lambda: True,
            )
        finally:
            wait_for_land_slot.probe_lands_in_flight = original  # ty: ignore[unresolved-attribute]
        assert exit_code == wait_for_land_slot.EXIT_TIMEOUT
        assert "LANDS IN FLIGHT" in summary
        assert ticks  # the probe genuinely ran and measured reading=0

    def test_no_land_at_all_still_returns_free_promptly(self) -> None:
        """T-2807 positive control (direction 2, the must-still-pass
        control): with no land in flight AND `unattributed_probe`
        reporting `False`, the slot is still reported free immediately --
        the fix must not degenerate into "never reports free"."""

        def _fake_probe(command: list[str]) -> int | None:
            return 0

        original = wait_for_land_slot.probe_lands_in_flight
        try:
            wait_for_land_slot.probe_lands_in_flight = _fake_probe  # type: ignore[assignment]  # ty: ignore[unresolved-attribute]  # noqa: E501
            exit_code, summary = wait_for_land_slot.wait_for_slot(
                command=["irrelevant"],
                max_in_flight=0,
                timeout_s=5.0,
                poll_interval_s=0.01,
                sleep=lambda _s: None,
                now=_counter(),
                unattributed_probe=lambda: False,
            )
        finally:
            wait_for_land_slot.probe_lands_in_flight = original  # ty: ignore[unresolved-attribute]
        assert exit_code == wait_for_land_slot.EXIT_SLOT_FREE
        assert "slot free" in summary


def _counter():
    """A deterministic `now()` stand-in that advances a fixed step every
    call, so a test never actually sleeps for real wall-clock time."""
    state = {"t": 0.0}

    def _now() -> float:
        state["t"] += 0.02
        return state["t"]

    return _now
