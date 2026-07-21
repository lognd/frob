"""Unit tests for `frob ticket new/close --evidence` routing through
frob.tickets.add_evidence (docs/modules/tickets.md, docs/commands/ticket.md).

collect_python_tests spawns a real `uv run pytest` subprocess, which is
unnecessary noise for exercising CLI plumbing -- these tests monkeypatch
`frob.testing.collect_python_tests` (imported locally at call time inside
`_apply_evidence`) so they stay fast and hermetic while still going through
the same `add_evidence` validation path as the real CLI.

T-0398 (D-01 CLI wiring): `_apply_evidence` now ALSO actually runs every
resolvable id (`_verify_ids_passing`) before recording it as evidence.
Tests that assert a RESOLVABLE id is recorded also monkeypatch
`_verify_ids_passing` (`_patch_passing`) to a hermetic stand-in that
reports every id it is asked about as passing -- these tests are about
resolution/routing plumbing, not re-proving D-01's pass/fail behavior
(that is `tests/test_evidence_integrity.py`'s and this file's own
`TestD01CliWiring`'s job).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typani import Ok

from frob.app.config import AppConfig
from frob.app.ticket_runner import _close, _new
from frob.testing._models import CollectedTests
from frob.tickets import TicketState, load_queue


# frob:waive DUP001 reason="parallel test fixtures across 2 sibling test \
# file(s) (2 sites) sharing an arrange-act scaffold typical of exhaustive \
# per-case/per-scenario coverage; extracting would obscure per-case intent"
def _patch_collect(monkeypatch: pytest.MonkeyPatch, node_ids: frozenset[str]) -> None:
    """Make `frob.testing.collect_python_tests` return `node_ids` without
    spawning pytest, so CLI evidence-routing tests stay hermetic."""
    import frob.testing as testing_mod

    monkeypatch.setattr(
        testing_mod,
        "collect_python_tests",
        lambda root: Ok(CollectedTests(node_ids=node_ids)),
    )


def _patch_passing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make `_verify_ids_passing` (D-01's actual-run step) report every id
    it is asked about as passing, without spawning pytest/cargo -- for
    tests exercising resolution/routing plumbing, not D-01's pass/fail
    behavior itself."""
    import frob.app.ticket_runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "_verify_ids_passing",
        lambda root, node_ids, python_collected, rust_collected, runners: frozenset(
            node_ids
        ),
    )


class TestTicketNewEvidence:
    """`frob ticket new --evidence <id>...` (T-0106)."""

    def test_resolvable_evidence_recorded_on_new_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        _patch_passing(monkeypatch)
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="wire evidence",
            ticket_kind="feature",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/x.py::test_a"],
        )
        _new(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.evidence == ("tests/x.py::test_a",)

    def test_unresolvable_evidence_does_not_abort_ticket_creation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        # The ticket itself is already written by new_ticket() before
        # evidence is applied; an unresolvable --evidence id must leave
        # the ticket created but with no evidence attached, and exit
        # nonzero to signal the failure to the caller.
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="wire evidence",
            ticket_kind="feature",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/does_not_exist.py::test_z"],
        )
        with pytest.raises(SystemExit) as exc:
            _new(tmp_path, cfg)
        assert exc.value.code == 1

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.evidence == ()

    def test_dedupes_against_already_recorded_evidence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # add_evidence's dedupe is against the ticket's *existing* evidence
        # list, not within a single batch (frob.tickets.add_evidence
        # semantics, reused as-is) -- so two `--evidence` flags calling
        # into the same helper twice must not duplicate the entry.
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        _patch_passing(monkeypatch)
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="wire evidence",
            ticket_kind="feature",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/x.py::test_a"],
        )
        _new(tmp_path, cfg)

        from frob.app.ticket_runner import _apply_evidence

        _apply_evidence(tmp_path, "T-0001", ["tests/x.py::test_a"])

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.evidence == ("tests/x.py::test_a",)


