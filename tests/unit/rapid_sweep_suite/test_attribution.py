"""Finding-attribution and revalidation tests for `frob.app.ticket_runner._rapid_sweep`
(T-3595 split of the former tests/unit/test_rapid_sweep.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from frob.app.ticket_runner import _rapid_sweep
from frob.app.ticket_runner._rapid_sweep import (
    _attribute_new_findings,
    _build_regression_body,
    _identities_still_reproducing,
    _regression_count_line,
    _reverify_unfiled_pairs_at_file_time,
    _true_finding_count_for_identities,
)
from tests.conftest import (
    _git_commit,
    _init_git_repo,
)


class TestAttributeNewFindings:
    """`_attribute_new_findings` degrades to `{}` (no attribution info,
    never a false 'everything unattributed') whenever the queue or the
    graph is unavailable."""

    def test_empty_queue_returns_empty_mapping(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestAttributeNewFindings.test_empty_queue_returns_empty_mapping  # noqa: E501
        assert _attribute_new_findings(tmp_path, [("RULE1", "a.py")]) == {}

    def test_attributed_and_unattributed_round_trip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestAttributeNewFindings.test_attributed_and_unattributed_round_trip  # noqa: E501
        import frob.verify._attribution as attribution_mod
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.verify import record_intent

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        call_graph = CallGraph(calls={})
        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, call_graph),
        )
        result = _attribute_new_findings(
            tmp_path, [("RULE1", "a.py", 2), ("RULE2", "nowhere.py", 9)]
        )
        assert result[("RULE1", "a.py")].status == "attributed"
        assert result[("RULE1", "a.py")].commit_sha == "commitA"
        assert result[("RULE2", "nowhere.py")].status == "unattributed"


# frob:ticket T-1935
class TestTrueFindingCount:
    """`_true_finding_count_for_identities` re-measures the TRUE
    per-finding count for a set of `(rule, file)` identities -- proving
    the T-1923 undercount (6 identities reported, 19 real findings) is
    now recoverable rather than silently lost."""

    # frob:ticket T-1935
    @staticmethod
    def _ok_result(stdout: str):
        from typani import Ok

        class _Proc:
            def __init__(self, stdout: str) -> None:
                self.stdout = stdout
                self.returncode = 1

        return Ok(_Proc(stdout))

    # frob:ticket T-1935
    def test_counts_every_diagnostic_matching_an_identity(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestTrueFindingCount.test_counts_every_diagnostic_matching_an_identity  # noqa: E501
        # T-1923's real shape: 5 files each carrying MULTIPLE COV003
        # findings (18 total) plus one F401 -- a coarse (rule, file)
        # identity set has only 6 entries, but the true finding count is
        # 19. This reproduces that undercount and proves the fix
        # recovers the real number.
        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {
                            "code": "COV003",
                            "file": "tickets/T-1872",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1872",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1895",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1895",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1895",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1895",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1896",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1896",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1900",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1900",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1900",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1900",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1900",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1906",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1906",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1906",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1906",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1906",
                            "severity": "error",
                        },
                        {"code": "F401", "file": "src/frob/x.py", "severity": "error"},
                        # A finding NOT in `pairs` below must not be counted.
                        {"code": "SCOPE001", "file": "other.py", "severity": "error"},
                    ],
                }
            ]
        }
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result(json.dumps(payload)),
        )
        pairs = frozenset(
            {
                ("COV003", "tickets/T-1872"),
                ("COV003", "tickets/T-1895"),
                ("COV003", "tickets/T-1896"),
                ("COV003", "tickets/T-1900"),
                ("COV003", "tickets/T-1906"),
                ("F401", "src/frob/x.py"),
            }
        )
        assert len(pairs) == 6
        count = _true_finding_count_for_identities(tmp_path, pairs)
        assert count == 19

    # frob:ticket T-1935
    def test_unparsable_json_is_none_not_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestTrueFindingCount.test_unparsable_json_is_none_not_zero  # noqa: E501
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result("not json at all"),
        )
        assert (
            _true_finding_count_for_identities(tmp_path, frozenset({("R", "f.py")}))
            is None
        )

    # frob:ticket T-1935
    def test_spawn_refused_is_none_not_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestTrueFindingCount.test_spawn_refused_is_none_not_zero  # noqa: E501
        from typani import Err

        from frob.process._guard import ProcessGuardError

        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: Err(ProcessGuardError.ExecDisabled),
        )
        assert (
            _true_finding_count_for_identities(tmp_path, frozenset({("R", "f.py")}))
            is None
        )


# frob:ticket T-2006
class TestIdentitiesStillReproducing:
    """T-2006: `_identities_still_reproducing` -- which of a candidate
    set STILL reproduce right now, as an identity set (not merely a
    count) -- what `revalidate_dispatchable_sweep_tickets` needs to
    decide which sweep-filed tickets to drop."""

    # frob:ticket T-2006
    @staticmethod
    def _ok_result(stdout: str):
        from typani import Ok

        class _Proc:
            def __init__(self, stdout: str) -> None:
                self.stdout = stdout
                self.returncode = 1

        return Ok(_Proc(stdout))

    # frob:ticket T-2006
    def test_only_reproducing_identities_returned(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestIdentitiesStillReproducing.test_only_reproducing_identities_returned  # noqa: E501
        import json

        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {"code": "COV003", "file": "a.py", "severity": "error"},
                        # DOC002/b.py is in the queried `pairs` below but
                        # NOT in this fresh measurement -- it has
                        # resolved and must not appear in the result.
                        {"code": "F401", "file": "unrelated.py", "severity": "error"},
                    ],
                }
            ]
        }
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result(json.dumps(payload)),
        )
        result = _identities_still_reproducing(
            tmp_path, frozenset({("COV003", "a.py"), ("DOC002", "b.py")})
        )
        assert result == frozenset({("COV003", "a.py")})

    # frob:ticket T-2006
    def test_unmeasurable_is_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestIdentitiesStillReproducing.test_unmeasurable_is_none  # noqa: E501
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result("not json at all"),
        )
        assert (
            _identities_still_reproducing(tmp_path, frozenset({("R", "f.py")})) is None
        )

    # frob:ticket T-2521
    def test_failed_silent_tool_result_is_unmeasurable_not_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestIdentitiesStillReproducing.test_failed_silent_tool_result_is_unmeasurable_not_zero  # noqa: E501
        """T-2521 required control #2: a re-measurement whose `ruff-check`
        (or any tool) FAILED (`exit_code != 0`) with zero error
        diagnostics -- the malformed-JSON shape T-2521's own investigation
        reproduced directly against this repo's real `parse_ruff_json` --
        must read as unmeasurable, never as "measured, none of the
        candidates reproduce". Before this fix, this exact JSON shape
        would have made `_identities_still_reproducing` return an empty
        set (not `None`), and the caller would have read that as
        `vanished = all_pairs`, dropping a ticket whose findings the
        run never actually managed to check."""
        import json

        payload = {
            "results": [
                {
                    "tool": "ruff-check",
                    "exit_code": 1,
                    "diagnostics": [],
                    "summary": "malformed JSON: Expecting value",
                },
            ]
        }
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result(json.dumps(payload)),
        )
        result = _identities_still_reproducing(
            tmp_path, frozenset({("E501", "src/frob/x.py")})
        )
        assert result is None


# frob:ticket T-2006
# frob:ticket T-2078
# frob:ticket T-2089
class TestRevalidateDispatchableSweepTickets:
    """T-2006, end-to-end: `frob ticket doable`'s residual gap after
    T-1983 -- a sweep-filed ticket must be re-verified at DISPATCH time,
    not only inside the next unrelated land's own sweep."""

    # frob:ticket T-2006
    def test_no_sweep_tickets_is_zero_cost(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestRevalidateDispatchableSweepTickets.test_no_sweep_tickets_is_zero_cost  # noqa: E501
        called = []
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: called.append(1),
        )

        class _PlainTicket:
            title = "some ordinary ticket"
            body = "nothing sweep-shaped here"

        dropped = _rapid_sweep.revalidate_dispatchable_sweep_tickets(
            tmp_path, [_PlainTicket()]
        )
        assert dropped == ()
        assert called == []  # no check spawn was attempted at all

    # frob:ticket T-2006
    def test_fully_resolved_candidate_is_dropped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestRevalidateDispatchableSweepTickets.test_fully_resolved_candidate_is_dropped  # noqa: E501
        from frob.tickets import TicketState, load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        # Fresh measurement: COV003/a.py no longer appears at all.
        import json

        payload = {"results": [{"tool": "gate-summary", "diagnostics": []}]}
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: TestIdentitiesStillReproducing._ok_result(
                json.dumps(payload)
            ),
        )

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())
        dropped = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert dropped == (ticket_id,)

        requeried = load_queue(tmp_path)
        assert requeried.is_ok
        assert requeried.danger_ok.tickets[ticket_id].state == TicketState.DROPPED

    # frob:ticket T-2006
    def test_still_reproducing_candidate_is_left_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestRevalidateDispatchableSweepTickets.test_still_reproducing_candidate_is_left_untouched  # noqa: E501
        from frob.tickets import TicketState, load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        # Fresh measurement: COV003/a.py STILL reproduces.
        import json

        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {"code": "COV003", "file": "a.py", "severity": "error"}
                    ],
                }
            ]
        }
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: TestIdentitiesStillReproducing._ok_result(
                json.dumps(payload)
            ),
        )

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())
        dropped = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert dropped == ()

        requeried = load_queue(tmp_path)
        assert requeried.is_ok
        assert requeried.danger_ok.tickets[ticket_id].state == TicketState.QUEUED

    # frob:ticket T-2006
    def test_unmeasurable_recheck_drops_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestRevalidateDispatchableSweepTickets.test_unmeasurable_recheck_drops_nothing  # noqa: E501
        from frob.tickets import TicketState, load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: TestIdentitiesStillReproducing._ok_result(
                "not json at all"
            ),
        )

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())
        dropped = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert dropped == ()

        requeried = load_queue(tmp_path)
        assert requeried.is_ok
        assert requeried.danger_ok.tickets[ticket_id].state == TicketState.QUEUED

    # frob:ticket T-2106
    def test_uncached_recheck_uses_the_doable_budget_not_the_sweep_budget(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestRevalidateDispatchableSweepTickets.test_uncached_recheck_uses_the_doable_budget_not_the_sweep_budget  # noqa: E501
        """T-2106: measured, `frob ticket doable`'s own sweep re-
        verification took 301.2s -- almost exactly `_TRUE_COUNT_BUDGET_S`
        (300), the constant sized for the deferred POST-LAND sweep, not
        an interactive query. The doable-time path (this function, via
        `_reproducing_identities_cached`) must spawn its own re-check with
        `_DOABLE_REVALIDATION_BUDGET_S` (20), never the 300s sweep
        budget -- verified here by capturing the actual spawned argv
        rather than trusting a wall-clock proxy."""
        from frob.tickets import load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok

        captured_argv: list[list[str]] = []

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN201, ARG001
            captured_argv.append(list(argv))
            return TestIdentitiesStillReproducing._ok_result(
                '{"results": [{"tool": "gate-summary", "diagnostics": []}]}'
            )

        monkeypatch.setattr("frob.process._guard.guarded_subprocess_run", _fake_run)
        # T-2089's cache is content-keyed on tree state; a non-repo
        # tmp_path makes `_tree_state_key` return None (git spawn fails),
        # so this exercises the uncached spawn path deterministically.

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())
        _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)

        assert len(captured_argv) == 1
        argv = captured_argv[0]
        assert "--budget" in argv
        budget_value = argv[argv.index("--budget") + 1]
        assert budget_value == str(_rapid_sweep._DOABLE_REVALIDATION_BUDGET_S)
        assert budget_value != str(_rapid_sweep._TRUE_COUNT_BUDGET_S)

    # frob:ticket T-2078
    def test_terminal_ticket_is_not_selected_and_logs_no_invalid_transition(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests \
        # tests/unit/rapid_sweep_suite/test_attribution.py::TestRevalidateDispatchableSweepTickets.test_terminal_ticket_is_not_selected_and_logs_no_invalid_transition  # noqa: E501
        """T-2078: `revalidate_dispatchable_sweep_tickets` is called from
        `doable`'s render path against the FULL candidate set -- unlike
        `_close_resolved_sweep_tickets`, it never filtered out
        already-terminal (`dropped`/`done`) tickets before this fix, so a
        resolved-but-already-dropped sweep ticket got a doomed
        `dropped -> dropped` transition attempted on every single
        `frob ticket doable` call: 9 InvalidTransition errors and 9
        dirtied files per invocation in the measured incident. This test
        MUST fail against pre-fix main (it would log the illegal
        transition and dirty the ticket's file)."""
        import json

        from frob.tickets import TicketState, drop_ticket, load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        # Already resolved by hand -- the ticket is TERMINAL before this
        # sweep ever runs, exactly like 7 of the 9 tickets in the
        # measured incident (`dropped -> dropped`).
        dropped_first = drop_ticket(tmp_path, ticket_id, "already handled by hand")
        assert dropped_first.is_ok

        queue = load_queue(tmp_path)
        assert queue.is_ok
        ticket_path = tmp_path / "tickets" / ticket_id / "ticket.md"
        if not ticket_path.exists():
            # v1/single-file store mode: fall back to tickets.md itself
            # for the byte-identity check below.
            ticket_path = tmp_path / "tickets.md"
        before = ticket_path.read_bytes()

        # Fresh measurement: COV003/a.py no longer appears -- "resolved".
        payload = {"results": [{"tool": "gate-summary", "diagnostics": []}]}
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: TestIdentitiesStillReproducing._ok_result(
                json.dumps(payload)
            ),
        )

        with caplog.at_level("WARNING"):
            tickets = list(load_queue(tmp_path).danger_ok.tickets.values())
            dispatched = _rapid_sweep.revalidate_dispatchable_sweep_tickets(
                tmp_path, tickets
            )

        # Not selected -- an already-terminal ticket is never a drop
        # candidate.
        assert dispatched == ()
        # No InvalidTransition anywhere in the log -- the illegal
        # transition must never even be attempted.
        assert "illegal transition" not in caplog.text
        assert "InvalidTransition" not in caplog.text
        # No modification at all -- byte-identical to before the call.
        after = ticket_path.read_bytes()
        assert after == before

        requeried = load_queue(tmp_path)
        assert requeried.is_ok
        assert requeried.danger_ok.tickets[ticket_id].state == TicketState.DROPPED

    # frob:ticket T-2089
    def test_second_call_same_tree_reuses_cache_no_second_spawn(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestRevalidateDispatchableSweepTickets.test_second_call_same_tree_reuses_cache_no_second_spawn  # noqa: E501
        # T-2089's own measured regression: `revalidate_dispatchable_
        # sweep_tickets` used to spawn a fresh, uncached full check on
        # EVERY call while a sweep-filed candidate existed, even when the
        # tree had not moved between calls (207.5s for 21 candidates / 265
        # identities, measured live). Two calls in a row against the same
        # unchanged tree must pay for exactly ONE spawn, not two.
        from frob.tickets import load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        _init_git_repo(tmp_path)
        _git_commit(tmp_path, "chore: init")

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok

        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {"code": "COV003", "file": "a.py", "severity": "error"}
                    ],
                }
            ]
        }
        spawn_calls: list[int] = []

        def _fake_spawn(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
            spawn_calls.append(1)
            return TestIdentitiesStillReproducing._ok_result(json.dumps(payload))

        monkeypatch.setattr("frob.process._guard.guarded_subprocess_run", _fake_spawn)

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())

        first = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert first == ()  # still reproducing, left dispatchable
        assert len(spawn_calls) == 1

        second = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert second == ()
        # The tree did not move between the two calls -- the second call
        # must reuse the cached result rather than spawning again.
        assert len(spawn_calls) == 1

    # frob:ticket T-2165
    def test_cache_hits_across_a_head_move_when_candidate_files_are_unchanged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestRevalidateDispatchableSweepTickets.test_cache_hits_across_a_head_move_when_candidate_files_are_unchanged  # noqa: E501
        # T-2165's own fix, end to end: T-2089's cache (keyed on whole
        # tree state) could NEVER hit here -- an intervening land moves
        # HEAD even though it never touches `a.py`, the candidate's own
        # file. The identity-scoped key must still hit.
        from frob.tickets import load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        _init_git_repo(tmp_path)
        _git_commit(tmp_path, "chore: init")

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok

        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {"code": "COV003", "file": "a.py", "severity": "error"}
                    ],
                }
            ]
        }
        spawn_calls: list[int] = []

        def _fake_spawn(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
            spawn_calls.append(1)
            return TestIdentitiesStillReproducing._ok_result(json.dumps(payload))

        monkeypatch.setattr("frob.process._guard.guarded_subprocess_run", _fake_spawn)

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())

        first = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert first == ()
        assert len(spawn_calls) == 1

        # An UNRELATED land: commits a file the candidate identity never
        # named, moving HEAD -- T-2089's own whole-tree key would change
        # here and force a second spawn; the identity-scoped key must
        # not.
        import subprocess

        (tmp_path / "unrelated.py").write_text("changed\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
        _git_commit(tmp_path, "chore: an unrelated land happened")

        second = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert second == ()
        assert len(spawn_calls) == 1

    # frob:ticket T-2165
    def test_uncommitted_edit_to_candidate_file_still_forces_a_respawn(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestRevalidateDispatchableSweepTickets.test_uncommitted_edit_to_candidate_file_still_forces_a_respawn  # noqa: E501
        # Must-still-pass soundness control: an agent's OWN uncommitted
        # fix to the candidate's own file must NOT be masked by the
        # cache, even though HEAD never moved -- T-2165's ticket body's
        # own explicit non-negotiable ("the narrowing has to be
        # identity-scoped, not blanket-relaxed").
        from frob.tickets import load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        _init_git_repo(tmp_path)
        (tmp_path / "a.py").write_text("broken\n", encoding="utf-8")
        import subprocess

        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
        _git_commit(tmp_path, "chore: init")

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n- COV003  a.py\n"),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok

        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {"code": "COV003", "file": "a.py", "severity": "error"}
                    ],
                }
            ]
        }
        spawn_calls: list[int] = []

        def _fake_spawn(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
            spawn_calls.append(1)
            return TestIdentitiesStillReproducing._ok_result(json.dumps(payload))

        monkeypatch.setattr("frob.process._guard.guarded_subprocess_run", _fake_spawn)

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())

        first = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert first == ()
        assert len(spawn_calls) == 1

        # An agent fixes a.py IN PLACE, uncommitted -- HEAD does not
        # move, but the candidate's own file content does.
        (tmp_path / "a.py").write_text("fixed\n", encoding="utf-8")

        second = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert second == ()
        # Must re-measure, never serve a stale cached result that would
        # mask the agent's own uncommitted fix.
        assert len(spawn_calls) == 2


