"""Unit tests for T-0572 acceptance-evidence binding: `Ticket.acceptance`
as `{text, evidence}` items, `unbound_acceptance`, `add_evidence(...,
accepts=...)`, and the close-time gate they feed (docs/modules/tickets.md).

Mirrors `tests/test_tickets_evidence_cli.py`'s hermetic monkeypatch pattern
(`_patch_collect`/`_patch_passing`) so these tests exercise the real CLI
plumbing (`_close`/`_evidence`) without spawning a real pytest subprocess.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pytest
from typani import Ok

from frob.app.config import AppConfig
from frob.app.ticket_runner import _accept, _close, _evidence
from frob.testing._models import CollectedTests
from frob.tickets import (
    Origin,
    Ticket,
    TicketError,
    TicketKind,
    TicketSpec,
    TicketState,
    add_evidence,
    amend_acceptance,
    drop_ticket,
    load_queue,
    new_ticket,
    remove_acceptance,
    transition,
    unbound_acceptance,
)
from frob.tickets._models import AcceptanceAmendmentOp, AcceptanceCriterion


def _patch_collect(monkeypatch: pytest.MonkeyPatch, node_ids: frozenset[str]) -> None:
    """Make `frob.testing.collect_python_tests` return `node_ids` without
    spawning pytest, so CLI acceptance-binding tests stay hermetic."""
    import frob.testing as testing_mod

    monkeypatch.setattr(
        testing_mod,
        "collect_python_tests",
        lambda root: Ok(CollectedTests(node_ids=node_ids)),
    )


def _patch_passing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make `_verify_ids_passing` report every id it is asked about as
    passing, without spawning pytest/cargo."""
    import frob.app.ticket_runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "_verify_ids_passing",
        lambda root, node_ids, python_collected, rust_collected, runners: frozenset(
            node_ids
        ),
    )


class TestUnboundAcceptance:
    """`frob.tickets.unbound_acceptance` (T-0572)."""

    def test_empty_acceptance_list_is_never_unbound(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestUnboundAcceptance.test_empty_acceptance_list_is_never_unbound  # noqa: E501
        new_ticket(
            tmp_path,
            TicketSpec(
                title="no acceptance", kind=TicketKind.FEATURE, origin=Origin.AGENT
            ),
        )
        ticket = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert ticket.acceptance == ()
        assert unbound_acceptance(ticket) == ()

    def test_legacy_plain_string_item_loads_and_reads_as_unbound(self) -> None:
        ticket = Ticket(
            id="T-0001",
            title="legacy",
            state=TicketState.QUEUED,
            kind=TicketKind.FEATURE,
            origin=Origin.AGENT,
            created=__import__("datetime").date.today(),
            # Legacy plain-string acceptance item (pre-T-0572 ledger shape)
            # -- `_coerce_acceptance` accepts it at runtime; the `type`
            # ignores name the mismatch against the POST-coercion field
            # type this test exists to exercise.
            acceptance=["given X, when Y, then Z"],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]  # noqa: E501
        )
        assert ticket.acceptance == (
            AcceptanceCriterion(text="given X, when Y, then Z", evidence=()),
        )
        assert unbound_acceptance(ticket) == ticket.acceptance

    def test_criterion_with_a_resolving_evidence_id_is_bound(self) -> None:
        ticket = Ticket(
            id="T-0001",
            title="bound",
            state=TicketState.QUEUED,
            kind=TicketKind.FEATURE,
            origin=Origin.AGENT,
            created=__import__("datetime").date.today(),
            evidence=("tests/x.py::test_a",),
            # Structured dict form (also runtime-coerced) -- see above.
            acceptance=[  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
                {"text": "criterion", "evidence": ["tests/x.py::test_a"]}
            ],
        )
        assert unbound_acceptance(ticket) == ()

    def test_criterion_whose_evidence_id_was_dropped_from_ticket_evidence_is_unbound(
        self,
    ) -> None:
        # The binding must hold NOW against ticket.evidence, not merely
        # have been recorded once (see unbound_acceptance's docstring).
        ticket = Ticket(
            id="T-0001",
            title="orphaned",
            state=TicketState.QUEUED,
            kind=TicketKind.FEATURE,
            origin=Origin.AGENT,
            created=__import__("datetime").date.today(),
            evidence=(),
            acceptance=[  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
                {"text": "criterion", "evidence": ["tests/x.py::test_a"]}
            ],
        )
        assert len(unbound_acceptance(ticket)) == 1


