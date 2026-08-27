"""T-3106: `frob ops process reap` -- a first-class, on-demand CLI verb
for `frob.process.reap_orphaned_forkservers` (T-3072/T-2443), which
previously only ran as a best-effort side effect of `frob check`
startup. Covers the CLI parser wiring (`frob._cli_parsers._ops`), the
`ops_runner.run` delegation, and `process_runner.run` itself -- both a
must-fire (pids reaped, reported) and a must-stay-quiet (a live-check-
parented forkserver is never touched, matching T-3072's own ancestry
walk which this ticket reuses rather than duplicating) case."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from frob.__main__ import _build_parser
from frob.app import ops_runner, process_runner
from frob.app.config import AppConfig


class TestProcessReapParser:
    """`frob ops process reap` must parse and reach `AppConfig.
    process_command`/`process_reap_json` -- the T-2004 "tested is not
    reached" class of gap this repo has been bitten by before."""

    def test_process_reap_parses_and_dispatches(self) -> None:
        """Bare `frob ops process reap` parses with `process_command ==
        'reap'` and `process_reap_json` defaulting False."""
        parser = _build_parser()
        args = parser.parse_args(["ops", "process", "reap"])
        assert args.ops_command == "process"
        assert args.process_command == "reap"
        assert args.process_reap_json is False

    def test_process_reap_json_flag_parses(self) -> None:
        """`--json` sets `process_reap_json` True."""
        parser = _build_parser()
        args = parser.parse_args(["ops", "process", "reap", "--json"])
        assert args.process_reap_json is True

    def test_process_reap_json_flag_reaches_appconfig(self) -> None:
        """The parsed `--json` flag actually reaches `AppConfig` through
        `from_external`'s real forwarding tables (T-2004) -- a flag that
        parses but never reaches its field is a defect this repo has
        been bitten by silently before."""
        parser = _build_parser()
        args = parser.parse_args(["ops", "process", "reap", "--json"])
        cfg = AppConfig.from_args(args)
        assert cfg.process_command == "reap"
        assert cfg.process_reap_json is True


class TestOpsRunnerProcessDelegation:
    """`ops_runner.run` must delegate `ops_command == "process"` into
    `process_runner.run`."""

    def test_process_subcommand_delegates_to_process_runner(self) -> None:
        """`ops_command="process"` calls `process_runner.run`, not any
        other branch."""
        cfg = AppConfig(command="ops", ops_command="process", process_command="reap")
        with patch.object(process_runner, "run") as mock_run:
            ops_runner.run(cfg)
        mock_run.assert_called_once_with(cfg)


class TestProcessRunnerReap:
    """`process_runner.run`'s `reap` branch: reports what `reap_orphaned_
    forkservers` actually did, in both text and `--json` modes, and
    refuses cleanly on an unknown subcommand."""

    def test_reap_reports_reaped_pids(self, capsys: pytest.CaptureFixture) -> None:
        """A non-empty reap result is reported by pid, human-readable
        mode."""
        cfg = AppConfig(command="ops", ops_command="process", process_command="reap")
        with patch(
            "frob.process.reap_orphaned_forkservers", return_value=[1234, 5678]
        ):
            process_runner.run(cfg)
        out = capsys.readouterr().out
        assert "1234" in out
        assert "5678" in out
        assert "SIGTERM" in out

    def test_reap_reports_nothing_reaped(self, capsys: pytest.CaptureFixture) -> None:
        """MUST-STAY-QUIET shape: an empty reap result (e.g. every
        forkserver found is parented to a live `frob check`, at any
        ancestry depth -- T-3072's own must-stay-quiet property, reused
        here rather than re-implemented) is reported as nothing to do,
        not an error."""
        cfg = AppConfig(command="ops", ops_command="process", process_command="reap")
        with patch("frob.process.reap_orphaned_forkservers", return_value=[]):
            process_runner.run(cfg)
        out = capsys.readouterr().out
        assert "nothing to reap" in out

    def test_reap_json_mode_emits_json(self, capsys: pytest.CaptureFixture) -> None:
        """`--json` emits a machine-readable payload instead of prose."""
        cfg = AppConfig(
            command="ops",
            ops_command="process",
            process_command="reap",
            process_reap_json=True,
        )
        with patch("frob.process.reap_orphaned_forkservers", return_value=[42]):
            process_runner.run(cfg)
        out = capsys.readouterr().out
        assert '"reaped_pids": [42]' in out

    def test_unknown_process_subcommand_exits_1(self) -> None:
        """An unrecognized `process_command` exits 1 rather than
        silently no-oping."""
        cfg = AppConfig(command="ops", ops_command="process", process_command="bogus")
        with pytest.raises(SystemExit) as exc:
            process_runner.run(cfg)
        assert exc.value.code == 1
