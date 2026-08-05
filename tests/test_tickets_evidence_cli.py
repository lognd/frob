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

# frob:waive OPAQUE001 reason="T-1038: every setattr(...) in this file is \
# monkeypatch-style test isolation (pytest fixtures reassigning a module/object \
# attribute by a name the test itself constructs) -- deliberate test infrastructure, \
# not an evasion risk over untrusted input"

from __future__ import annotations

from pathlib import Path

import pytest
from typani import Ok

from frob.app.config import AppConfig
from frob.app.ticket_runner import _close, _new
from frob.testing._models import CollectedTests
from frob.tickets import TicketState, load_queue


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


# frob:ticket T-0492
class TestDotFormEvidenceNormalizesBeforePassingCheck:
    """T-0492 regression: `_apply_evidence` must normalize a dot-form
    `path::Class.method` id BEFORE checking whether it passed, not just
    before recording it -- otherwise the passing-check's `matches_collected`
    bucketing (which only ever holds pytest's native `::`-form ids) silently
    finds no bucket for the raw dot-form id, and the id is rejected as
    `EvidenceNotPassing` even though the underlying test genuinely passed.
    Deliberately does NOT monkeypatch `_verify_ids_passing` itself (unlike
    this file's other tests) -- the whole point is to exercise the REAL
    bucket-matching + run path with a dot-form id."""

    def test_dot_form_id_passes_exactly_like_its_colon_form(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_tickets_evidence_cli.py::TestDotFormEvidenceNormalizesBeforePassingCheck.test_dot_form_id_passes_exactly_like_its_colon_form  # noqa: E501
        import frob.testing as testing_mod
        from frob.app.ticket_runner import _apply_evidence
        from frob.testing._models import TestRunReport

        colon_id = "tests/test_foo.py::TestBar::test_baz"
        dot_id = "tests/test_foo.py::TestBar.test_baz"

        _patch_collect(monkeypatch, frozenset({colon_id}))

        def _fake_run_selected(selection, runners, root):  # noqa: ANN001
            return Ok(TestRunReport(selection=selection, outcomes=(), ok=True))

        monkeypatch.setattr(testing_mod, "run_selected", _fake_run_selected)

        new_cfg = AppConfig(
            ticket_command="new",
            ticket_title="dot-form evidence",
            ticket_kind="feature",
            ticket_path=tmp_path,
        )
        _new(tmp_path, new_cfg)

        result = _apply_evidence(tmp_path, "T-0001", [dot_id])
        assert result.is_ok, result.err
        assert result.danger_ok.evidence == (colon_id,)


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

        # T-1553: this asserts the v1 body-embedded report compose path;
        # pin single mode now that a bare tmp_path defaults to v2.
        (tmp_path / "tickets.md").write_text("# Tickets\n", encoding="utf-8")

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


# frob:ticket T-0805
class TestRunEvidenceCommandNoShell:
    """`_run_evidence_command` must spawn `cmd:` evidence as an argv, never
    through a shell (T-0805): ticket YAML is repo-writable, so a string
    handed to `shell=True` is injection-adjacent. Shell metacharacters
    (`;`, `$()`, backticks, `|`, `>`) in a crafted evidence command must be
    treated as literal argv characters, not interpreted."""

    def test_shell_metacharacters_do_not_reach_a_shell(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell.test_shell_metacharacters_do_not_reach_a_shell  # noqa: E501
        from frob.tickets import run_cmd_evidence

        marker = tmp_path / "shell_ran"
        # If this string ever reached a shell, `;` would sequence a second
        # command that touches `marker`. Passed as a single argv to
        # `printf`, the whole thing is inert literal text instead.
        crafted = f"printf hi; touch {marker}"
        result = run_cmd_evidence(crafted)
        assert result.is_ok
        assert not marker.exists()

    def test_command_substitution_is_not_expanded(self) -> None:
        # frob:tests tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell.test_command_substitution_is_not_expanded  # noqa: E501
        #
        # T-0805 review round 1 (reviewer): the original version of this
        # test asserted "$(whoami)" appeared in the *returned evidence
        # string*, which is built from the caller-supplied command text
        # verbatim regardless of how (or whether) it was executed -- that
        # assertion passed identically under the old `shell=True` code and
        # never actually observed the child process. This version instead
        # inspects the CHILD'S OWN STDOUT via `_run_evidence_command`
        # directly: under argv execution `printf` receives the literal
        # 2-element argv `["printf", "$(whoami)"]` and echoes that text
        # back unexpanded; under a shell, `$(whoami)` would be substituted
        # BEFORE printf ever ran and stdout would be the real username
        # instead. Asserting the literal string on stdout -- and asserting
        # the actual username is NOT what came back -- can only pass
        # against genuine no-shell argv execution.
        import getpass

        from frob.tickets import _run_evidence_command

        result = _run_evidence_command("printf $(whoami)")
        assert result.is_ok
        stdout = result.danger_ok.stdout
        assert stdout == "$(whoami)"
        assert stdout != getpass.getuser()

    def test_malformed_quoting_fails_cleanly_instead_of_shelling_out(self) -> None:
        # frob:tests tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell.test_malformed_quoting_fails_cleanly_instead_of_shelling_out  # noqa: E501
        from frob.tickets import TicketError, run_cmd_evidence

        result = run_cmd_evidence("printf 'unbalanced")
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceCmdFailed

    def test_exec_kill_switch_stops_evidence_commands(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell.test_exec_kill_switch_stops_evidence_commands  # noqa: E501
        from frob.process._guard import EXEC_KILL_SWITCH_ENV
        from frob.tickets import TicketError, run_cmd_evidence

        monkeypatch.setenv(EXEC_KILL_SWITCH_ENV, "1")
        result = run_cmd_evidence("printf ok")
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceCmdFailed


# frob:ticket T-0796
class TestCmdEvidenceAcceptsBinding:
    """T-0796 regression: `frob ticket evidence T-X --evidence-cmd CMD
    --accepts N` must bind the recorded cmd evidence onto acceptance index
    N exactly like `--evidence <pytest-node-id> --accepts N` already does
    -- before this fix `add_cmd_evidence` had no `accepts` parameter and
    both CLI call sites (`_close`, `_evidence`) dropped `cfg.ticket_accepts`
    for the cmd-evidence path, so a docs-kind ticket's acceptance criterion
    stayed UNBOUND despite the operator passing `--accepts`."""

    def _seed_docs_ticket_with_acceptance(self, tmp_path: Path) -> None:
        from frob.tickets import (
            AcceptanceCriterion,
            Origin,
            TicketKind,
            TicketSpec,
            new_ticket,
            transition,
        )

        new_ticket(
            tmp_path,
            TicketSpec(
                title="docs cmd-evidence subject",
                kind=TicketKind.DOCS,
                origin=Origin.AGENT,
                body="## Description\nx\n\n## Done report\nAll good.\n",
                acceptance=(
                    AcceptanceCriterion(text="GIVEN doc WHEN updated THEN linked"),
                ),
            ),
        )
        transition(tmp_path, "T-0001", TicketState.PLANNED)
        transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)

    def test_evidence_cmd_with_accepts_binds_acceptance_via_cli(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding.test_evidence_cmd_with_accepts_binds_acceptance_via_cli  # noqa: E501
        from frob.app.ticket_runner import _evidence

        self._seed_docs_ticket_with_acceptance(tmp_path)
        cfg = AppConfig(
            ticket_command="evidence",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_cmd="printf ok",
            ticket_accepts=[0],
        )
        _evidence(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert len(ticket.evidence) == 1
        entry = ticket.evidence[0]
        assert entry.startswith("cmd:")
        assert ticket.acceptance[0].evidence == (entry,)

    def test_close_evidence_cmd_with_accepts_binds_acceptance_via_cli(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding.test_close_evidence_cmd_with_accepts_binds_acceptance_via_cli  # noqa: E501
        self._seed_docs_ticket_with_acceptance(tmp_path)
        cfg = AppConfig(
            ticket_command="close",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_cmd="printf ok",
            ticket_accepts=[0],
        )
        _close(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.state == TicketState.DONE
        entry = ticket.evidence[0]
        assert ticket.acceptance[0].evidence == (entry,)


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


# frob:ticket T-1537
class TestReplaceEvidence:
    """`frob.tickets.replace_evidence` (T-1537): rebind one evidence id
    everywhere it appears -- the flat evidence list AND every acceptance
    criterion's own binding -- in a single atomic write."""

    def _seed_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, accepts=None
    ):
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_old"}))
        _patch_passing(monkeypatch)
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="replace evidence target",
            ticket_kind="feature",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/x.py::test_old"],
            ticket_acceptance=["GIVEN x WHEN y THEN z"],
        )
        _new(tmp_path, cfg)
        if accepts is not None:
            from frob.app.ticket_runner import _apply_evidence

            _apply_evidence(
                tmp_path, "T-0001", ["tests/x.py::test_old"], accepts=accepts
            )
        return "T-0001"

    def test_replaces_flat_evidence_and_acceptance_binding_atomically(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.tickets import replace_evidence

        ticket_id = self._seed_ticket(tmp_path, monkeypatch, accepts=[0])

        result = replace_evidence(
            tmp_path,
            ticket_id,
            "tests/x.py::test_old",
            "tests/x.py::test_new",
            collected=frozenset({"tests/x.py::test_new"}),
            passed=frozenset({"tests/x.py::test_new"}),
        )
        assert result.is_ok
        updated = result.danger_ok
        assert updated.evidence == ("tests/x.py::test_new",)
        assert updated.acceptance[0].evidence == ("tests/x.py::test_new",)

        queue = load_queue(tmp_path).danger_ok
        on_disk = queue.tickets[ticket_id]
        assert on_disk.evidence == ("tests/x.py::test_new",)
        assert on_disk.acceptance[0].evidence == ("tests/x.py::test_new",)

    def test_old_node_absent_is_a_hard_refusal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.tickets import TicketError, replace_evidence

        ticket_id = self._seed_ticket(tmp_path, monkeypatch)
        result = replace_evidence(
            tmp_path,
            ticket_id,
            "tests/x.py::does_not_exist",
            "tests/x.py::test_new",
            collected=frozenset({"tests/x.py::test_new"}),
        )
        assert result.is_err
        assert result.danger_err == TicketError.EvidenceReplaceNotFound

        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets[ticket_id].evidence == ("tests/x.py::test_old",)

    def test_unresolvable_new_node_is_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.tickets import TicketError, replace_evidence

        ticket_id = self._seed_ticket(tmp_path, monkeypatch)
        result = replace_evidence(
            tmp_path,
            ticket_id,
            "tests/x.py::test_old",
            "tests/x.py::does_not_resolve",
            collected=frozenset({"tests/x.py::test_old"}),
        )
        assert result.is_err
        assert result.danger_err == TicketError.UnknownEvidence
        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets[ticket_id].evidence == ("tests/x.py::test_old",)

    def test_same_old_and_new_is_a_no_op_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.tickets import replace_evidence

        ticket_id = self._seed_ticket(tmp_path, monkeypatch)
        result = replace_evidence(
            tmp_path, ticket_id, "tests/x.py::test_old", "tests/x.py::test_old"
        )
        assert result.is_ok
        assert result.danger_ok.evidence == ("tests/x.py::test_old",)


# frob:ticket T-1537
class TestReplaceEvidenceCli:
    """`frob ticket evidence <id> --replace OLD NEW` (T-1537): the CLI
    layer (`_evidence`/`_apply_replace_evidence`) wiring `replace_evidence`
    through the same collect/pass oracle `--evidence` ids use."""

    def test_cli_replaces_and_commits(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_old"}))
        _patch_passing(monkeypatch)
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="replace via cli",
            ticket_kind="feature",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/x.py::test_old"],
        )
        _new(tmp_path, cfg)

        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_new"}))
        _patch_passing(monkeypatch)
        from frob.app.ticket_runner import _evidence

        replace_cfg = AppConfig(
            ticket_command="evidence",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_replace=["tests/x.py::test_old", "tests/x.py::test_new"],
        )
        _evidence(tmp_path, replace_cfg)

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.evidence == ("tests/x.py::test_new",)

    def test_cli_requires_at_least_one_of_the_three_modes(self, tmp_path: Path) -> None:
        from frob.app.ticket_runner import _evidence

        cfg = AppConfig(
            ticket_command="evidence", ticket_id="T-0001", ticket_path=tmp_path
        )
        with pytest.raises(SystemExit) as exc:
            _evidence(tmp_path, cfg)
        assert exc.value.code == 1

    def test_cli_replace_not_found_exits_nonzero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_old"}))
        _patch_passing(monkeypatch)
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="replace not found",
            ticket_kind="feature",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/x.py::test_old"],
        )
        _new(tmp_path, cfg)

        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_new"}))
        _patch_passing(monkeypatch)
        from frob.app.ticket_runner import _evidence

        replace_cfg = AppConfig(
            ticket_command="evidence",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_replace=[
                "tests/x.py::does_not_exist",
                "tests/x.py::test_new",
            ],
        )
        with pytest.raises(SystemExit) as exc:
            _evidence(tmp_path, replace_cfg)
        assert exc.value.code == 1

    # frob:ticket T-1561
    def test_cli_replace_archived_reaches_the_archive(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli.test_cli_replace_a\
        # rchived_reaches_the_archive kind="unit"
        """T-1561: the 2026-08-05 incident this fixes -- COV003 scans
        `tickets-archive.md`/`tickets/archive/**` too, but `evidence
        --replace` (no `--archived`) only ever reaches active storage
        and answers `NotFound` for an already-archived ticket. `--replace
        OLD NEW --archived` must rebind the id AND leave the ticket
        archived (never resurrect it into active storage as a
        side effect)."""
        from frob.tickets import TicketState, archive, load_active
        from frob.tickets._store import load_archive, write_ticket

        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_old"}))
        _patch_passing(monkeypatch)
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="archived replace target",
            ticket_kind="feature",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/x.py::test_old"],
        )
        _new(tmp_path, cfg)

        # Force T-0001 straight to DONE (bypassing the transition-guard
        # workflow -- this test is about --archived reach, not about
        # legally EARNING a done state) so `archive()` -- mode-agnostic,
        # works for both v1 and v2 storage -- moves it out of active.
        ticket = load_active(tmp_path).danger_ok.tickets["T-0001"]
        assert write_ticket(
            tmp_path, ticket.model_copy(update={"state": TicketState.DONE})
        ).is_ok
        assert archive(tmp_path).danger_ok == 1
        assert "T-0001" not in load_active(tmp_path).danger_ok.tickets

        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_new"}))
        _patch_passing(monkeypatch)
        from frob.app.ticket_runner import _evidence

        replace_cfg = AppConfig(
            ticket_command="evidence",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_replace=["tests/x.py::test_old", "tests/x.py::test_new"],
            ticket_evidence_archived=True,
        )
        _evidence(tmp_path, replace_cfg)

        archived = load_archive(tmp_path).danger_ok
        assert archived["T-0001"].evidence == ("tests/x.py::test_new",)
        # Never resurrected into active storage as a side effect.
        assert "T-0001" not in load_active(tmp_path).danger_ok.tickets

    # frob:ticket T-1561
    def test_cli_replace_without_archived_flag_cannot_reach_an_archived_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli.test_cli_replace_w\
        # ithout_archived_flag_cannot_reach_an_archived_ticket kind="unit"
        """Control case: the SAME archived ticket, replaced WITHOUT
        `--archived`, must fail NotFound -- proving the flag is load-
        bearing, not a no-op."""
        from frob.tickets import TicketState, archive, load_active
        from frob.tickets._store import write_ticket

        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_old"}))
        _patch_passing(monkeypatch)
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="archived replace target 2",
            ticket_kind="feature",
            ticket_path=tmp_path,
            ticket_evidence_ids=["tests/x.py::test_old"],
        )
        _new(tmp_path, cfg)
        ticket = load_active(tmp_path).danger_ok.tickets["T-0001"]
        assert write_ticket(
            tmp_path, ticket.model_copy(update={"state": TicketState.DONE})
        ).is_ok
        assert archive(tmp_path).danger_ok == 1

        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_new"}))
        _patch_passing(monkeypatch)
        from frob.app.ticket_runner import _evidence

        replace_cfg = AppConfig(
            ticket_command="evidence",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_evidence_replace=["tests/x.py::test_old", "tests/x.py::test_new"],
        )
        with pytest.raises(SystemExit) as exc:
            _evidence(tmp_path, replace_cfg)
        assert exc.value.code == 1