class TestAddEvidenceAccepts:
    """`add_evidence(..., accepts=...)` (T-0572)."""

    def _seed(self, tmp_path: Path) -> None:
        new_ticket(
            tmp_path,
            TicketSpec(
                title="acceptance-bound",
                kind=TicketKind.FEATURE,
                origin=Origin.AGENT,
                acceptance=[  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
                    "first criterion",
                    "second criterion",
                ],
            ),
        )

    def test_accepts_binds_evidence_onto_the_named_criterion(
        self, tmp_path: Path
    ) -> None:
        self._seed(tmp_path)
        result = add_evidence(
            tmp_path,
            "T-0001",
            ["tests/x.py::test_a"],
            collected=frozenset({"tests/x.py::test_a"}),
            passed=frozenset({"tests/x.py::test_a"}),
            accepts=[0],
        )
        assert result.is_ok, result.err
        ticket = result.danger_ok
        assert ticket.evidence == ("tests/x.py::test_a",)
        assert ticket.acceptance[0].evidence == ("tests/x.py::test_a",)
        assert ticket.acceptance[1].evidence == ()

    def test_accepts_out_of_range_rejects_the_whole_batch(self, tmp_path: Path) -> None:
        self._seed(tmp_path)
        result = add_evidence(
            tmp_path,
            "T-0001",
            ["tests/x.py::test_a"],
            collected=frozenset({"tests/x.py::test_a"}),
            passed=frozenset({"tests/x.py::test_a"}),
            accepts=[7],
        )
        assert result.is_err
        assert result.danger_err == TicketError.AcceptanceIndexOutOfRange
        ticket = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert ticket.evidence == ()

    def test_accepts_dedupes_within_a_criterions_evidence(self, tmp_path: Path) -> None:
        self._seed(tmp_path)
        add_evidence(
            tmp_path,
            "T-0001",
            ["tests/x.py::test_a"],
            collected=frozenset({"tests/x.py::test_a"}),
            passed=frozenset({"tests/x.py::test_a"}),
            accepts=[0],
        )
        result = add_evidence(
            tmp_path,
            "T-0001",
            ["tests/x.py::test_a"],
            collected=frozenset({"tests/x.py::test_a"}),
            passed=frozenset({"tests/x.py::test_a"}),
            accepts=[0],
        )
        assert result.is_ok, result.err
        assert result.danger_ok.acceptance[0].evidence == ("tests/x.py::test_a",)


