"""Unit tests for T-0572 acceptance-evidence binding: `Ticket.acceptance`
as `{text, evidence}` items, `unbound_acceptance`, `add_evidence(...,
accepts=...)`, and the close-time gate they feed (docs/modules/tickets.md).

Mirrors `tests/test_tickets_evidence_cli.py`'s hermetic monkeypatch pattern
(`_patch_collect`/`_patch_passing`) so these tests exercise the real CLI
plumbing (`_close`/`_evidence`) without spawning a real pytest subprocess.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from typani import Ok

from frob.app.config import AppConfig
from frob.app.ticket_runner import _close, _evidence
from frob.testing._models import CollectedTests
from frob.tickets import (
    Origin,
    Ticket,
    TicketError,
    TicketKind,
    TicketSpec,
    TicketState,
    add_evidence,
    load_queue,
    new_ticket,
    transition,
    unbound_acceptance,
)
from frob.tickets._models import AcceptanceCriterion


# frob:waive DUP001 reason="parallel per-domain test scaffolding across \
# test_app_runners_batch7.py, test_ticket_reverify.py, \
# test_tickets_acceptance.py, test_tickets_evidence_cli.py (4 sites) \
# -- each file exercises a structurally similar check for a distinct \
# domain/module with the same arrange-act shape; extracting would \
# blur which domain owns which check"
def _patch_collect(monkeypatch: pytest.MonkeyPatch, node_ids: frozenset[str]) -> None:
    """Make `frob.testing.collect_python_tests` return `node_ids` without
    spawning pytest, so CLI acceptance-binding tests stay hermetic."""
    import frob.testing as testing_mod

    monkeypatch.setattr(
        testing_mod,
        "collect_python_tests",
        lambda root: Ok(CollectedTests(node_ids=node_ids)),
    )


# frob:waive DUP001 reason="parallel per-domain test scaffolding across \
# test_app_runners_batch7.py, test_ticket_reverify.py, \
# test_tickets_acceptance.py, test_tickets_evidence_cli.py (4 sites) \
# -- each file exercises a structurally similar check for a distinct \
# domain/module with the same arrange-act shape; extracting would \
# blur which domain owns which check"
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
