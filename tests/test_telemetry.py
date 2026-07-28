"""frob.app.telemetry: non-gated agentic time/token telemetry (T-0178)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from frob.app.telemetry import (
    TELEMETRY_REL,
    append_event,
    estimate_tokens,
    is_disabled,
    iso_now,
    record_cli_event,
    record_ticket_event,
    redact_command,
    timed_call,
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
