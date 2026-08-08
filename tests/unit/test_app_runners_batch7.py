"""Direct-call coverage for batch-7 app/*_runner.py CLI entry points (T-0160).

Same rationale as `test_app_runners_batch6.py`: CLI-subprocess tests don't
attribute coverage back to the running process, so these tests call each
runner's `run(cfg)` (or, for `ticket_runner`'s larger surface, its per-
subcommand handlers) directly against a hand-built `AppConfig`. Modules
covered this batch: `app/ticket_runner.py`, `app/sys_runner.py`.
"""


from __future__ import annotations

from pathlib import Path

import pytest
from typani import Err, Ok

from frob.app.config import AppConfig
from frob.app.sys_runner import run as sys_run
from frob.app.ticket_runner import run as ticket_run
from frob.testing._models import CollectedTests
from frob.tickets import TicketState, load_queue


def _patch_collect(monkeypatch: pytest.MonkeyPatch, node_ids: frozenset[str]) -> None:
    """Make `frob.testing.collect_python_tests` return `node_ids` without
    spawning a real pytest subprocess, so evidence-routing tests stay fast
    and hermetic (same helper as `tests/test_tickets_evidence_cli.py`)."""
    import frob.testing as testing_mod

    monkeypatch.setattr(
        testing_mod,
        "collect_python_tests",
        lambda root: Ok(CollectedTests(node_ids=node_ids)),
    )


