"""T-0976 send-back (T-0919/T-0948 precedent): behavioral tests pinning
the exact conditions TEST016 reported as surviving mutants inside three
helpers this ticket extracted --
`frob.app.perf_runner._collect_stacks_via_sampler` (perf_runner.py:238,
the `argv and argv[0] == "--"` guard: compare-Eq-swapped and
boolop-And-swapped mutants), `frob.app.ticket_runner.
_render_doable_dispatchable` (ticket_runner.py:539, the `parent_id is not
None and parent_id in queue.tickets` guard: boolop-And-swapped), and
`frob.app.ticket_runner._close_guards_for_ticket` (ticket_runner.py:2103,
the `mutation_evidence is False and cfg.ticket_close_skip_mutation_
evidence` guard: bool-False-negated and boolop-And-swapped). Each test
drives the helper through both branches with an assertion that flips
under the specific mutation named -- see this module's own docstring
comments per test for exactly which mutant each kills.
"""


from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from frob.app import perf_runner, ticket_runner
from frob.app.config import AppConfig
from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState


def _ticket(*, ticket_id: str, parent: str | None = None, priority=None) -> Ticket:
    """Minimal real `Ticket` fixture (mirrors `tests/test_tickets_lease.py`'s
    own `_ticket` helper) -- just enough fields for `_render_doable_
    dispatchable`'s grouping/row-rendering path to run end to end."""
    from frob.tickets import Priority

    return Ticket(
        id=ticket_id,
        title=f"ticket {ticket_id}",
        state=TicketState.QUEUED,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        priority=priority or Priority.MEDIUM,
        blocked_by=(),
        parent=parent,
        scope=(),
        evidence=(),
        attachments=(),
        body="## Description\nsomething\n",
    )