# frob:ticket T-2077
class TestRegressionCountLine:
    """T-2058 (ARCH001 split of `_file_regression_ticket`): the T-1935
    identity-vs-finding-count caveat line."""

    # frob:ticket T-2077
    def test_true_count_known(self) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestRegressionCountLine.test_true_count_known  # noqa: E501
        line = _regression_count_line([("RULE1", "a.py"), ("RULE2", "b.py")], 5)
        assert "2 identit" in line
        assert "5 actual finding" in line

    # frob:ticket T-2077
    def test_true_count_unmeasurable(self) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestRegressionCountLine.test_true_count_unmeasurable  # noqa: E501
        line = _regression_count_line([("RULE1", "a.py")], None)
        assert "could not be independently re-measured" in line
        assert "5 actual finding" not in line


# frob:ticket T-2077
class TestBuildRegressionBody:
    """T-2058 (ARCH001 split of `_file_regression_ticket`): body assembly
    -- the T-2009 multi-land block and the T-1690 attribution block are
    each appended only when their own inputs are non-empty."""

    # frob:ticket T-2077
    def test_no_attribution_lines_no_multi_land(self) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestBuildRegressionBody.test_no_attribution_lines_no_multi_land  # noqa: E501
        body = _build_regression_body(
            attribution_label="T-9000",
            commit_sha="deadbeef",
            pairs=[("RULE1", "a.py")],
            unfiled_pairs=[("RULE1", "a.py")],
            count_line="count line here",
            attributed_ids=None,
            attribution_lines=(),
        )
        assert "T-9000" in body
        assert "RULE1  a.py" in body
        assert "T-2009" not in body
        assert "Attribution (T-1690" not in body

    # frob:ticket T-2077
    def test_multi_land_and_attribution_lines_both_appended(self) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestBuildRegressionBody.test_multi_land_and_attribution_lines_both_appended  # noqa: E501
        body = _build_regression_body(
            attribution_label="T-9000, T-9001",
            commit_sha="deadbeef",
            pairs=[("RULE1", "a.py")],
            unfiled_pairs=[("RULE1", "a.py")],
            count_line="count line here",
            attributed_ids=["T-9000", "T-9001"],
            attribution_lines=["- RULE1 a.py: unattributed"],
        )
        assert "T-2009: 2 lands (T-9000, T-9001)" in body
        assert "Attribution (T-1690" in body
        assert "- RULE1 a.py: unattributed" in body