def _patch_passing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make D-01's `_verify_ids_passing` (T-0398 CLI wiring) report every
    id it is asked about as passing, without spawning pytest/cargo (same
    helper as `tests/test_tickets_evidence_cli.py`)."""
    import frob.app.ticket_runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "_verify_ids_passing",
        lambda root, node_ids, python_collected, rust_collected, runners: frozenset(
            node_ids
        ),
    )


# ---------------------------------------------------------------------------
# ticket_runner
# ---------------------------------------------------------------------------


class TestTicketRunnerDispatch:
    def test_unknown_command_exits_1(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(ticket_command="bogus", ticket_path=tmp_path)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            ticket_run(cfg)
        assert exc.value.code == 1
        assert "usage: frob ticket" in caplog.text

    # frob:ticket T-1570
    def test_debt_subcommand_delegates_to_debt_runner(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`frob ticket debt` (T-1570) delegates straight into
        `debt_runner.run` with the SAME cfg, ignoring `root`."""
        import frob.app.debt_runner as debt_mod

        called = {}
        monkeypatch.setattr(
            debt_mod, "run", lambda cfg: called.setdefault("cfg", cfg)
        )
        cfg = AppConfig(ticket_command="debt", ticket_path=tmp_path, debt_path=tmp_path)
        ticket_run(cfg)
        assert called["cfg"] is cfg

    # frob:ticket T-1570
    def test_deprecated_subcommand_delegates_to_deprecated_runner(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`frob ticket deprecated` (T-1570) delegates straight into
        `deprecated_runner.run` with the SAME cfg, ignoring `root`."""
        import frob.app.deprecated_runner as deprecated_mod

        called = {}
        monkeypatch.setattr(
            deprecated_mod, "run", lambda cfg: called.setdefault("cfg", cfg)
        )
        cfg = AppConfig(
            ticket_command="deprecated", ticket_path=tmp_path, deprecated_path=tmp_path
        )
        ticket_run(cfg)
        assert called["cfg"] is cfg


# frob:ticket T-1674
class TestTicketRunnerRootResolution:
    """T-1674: `_resolve_ticket_root` -- `FROB_ROOT` as a fallback for an
    ambient-cwd-drift incident, explicit `--path` always winning over it,
    and the resolved root logged unconditionally for a mutating verb."""

    def test_frob_root_env_used_when_path_not_explicit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_app_runners_batch7.py::TestTicketRunnerRootResolution.test_frob_root_env_used_when_path_not_explicit  # noqa: E501
        from frob.app.ticket_runner import _resolve_ticket_root

        target = tmp_path / "pinned"
        target.mkdir()
        monkeypatch.setenv("FROB_ROOT", str(target))
        cfg = AppConfig(ticket_command="new")
        assert _resolve_ticket_root(cfg) == target.resolve()

    def test_explicit_path_wins_over_frob_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_app_runners_batch7.py::TestTicketRunnerRootResolution.test_explicit_path_wins_over_frob_root  # noqa: E501
        from frob.app.ticket_runner import _resolve_ticket_root

        env_target = tmp_path / "env-pinned"
        env_target.mkdir()
        explicit_target = tmp_path / "explicit"
        explicit_target.mkdir()
        monkeypatch.setenv("FROB_ROOT", str(env_target))
        cfg = AppConfig(ticket_command="new", ticket_path=explicit_target)
        assert _resolve_ticket_root(cfg) == explicit_target.resolve()

    def test_no_frob_root_falls_back_to_cwd_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_app_runners_batch7.py::TestTicketRunnerRootResolution.test_no_frob_root_falls_back_to_cwd_default  # noqa: E501
        from frob.app.ticket_runner import _resolve_ticket_root

        monkeypatch.delenv("FROB_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)
        cfg = AppConfig(ticket_command="new")
        assert _resolve_ticket_root(cfg) == tmp_path.resolve()

    def test_resolved_root_is_logged_for_a_mutating_verb(
        self, tmp_path: Path, caplog
    ) -> None:
        # frob:tests tests/unit/test_app_runners_batch7.py::TestTicketRunnerRootResolution.test_resolved_root_is_logged_for_a_mutating_verb  # noqa: E501
        cfg = AppConfig(
            ticket_command="new", ticket_path=tmp_path, ticket_title="t", ticket_kind="bug"
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert f"resolved root {tmp_path.resolve()}" in caplog.text


class TestTicketNewErrors:
    def test_missing_title_or_kind_exits_1(self, tmp_path: Path) -> None:
        cfg = AppConfig(ticket_command="new", ticket_path=tmp_path)
        with pytest.raises(SystemExit) as exc:
            ticket_run(cfg)
        assert exc.value.code == 1


class TestTicketList:
    def test_no_tickets_logs_message(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(ticket_command="list", ticket_path=tmp_path)
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "no tickets" in caplog.text

    def test_list_json_mode(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="a ticket",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(ticket_command="list", ticket_path=tmp_path, ticket_json=True)
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert '"title": "a ticket"' in caplog.text

    def test_list_filters_by_state(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="a ticket",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="list", ticket_path=tmp_path, ticket_state="done"
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "no tickets" in caplog.text

    def test_list_text_mode_prints_ticket_line(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="a ticket",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(ticket_command="list", ticket_path=tmp_path)
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "a ticket" in caplog.text


def _write_malformed_ledger(tmp_path: Path) -> None:
    """A `tickets.md` whose one section has no valid ```yaml frontmatter --
    triggers `load_queue`'s Err branch in every reader that checks it."""
    (tmp_path / "tickets.md").write_text(
        "# Tickets\n\n<!-- ticket:T-0001 -->\nnot yaml at all\n"
    )


class TestTicketListShowDoableLoadErrors:
    def test_list_load_error_exits_1(self, tmp_path: Path, caplog) -> None:
        _write_malformed_ledger(tmp_path)
        cfg = AppConfig(ticket_command="list", ticket_path=tmp_path)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "ticket list failed" in caplog.text

    def test_show_load_error_exits_1(self, tmp_path: Path, caplog) -> None:
        _write_malformed_ledger(tmp_path)
        cfg = AppConfig(ticket_command="show", ticket_path=tmp_path, ticket_id="T-0001")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "ticket show failed" in caplog.text

    def test_doable_load_error_exits_1(self, tmp_path: Path, caplog) -> None:
        _write_malformed_ledger(tmp_path)
        cfg = AppConfig(ticket_command="doable", ticket_path=tmp_path)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "ticket doable failed" in caplog.text


class TestTicketShow:
    def test_missing_id_exits_1(self, tmp_path: Path) -> None:
        cfg = AppConfig(ticket_command="show", ticket_path=tmp_path)
        with pytest.raises(SystemExit):
            ticket_run(cfg)

    def test_unknown_id_exits_1(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(ticket_command="show", ticket_path=tmp_path, ticket_id="T-9999")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "no ticket" in caplog.text

    def test_show_found_json_mode(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="show me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="show",
            ticket_path=tmp_path,
            ticket_id="T-0001",
            ticket_json=True,
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert '"title": "show me"' in caplog.text

    def test_show_found_text_mode(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="show me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(ticket_command="show", ticket_path=tmp_path, ticket_id="T-0001")
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "show me" in caplog.text


class TestTicketDoable:
    def test_nothing_doable(self, tmp_path: Path, caplog) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_batch7.py::TestTicketDoable.test_nothing_doable
        cfg = AppConfig(ticket_command="doable", ticket_path=tmp_path)
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "zero doable tickets" in caplog.text

    def test_doable_json_mode(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="a ticket",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(ticket_command="doable", ticket_path=tmp_path, ticket_json=True)
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert '"title": "a ticket"' in caplog.text

    def test_doable_text_mode(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="a ticket",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(ticket_command="doable", ticket_path=tmp_path)
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "a ticket" in caplog.text


class TestTicketMigrate:
    def test_no_legacy_files(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(ticket_command="migrate", ticket_path=tmp_path)
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "no legacy" in caplog.text

    def test_migrates_legacy_dir_ticket(self, tmp_path: Path, caplog) -> None:
        from frob.tickets._models import Origin, Ticket, TicketKind, TicketState
        from frob.tickets._store import _serialize_ticket, tickets_dir

        tickets_dir(tmp_path).mkdir()
        from datetime import date

        ticket = Ticket(
            id="T-0001",
            title="legacy ticket",
            kind=TicketKind.BUG,
            state=TicketState.QUEUED,
            origin=Origin.HUMAN,
            body="body text",
            created=date.today(),
        )
        (tickets_dir(tmp_path) / "T-0001-legacy-ticket.md").write_text(
            _serialize_ticket(ticket)
        )
        cfg = AppConfig(ticket_command="migrate", ticket_path=tmp_path)
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "migrated 1 ticket(s)" in caplog.text
        assert (tmp_path / "tickets.md").exists()


class TestTicketRenumber:
    def test_dry_run_without_old_new_exits_1(self, tmp_path: Path) -> None:
        cfg = AppConfig(
            ticket_command="renumber", ticket_path=tmp_path, ticket_dry_run=True
        )
        with pytest.raises(SystemExit):
            ticket_run(cfg)

    def test_whole_ledger_already_contiguous(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(ticket_command="renumber", ticket_path=tmp_path)
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "already contiguous" in caplog.text

    def test_one_missing_new_id_exits_1(self, tmp_path: Path) -> None:
        cfg = AppConfig(
            ticket_command="renumber",
            ticket_path=tmp_path,
            ticket_old_id="T-0001",
        )
        with pytest.raises(SystemExit):
            ticket_run(cfg)

    def test_renumber_one_dry_run_prints_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        from frob.tickets._models import RenumberReport

        report = RenumberReport(
            old_id="T-0001",
            new_id="T-0042",
            ledger_changed=True,
            files_changed=("a.py", "b.py"),
            occurrences=3,
            dry_run=True,
        )
        import frob.tickets as tickets_mod

        monkeypatch.setattr(tickets_mod, "renumber_one", lambda *a, **k: Ok(report))
        cfg = AppConfig(
            ticket_command="renumber",
            ticket_path=tmp_path,
            ticket_old_id="T-0001",
            ticket_new_id="T-0042",
            ticket_dry_run=True,
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "would rewrite T-0001 -> T-0042" in caplog.text
        assert "a.py" in caplog.text
        assert "b.py" in caplog.text

    def test_renumber_one_success(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="renumber me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="renumber",
            ticket_path=tmp_path,
            ticket_old_id="T-0001",
            ticket_new_id="T-0042",
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "T-0001 -> T-0042" in caplog.text
        assert load_queue(tmp_path).danger_ok.tickets.get("T-0042") is not None


class TestTicketLand:
    def test_missing_id_exits_1(self, tmp_path: Path) -> None:
        cfg = AppConfig(ticket_command="land", ticket_path=tmp_path)
        with pytest.raises(SystemExit):
            ticket_run(cfg)

    def test_missing_worktree_exits_1(self, tmp_path: Path) -> None:
        cfg = AppConfig(ticket_command="land", ticket_path=tmp_path, ticket_id="T-0001")
        with pytest.raises(SystemExit):
            ticket_run(cfg)

    def test_land_failure_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        import frob.tickets as tickets_mod
        from frob.tickets import TicketError

        monkeypatch.setattr(
            tickets_mod, "land", lambda *a, **k: Err(TicketError.NotFound)
        )
        cfg = AppConfig(
            ticket_command="land",
            ticket_path=tmp_path,
            ticket_id="T-0001",
            ticket_worktree=tmp_path,
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "ticket land failed" in caplog.text

    def test_land_dry_run_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        from frob.tickets._models import LandReport

        report = LandReport(
            ticket_id="T-0001",
            final_id="T-0001",
            dry_run=True,
            wip_committed=False,
            merged_main_into_worktree=True,
            ledger_spliced=False,
        )
        import frob.tickets as tickets_mod

        monkeypatch.setattr(tickets_mod, "land", lambda *a, **k: Ok(report))
        cfg = AppConfig(
            ticket_command="land",
            ticket_path=tmp_path,
            ticket_id="T-0001",
            ticket_worktree=tmp_path,
            ticket_dry_run=True,
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "DRY RUN clean" in caplog.text

    def test_land_success_prints_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        from frob.tickets._models import LandReport

        report = LandReport(
            ticket_id="T-0001",
            final_id="T-0001",
            dry_run=False,
            wip_committed=True,
            merged_main_into_worktree=True,
            ledger_spliced=True,
            commit_sha="deadbeef",
            files_changed=("a.py",),
        )
        import frob.tickets as tickets_mod

        monkeypatch.setattr(tickets_mod, "land", lambda *a, **k: Ok(report))
        cfg = AppConfig(
            ticket_command="land",
            ticket_path=tmp_path,
            ticket_id="T-0001",
            ticket_worktree=tmp_path,
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "landed as T-0001 at deadbeef" in caplog.text
        assert "a.py" in caplog.text


class TestTicketPlan:
    def test_missing_id_exits_1(self, tmp_path: Path) -> None:
        cfg = AppConfig(ticket_command="plan", ticket_path=tmp_path)
        with pytest.raises(SystemExit):
            ticket_run(cfg)

    def test_plan_success(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="plan me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(ticket_command="plan", ticket_path=tmp_path, ticket_id="T-0001")
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "planned T-0001" in caplog.text
        assert (
            load_queue(tmp_path).danger_ok.tickets["T-0001"].state
            == TicketState.PLANNED
        )


class TestTicketStart:
    def test_missing_id_exits_1(self, tmp_path: Path) -> None:
        cfg = AppConfig(ticket_command="start", ticket_path=tmp_path)
        with pytest.raises(SystemExit):
            ticket_run(cfg)

    def test_unknown_id_exits_1(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="start", ticket_path=tmp_path, ticket_id="T-9999"
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "no ticket" in caplog.text

    def test_start_auto_plans_queued_ticket(self, tmp_path: Path, caplog) -> None:
        # T-0474: `start`'s default backgrounds the pre-work sweep -- it
        # logs that the sweep was LAUNCHED, not "swept T-0001" (that line
        # only comes from `_run_sweep` actually completing, which now
        # happens in a detached subprocess, not this one).
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="start me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="start", ticket_path=tmp_path, ticket_id="T-0001"
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "auto-planned T-0001" in caplog.text
        assert "pre-work sweep launched in the background" in caplog.text
        assert (
            load_queue(tmp_path).danger_ok.tickets["T-0001"].state
            == TicketState.IN_PROGRESS
        )

    # frob:ticket T-1645
    def test_start_warns_on_over_broad_scope(self, tmp_path: Path, caplog) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_batch7.py::TestTicketStart.test_start_warns_on_ov\
        # er_broad_scope
        """T-1645: `start` surfaces TICK009's over-broad-scope nudge
        directly, right when the ticket enters `PLANNED`/`IN_PROGRESS` --
        "narrow it now" is actionable in the moment, not a warning that
        accumulates silently in a full-repo check nobody reads."""
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="broad scope ticket",
            ticket_kind="bug",
            ticket_scope=["src/frob/**"],
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="start", ticket_path=tmp_path, ticket_id="T-0001"
        )
        with caplog.at_level("WARNING"):
            ticket_run(cfg)
        assert "T-0001" in caplog.text
        assert "chronically over-broad" in caplog.text or "narrow it" in caplog.text

    # frob:ticket T-1645
    def test_start_precise_scope_warns_nothing(self, tmp_path: Path, caplog) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_batch7.py::TestTicketStart.test_start_precise_sco\
        # pe_warns_nothing
        """A precisely-scoped ticket's `start` produces no scope-breadth
        nudge at all."""
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="precise scope ticket",
            ticket_kind="bug",
            ticket_scope=["tests/test_gates.py"],
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="start", ticket_path=tmp_path, ticket_id="T-0001"
        )
        with caplog.at_level("WARNING"):
            ticket_run(cfg)
        assert "chronically over-broad" not in caplog.text

    def test_start_foreground_runs_sweep_synchronously(
        self, tmp_path: Path, caplog
    ) -> None:
        """`--foreground` (`ticket_foreground=True`) is T-0474's opt-out --
        the sweep completes synchronously, in this process, exactly like
        every `start` did before T-0474."""
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="start me fg",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="start",
            ticket_path=tmp_path,
            ticket_id="T-0001",
            ticket_foreground=True,
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "swept T-0001" in caplog.text
        assert "pre-work sweep launched in the background" not in caplog.text

    def test_start_already_in_progress_exits_1(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="start me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="start", ticket_path=tmp_path, ticket_id="T-0001"
        )
        ticket_run(cfg)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "already in-progress" in caplog.text


class TestSpawnBackgroundSweep:
    """`frob.app.ticket_runner._spawn_background_sweep` (T-0474): the
    default `start` no longer blocks on the pre-work sweep -- it launches
    it as a detached subprocess and returns."""

    def test_spawns_detached_sweep_subprocess(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep.test_spawns_d\
        # etached_sweep_subprocess
        import subprocess
        import sys

        from frob.app import ticket_runner as ticket_runner_mod

        calls: list[dict] = []

        class _FakePopen:
            def __init__(self, argv, **kwargs) -> None:  # noqa: ANN001
                calls.append({"argv": argv, "kwargs": kwargs})

        monkeypatch.setattr(subprocess, "Popen", _FakePopen)
        ticket_runner_mod._spawn_background_sweep(tmp_path, "T-0001")

        assert len(calls) == 1
        argv = calls[0]["argv"]
        assert argv[:1] == [sys.executable]
        assert "sweep" in argv
        assert "T-0001" in argv
        assert calls[0]["kwargs"]["start_new_session"] is True

    def test_popen_failure_falls_back_to_synchronous_sweep(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        """A spawn failure (e.g. a sandboxed environment refusing
        `subprocess.Popen`) must never silently drop the sweep -- it falls
        back to running it synchronously right there."""
        # frob:tests \
        # tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep.test_popen_fa\
        # ilure_falls_back_to_synchronous_sweep
        import subprocess

        from frob.app import ticket_runner as ticket_runner_mod

        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="fallback me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(ticket_command="plan", ticket_path=tmp_path, ticket_id="T-0001")
        ticket_run(cfg)
        # Manually drive to in-progress the way `_start` does, so the
        # helper under test sees a real in-progress ticket to sweep.
        from frob.tickets import TicketState, transition

        assert transition(tmp_path, "T-0001", TicketState.IN_PROGRESS).is_ok

        def _raise(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            raise OSError("sandbox refused Popen")

        monkeypatch.setattr(subprocess, "Popen", _raise)
        with caplog.at_level("INFO"):
            ticket_runner_mod._spawn_background_sweep(tmp_path, "T-0001")
        assert "background sweep spawn failed" in caplog.text
        assert "swept T-0001" in caplog.text

    def test_exec_kill_switch_forces_synchronous_sweep(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        """FROB_DISABLE_EXEC must genuinely stop the spawn (the cli node's
        `may "exec"` kill-switch claim in design/frob.strata, T-0474): no
        Popen at all, sweep runs synchronously in-process instead."""
        # frob:tests \
        # tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep.test_exec_kil\
        # l_switch_forces_synchronous_sweep
        import subprocess

        from frob.app import ticket_runner as ticket_runner_mod

        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="kill switch me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(ticket_command="plan", ticket_path=tmp_path, ticket_id="T-0001")
        ticket_run(cfg)
        from frob.tickets import TicketState, transition

        assert transition(tmp_path, "T-0001", TicketState.IN_PROGRESS).is_ok

        def _fail(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            raise AssertionError("Popen must not be called under the kill switch")

        monkeypatch.setattr(subprocess, "Popen", _fail)
        monkeypatch.setenv("FROB_DISABLE_EXEC", "1")
        with caplog.at_level("INFO"):
            ticket_runner_mod._spawn_background_sweep(tmp_path, "T-0001")
        assert "exec kill switch" in caplog.text
        assert "swept T-0001" in caplog.text


class TestTicketRequeue:
    def test_missing_id_exits_1(self, tmp_path: Path) -> None:
        cfg = AppConfig(ticket_command="requeue", ticket_path=tmp_path)
        with pytest.raises(SystemExit):
            ticket_run(cfg)

    def test_unknown_id_exits_1(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="requeue", ticket_path=tmp_path, ticket_id="T-9999"
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "no ticket" in caplog.text

    def test_requeue_success(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="requeue me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="start", ticket_path=tmp_path, ticket_id="T-0001"
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="requeue",
            ticket_path=tmp_path,
            ticket_id="T-0001",
            ticket_reason="parked, wrong assumption",
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "T-0001 requeued (in-progress -> queued): parked, wrong assumption" in (
            caplog.text
        )
        assert (
            load_queue(tmp_path).danger_ok.tickets["T-0001"].state == TicketState.QUEUED
        )

    def test_requeue_not_in_progress_exits_1(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="requeue me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="requeue", ticket_path=tmp_path, ticket_id="T-0001"
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "not in-progress" in caplog.text


class TestTicketStartTransitionFailure:
    def test_transition_to_in_progress_failure_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="start me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        # queued -> planned succeeds for real, but planned -> in-progress fails.
        import frob.tickets as tickets_mod
        from frob.tickets import TicketError, TicketState

        real_transition = tickets_mod.transition

        def _fake_transition(root, ticket_id, state):
            if state == TicketState.IN_PROGRESS:
                return Err(TicketError.InvalidTransition)
            return real_transition(root, ticket_id, state)

        monkeypatch.setattr(tickets_mod, "transition", _fake_transition)
        cfg = AppConfig(
            ticket_command="start", ticket_path=tmp_path, ticket_id="T-0001"
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "ticket start failed" in caplog.text


class TestTicketSweep:
    def test_missing_id_exits_1(self, tmp_path: Path) -> None:
        cfg = AppConfig(ticket_command="sweep", ticket_path=tmp_path)
        with pytest.raises(SystemExit):
            ticket_run(cfg)

    def test_not_in_progress_exits_1(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="sweep me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="sweep", ticket_path=tmp_path, ticket_id="T-0001"
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "is not in-progress" in caplog.text


class TestTicketReconcileCli:
    """`frob ticket reconcile` (T-0476) dispatch smoke test -- the real
    stale-hold/orphan-worktree behavior is covered end to end (real `git
    worktree` fixtures) by `tests/test_ticket_reconcile.py`; this just
    exercises the CLI plumbing (flag wiring, log summary, clean exit) on
    the trivial no-anomalies case."""

    def test_no_anomalies_logs_clean_summary(self, tmp_path: Path, caplog) -> None:
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        cfg = AppConfig(ticket_command="reconcile", ticket_path=tmp_path)
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "no stale in-progress holds found" in caplog.text
        assert "no orphan worktrees found" in caplog.text

    def test_load_error_exits_1(self, tmp_path: Path, caplog) -> None:
        _write_malformed_ledger(tmp_path)
        cfg = AppConfig(ticket_command="reconcile", ticket_path=tmp_path)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "ticket reconcile failed" in caplog.text


class TestClipboardAttachOnNew:
    """`_maybe_attach_clipboard_image`, exercised via `frob ticket new` on a
    monkeypatched TTY + clipboard."""

    def test_no_clipboard_image_skips(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        import frob.tickets.clipboard as clipboard_mod

        monkeypatch.setattr(clipboard_mod, "clipboard_has_image", lambda: False)
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="clip me",
            ticket_kind="bug",
        )
        ticket_run(cfg)  # must not hang / not raise

    def test_declined_answer_skips_attach(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        import frob.tickets.clipboard as clipboard_mod

        monkeypatch.setattr(clipboard_mod, "clipboard_has_image", lambda: True)
        monkeypatch.setattr("builtins.input", lambda *_: "n")
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="clip me",
            ticket_kind="bug",
        )
        ticket_run(cfg)

    def test_accepted_answer_attaches(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        import frob.tickets.clipboard as clipboard_mod

        monkeypatch.setattr(clipboard_mod, "clipboard_has_image", lambda: True)
        monkeypatch.setattr("builtins.input", lambda *_: "y")

        import frob.tickets as tickets_mod
        from frob.tickets._models import Attachment

        monkeypatch.setattr(
            tickets_mod,
            "attach",
            lambda *a, **k: Ok(
                Attachment(
                    path="tickets/attachments/T-0001/x.png",
                    caption="",
                    sha256="ab" * 32,
                )
            ),
        )
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="clip me",
            ticket_kind="bug",
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "attached clipboard image" in caplog.text


class TestTicketAttach:
    def test_missing_id_exits_1(self, tmp_path: Path) -> None:
        cfg = AppConfig(ticket_command="attach", ticket_path=tmp_path)
        with pytest.raises(SystemExit):
            ticket_run(cfg)

    def test_no_path_non_tty_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="attach me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        cfg = AppConfig(
            ticket_command="attach", ticket_path=tmp_path, ticket_id="T-0001"
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "no path given and stdin is not a TTY" in caplog.text

    def test_attach_from_path_success(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="attach me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        image = tmp_path / "img.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 16)
        cfg = AppConfig(
            ticket_command="attach",
            ticket_path=tmp_path,
            ticket_id="T-0001",
            ticket_attach_path=image,
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "attached" in caplog.text


class TestTicketBlock:
    def test_missing_args_exits_1(self, tmp_path: Path) -> None:
        cfg = AppConfig(ticket_command="block", ticket_path=tmp_path)
        with pytest.raises(SystemExit):
            ticket_run(cfg)

    def test_block_success(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="block me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="block",
            ticket_path=tmp_path,
            ticket_id="T-0001",
            ticket_by="T-0002",
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "T-0001 now blocked by T-0002" in caplog.text
        ticket = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert ticket.blocked_by == ("T-0002",)


class TestTicketClose:
    def test_missing_id_exits_1(self, tmp_path: Path) -> None:
        cfg = AppConfig(ticket_command="close", ticket_path=tmp_path)
        with pytest.raises(SystemExit):
            ticket_run(cfg)

    def test_close_queued_gives_start_hint(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="close me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="close", ticket_path=tmp_path, ticket_id="T-0001"
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "frob ticket start T-0001" in caplog.text

    def test_close_missing_evidence_gives_hint(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="close me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="start", ticket_path=tmp_path, ticket_id="T-0001"
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="close", ticket_path=tmp_path, ticket_id="T-0001"
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "missing evidence or a Done report" in caplog.text

    def test_close_with_bad_evidence_ids_exits_1_without_closing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_collect(monkeypatch, frozenset())
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="close me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="start", ticket_path=tmp_path, ticket_id="T-0001"
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="close",
            ticket_path=tmp_path,
            ticket_id="T-0001",
            ticket_evidence_ids=["tests/x.py::nope"],
        )
        with pytest.raises(SystemExit):
            ticket_run(cfg)
        ticket = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert ticket.state == TicketState.IN_PROGRESS


class TestTicketFail:
    def test_missing_args_exits_1(self, tmp_path: Path) -> None:
        cfg = AppConfig(ticket_command="fail", ticket_path=tmp_path)
        with pytest.raises(SystemExit):
            ticket_run(cfg)

    def test_unknown_id_exits_1(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="fail",
            ticket_path=tmp_path,
            ticket_id="T-9999",
            ticket_summary="oops",
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "no ticket" in caplog.text

    def test_fail_records_attempt(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="fail me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="fail",
            ticket_path=tmp_path,
            ticket_id="T-0001",
            ticket_summary="didn't work",
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "recorded failure attempt 1" in caplog.text


class TestTicketEvidence:
    def test_missing_args_exits_1(self, tmp_path: Path) -> None:
        cfg = AppConfig(ticket_command="evidence", ticket_path=tmp_path)
        with pytest.raises(SystemExit):
            ticket_run(cfg)

    def test_evidence_ids_applied(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        _patch_collect(monkeypatch, frozenset({"tests/x.py::test_a"}))
        _patch_passing(monkeypatch)
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="evidence me",
            ticket_kind="bug",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="evidence",
            ticket_path=tmp_path,
            ticket_id="T-0001",
            ticket_evidence_ids=["tests/x.py::test_a"],
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "evidence now has 1 id(s)" in caplog.text

    def test_evidence_cmd_applied_for_docs_ticket(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="docs ticket",
            ticket_kind="docs",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="evidence",
            ticket_path=tmp_path,
            ticket_id="T-0001",
            ticket_evidence_cmd="true",
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "evidence now has 1 entries" in caplog.text

    def test_evidence_cmd_failure_logs_error(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="docs ticket",
            ticket_kind="docs",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="evidence",
            ticket_path=tmp_path,
            ticket_id="T-0001",
            ticket_evidence_cmd="false",
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            ticket_run(cfg)
        assert "ticket evidence-cmd failed" in caplog.text


class TestTicketArchive:
    def test_nothing_to_archive(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(ticket_command="archive", ticket_path=tmp_path)
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "nothing to archive" in caplog.text

    def test_archives_done_ticket(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="archive me",
            ticket_kind="docs",
            ticket_body="## Done report\n\nDone.\n",
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="start", ticket_path=tmp_path, ticket_id="T-0001"
        )
        ticket_run(cfg)
        cfg = AppConfig(
            ticket_command="close",
            ticket_path=tmp_path,
            ticket_id="T-0001",
            ticket_evidence_cmd="true",
        )
        ticket_run(cfg)
        cfg = AppConfig(ticket_command="archive", ticket_path=tmp_path)
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "archived 1 ticket(s)" in caplog.text


# ---------------------------------------------------------------------------
# sys_runner
# ---------------------------------------------------------------------------

_CLEAN_MODEL = """\
module m
node evil : foreign
node api : trusted
flow f1 : evil -> api { rate 5 req/s; attr timeout; }
"""

_GAP_MODEL = """\
module m
node evil : foreign
node web : trusted {
    may "sql";
}
flow f1 : evil -> web
"""


def _init_design_repo(tmp_path: Path, model: str) -> Path:
    """A minimal frob repo (no git needed for direct-call `run(cfg)` tests):
    empty ledger + one design file."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "tickets.md").write_text("# Tickets\n")
    (repo / "design").mkdir()
    (repo / "design" / "m.strata").write_text(model)
    return repo


class TestSysRunnerDispatch:
    def test_unknown_command_exits_1(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(sys_command="bogus", sys_path=tmp_path)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            sys_run(cfg)
        assert exc.value.code == 1
        assert "usage: frob sys" in caplog.text


class TestSysPlan:
    def test_no_design_models(self, tmp_path: Path, caplog) -> None:
        repo = tmp_path / "empty"
        repo.mkdir()
        (repo / "tickets.md").write_text("# Tickets\n")
        cfg = AppConfig(sys_command="plan", sys_path=repo)
        with caplog.at_level("INFO"):
            sys_run(cfg)
        assert "no design models" in caplog.text

    def test_dry_run_prints_plan(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, _GAP_MODEL)
        cfg = AppConfig(sys_command="plan", sys_path=repo)
        with caplog.at_level("INFO"):
            sys_run(cfg)
        assert "DRY RUN" in caplog.text

    def test_apply_writes_tickets(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, _GAP_MODEL)
        cfg = AppConfig(sys_command="plan", sys_path=repo, sys_apply=True)
        with caplog.at_level("INFO"):
            sys_run(cfg)
        assert "sys plan: created" in caplog.text
        assert load_queue(repo).danger_ok.tickets

    def test_file_arg_fails(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        cfg = AppConfig(sys_command="plan", sys_path=repo / "design" / "m.strata")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            sys_run(cfg)
        assert "is a file" in caplog.text

    def test_malformed_design_file_exits_1(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, "not a valid design file {{{")
        cfg = AppConfig(sys_command="plan", sys_path=repo)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            sys_run(cfg)
        assert "failed to load" in caplog.text

    def test_apply_new_ticket_failure_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        repo = _init_design_repo(tmp_path, _GAP_MODEL)
        import frob.app.sys_runner as sys_runner_mod
        from frob.tickets import TicketError

        monkeypatch.setattr(
            sys_runner_mod, "new_ticket", lambda *a, **k: Err(TicketError.DuplicateId)
        )
        cfg = AppConfig(sys_command="plan", sys_path=repo, sys_apply=True)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            sys_run(cfg)
        assert "failed to create ticket" in caplog.text

    def test_custom_design_dir_from_frob_toml(self, tmp_path: Path, caplog) -> None:
        repo = tmp_path / "custom"
        repo.mkdir()
        (repo / "tickets.md").write_text("# Tickets\n")
        (repo / "frob.toml").write_text('[strata]\ndesign_dir = "models"\n')
        (repo / "models").mkdir()
        (repo / "models" / "m.strata").write_text(_CLEAN_MODEL)
        cfg = AppConfig(sys_command="plan", sys_path=repo)
        with caplog.at_level("INFO"):
            sys_run(cfg)
        assert "DRY RUN" in caplog.text

    def test_unreadable_frob_toml_falls_back_to_default(
        self, tmp_path: Path, caplog
    ) -> None:
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        (repo / "frob.toml").write_text("not [ valid toml")
        cfg = AppConfig(sys_command="plan", sys_path=repo)
        with caplog.at_level("WARNING"):
            sys_run(cfg)
        assert "frob.toml unreadable" in caplog.text

    def test_unchanged_model_second_run_no_new_tickets(
        self, tmp_path: Path, caplog
    ) -> None:
        repo = _init_design_repo(tmp_path, _GAP_MODEL)
        cfg = AppConfig(sys_command="plan", sys_path=repo, sys_apply=True)
        sys_run(cfg)
        cfg = AppConfig(sys_command="plan", sys_path=repo, sys_apply=True)
        with caplog.at_level("INFO"):
            sys_run(cfg)
        assert "model unchanged, nothing to plan" in caplog.text


class TestSysDoc:
    def test_no_design_models(self, tmp_path: Path, caplog) -> None:
        repo = tmp_path / "empty"
        repo.mkdir()
        (repo / "tickets.md").write_text("# Tickets\n")
        cfg = AppConfig(sys_command="doc", sys_path=repo)
        with caplog.at_level("INFO"):
            sys_run(cfg)
        assert "no design models" in caplog.text

    def test_renders_matrix(self, tmp_path: Path, capsys) -> None:
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        cfg = AppConfig(sys_command="doc", sys_path=repo)
        sys_run(cfg)
        out = capsys.readouterr().out
        assert out.strip() != ""

    def test_malformed_design_file_exits_1(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, "not a valid design file {{{")
        cfg = AppConfig(sys_command="doc", sys_path=repo)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            sys_run(cfg)
        assert "failed to load" in caplog.text

    def test_unknown_view_exits_1(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        cfg = AppConfig(sys_command="doc", sys_path=repo, sys_view="bogus-view")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            sys_run(cfg)
        assert "sys doc:" in caplog.text


class TestSysExport:
    def test_bad_format_exits_1(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        cfg = AppConfig(
            sys_command="export",
            sys_export_format="bogus",
            sys_export_path=repo / "design" / "m.strata",
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            sys_run(cfg)
        assert "--format must be one of" in caplog.text

    def test_directory_path_exits_1(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        cfg = AppConfig(
            sys_command="export",
            sys_export_format="k8s",
            sys_export_path=repo / "design",
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            sys_run(cfg)
        assert "is a directory" in caplog.text

    def test_missing_path_exits_1(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(
            sys_command="export",
            sys_export_format="k8s",
            sys_export_path=tmp_path / "ghost.strata",
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            sys_run(cfg)
        assert "does not exist" in caplog.text

    def test_parse_failure_exits_1(self, tmp_path: Path, caplog) -> None:
        bad = tmp_path / "bad.strata"
        bad.write_text("not a valid design file {{{")
        cfg = AppConfig(
            sys_command="export", sys_export_format="k8s", sys_export_path=bad
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            sys_run(cfg)
        assert "parse failed" in caplog.text

    @pytest.mark.parametrize("fmt", ["k8s", "seccomp", "iam"])
    def test_each_format_renders(self, tmp_path: Path, capsys, fmt: str) -> None:
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        cfg = AppConfig(
            sys_command="export",
            sys_export_format=fmt,
            sys_export_path=repo / "design" / "m.strata",
        )
        sys_run(cfg)
        out = capsys.readouterr().out
        assert out.strip() != ""

    def test_default_design_path(self, tmp_path: Path, monkeypatch, capsys) -> None:
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        (repo / "design" / "frob.strata").write_text(_CLEAN_MODEL)
        monkeypatch.chdir(repo)
        cfg = AppConfig(sys_command="export", sys_export_format="k8s")
        sys_run(cfg)
        out = capsys.readouterr().out
        assert out.strip() != ""

    def test_dangling_flow_endpoint_fails_closed(
        self, tmp_path: Path, caplog
    ) -> None:
        # frob:tests src/frob/app/sys_runner.py::_load_export_model kind="unit"
        # T-1834: a flow naming a node id declared nowhere in the file must
        # fail closed via elaborate_merged's check_cross_file_references,
        # the same way a design loaded under design/ would -- not silently
        # build a KernelModel with a dangling flow endpoint.
        bad = tmp_path / "dangling.strata"
        bad.write_text(
            "module m\n"
            "node api : trusted\n"
            "flow f1 : ghost -> api { rate 5 req/s; attr timeout; }\n"
        )
        cfg = AppConfig(
            sys_command="export", sys_export_format="k8s", sys_export_path=bad
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            sys_run(cfg)
        assert exc.value.code == 1
        assert "elaborate failed" in caplog.text
        assert "ghost" in caplog.text


class TestSysAudit:
    def test_no_design_models(self, tmp_path: Path, caplog) -> None:
        repo = tmp_path / "empty"
        repo.mkdir()
        (repo / "tickets.md").write_text("# Tickets\n")
        cfg = AppConfig(sys_command="audit", sys_path=repo)
        with caplog.at_level("INFO"):
            sys_run(cfg)
        assert "no design models" in caplog.text

    def test_clean_model_passes(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        cfg = AppConfig(sys_command="audit", sys_path=repo)
        with caplog.at_level("INFO"):
            sys_run(cfg)
        assert "PROVED" in caplog.text

    def test_malformed_design_file_exits_1(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, "not a valid design file {{{")
        cfg = AppConfig(sys_command="audit", sys_path=repo)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            sys_run(cfg)
        assert "failed to load" in caplog.text

    def test_waived_gap_still_proves_clean(self, tmp_path: Path, caplog) -> None:
        model = """\
module m
node evil : foreign
node web : trusted {
    may "sql";
    waive "THREAT003:CWE-89" reason "test waiver, no real risk here" ticket "T-0001";
}
flow f1 : evil -> web
"""
        repo = _init_design_repo(tmp_path, model)
        cfg = AppConfig(sys_command="audit", sys_path=repo)
        with caplog.at_level("WARNING"), pytest.raises(SystemExit):
            sys_run(cfg)
        assert "WAIVED" in caplog.text

    def test_gap_model_exits_1(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, _GAP_MODEL)
        cfg = AppConfig(sys_command="audit", sys_path=repo)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            sys_run(cfg)
        assert "gap(s) found" in caplog.text

    def test_file_arg_fails(self, tmp_path: Path, caplog) -> None:
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        cfg = AppConfig(sys_command="audit", sys_path=repo / "design" / "m.strata")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit):
            sys_run(cfg)
        assert "is a file" in caplog.text