class TestCloseGate:
    """`frob ticket close` refuses an unbound acceptance criterion (T-0572)."""

    def _seed_in_progress_ticket(self, tmp_path: Path, acceptance: list[str]) -> None:
        new_ticket(
            tmp_path,
            TicketSpec(
                title="closeable",
                kind=TicketKind.FEATURE,
                origin=Origin.AGENT,
                acceptance=acceptance,  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
                body="## Description\nx\n\n## Done report\nAll good.\n",
            ),
        )
        transition(tmp_path, "T-0001", TicketState.PLANNED)
        transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)

    def test_ticket_with_no_acceptance_list_closes_as_before(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._seed_in_progress_ticket(tmp_path, acceptance=[])
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        _patch_passing(monkeypatch)
        cfg = AppConfig(
            ticket_command="close",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/x.py::test_a"],
        )
        _close(tmp_path, cfg)
        ticket = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert ticket.state == TicketState.DONE

    def test_unbound_acceptance_criterion_refuses_close(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        self._seed_in_progress_ticket(tmp_path, acceptance=["given/when/then item"])
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        _patch_passing(monkeypatch)
        cfg = AppConfig(
            ticket_command="close",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            # Evidence recorded, but never bound to the acceptance item via
            # --accepts -- close must still refuse.
            ticket_evidence_ids=["tests/x.py::test_a"],
        )
        with caplog.at_level(logging.WARNING):
            with pytest.raises(SystemExit) as exc:
                _close(tmp_path, cfg)
        assert exc.value.code == 1
        ticket = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert ticket.state == TicketState.IN_PROGRESS
        # The refusal must NAME the unbound criterion, not just fail
        # silently -- _done_transition_guard's WARNING line lists each
        # unbound criterion's text (see unbound_acceptance's docstring).
        assert "given/when/then item" in caplog.text

    def test_binding_the_criterion_via_accepts_then_closing_succeeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._seed_in_progress_ticket(tmp_path, acceptance=["given/when/then item"])
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        _patch_passing(monkeypatch)
        cfg = AppConfig(
            ticket_command="close",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/x.py::test_a"],
            ticket_accepts=[0],
        )
        _close(tmp_path, cfg)
        ticket = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert ticket.state == TicketState.DONE
        assert ticket.acceptance[0].evidence == ("tests/x.py::test_a",)

    def test_evidence_command_can_bind_acceptance_before_close(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._seed_in_progress_ticket(tmp_path, acceptance=["given/when/then item"])
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        _patch_passing(monkeypatch)
        evidence_cfg = AppConfig(
            ticket_command="evidence",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/x.py::test_a"],
            ticket_accepts=[0],
        )
        _evidence(tmp_path, evidence_cfg)

        close_cfg = AppConfig(
            ticket_command="close", ticket_id="T-0001", ticket_path=tmp_path
        )
        _close(tmp_path, close_cfg)
        ticket = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert ticket.state == TicketState.DONE


# frob:ticket T-0749
class TestAcceptsCliWiring:
    """T-0749 regression: `--accepts N` parsed by argparse into
    `args.ticket_accepts` must actually reach `AppConfig.ticket_accepts` via
    `AppConfig.from_external` -- the field was missing from every field-copy
    loop in `from_external`, so the CLI always bound `accepts=[]` regardless
    of what `--accepts` said, in-repo AND via `--path` alike (root cause:
    a config-layer drop, not a store/root-resolution divergence). The
    tests above construct `AppConfig(...)` directly and therefore never
    exercised `from_external`/argparse at all -- these go through the real
    parser so this exact class of gap cannot regress silently again."""

    def _seed(self, tmp_path: Path) -> None:
        new_ticket(
            tmp_path,
            TicketSpec(
                title="cli-wiring",
                kind=TicketKind.FEATURE,
                origin=Origin.AGENT,
                acceptance=["given/when/then item"],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]  # noqa: E501
                body="## Description\nx\n\n## Done report\nAll good.\n",
            ),
        )

    def test_from_external_carries_accepts_from_parsed_argv(
        self, tmp_path: Path
    ) -> None:
        """`AppConfig.from_external` must copy `ticket_accepts` out of a
        real parsed argv -- the exact step T-0749 found missing."""
        from frob.__main__ import _build_parser

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "evidence",
                "T-0001",
                "tests/x.py::test_a",
                "--accepts",
                "0",
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_accepts == [0]

    def test_evidence_cli_binds_acceptance_via_path_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End-to-end field repro (T-0749): `frob ticket evidence <id>
        <node> --accepts 0 --path DIR`, driven through the real argparse
        parser, must leave `acceptance[0].evidence` bound on read-back --
        not just append to the flat evidence list."""
        from frob.__main__ import _build_parser

        self._seed(tmp_path)
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        _patch_passing(monkeypatch)

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "evidence",
                "T-0001",
                "tests/x.py::test_a",
                "--accepts",
                "0",
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        _evidence(tmp_path, cfg)

        ticket = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert ticket.evidence == ("tests/x.py::test_a",)
        assert ticket.acceptance[0].evidence == ("tests/x.py::test_a",)
        assert unbound_acceptance(ticket) == ()

    def test_evidence_cli_binds_acceptance_in_repo_no_path_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Same as above but WITHOUT `--path` (defaults to '.', cwd) --
        audits the in-repo leg too, per T-0749's instruction to check both,
        even though T-0572's own in-repo tests (calling `add_evidence`
        directly) already passed and did not catch this CLI-layer gap."""
        from frob.__main__ import _build_parser

        self._seed(tmp_path)
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        _patch_passing(monkeypatch)

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "evidence",
                "T-0001",
                "tests/x.py::test_a",
                "--accepts",
                "0",
            ]
        )
        monkeypatch.chdir(tmp_path)
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        _evidence(tmp_path, cfg)

        ticket = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert ticket.evidence == ("tests/x.py::test_a",)
        assert ticket.acceptance[0].evidence == ("tests/x.py::test_a",)

    def test_close_time_verification_consumes_the_accepts_binding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The T-0736/T-0627 field shape: `evidence --accepts` bound via
        the real CLI parser, THEN `close` (with no further --accepts)
        must see the binding already persisted and succeed -- a fresh
        `_close` re-load must observe the SAME bound acceptance the
        `evidence` call wrote, not a copy the ledger write never carried."""
        from frob.__main__ import _build_parser

        self._seed(tmp_path)
        transition(tmp_path, "T-0001", TicketState.PLANNED)
        transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        _patch_passing(monkeypatch)

        parser = _build_parser()
        evidence_args = parser.parse_args(
            [
                "ticket",
                "evidence",
                "T-0001",
                "tests/x.py::test_a",
                "--accepts",
                "0",
                "--path",
                str(tmp_path),
            ]
        )
        evidence_cfg = AppConfig.from_external(
            evidence_args, tmp_path / "pyproject.toml"
        )
        _evidence(tmp_path, evidence_cfg)

        # Fresh load, no --accepts on close: the binding must already be
        # on disk from the `evidence` call above, not re-supplied here.
        close_args = parser.parse_args(
            ["ticket", "close", "T-0001", "--path", str(tmp_path)]
        )
        close_cfg = AppConfig.from_external(close_args, tmp_path / "pyproject.toml")
        _close(tmp_path, close_cfg)

        ticket = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert ticket.state == TicketState.DONE
        assert ticket.acceptance[0].evidence == ("tests/x.py::test_a",)


def _seed_ticket(tmp_path: Path, acceptance: list[str]) -> str:
    """Fixture helper for the T-1422 amend/remove tests below: a fresh
    queued ticket with `acceptance` criteria attached, returning its id."""
    created = new_ticket(
        tmp_path,
        TicketSpec(
            title="amendment fixture",
            kind=TicketKind.FEATURE,
            origin=Origin.AGENT,
            acceptance=acceptance,  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        ),
    )
    assert created.is_ok, created
    return created.danger_ok.id


class TestAmendAcceptance:
    """`frob.tickets.amend_acceptance`/`remove_acceptance` (T-1422): the
    supported alternative to hand-editing `tickets.md` for a criterion
    that was WRONG (amend) or unsatisfiable by construction (remove),
    modelled on the two real incidents named in T-1422's own body."""

    def test_amend_replaces_text_and_records_reason(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAmendAcceptance.test_amend_replaces_text_and_records_reason  # noqa: E501
        # Models the T-1411 incident: criterion [0] was mis-specified (a
        # trailing comment naming no in-scope identifier would have
        # silenced the poorly-named-variable case PII012 exists for) and
        # needed correcting, not appending-around.
        ticket_id = _seed_ticket(
            tmp_path,
            [
                "a comment naming no in-scope identifier must not fire PII012",
                "second criterion",
            ],
        )
        result = amend_acceptance(
            tmp_path,
            ticket_id,
            0,
            "a comment naming no in-scope identifier, INCLUDING a poorly "
            "named variable's own trailing comment, must not fire PII012",
            reason=(
                "T-1411's original wording also matched a trailing comment "
                "naming no identifier, which would have silenced the "
                "poorly-named-variable case the rule exists for -- "
                "mis-specified, not merely unmet"
            ),
        )
        assert result.is_ok, result
        updated = result.danger_ok
        assert updated.acceptance[0].text.startswith(
            "a comment naming no in-scope identifier, INCLUDING"
        )
        # the second, untouched criterion must survive unchanged
        assert updated.acceptance[1].text == "second criterion"
        assert len(updated.acceptance_amendments) == 1
        entry = updated.acceptance_amendments[0]
        assert entry.op is AcceptanceAmendmentOp.REPLACE
        assert entry.index == 0
        assert entry.old_text == (
            "a comment naming no in-scope identifier must not fire PII012"
        )
        assert entry.new_text == updated.acceptance[0].text
        assert "mis-specified" in entry.reason
        assert entry.at == date.today()

        # re-load from disk: the ledger write is durable, and the
        # amendment is not lost on a round trip through YAML (hashes,
        # colons, and quotes in the reason must survive verbatim).
        reloaded = load_queue(tmp_path).danger_ok.tickets[ticket_id]
        assert reloaded.acceptance_amendments[0].reason == entry.reason

    def test_amend_preserves_existing_evidence_binding(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAmendAcceptance.test_amend_preserves_existing_evidence_binding  # noqa: E501
        ticket_id = _seed_ticket(tmp_path, ["first criterion"])
        bound = add_evidence(
            tmp_path,
            ticket_id,
            ["tests/x.py::test_a"],
            collected=frozenset({"tests/x.py::test_a"}),
            passed=frozenset({"tests/x.py::test_a"}),
            accepts=[0],
        )
        assert bound.is_ok, bound
        result = amend_acceptance(
            tmp_path, ticket_id, 0, "first criterion, reworded", reason="typo fix"
        )
        assert result.is_ok, result
        assert result.danger_ok.acceptance[0].evidence == ("tests/x.py::test_a",)

    def test_amend_refuses_empty_reason(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAmendAcceptance.test_amend_refuses_empty_reason  # noqa: E501
        ticket_id = _seed_ticket(tmp_path, ["first criterion"])
        result = amend_acceptance(tmp_path, ticket_id, 0, "new text", reason="   ")
        assert result.is_err
        assert result.danger_err == TicketError.AcceptanceAmendReasonMissing

    def test_amend_refuses_out_of_range_index(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAmendAcceptance.test_amend_refuses_out_of_range_index  # noqa: E501
        ticket_id = _seed_ticket(tmp_path, ["first criterion"])
        result = amend_acceptance(tmp_path, ticket_id, 5, "new text", reason="why")
        assert result.is_err
        assert result.danger_err == TicketError.AcceptanceAmendIndexOutOfRange

    def test_amend_refuses_on_terminal_ticket(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAmendAcceptance.test_amend_refuses_on_terminal_ticket  # noqa: E501
        ticket_id = _seed_ticket(tmp_path, ["first criterion"])
        dropped = drop_ticket(tmp_path, ticket_id, "superseded")
        assert dropped.is_ok, dropped
        result = amend_acceptance(
            tmp_path, ticket_id, 0, "new text", reason="trying to sneak this in"
        )
        assert result.is_err
        assert result.danger_err == TicketError.AcceptanceAmendTerminalState

    def test_remove_drops_criterion_and_records_reason(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAmendAcceptance.test_remove_drops_criterion_and_records_reason  # noqa: E501
        # Models the ten-burn-down-tickets incident: "0 TEST005 findings
        # under package X" against 100-400 findings is unsatisfiable by
        # construction, so it must be REMOVED (never silently
        # weakened-in-place) with a reason, replaced by a triage-shaped
        # criterion via a normal `frob ticket accept --criterion` append.
        ticket_id = _seed_ticket(
            tmp_path,
            ["0 TEST005 findings under src/frob/strata", "unrelated criterion"],
        )
        result = remove_acceptance(
            tmp_path,
            ticket_id,
            0,
            reason=(
                "unsatisfiable by construction: 196 findings, no single "
                "dispatch can drive this to 0 -- replaced by triage-shaped "
                "acceptance instead"
            ),
        )
        assert result.is_ok, result
        updated = result.danger_ok
        assert len(updated.acceptance) == 1
        assert updated.acceptance[0].text == "unrelated criterion"
        assert len(updated.acceptance_amendments) == 1
        entry = updated.acceptance_amendments[0]
        assert entry.op is AcceptanceAmendmentOp.REMOVE
        assert entry.index == 0
        assert entry.old_text == "0 TEST005 findings under src/frob/strata"
        assert entry.new_text is None
        assert "unsatisfiable" in entry.reason

    def test_remove_refuses_on_terminal_ticket(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAmendAcceptance.test_remove_refuses_on_terminal_ticket  # noqa: E501
        ticket_id = _seed_ticket(tmp_path, ["first criterion"])
        dropped = drop_ticket(tmp_path, ticket_id, "superseded")
        assert dropped.is_ok, dropped
        result = remove_acceptance(tmp_path, ticket_id, 0, reason="goalpost moving")
        assert result.is_err
        assert result.danger_err == TicketError.AcceptanceAmendTerminalState

    def test_amend_reason_containing_hash_colon_and_quotes_round_trips(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAmendAcceptance.test_amend_reason_containing_hash_colon_and_quotes_round_trips  # noqa: E501
        # The ledger must remain parseable after an amendment whose text
        # would break hand-typed YAML: a space-hash sequence starts a
        # YAML comment in a plain scalar, which is exactly what corrupted
        # tickets.md the first time this was attempted by hand (T-1422's
        # own motivating incident). The CLI verb must escape this
        # correctly, never merely reject it.
        ticket_id = _seed_ticket(tmp_path, ["first criterion"])
        tricky_reason = (
            'mis-specified: PII012 #comment-lookalike, "quoted" and a '
            "colon: like this -- see T-1411's criterion [0]"
        )
        result = amend_acceptance(
            tmp_path,
            ticket_id,
            0,
            "criterion text with a # hash and a colon: too",
            reason=tricky_reason,
        )
        assert result.is_ok, result

        reloaded = load_queue(tmp_path).danger_ok
        assert ticket_id in reloaded.tickets
        reloaded_ticket = reloaded.tickets[ticket_id]
        assert reloaded_ticket.acceptance[0].text == (
            "criterion text with a # hash and a colon: too"
        )
        assert reloaded_ticket.acceptance_amendments[0].reason == tricky_reason
        # every OTHER ticket in the ledger must still parse too -- a
        # malformed write here previously took the entire gate layer down.
        assert reloaded.tickets  # ledger loaded at all, not "all gates skipped"


class TestAcceptCliAmendRemove:
    """`frob ticket accept <id> --amend/--remove` (T-1422): the CLI wiring
    for `amend_acceptance`/`remove_acceptance`, mirroring `TestScopeCli`'s
    coverage shape in tests/test_tickets_scope_mutation.py."""

    def test_cli_amend_replaces_text(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove.test_cli_amend_replaces_text  # noqa: E501
        ticket_id = _seed_ticket(tmp_path, ["first criterion"])
        cfg = AppConfig(
            ticket_command="accept",
            ticket_id=ticket_id,
            ticket_path=tmp_path,
            ticket_accept_amend_index=0,
            ticket_accept_amend_text="corrected criterion",
            ticket_accept_amend_reason="was mis-specified",
        )
        _accept(tmp_path, cfg)
        ticket = load_queue(tmp_path).danger_ok.tickets[ticket_id]
        assert ticket.acceptance[0].text == "corrected criterion"
        assert ticket.acceptance_amendments[0].reason == "was mis-specified"

    def test_cli_remove_drops_criterion(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove.test_cli_remove_drops_criterion  # noqa: E501
        ticket_id = _seed_ticket(tmp_path, ["only criterion"])
        cfg = AppConfig(
            ticket_command="accept",
            ticket_id=ticket_id,
            ticket_path=tmp_path,
            ticket_accept_remove_index=0,
            ticket_accept_amend_reason="unsatisfiable by construction",
        )
        _accept(tmp_path, cfg)
        ticket = load_queue(tmp_path).danger_ok.tickets[ticket_id]
        assert ticket.acceptance == ()
        assert ticket.acceptance_amendments[0].op is AcceptanceAmendmentOp.REMOVE

    def test_cli_amend_without_reason_exits_nonzero(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove.test_cli_amend_without_reason_exits_nonzero  # noqa: E501
        ticket_id = _seed_ticket(tmp_path, ["first criterion"])
        cfg = AppConfig(
            ticket_command="accept",
            ticket_id=ticket_id,
            ticket_path=tmp_path,
            ticket_accept_amend_index=0,
            ticket_accept_amend_text="corrected criterion",
        )
        with pytest.raises(SystemExit) as exc_info:
            _accept(tmp_path, cfg)
        assert exc_info.value.code == 1

    def test_cli_amend_and_remove_together_is_rejected(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove.test_cli_amend_and_remove_together_is_rejected  # noqa: E501
        ticket_id = _seed_ticket(tmp_path, ["a", "b"])
        cfg = AppConfig(
            ticket_command="accept",
            ticket_id=ticket_id,
            ticket_path=tmp_path,
            ticket_accept_amend_index=0,
            ticket_accept_amend_text="x",
            ticket_accept_remove_index=1,
            ticket_accept_amend_reason="why",
        )
        with pytest.raises(SystemExit) as exc_info:
            _accept(tmp_path, cfg)
        assert exc_info.value.code == 1


class TestAcceptanceAmendmentsSurfaced:
    """Acceptance [1]: an amendment must be surfaced in `frob ticket show`
    and the rendered Done report, never buried (T-1422)."""

    def test_show_renders_amendment_and_reason(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced.test_show_renders_amendment_and_reason  # noqa: E501
        from frob.app.ticket_runner._query import _render_acceptance

        ticket_id = _seed_ticket(tmp_path, ["first criterion"])
        amend_acceptance(
            tmp_path, ticket_id, 0, "corrected criterion", reason="was mis-specified"
        )
        ticket = load_queue(tmp_path).danger_ok.tickets[ticket_id]
        rendered = _render_acceptance(ticket)
        assert "acceptance_amendments:" in rendered
        assert "replace" in rendered
        assert "was mis-specified" in rendered
        assert "corrected criterion" in rendered

    # frob:ticket T-1855
    def test_show_renders_implicit_cli_wiring_scope(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced.test_show_renders_implicit_cli_wiring_scope  # noqa: E501
        """`frob ticket show` discloses the FEATURE-kind CLI-wiring files a
        ticket effectively holds but never declared (T-1855 item 2) -- the
        disclosure half of the T-1848 incident: today the declared list is
        all `show` prints, so a coordinator running `scope --remove`
        cannot see it holds more than it declared."""
        from frob.app.ticket_runner._query import _render_implicit_scope
        from frob.tickets import TicketKind
        from frob.tickets import Origin, TicketSpec, new_ticket

        spec = TicketSpec(
            title="new subcommand",
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            scope=("src/frob/other/**",),
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok, created
        ticket = created.danger_ok
        rendered = _render_implicit_scope(ticket)
        assert "implicit_scope:" in rendered
        assert "src/frob/__main__.py" in rendered

    # frob:ticket T-1855
    def test_show_omits_implicit_scope_when_fully_declared(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced.test_show_omits_implicit_scope_when_fully_declared  # noqa: E501
        """No `implicit_scope:` line for a non-FEATURE ticket -- matches
        every sibling `_render_*` helper's "nothing to add" posture."""
        from frob.app.ticket_runner._query import _render_implicit_scope
        from frob.tickets import TicketKind
        from frob.tickets import Origin, TicketSpec, new_ticket

        spec = TicketSpec(
            title="a bug fix",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            scope=("src/frob/other/**",),
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok, created
        ticket = created.danger_ok
        assert _render_implicit_scope(ticket) == ""

    def test_done_report_renders_amendment_section(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced.test_done_report_renders_amendment_section  # noqa: E501
        from frob.tickets import compose_done_report
        from frob.tickets._models import AcceptanceAmendmentEntry

        entry = AcceptanceAmendmentEntry(
            op=AcceptanceAmendmentOp.REMOVE,
            index=0,
            old_text="0 TEST005 findings under src/frob/strata",
            new_text=None,
            reason="unsatisfiable by construction",
            actor="agent",
            at=date.today(),
        )
        report = compose_done_report(
            "did the work",
            [],
            [],
            acceptance_amendments=(entry,),
        )
        assert "### Acceptance amendments" in report
        assert "unsatisfiable by construction" in report
        assert "0 TEST005 findings under src/frob/strata" in report

    def test_done_report_omits_section_when_no_amendments(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced.test_done_report_omits_section_when_no_amendments  # noqa: E501
        from frob.tickets import compose_done_report

        report = compose_done_report("did the work", [], [])
        assert "### Acceptance amendments" not in report
