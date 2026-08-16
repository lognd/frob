"""frob.app.telemetry: non-gated agentic time/token telemetry (T-0178)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from frob.app.telemetry import (
    TELEMETRY_REL,
    append_event,
    detect_footguns,
    estimate_tokens,
    is_disabled,
    iso_now,
    record_cli_event,
    record_dispatch_event,
    record_ticket_event,
    redact_command,
    render_tips,
    timed_call,
    tips_disabled,
    tree_hash,
    usage_report,
)


def test_append_event_writes_one_json_line(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::append_event
    append_event(tmp_path, {"a": 1})
    append_event(tmp_path, {"a": 2})
    lines = (tmp_path / TELEMETRY_REL).read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["a"] for line in lines] == [1, 2]


def test_append_event_respects_no_telemetry_env(tmp_path: Path, monkeypatch):
    # frob:tests src/frob/app/telemetry.py::is_disabled
    monkeypatch.setenv("FROB_NO_TELEMETRY", "1")
    assert is_disabled()
    append_event(tmp_path, {"a": 1})
    assert not (tmp_path / TELEMETRY_REL).exists()


def test_no_telemetry_env_false_like_values_stay_enabled(tmp_path: Path, monkeypatch):
    # frob:tests src/frob/app/telemetry.py::is_disabled
    monkeypatch.setenv("FROB_NO_TELEMETRY", "0")
    assert not is_disabled()
    monkeypatch.delenv("FROB_NO_TELEMETRY", raising=False)
    assert not is_disabled()


def test_record_cli_event_shape(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::record_cli_event
    record_cli_event(
        tmp_path,
        subcommand="check",
        args_head="check --json",
        duration_ms=12.5,
        exit_code=0,
    )
    line = (tmp_path / TELEMETRY_REL).read_text(encoding="utf-8").strip()
    record = json.loads(line)
    assert record["kind"] == "cli"
    assert record["subcommand"] == "check"
    assert record["exit"] == 0
    assert record["duration_ms"] == 12.5
    assert "iso_ts" in record
    assert "tree_hash" in record


def test_record_ticket_event_shape(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::record_ticket_event
    record_ticket_event(tmp_path, ticket_id="T-0001", event="started")
    line = (tmp_path / TELEMETRY_REL).read_text(encoding="utf-8").strip()
    record = json.loads(line)
    assert record == {
        "kind": "ticket",
        "ticket_id": "T-0001",
        "event": "started",
        "iso_ts": record["iso_ts"],
    }


class TestRecordDispatchEvent:
    """T-1724: the dispatch-boundary recording API `dispatch_cost_report`
    joins against `kind="tool"`/`kind="ticket"` events by timestamp
    window."""

    def test_start_and_end_events_shaped_correctly(self, tmp_path: Path):
        # frob:tests src/frob/app/telemetry.py::record_dispatch_event
        record_dispatch_event(
            tmp_path,
            dispatch_id="d1",
            event="start",
            worktree="/repo/.claude/worktrees/x",
            branch="worktree-x",
            cold_start=True,
        )
        record_dispatch_event(tmp_path, dispatch_id="d1", event="end")
        lines = (tmp_path / TELEMETRY_REL).read_text(encoding="utf-8").splitlines()
        start, end = (json.loads(line) for line in lines)
        assert start["kind"] == "dispatch"
        assert start["dispatch_id"] == "d1"
        assert start["event"] == "start"
        assert start["worktree"] == "/repo/.claude/worktrees/x"
        assert start["branch"] == "worktree-x"
        assert start["cold_start"] is True
        assert "iso_ts" in start
        assert end["kind"] == "dispatch"
        assert end["event"] == "end"

    def test_optional_fields_omitted_when_none(self, tmp_path: Path):
        # frob:tests src/frob/app/telemetry.py::record_dispatch_event
        record_dispatch_event(tmp_path, dispatch_id="d1", event="start")
        record = json.loads(
            (tmp_path / TELEMETRY_REL).read_text(encoding="utf-8").strip()
        )
        assert "worktree" not in record
        assert "branch" not in record
        assert "cold_start" not in record


# invariant spec: [INV-022](invariants/INV-022.md)
def test_redact_command_hides_recognizable_secret():
    # frob:tests src/frob/app/telemetry.py::redact_command
    fake_key = "sk-ant-api03-" + ("a" * 95)
    redacted = redact_command(f"echo {fake_key}")
    assert fake_key not in redacted
    assert "chars)" in redacted


def test_redact_command_leaves_ordinary_text_alone():
    # frob:tests src/frob/app/telemetry.py::redact_command
    assert redact_command("check --json --path .") == "check --json --path ."


def test_estimate_tokens_is_len_over_four():
    # frob:tests src/frob/app/telemetry.py::estimate_tokens
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcdefgh") == 2


def test_iso_now_has_iso_shape_with_z_suffix():
    # frob:tests src/frob/app/telemetry.py::iso_now
    ts = iso_now()
    assert ts.endswith("Z")
    assert "T" in ts
    # round-trips through fromisoformat once the Z is swapped for +00:00
    datetime.fromisoformat(ts.replace("Z", "+00:00"))


def test_timed_call_records_event_and_returns_value(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::timed_call
    result = timed_call(tmp_path, subcommand="check", args_head="check", fn=lambda: 42)
    assert result == 42
    record = json.loads((tmp_path / TELEMETRY_REL).read_text(encoding="utf-8").strip())
    assert record["exit"] == 0
    assert record["subcommand"] == "check"


def test_timed_call_records_nonzero_exit_on_system_exit(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::timed_call
    def _boom():
        raise SystemExit(1)

    try:
        timed_call(tmp_path, subcommand="check", args_head="check", fn=_boom)
    except SystemExit:
        pass
    record = json.loads((tmp_path / TELEMETRY_REL).read_text(encoding="utf-8").strip())
    assert record["exit"] == 1


def test_timed_call_maps_bare_system_exit_to_zero(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::timed_call
    def _bare_exit():
        raise SystemExit()

    try:
        timed_call(tmp_path, subcommand="check", args_head="check", fn=_bare_exit)
    except SystemExit:
        pass
    record = json.loads((tmp_path / TELEMETRY_REL).read_text(encoding="utf-8").strip())
    assert record["exit"] == 0


def test_timed_call_maps_non_int_system_exit_code_to_one(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::timed_call
    def _msg_exit():
        raise SystemExit("boom")

    try:
        timed_call(tmp_path, subcommand="check", args_head="check", fn=_msg_exit)
    except SystemExit:
        pass
    record = json.loads((tmp_path / TELEMETRY_REL).read_text(encoding="utf-8").strip())
    assert record["exit"] == 1


def test_append_event_swallows_oserror_and_logs(tmp_path: Path, caplog):
    # frob:tests src/frob/app/telemetry.py::append_event
    # T-1457: an I/O failure writing the telemetry file must never raise --
    # telemetry is best-effort and must not be able to break a real
    # invocation. Force `Path.open` to fail with an OSError and confirm the
    # call returns normally, with the failure only logged at debug.
    import logging

    with caplog.at_level(logging.DEBUG, logger="frob.app.telemetry"):
        with patch("frob.app.telemetry.Path.open", side_effect=OSError("disk full")):
            append_event(tmp_path, {"a": 1})
    assert not (tmp_path / TELEMETRY_REL).exists()
    assert any("append failed (ignored)" in rec.message for rec in caplog.records)


def test_tree_hash_returns_unknown_when_git_spawn_errors(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::tree_hash
    # T-1457: `run_argv` itself failing (git binary missing, spawn refused,
    # etc.) is the `spawned.is_err` branch -- must degrade to "unknown"
    # rather than raise.
    from typani import Err

    from frob.gitio import GitError

    with patch("frob.gitio.run_argv", return_value=Err(GitError.GitFailed)):
        assert tree_hash(tmp_path) == "unknown"


def test_tree_hash_returns_unknown_on_nonzero_returncode(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::tree_hash
    # T-1457: git ran but exited nonzero (e.g. not a git repo) -- the
    # separate `result.returncode != 0` fallback branch.
    from typani import Ok

    from frob.gitio import ProcResult

    fake_result = ProcResult(
        argv=("git", "rev-parse", "--short", "HEAD"),
        returncode=128,
        stdout="",
        stderr="not a git repository",
    )
    with patch("frob.gitio.run_argv", return_value=Ok(fake_result)):
        assert tree_hash(tmp_path) == "unknown"


def test_tree_hash_returns_stripped_stdout_on_success(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::tree_hash
    # T-1457: happy path, kept alongside the two "unknown" fallback
    # branches so the whole function reads as intentional, not accidental.
    from typani import Ok

    from frob.gitio import ProcResult

    fake_result = ProcResult(
        argv=("git", "rev-parse", "--short", "HEAD"),
        returncode=0,
        stdout="abc1234\n",
        stderr="",
    )
    with patch("frob.gitio.run_argv", return_value=Ok(fake_result)):
        assert tree_hash(tmp_path) == "abc1234"


def test_record_ticket_event_merges_extra_fields(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::record_ticket_event
    # T-1457: the `if extra:` branch -- extra keys must land in the
    # written record alongside the fixed ticket-event fields.
    record_ticket_event(
        tmp_path,
        ticket_id="T-1457",
        event="done",
        extra={"duration_s": 42, "worktree": "w4k-test005"},
    )
    record = json.loads((tmp_path / TELEMETRY_REL).read_text(encoding="utf-8").strip())
    assert record["duration_s"] == 42
    assert record["worktree"] == "w4k-test005"
    assert record["ticket_id"] == "T-1457"
    assert record["event"] == "done"


def test_timed_call_records_nonzero_exit_on_plain_exception(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::timed_call
    # T-1457: a plain (non-SystemExit) exception from `fn()` must still
    # record exit_code=1 and re-raise unchanged -- the `except Exception`
    # branch, distinct from the SystemExit branches already covered above.
    def _boom():
        raise RuntimeError("kaboom")

    try:
        timed_call(tmp_path, subcommand="check", args_head="check", fn=_boom)
        raised = False
    except RuntimeError:
        raised = True
    assert raised
    record = json.loads((tmp_path / TELEMETRY_REL).read_text(encoding="utf-8").strip())
    assert record["exit"] == 1


def test_timed_call_does_not_leak_gitio_logs_onto_stdout(tmp_path: Path, capsys):
    # frob:tests src/frob/app/telemetry.py::timed_call
    # T-1360 regression: `_finish_timed_call`'s footgun-detection path used
    # to call `tree_hash(root)` (which spawns `git` via `frob.gitio`,
    # logging at DEBUG) OUTSIDE `quiet_stdout_logs()` -- only the LATER
    # `tree_hash` call inside `record_cli_event` was quieted. That left
    # gitio's spawn log free to print on stdout, appended after whatever
    # `fn()` itself already wrote there, corrupting any `--json` command's
    # stdout for a caller doing `json.loads(stdout)`. Use a real (tiny)
    # git repo so `tree_hash`'s git spawn genuinely happens and would
    # genuinely log if unquieted.
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@example.com",
            "-c",
            "user.name=t",
            "commit",
            "--allow-empty",
            "-q",
            "-m",
            "x",
        ],
        cwd=tmp_path,
        check=True,
    )

    def _print_json():
        print('{"ok": true}')
        return 0

    timed_call(tmp_path, subcommand="check", args_head="check --json", fn=_print_json)
    captured = capsys.readouterr()
    assert captured.out.strip() == '{"ok": true}'
    assert "gitio" not in captured.out


# --- footgun detection (T-1360) ---------------------------------------


def test_detect_footguns_flags_redundant_rerun(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::detect_footguns
    record_cli_event(
        tmp_path, subcommand="check", args_head="check", duration_ms=500, exit_code=0
    )
    tips = detect_footguns(
        tmp_path,
        subcommand="check",
        args_head="check",
        duration_ms=500,
        exit_code=0,
        tree_hash_value="unknown",
    )
    assert [t.rule_id for t in tips] == ["REDUNDANT_RERUN"]
    assert "before" in tips[0].message


def test_detect_footguns_flags_fast_exit1(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::detect_footguns
    tips = detect_footguns(
        tmp_path,
        subcommand="check",
        args_head="check --ticket T-1",
        duration_ms=250,
        exit_code=1,
        tree_hash_value="unknown",
    )
    assert "FAST_EXIT1" in [t.rule_id for t in tips]


def test_detect_footguns_does_not_flag_fast_exit1_on_success(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::detect_footguns
    tips = detect_footguns(
        tmp_path,
        subcommand="check",
        args_head="check",
        duration_ms=250,
        exit_code=0,
        tree_hash_value="unknown",
    )
    assert tips == []


def test_detect_footguns_flags_repeated_failure_streak(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::detect_footguns
    for _ in range(2):
        record_cli_event(
            tmp_path,
            subcommand="ticket",
            args_head="land T-1",
            duration_ms=5000,
            exit_code=1,
        )
    tips = detect_footguns(
        tmp_path,
        subcommand="ticket",
        args_head="land T-1",
        duration_ms=5000,
        exit_code=1,
        tree_hash_value="unknown",
    )
    assert "REPEATED_FAILURE" in [t.rule_id for t in tips]


def test_detect_footguns_respects_suppress_env(tmp_path: Path, monkeypatch):
    # frob:tests src/frob/app/telemetry.py::detect_footguns
    monkeypatch.setenv("FROB_SUPPRESS_TIPS", "FAST_EXIT1")
    tips = detect_footguns(
        tmp_path,
        subcommand="check",
        args_head="check",
        duration_ms=100,
        exit_code=1,
        tree_hash_value="unknown",
    )
    assert tips == []


def test_detect_footguns_returns_empty_when_tips_disabled(tmp_path: Path, monkeypatch):
    # frob:tests src/frob/app/telemetry.py::detect_footguns
    # frob:tests src/frob/app/telemetry.py::tips_disabled
    monkeypatch.setenv("FROB_NO_FOOTGUN_TIPS", "1")
    assert tips_disabled()
    tips = detect_footguns(
        tmp_path,
        subcommand="check",
        args_head="check",
        duration_ms=100,
        exit_code=1,
        tree_hash_value="unknown",
    )
    assert tips == []


def test_render_tips_json_is_parseable(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::render_tips
    tips = detect_footguns(
        tmp_path,
        subcommand="check",
        args_head="check",
        duration_ms=100,
        exit_code=1,
        tree_hash_value="unknown",
    )
    rendered = render_tips(tips, as_json=True)
    parsed = json.loads(rendered)
    assert parsed[0]["rule_id"] == "FAST_EXIT1"


def test_render_tips_empty_list_is_empty_string():
    # frob:tests src/frob/app/telemetry.py::render_tips
    assert render_tips([], as_json=True) == ""
    assert render_tips([], as_json=False) == ""


def test_render_tips_human_readable_names_the_rule():
    # frob:tests src/frob/app/telemetry.py::render_tips
    from frob.app.telemetry import Tip

    rendered = render_tips([Tip(rule_id="FAST_EXIT1", message="boom")], as_json=False)
    assert rendered == "[FAST_EXIT1] boom"


# --- usage_report / doctor --usage (T-1360) ----------------------------


def test_usage_report_empty_corpus_is_all_zero(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::usage_report
    report = usage_report(tmp_path)
    assert report.total_calls == 0
    assert report.total_duration_ms == 0.0
    assert report.failure_rate == 0.0
    assert report.top_time_sinks == []


def test_usage_report_aggregates_time_and_failures(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::usage_report
    record_cli_event(
        tmp_path, subcommand="check", args_head="check", duration_ms=1000, exit_code=0
    )
    record_cli_event(
        tmp_path, subcommand="check", args_head="check", duration_ms=500, exit_code=1
    )
    record_cli_event(
        tmp_path,
        subcommand="ticket",
        args_head="land T-1",
        duration_ms=2000,
        exit_code=0,
    )
    report = usage_report(tmp_path)
    assert report.total_calls == 3
    assert report.total_duration_ms == 3500.0
    assert report.failures == 1
    assert report.failure_rate == 1 / 3
    assert report.top_time_sinks[0].subcommand == "ticket"
    assert report.top_time_sinks[0].total_duration_ms == 2000.0


def test_usage_report_counts_redundant_reruns(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::usage_report
    for _ in range(3):
        record_cli_event(
            tmp_path,
            subcommand="check",
            args_head="check --ticket T-1",
            duration_ms=1000,
            exit_code=0,
        )
    report = usage_report(tmp_path)
    assert report.redundant_rerun_count == 2
    assert report.redundant_rerun_wasted_ms == 2000.0


def test_usage_report_counts_fast_exit1(tmp_path: Path):
    # frob:tests src/frob/app/telemetry.py::usage_report
    record_cli_event(
        tmp_path, subcommand="check", args_head="check", duration_ms=100, exit_code=1
    )
    report = usage_report(tmp_path)
    assert report.fast_exit1_count == 1


# --- REDUNDANT_RERUN must not fire across a real external-state change (T-2191) ---


def test_redundant_rerun_not_flagged_when_home_claude_config_changed(
    tmp_path: Path, monkeypatch
):
    # frob:tests src/frob/app/telemetry.py::detect_footguns
    # Reproduces the exact live incident: `frob claude sync --check`
    # reported drifted; `frob claude sync` wrote ~/.claude/refs/*; the next
    # `--check` claimed REDUNDANT_RERUN ("nothing has changed since") even
    # though its own materialized target had just changed. `tree_hash`
    # alone (the repo tree) cannot see this -- the change is entirely
    # under `~/.claude`, outside the repo `tmp_path` represents here.
    home = tmp_path / "fake-home"
    claude_refs = home / ".claude" / "refs"
    claude_refs.mkdir(parents=True)
    ref_file = claude_refs / "agent-playbook.md"
    ref_file.write_text("v1 -- stale copy")
    monkeypatch.setenv("HOME", str(home))

    record_cli_event(
        tmp_path,
        subcommand="claude",
        args_head="claude sync --check",
        duration_ms=500,
        exit_code=0,
    )

    # The materialized copy under ~/.claude changes -- exactly what
    # `frob claude sync` (no --check) does between the two `--check` runs
    # in the live incident. The repo tree (`tmp_path`) itself never moves.
    ref_file.write_text("v2 -- freshly synced content")

    tips = detect_footguns(
        tmp_path,
        subcommand="claude",
        args_head="claude sync --check",
        duration_ms=500,
        exit_code=0,
        tree_hash_value="unknown",
    )
    assert "REDUNDANT_RERUN" not in [t.rule_id for t in tips], (
        "REDUNDANT_RERUN fired even though ~/.claude (this verb's real "
        "input) changed between the two runs -- the tree_hash-only key "
        "cannot see state outside the repo"
    )


def test_redundant_rerun_still_flags_when_nothing_changed_at_all(
    tmp_path: Path, monkeypatch
):
    # frob:tests src/frob/app/telemetry.py::detect_footguns
    # The positive case: when NEITHER the repo tree NOR ~/.claude changed,
    # REDUNDANT_RERUN must still fire -- the fix must not blunt the
    # detector into never firing at all.
    home = tmp_path / "fake-home"
    claude_refs = home / ".claude" / "refs"
    claude_refs.mkdir(parents=True)
    (claude_refs / "agent-playbook.md").write_text("unchanged")
    monkeypatch.setenv("HOME", str(home))

    record_cli_event(
        tmp_path, subcommand="check", args_head="check", duration_ms=500, exit_code=0
    )
    tips = detect_footguns(
        tmp_path,
        subcommand="check",
        args_head="check",
        duration_ms=500,
        exit_code=0,
        tree_hash_value="unknown",
    )
    assert [t.rule_id for t in tips] == ["REDUNDANT_RERUN"]


# --- REDUNDANT_RERUN must not fire when an external PATH argument's own
# --- state changes either (T-2204) ---


class TestExternalPathArgHash:
    """`_external_path_arg_hash`/`REDUNDANT_RERUN` (T-2204): a verb taking
    an arbitrary positional PATH argument (`frob cycle <path>`) decides
    from that path's own on-disk state, which neither `tree_hash` (the
    repo tree) nor `home_config_hash` (the hardcoded `~/.claude` target,
    T-2191) describes at all."""

    # frob:ticket T-2204
    # frob:tests tests/test_telemetry.py::TestExternalPathArgHash.test_a_deleted_external_fixture_changes_the_hash  # noqa: E501
    def test_a_deleted_external_fixture_changes_the_hash(self, tmp_path: Path):
        # T-2204's DESIGNATED REPRO (BUG002): reproduces the exact live
        # incident. `frob cycle <fixture>/srclayout` (fixture lives
        # OUTSIDE the repo `tmp_path` represents here) reported a cycle
        # with a `pyproject.toml` present; deleting that file flips the
        # verdict to "no cycles found" -- a real result change `tree_hash`
        # structurally cannot see, since the fixture is not under `root`
        # at all. REDUNDANT_RERUN must not claim "nothing has changed"
        # across that deletion.
        fixture_root = tmp_path.parent / f"fixture-{tmp_path.name}"
        srclayout = fixture_root / "srclayout"
        srclayout.mkdir(parents=True)
        pyproject = srclayout / "pyproject.toml"
        pyproject.write_text("[tool.setuptools.packages.find]\nwhere = ['src']\n")

        args_head = f"cycle {srclayout}"
        record_cli_event(
            tmp_path,
            subcommand="cycle",
            args_head=args_head,
            duration_ms=300,
            exit_code=0,
        )

        # The verdict-determining input changes: the fixture's own
        # pyproject.toml is deleted, exactly as in the live incident.
        pyproject.unlink()

        tips = detect_footguns(
            tmp_path,
            subcommand="cycle",
            args_head=args_head,
            duration_ms=300,
            exit_code=0,
            tree_hash_value="unknown",
        )
        assert "REDUNDANT_RERUN" not in [t.rule_id for t in tips], (
            "REDUNDANT_RERUN fired even though the external fixture path "
            "named in args_head changed between the two runs -- neither "
            "tree_hash nor home_config_hash can see state outside the "
            "repo AND outside ~/.claude"
        )

    # frob:ticket T-2204
    # frob:tests tests/test_telemetry.py::TestExternalPathArgHash.test_still_flags_when_the_external_fixture_is_unchanged  # noqa: E501
    def test_still_flags_when_the_external_fixture_is_unchanged(
        self, tmp_path: Path
    ):
        # The positive case: when the named external path's own state
        # genuinely has not moved, REDUNDANT_RERUN must still fire -- the
        # fix must not blunt the detector into never firing at all.
        fixture_root = tmp_path.parent / f"fixture-{tmp_path.name}-2"
        srclayout = fixture_root / "srclayout"
        srclayout.mkdir(parents=True)
        (srclayout / "pyproject.toml").write_text("[tool.setuptools]\n")

        args_head = f"cycle {srclayout}"
        record_cli_event(
            tmp_path,
            subcommand="cycle",
            args_head=args_head,
            duration_ms=300,
            exit_code=0,
        )
        tips = detect_footguns(
            tmp_path,
            subcommand="cycle",
            args_head=args_head,
            duration_ms=300,
            exit_code=0,
            tree_hash_value="unknown",
        )
        assert [t.rule_id for t in tips] == ["REDUNDANT_RERUN"]

    # frob:ticket T-2204
    # frob:tests tests/test_telemetry.py::TestExternalPathArgHash.test_no_path_looking_argument_yields_none  # noqa: E501
    def test_no_path_looking_argument_yields_none(self, tmp_path: Path):
        # A subcommand with no PATH-shaped positional argument at all
        # (e.g. plain "check") must not be affected by this digest --
        # the redundant-rerun behavior for that case is unchanged.
        record_cli_event(
            tmp_path, subcommand="check", args_head="check", duration_ms=500, exit_code=0
        )
        tips = detect_footguns(
            tmp_path,
            subcommand="check",
            args_head="check",
            duration_ms=500,
            exit_code=0,
            tree_hash_value="unknown",
        )
        assert [t.rule_id for t in tips] == ["REDUNDANT_RERUN"]
