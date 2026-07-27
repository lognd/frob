"""Tests for frob.testing._stability -- per-test stability tracking and
quarantine-with-ticket (docs/modules/testing.md, T-0575)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typani import Err, Ok

from frob.gitio import ProcResult
from frob.testing import (
    FlakeError,
    StabilityEntry,
    evaluate_gate,
    flaky_node_ids,
    is_flaky,
    lift_quarantine,
    load_stability,
    quarantine,
    quarantine_alarms,
    quarantined_node_ids,
    record_outcomes,
)
from frob.testing._stability import (
    DEFAULT_REGRESSION_TAIL_K,
    capture_python_outcomes,
    hard_regression_alarms,
    is_hard_regression,
    track_python_stability,
)
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    transition,
)


class TestRecord:
    def test_persists(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::record_outcomes
        entries = record_outcomes(tmp_path, {"tests/t.py::a": True}).danger_ok
        assert entries["tests/t.py::a"].history == ("P",)
        reloaded = load_stability(tmp_path)
        assert reloaded["tests/t.py::a"].history == ("P",)

    def test_window_bounded(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::record_outcomes
        for i in range(25):
            record_outcomes(tmp_path, {"tests/t.py::a": i % 2 == 0})
        entries = load_stability(tmp_path)
        assert len(entries["tests/t.py::a"].history) == 20

    def test_carries_quarantine(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::record_outcomes
        ticket = new_ticket(
            tmp_path,
            TicketSpec(title="flake", kind=TicketKind.BUG, origin=Origin.AGENT),
        ).danger_ok
        quarantine(tmp_path, "tests/t.py::a", ticket_id=ticket.id)
        record_outcomes(tmp_path, {"tests/t.py::a": False})
        entries = load_stability(tmp_path)
        assert entries["tests/t.py::a"].quarantine_ticket == ticket.id


class TestIsFlaky:
    def test_all_pass_ok(self) -> None:
        # frob:tests src/frob/testing/_stability.py::is_flaky
        entry = StabilityEntry(node_id="x", history=("P", "P", "P"))
        assert is_flaky(entry) is False

    def test_all_fail_ok(self) -> None:
        # frob:tests src/frob/testing/_stability.py::is_flaky
        entry = StabilityEntry(node_id="x", history=("F", "F"))
        assert is_flaky(entry) is False

    def test_mixed_is_flaky(self) -> None:
        # frob:tests src/frob/testing/_stability.py::is_flaky
        entry = StabilityEntry(node_id="x", history=("F", "P"))
        assert is_flaky(entry) is True

    def test_single_run_ok(self) -> None:
        # frob:tests src/frob/testing/_stability.py::is_flaky
        entry = StabilityEntry(node_id="x", history=("F",))
        assert is_flaky(entry) is False

    def test_filters_map(self) -> None:
        # frob:tests src/frob/testing/_stability.py::flaky_node_ids
        entries = {
            "a": StabilityEntry(node_id="a", history=("P", "F")),
            "b": StabilityEntry(node_id="b", history=("P", "P")),
        }
        assert flaky_node_ids(entries) == frozenset({"a"})


class TestHardRegression:
    def test_past_thresh(self) -> None:
        # frob:tests src/frob/testing/_stability.py::is_hard_regression
        entry = StabilityEntry(node_id="x", history=("F", "F", "F"))
        assert is_hard_regression(entry) is True

    def test_under_thresh(self) -> None:
        # frob:tests src/frob/testing/_stability.py::is_hard_regression
        entry = StabilityEntry(node_id="x", history=("F", "F"))
        assert is_hard_regression(entry) is False

    def test_mixed(self) -> None:
        # frob:tests src/frob/testing/_stability.py::is_hard_regression
        entry = StabilityEntry(node_id="x", history=("F", "F", "P"))
        assert is_hard_regression(entry) is False

    def test_tail_stale(self) -> None:
        # frob:tests src/frob/testing/_stability.py::is_hard_regression
        # a stale pass sits early in the window, followed by a
        # DEFAULT_REGRESSION_TAIL_K-long all-fail tail: the whole-window
        # rule alone would never fire (T-0636's gap), but the recent-tail
        # rule must (T-0679).
        entry = StabilityEntry(
            node_id="x", history=("P",) + ("F",) * DEFAULT_REGRESSION_TAIL_K
        )
        assert is_hard_regression(entry) is True

    def test_tail_short(self) -> None:
        # frob:tests src/frob/testing/_stability.py::is_hard_regression
        # only tail_k - 1 consecutive fails after the stale pass: neither
        # the whole-window rule (a pass is present) nor the tail rule
        # (not enough fails yet) should fire.
        entry = StabilityEntry(
            node_id="x", history=("P",) + ("F",) * (DEFAULT_REGRESSION_TAIL_K - 1)
        )
        assert is_hard_regression(entry) is False

    def test_tail_cfg(self) -> None:
        # frob:tests src/frob/testing/_stability.py::is_hard_regression
        # a caller-supplied tail_k narrower than the default still trips
        # on its own shorter fail tail.
        entry = StabilityEntry(node_id="x", history=("P", "F", "P", "F", "F", "F"))
        assert is_hard_regression(entry, tail_k=3) is True
        assert is_hard_regression(entry, tail_k=DEFAULT_REGRESSION_TAIL_K) is False


class TestQuarantine:
    def test_explicit_ticket(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::quarantine
        ticket = new_ticket(
            tmp_path,
            TicketSpec(title="flake", kind=TicketKind.BUG, origin=Origin.AGENT),
        ).danger_ok
        result = quarantine(tmp_path, "tests/t.py::a", ticket_id=ticket.id)
        assert result.is_ok
        assert result.danger_ok == ticket.id
        assert "tests/t.py::a" in quarantined_node_ids(load_stability(tmp_path))

    def test_rejects_bad(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::quarantine
        result = quarantine(tmp_path, "tests/t.py::a", ticket_id="T-9999")
        assert result.is_err
        assert result.danger_err == FlakeError.TicketUnresolvable

    def test_auto_files(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::quarantine
        result = quarantine(tmp_path, "tests/t.py::flaky")
        assert result.is_ok
        ticket_id = result.danger_ok
        from frob.tickets import load_queue

        queue = load_queue(tmp_path).danger_ok
        assert ticket_id in queue.tickets
        assert "flaky" in queue.tickets[ticket_id].title.lower() or "tests/t.py" in (
            queue.tickets[ticket_id].body
        )

    def test_lift_clears(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::lift_quarantine
        ticket = new_ticket(
            tmp_path,
            TicketSpec(title="flake", kind=TicketKind.BUG, origin=Origin.AGENT),
        ).danger_ok
        record_outcomes(tmp_path, {"tests/t.py::a": True})
        quarantine(tmp_path, "tests/t.py::a", ticket_id=ticket.id)
        lifted = lift_quarantine(tmp_path, "tests/t.py::a")
        assert lifted.is_ok
        entries = load_stability(tmp_path)
        assert entries["tests/t.py::a"].quarantine_ticket is None
        assert entries["tests/t.py::a"].history == ("P",)

    def test_lift_unknown_errs(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::lift_quarantine
        result = lift_quarantine(tmp_path, "tests/t.py::never_seen")
        assert result.is_err
        assert result.danger_err == FlakeError.UnknownTest


class TestAlarms:
    def test_closed_still_flaky(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::quarantine_alarms
        ticket = new_ticket(
            tmp_path,
            TicketSpec(title="flake", kind=TicketKind.BUG, origin=Origin.AGENT),
        ).danger_ok
        quarantine(tmp_path, "tests/t.py::a", ticket_id=ticket.id)
        record_outcomes(tmp_path, {"tests/t.py::a": False})
        record_outcomes(tmp_path, {"tests/t.py::a": True})
        transition(tmp_path, ticket.id, TicketState.PLANNED)
        transition(tmp_path, ticket.id, TicketState.IN_PROGRESS)
        transition(tmp_path, ticket.id, TicketState.DROPPED)
        entries = load_stability(tmp_path)
        assert "tests/t.py::a" in quarantine_alarms(tmp_path, entries)

    def test_no_alarm_open(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::quarantine_alarms
        ticket = new_ticket(
            tmp_path,
            TicketSpec(title="flake", kind=TicketKind.BUG, origin=Origin.AGENT),
        ).danger_ok
        quarantine(tmp_path, "tests/t.py::a", ticket_id=ticket.id)
        record_outcomes(tmp_path, {"tests/t.py::a": False})
        record_outcomes(tmp_path, {"tests/t.py::a": True})
        entries = load_stability(tmp_path)
        assert quarantine_alarms(tmp_path, entries) == ()

    def test_no_alarm_stable(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::quarantine_alarms
        ticket = new_ticket(
            tmp_path,
            TicketSpec(title="flake", kind=TicketKind.BUG, origin=Origin.AGENT),
        ).danger_ok
        quarantine(tmp_path, "tests/t.py::a", ticket_id=ticket.id)
        record_outcomes(tmp_path, {"tests/t.py::a": True})
        transition(tmp_path, ticket.id, TicketState.PLANNED)
        transition(tmp_path, ticket.id, TicketState.IN_PROGRESS)
        transition(tmp_path, ticket.id, TicketState.DROPPED)
        entries = load_stability(tmp_path)
        assert quarantine_alarms(tmp_path, entries) == ()

    def test_hard_alarm(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::hard_regression_alarms
        ticket = new_ticket(
            tmp_path,
            TicketSpec(title="flake", kind=TicketKind.BUG, origin=Origin.AGENT),
        ).danger_ok
        quarantine(tmp_path, "tests/t.py::a", ticket_id=ticket.id)
        record_outcomes(tmp_path, {"tests/t.py::a": False})
        record_outcomes(tmp_path, {"tests/t.py::a": False})
        record_outcomes(tmp_path, {"tests/t.py::a": False})
        entries = load_stability(tmp_path)
        # regressed to all-fail: no longer flaky, so the expiry alarm
        # (is_flaky-gated) can never see this -- the hard-regression alarm
        # must, even while the ticket is still open (T-0636).
        assert quarantine_alarms(tmp_path, entries) == ()
        assert hard_regression_alarms(entries) == ("tests/t.py::a",)

    def test_hard_no_alarm_flaky(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::hard_regression_alarms
        ticket = new_ticket(
            tmp_path,
            TicketSpec(title="flake", kind=TicketKind.BUG, origin=Origin.AGENT),
        ).danger_ok
        quarantine(tmp_path, "tests/t.py::a", ticket_id=ticket.id)
        record_outcomes(tmp_path, {"tests/t.py::a": False})
        record_outcomes(tmp_path, {"tests/t.py::a": True})
        record_outcomes(tmp_path, {"tests/t.py::a": False})
        entries = load_stability(tmp_path)
        assert hard_regression_alarms(entries) == ()

    def test_hard_alarm_tail(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::hard_regression_alarms
        ticket = new_ticket(
            tmp_path,
            TicketSpec(title="flake", kind=TicketKind.BUG, origin=Origin.AGENT),
        ).danger_ok
        quarantine(tmp_path, "tests/t.py::a", ticket_id=ticket.id)
        # one stale pass, then a long all-fail tail: the whole-window rule
        # alone (T-0636) would never fire here since a pass is present
        # somewhere in the bounded history -- the recent-tail rule (T-0679)
        # must still surface it.
        record_outcomes(tmp_path, {"tests/t.py::a": True})
        for _ in range(DEFAULT_REGRESSION_TAIL_K):
            record_outcomes(tmp_path, {"tests/t.py::a": False})
        entries = load_stability(tmp_path)
        assert quarantine_alarms(tmp_path, entries) == ()
        assert hard_regression_alarms(entries) == ("tests/t.py::a",)


class TestGate:
    def test_already_ok_stays_ok(self) -> None:
        # frob:tests src/frob/testing/_stability.py::evaluate_gate
        assert evaluate_gate(True, frozenset(), {}) is True

    def test_all_quarantined_ok(self) -> None:
        # frob:tests src/frob/testing/_stability.py::evaluate_gate
        entries = {"a": StabilityEntry(node_id="a", quarantine_ticket="T-0001")}
        assert evaluate_gate(False, frozenset({"a"}), entries) is True

    def test_one_bad_stays_failed(self) -> None:
        # frob:tests src/frob/testing/_stability.py::evaluate_gate
        entries = {"a": StabilityEntry(node_id="a", quarantine_ticket="T-0001")}
        assert evaluate_gate(False, frozenset({"a", "b"}), entries) is False

    def test_hard_regress_fails(self) -> None:
        # frob:tests src/frob/testing/_stability.py::evaluate_gate
        entries = {
            "a": StabilityEntry(
                node_id="a",
                history=("F", "F", "F"),
                quarantine_ticket="T-0001",
            )
        }
        # quarantined, but now a hard regression (all-fail) -- quarantine
        # status alone must not promote this back to green (T-0636).
        assert evaluate_gate(False, frozenset({"a"}), entries) is False

    def test_hard_regress_tail_fails(self) -> None:
        # frob:tests src/frob/testing/_stability.py::evaluate_gate
        entries = {
            "a": StabilityEntry(
                node_id="a",
                history=("P",) + ("F",) * DEFAULT_REGRESSION_TAIL_K,
                quarantine_ticket="T-0001",
            )
        }
        # a stale pass earlier in the window plus a live recent-tail
        # all-fail run: the whole-window rule alone would promote this
        # back to green (T-0636's original gap); the recent-tail rule
        # (T-0679) must keep the gate red.
        assert evaluate_gate(False, frozenset({"a"}), entries) is False


class TestCapture:
    def test_empty_ok(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::capture_python_outcomes
        assert capture_python_outcomes(tmp_path, ()).danger_ok == {}

    def test_spawn_err(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::capture_python_outcomes
        from frob.gitio import GitError

        with patch(
            "frob.testing._stability.run_argv", return_value=Err(GitError.GitFailed)
        ):
            result = capture_python_outcomes(tmp_path, ("tests/t.py::a",))
        assert result.is_err
        assert result.danger_err == FlakeError.CaptureSpawnFailed

    def test_parses_junit(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::capture_python_outcomes
        junit_xml = (
            '<?xml version="1.0"?>'
            "<testsuites><testsuite>"
            '<testcase classname="tests.t" name="a"></testcase>'
            '<testcase classname="tests.t" name="b">'
            "<failure>boom</failure></testcase>"
            "</testsuite></testsuites>"
        )

        def _fake_run_argv(argv, cwd=None, timeout_s=None):  # noqa: ANN001
            report_path = Path(argv[argv.index("--junit-xml") + 1])
            report_path.write_text(junit_xml)
            return Ok(ProcResult(argv=tuple(argv), returncode=1, stdout="", stderr=""))

        with patch("frob.testing._stability.run_argv", side_effect=_fake_run_argv):
            result = capture_python_outcomes(
                tmp_path, ("tests/t.py::a", "tests/t.py::b")
            )
        assert result.is_ok
        assert result.danger_ok == {"tests/t.py::a": True, "tests/t.py::b": False}


class TestTrack:
    def test_captures_then_records(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_stability.py::track_python_stability
        with patch(
            "frob.testing._stability.capture_python_outcomes",
            return_value=Ok({"tests/t.py::a": True}),
        ):
            result = track_python_stability(tmp_path, ("tests/t.py::a",))
        assert result.is_ok
        assert load_stability(tmp_path)["tests/t.py::a"].history == ("P",)