class TestCollectStacksViaSamplerArgvStripping:
    """Pins perf_runner.py:238's `if argv and argv[0] == "--":` guard."""

    def _captured_argv(
        self, monkeypatch: pytest.MonkeyPatch, cfg: AppConfig
    ) -> list[str]:
        """Run `_collect_stacks_via_sampler(cfg)` with `run_sampled`
        stubbed to just invoke the workload once (bypassing real stack
        sampling) and `pytest.main` stubbed to record its own `argv`
        instead of actually running a suite -- returns the argv the
        workload closure actually passed to `pytest.main`."""
        import pytest as _pytest_module

        captured: dict[str, list[str]] = {}

        def _fake_run_sampled(fn, config=None):  # noqa: ANN001
            fn()
            return [], 0.0

        def _fake_pytest_main(argv):  # noqa: ANN001
            captured["argv"] = list(argv)

        monkeypatch.setattr("frob.perf.run_sampled", _fake_run_sampled)
        monkeypatch.setattr(_pytest_module, "main", _fake_pytest_main)
        perf_runner._collect_stacks_via_sampler(cfg)
        return captured["argv"]

    def test_non_marker_first_arg_is_not_stripped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`argv=["foo"]`: the real guard is False (argv[0] != "--"), so
        "foo" must survive untouched. This single case kills BOTH named
        mutants at once: compare-Eq-swapped (`!=` would make the guard
        True and wrongly strip "foo") and boolop-And-swapped (`or` would
        short-circuit True on `argv` alone and also wrongly strip "foo")."""
        cfg = AppConfig(perf_argv=["foo"])
        assert self._captured_argv(monkeypatch, cfg) == ["foo"]

    def test_marker_first_arg_is_stripped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`argv=["--", "foo"]`: the real guard is True, so the leading
        "--" marker is stripped and only "foo" remains -- the normal-path
        pin the guard exists for."""
        cfg = AppConfig(perf_argv=["--", "foo"])
        assert self._captured_argv(monkeypatch, cfg) == ["foo"]

    def test_empty_argv_falls_back_to_dash_q(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`argv=[]`: `argv and ...` must short-circuit False without
        ever indexing `argv[0]` (which would raise on an empty list) --
        falls through to the `not argv` default of `["-q"]`."""
        cfg = AppConfig(perf_argv=[])
        assert self._captured_argv(monkeypatch, cfg) == ["-q"]


class TestRenderDoableDispatchableByParentGrouping:
    """Pins ticket_runner.py:539's `if parent_id is not None and
    parent_id in queue.tickets:` guard inside the `--by-parent` grouping
    path."""

    def test_parent_id_not_in_queue_falls_back_to_no_parent_bucket(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A ticket whose `parent` is set but does NOT resolve in
        `queue.tickets` (a dangling/foreign parent id) must group under
        "(no parent)", not raise. This is the exact case the
        boolop-And-swapped mutant (`or`) breaks: `parent_id is not
        None`(True) `or` `parent_id in queue.tickets`(False) evaluates
        True under `or`, so the mutant takes the `if` branch and does
        `queue.tickets[parent_id].title` -- a `KeyError` on a parent id
        that was never in the queue. The real `and` guard correctly
        short-circuits to the `else` branch instead."""
        t = _ticket(ticket_id="T-0001", parent="T-9999")
        queue = TicketQueue(tickets={"T-0001": t})
        cfg = AppConfig(ticket_doable_by_parent=True)

        with caplog.at_level("INFO"):
            ticket_runner._render_doable_dispatchable([t], {}, queue, cfg)

        assert not any(r.levelname == "ERROR" for r in caplog.records)
        assert any("(no parent)" in r.message for r in caplog.records)

    def test_parent_id_present_in_queue_uses_its_title(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A ticket whose `parent` DOES resolve in `queue.tickets` groups
        under that parent's own title -- the normal-path pin."""
        parent = _ticket(ticket_id="T-0001")
        child = _ticket(ticket_id="T-0002", parent="T-0001")
        queue = TicketQueue(tickets={"T-0001": parent, "T-0002": child})
        cfg = AppConfig(ticket_doable_by_parent=True)

        with caplog.at_level("INFO"):
            ticket_runner._render_doable_dispatchable([child], {}, queue, cfg)

        assert any(parent.title in r.message for r in caplog.records)
        assert not any("(no parent)" in r.message for r in caplog.records)


class TestCloseGuardsMutationEvidenceDowngrade:
    """Pins ticket_runner.py:2103's `if mutation_evidence is False and
    cfg.ticket_close_skip_mutation_evidence:` guard inside
    `_close_guards_for_ticket`."""

    def _guards(
        self, monkeypatch: pytest.MonkeyPatch, *, mutation_evidence, skip: bool
    ):  # noqa: ANN001, ANN202
        """Run `_close_guards_for_ticket` with its five OTHER sub-guard
        helpers stubbed to fixed, uninteresting values so only the
        `mutation_evidence`/`skip` interaction under test varies. T-1410/
        T-1387 each added one more independently-computed guard
        (gate_claims_verified, own_obligations_clean) -- stubbed here to
        `None` (skip) same as every other uninteresting guard, so this
        test file's own fixed `object()` stand-in ticket never has to grow
        real `.acceptance`/diff-shaped attributes just to satisfy them."""
        monkeypatch.setattr(
            ticket_runner, "_covers_scope_for_ticket", lambda root, t: None
        )
        monkeypatch.setattr(
            ticket_runner, "_covers_review_for_ticket", lambda root, cfg, t: None
        )
        monkeypatch.setattr(
            ticket_runner,
            "_close_mutation_evidence_for_ticket",
            lambda root, t, base_ref="main": mutation_evidence,
        )
        monkeypatch.setattr(
            ticket_runner, "_reverify_evidence_for_close", lambda root, t: None
        )
        monkeypatch.setattr(
            ticket_runner, "_close_gate_claims_for_ticket", lambda root, t: None
        )
        monkeypatch.setattr(
            ticket_runner, "_close_own_obligations_for_ticket", lambda root, t: None
        )
        cfg = AppConfig(ticket_close_skip_mutation_evidence=skip)
        return ticket_runner._close_guards_for_ticket(Path("."), cfg, object())

    def test_true_mutation_evidence_with_skip_flag_is_never_downgraded(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`mutation_evidence=True`, `--skip-mutation-evidence` set: the
        real guard (`True is False`) is False regardless of the flag, so
        `mutation_evidence` must stay `True`, unchanged. This single case
        kills BOTH named mutants: bool-False-negated (`is True` would
        make the guard True here and wrongly downgrade to `None`) and
        boolop-And-swapped (`or` would make the guard True on the flag
        alone and also wrongly downgrade to `None`)."""
        _covers_scope, _reviewed, mutation_evidence, _reverified, _claims, _own = (
            self._guards(monkeypatch, mutation_evidence=True, skip=True)
        )
        assert mutation_evidence is True

    def test_false_mutation_evidence_with_skip_flag_is_downgraded_to_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`mutation_evidence=False`, `--skip-mutation-evidence` set: the
        real guard is True, so the escape hatch downgrades the
        confirmatory-only finding to `None` (skip) -- the normal-path pin
        the guard exists for."""
        _covers_scope, _reviewed, mutation_evidence, _reverified, _claims, _own = (
            self._guards(monkeypatch, mutation_evidence=False, skip=True)
        )
        assert mutation_evidence is None

    def test_false_mutation_evidence_without_skip_flag_stays_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`mutation_evidence=False` with NO `--skip-mutation-evidence`:
        the guard's second operand is False, so `mutation_evidence` must
        stay `False` (the confirmatory-only refusal still fires
        upstream) -- confirms the flag half of the `and` is load-bearing
        too, not just the `is False` half."""
        _covers_scope, _reviewed, mutation_evidence, _reverified, _claims, _own = (
            self._guards(monkeypatch, mutation_evidence=False, skip=False)
        )
        assert mutation_evidence is False
