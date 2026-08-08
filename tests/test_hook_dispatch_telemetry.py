""".claude/hooks/dispatch-telemetry.py: SessionStart/Stop dispatch telemetry
hook (T-1787).

Subprocess-only, matching `tests/test_hook_diagnosis_nudge.py`'s own pattern
-- the hook is a standalone script outside the `frob` package, so it is
exercised through its real stdin/stdout/exit-code contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "dispatch-telemetry.py"


# frob:waive DUP001 reason="matches the existing 2-line _init_repo helper duplicated \
# identically across tests/test_telemetry_hook_script.py and \
# tests/test_hook_diagnosis_nudge.py -- same standalone-hook-test pattern, not worth a \
# shared conftest fixture for a 2-line git-init call"
def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)


def _run_hook(payload: dict, *, cwd: Path):
    return subprocess.run(
        [sys.executable, str(_HOOK)],
        cwd=str(cwd),
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )


def _telemetry_records(root: Path) -> list[dict]:
    path = root / ".frob" / "telemetry.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_session_start_records_dispatch_start_event(tmp_path: Path):
    # frob:tests .claude/hooks/dispatch-telemetry.py kind="integration"
    _init_repo(tmp_path)
    payload = {
        "hook_event_name": "SessionStart",
        "session_id": "sess-1",
        "cwd": str(tmp_path),
        "source": "startup",
    }
    result = _run_hook(payload, cwd=tmp_path)
    assert result.returncode == 0
    records = _telemetry_records(tmp_path)
    assert len(records) == 1
    record = records[0]
    assert record["kind"] == "dispatch"
    assert record["dispatch_id"] == "sess-1"
    assert record["event"] == "start"
    assert record["cold_start"] is True
    assert record["worktree"] == str(tmp_path)


def test_session_start_resume_is_not_cold_start(tmp_path: Path):
    # frob:tests .claude/hooks/dispatch-telemetry.py kind="integration"
    _init_repo(tmp_path)
    payload = {
        "hook_event_name": "SessionStart",
        "session_id": "sess-1",
        "cwd": str(tmp_path),
        "source": "resume",
    }
    _run_hook(payload, cwd=tmp_path)
    records = _telemetry_records(tmp_path)
    assert records[0]["cold_start"] is False


def test_session_start_unrecognized_source_omits_cold_start(tmp_path: Path):
    # frob:tests .claude/hooks/dispatch-telemetry.py kind="integration"
    _init_repo(tmp_path)
    payload = {
        "hook_event_name": "SessionStart",
        "session_id": "sess-1",
        "cwd": str(tmp_path),
    }
    _run_hook(payload, cwd=tmp_path)
    records = _telemetry_records(tmp_path)
    assert "cold_start" not in records[0]


def test_stop_records_dispatch_end_event(tmp_path: Path):
    # frob:tests .claude/hooks/dispatch-telemetry.py kind="integration"
    _init_repo(tmp_path)
    payload = {
        "hook_event_name": "Stop",
        "session_id": "sess-1",
        "cwd": str(tmp_path),
    }
    result = _run_hook(payload, cwd=tmp_path)
    assert result.returncode == 0
    records = _telemetry_records(tmp_path)
    assert len(records) == 1
    assert records[0]["kind"] == "dispatch"
    assert records[0]["event"] == "end"
    assert records[0]["dispatch_id"] == "sess-1"


def test_stop_skips_reentrant_stop_hook_active(tmp_path: Path):
    # frob:tests .claude/hooks/dispatch-telemetry.py kind="integration"
    _init_repo(tmp_path)
    payload = {
        "hook_event_name": "Stop",
        "session_id": "sess-1",
        "cwd": str(tmp_path),
        "stop_hook_active": True,
    }
    result = _run_hook(payload, cwd=tmp_path)
    assert result.returncode == 0
    assert _telemetry_records(tmp_path) == []


def test_start_and_end_share_dispatch_id_across_the_session(tmp_path: Path):
    # frob:tests .claude/hooks/dispatch-telemetry.py kind="integration"
    _init_repo(tmp_path)
    _run_hook(
        {
            "hook_event_name": "SessionStart",
            "session_id": "sess-9",
            "cwd": str(tmp_path),
            "source": "startup",
        },
        cwd=tmp_path,
    )
    _run_hook(
        {"hook_event_name": "Stop", "session_id": "sess-9", "cwd": str(tmp_path)},
        cwd=tmp_path,
    )
    records = _telemetry_records(tmp_path)
    assert len(records) == 2
    assert records[0]["dispatch_id"] == records[1]["dispatch_id"] == "sess-9"
    assert {records[0]["event"], records[1]["event"]} == {"start", "end"}


def test_unrecognized_hook_event_name_is_a_silent_noop(tmp_path: Path):
    # frob:tests .claude/hooks/dispatch-telemetry.py kind="integration"
    _init_repo(tmp_path)
    payload = {"hook_event_name": "PostToolUse", "cwd": str(tmp_path)}
    result = _run_hook(payload, cwd=tmp_path)
    assert result.returncode == 0
    assert _telemetry_records(tmp_path) == []


def test_never_blocks_on_malformed_stdin(tmp_path: Path):
    # frob:tests .claude/hooks/dispatch-telemetry.py kind="integration"
    _init_repo(tmp_path)
    result = subprocess.run(
        [sys.executable, str(_HOOK)],
        cwd=str(tmp_path),
        input="not json",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0


def test_no_git_repo_is_a_silent_noop(tmp_path: Path):
    # frob:tests .claude/hooks/dispatch-telemetry.py kind="integration"
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    payload = {
        "hook_event_name": "SessionStart",
        "session_id": "sess-1",
        "cwd": str(outside),
        "source": "startup",
    }
    result = _run_hook(payload, cwd=outside)
    assert result.returncode == 0
    assert not (outside / ".frob").exists()