# frob:ticket T-3222
class TestReverifyUnfiledPairsAtFileTime:
    """T-3222: `_reverify_unfiled_pairs_at_file_time` -- the file-time
    liveness gate. MEASURED: 27 of 30 sweep-filed identities across two
    independent samples no longer reproduced by read time; the fix is
    to re-check each identity with the SAME independent spawn the
    pre-fix code already paid for (`_true_finding_count_for_identities`)
    and use it to drop dead identities instead of only reporting a
    count."""

    @staticmethod
    def _ok_result(stdout: str):
        from typani import Ok

        class _Proc:
            def __init__(self, stdout: str) -> None:
                self.stdout = stdout
                self.returncode = 1

        return Ok(_Proc(stdout))

    # frob:ticket T-3222
    def test_still_live_pair_is_kept(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestReverifyUnfiledPairsAtFileTime.test_still_live_pair_is_kept  # noqa: E501
        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {"code": "RULE1", "file": "a.py", "severity": "error"},
                    ],
                }
            ]
        }
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result(json.dumps(payload)),
        )
        live_pairs, true_count = _reverify_unfiled_pairs_at_file_time(
            tmp_path, "T-9000", [("RULE1", "a.py")]
        )
        assert live_pairs == [("RULE1", "a.py")]
        assert true_count == 1

    # frob:ticket T-3222
    def test_vanished_pair_is_dropped_and_recorded_as_debt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestReverifyUnfiledPairsAtFileTime.test_vanished_pair_is_dropped_and_recorded_as_debt  # noqa: E501
        # T-3188/T-3210/T-3215's exact real shape: the identity was fresh
        # at spawn time but the independent re-measure at file time finds
        # nothing for it -- it must be dropped, not filed with a "0
        # finding(s)" label as the pre-fix code did.
        payload = {"results": [{"tool": "gate-summary", "diagnostics": []}]}
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result(json.dumps(payload)),
        )
        live_pairs, true_count = _reverify_unfiled_pairs_at_file_time(
            tmp_path, "T-9000", [("RULE1", "a.py")]
        )
        assert live_pairs == []
        assert true_count == 0
        debt_path = tmp_path / ".frob" / "rapid-debt.jsonl"
        lines = debt_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["ticket"] == "T-9000"
        assert record["skipped"] == "sweep-finding-vanished-before-file:RULE1:a.py"

    # frob:ticket T-3222
    def test_unmeasurable_files_everything_as_before(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_attribution.py::TestReverifyUnfiledPairsAtFileTime.test_unmeasurable_files_everything_as_before  # noqa: E501
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result("not json at all"),
        )
        live_pairs, true_count = _reverify_unfiled_pairs_at_file_time(
            tmp_path, "T-9000", [("RULE1", "a.py"), ("RULE2", "b.py")]
        )
        assert live_pairs == [("RULE1", "a.py"), ("RULE2", "b.py")]
        assert true_count is None
        # Unmeasurable must never be silently recorded as vanished debt.
        assert not (tmp_path / ".frob" / "rapid-debt.jsonl").exists()