class TestTicketCloseEvidence:
    """`frob ticket close --evidence <id>...` (T-0106)."""

    def _seed_in_progress_ticket(self, tmp_path: Path) -> None:
        from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket

        new_ticket(
            tmp_path,
            TicketSpec(
                title="closeable",
                kind=TicketKind.FEATURE,
                origin=Origin.AGENT,
                body="## Description\nx\n\n## Done report\nAll good.\n",
            ),
        )
        from frob.tickets import transition

        transition(tmp_path, "T-0001", TicketState.PLANNED)
        transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)

    def test_resolvable_evidence_recorded_then_closed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._seed_in_progress_ticket(tmp_path)
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        _patch_passing(monkeypatch)
        cfg = AppConfig(
            ticket_command="close",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/x.py::test_a"],
        )
        _close(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.state == TicketState.DONE
        assert ticket.evidence == ("tests/x.py::test_a",)

    def test_unresolvable_evidence_blocks_close_entirely(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The whole point of T-0106: a bad --evidence id must refuse the
        # DONE transition outright, not close on unvalidated evidence.
        self._seed_in_progress_ticket(tmp_path)
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        cfg = AppConfig(
            ticket_command="close",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/does_not_exist.py::test_z"],
        )
        with pytest.raises(SystemExit) as exc:
            _close(tmp_path, cfg)
        assert exc.value.code == 1

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.state == TicketState.IN_PROGRESS
        assert ticket.evidence == ()

    def test_dedupes_against_ids_already_on_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.tickets import add_evidence

        self._seed_in_progress_ticket(tmp_path)
        add_evidence(
            tmp_path,
            "T-0001",
            ("tests/x.py::test_a",),
            frozenset({"tests/x.py::test_a"}),
        )
        _patch_collect(
            monkeypatch, frozenset({"tests/x.py::test_a", "tests/x.py::test_b"})
        )
        _patch_passing(monkeypatch)
        cfg = AppConfig(
            ticket_command="close",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/x.py::test_a", "tests/x.py::test_b"],
        )
        _close(tmp_path, cfg)
        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].evidence == (
            "tests/x.py::test_a",
            "tests/x.py::test_b",
        )


class TestTicketEvidenceRustOracle:
    """T-0301 (feldspar T-0015 escalation): `--evidence` ids must resolve
    against the union of every collected oracle a repo's `[[test.runner]]`
    entries declare, not pytest alone -- a rust node id collected via
    `collect_rust_tests` (cached at `.frob/cargo-collect.json`) must
    validate the same way a pytest node id does."""

    def _write_rust_runner_toml(self, tmp_path: Path) -> None:
        (tmp_path / "frob.toml").write_text(
            "[[test.runner]]\n"
            'language = "rust"\n'
            'command = ["cargo", "test", "--lib", "{filters}"]\n'
            'all_command = ["cargo", "test", "--lib"]\n'
            'cwd = "."\n',
            encoding="utf-8",
        )

    def test_rust_node_id_from_fake_cargo_collect_cache_resolves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_collect(monkeypatch, frozenset())
        _patch_passing(monkeypatch)
        self._write_rust_runner_toml(tmp_path)

        import frob.testing as testing_mod

        rust_node_id = "crates/feldspar-core/src/symbolic.rs::tests::solves"
        monkeypatch.setattr(
            testing_mod,
            "collect_rust_tests",
            lambda root: Ok(CollectedTests(node_ids=frozenset({rust_node_id}))),
        )

        cfg = AppConfig(
            ticket_command="new",
            ticket_title="rust evidence",
            ticket_kind="feature",
            ticket_path=tmp_path,
            ticket_evidence_ids=[rust_node_id],
        )
        _new(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.evidence == (rust_node_id,)

    def test_no_rust_runner_declared_never_collects_rust(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # No frob.toml at all here -- load_runners is Ok(()), so
        # collect_rust_tests must never even be attempted (no unnecessary
        # cargo invocation for repos with no rust runner configured).
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        _patch_passing(monkeypatch)

        import frob.testing as testing_mod

        def _boom(root):  # noqa: ANN001, ANN202
            raise AssertionError("collect_rust_tests must not be called")

        monkeypatch.setattr(testing_mod, "collect_rust_tests", _boom)

        cfg = AppConfig(
            ticket_command="new",
            ticket_title="python only",
            ticket_kind="feature",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/x.py::test_a"],
        )
        _new(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].evidence == ("tests/x.py::test_a",)

    def test_rust_collection_failure_degrades_to_python_only(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        # A rust-collection failure (e.g. no PyO3 dev env) must not block
        # evidence recording for an unrelated python id -- it degrades to
        # python-only validation with a warning, not a hard failure.
        from typani import Err

        from frob.testing import TestingError

        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        _patch_passing(monkeypatch)
        self._write_rust_runner_toml(tmp_path)

        import frob.testing as testing_mod

        monkeypatch.setattr(
            testing_mod,
            "collect_rust_tests",
            lambda root: Err(TestingError.CargoEnvUnavailable),
        )

        cfg = AppConfig(
            ticket_command="new",
            ticket_title="degraded rust collection",
            ticket_kind="feature",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/x.py::test_a"],
        )
        _new(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].evidence == ("tests/x.py::test_a",)


# frob:ticket T-0458
class TestDoneReportCli:
    """`frob ticket done-report <id> --why ...` -- the CLI wrapper around
    `frob.tickets.set_done_report` (T-0458): supplies ONLY the narrative,
    never touches markdown itself."""

    def test_cli_composes_and_writes(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_evidence_cli.py::TestDoneReportCli.test_cli_composes_and_writes  # noqa: E501
        from frob.app.ticket_runner import _done_report

        new_cfg = AppConfig(
            ticket_command="new",
            ticket_title="done-report smoke",
            ticket_kind="feature",
            ticket_path=tmp_path,
        )
        _new(tmp_path, new_cfg)

        report_cfg = AppConfig(
            ticket_command="done-report",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_why="implemented via the new command",
            ticket_base_ref="does-not-exist",
        )
        _done_report(tmp_path, report_cfg)

        ticket = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert "## Done report" in ticket.body
        assert "implemented via the new command" in ticket.body
        assert "### Changed" in ticket.body
        assert "### Evidence" in ticket.body

    def test_missing_why_exits_nonzero(self, tmp_path: Path, monkeypatch) -> None:
        from frob.app.ticket_runner import _done_report

        new_cfg = AppConfig(
            ticket_command="new",
            ticket_title="no why given",
            ticket_kind="feature",
            ticket_path=tmp_path,
        )
        _new(tmp_path, new_cfg)

        monkeypatch.setattr("sys.stdin.read", lambda: "")
        cfg = AppConfig(
            ticket_command="done-report", ticket_id="T-0001", ticket_path=tmp_path
        )
        with pytest.raises(SystemExit) as exc:
            _done_report(tmp_path, cfg)
        assert exc.value.code == 1


class TestLogEvidenceResultRemedy:
    """`_log_evidence_result`'s failure-path remedy text (T-0445, T-0292
    sibling): must not point at the nonexistent `frob test --collect`
    flag."""

    def test_error_remedy_names_no_nonexistent_flag(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:ticket T-0445
        import logging

        from typani import Err

        from frob.app.ticket_runner import _log_evidence_result
        from frob.tickets import TicketError

        with caplog.at_level(logging.ERROR):
            _log_evidence_result("T-0001", Err(TicketError.UnknownEvidence))
        messages = " ".join(r.message for r in caplog.records)
        assert "frob test --collect to refresh" not in messages
        assert "self-refreshes" in messages
