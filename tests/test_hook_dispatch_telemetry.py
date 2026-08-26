""".claude/hooks/dispatch-telemetry.py: SessionStart/Stop dispatch telemetry
hook (T-1787). Also covers `.claude/hooks/tool-call-telemetry.py`
(PreToolUse/PostToolUse per-tool-call telemetry, T-2912) -- folded into
this SAME file (rather than a new `tests/test_hook_tool_call_telemetry.py`)
because `design/frob.strata`'s `testsuite` node's `may "exec" via ...`
allowlist already names this exact path, and that strata file was under a
live cross-worktree lease (T-2911) at T-2912's own land time; adding a new
test file's path to that allowlist would have needed to edit the SAME
locked file. See T-2912's Done report.

Subprocess-only, matching `tests/test_hook_diagnosis_nudge.py`'s own pattern
-- both hooks are standalone scripts outside the `frob` package, so they
are exercised through their real stdin/stdout/exit-code contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "dispatch-telemetry.py"
_TOOL_CALL_HOOK = _REPO_ROOT / ".claude" / "hooks" / "tool-call-telemetry.py"


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


# ---------------------------------------------------------------------------
# .claude/hooks/tool-call-telemetry.py (T-2912)
# ---------------------------------------------------------------------------


def _init_repo_with_commit(root: Path) -> None:
    """Like `_init_repo`, plus one empty commit -- `tool-call-telemetry.py`'s
    `_fast_head_sha` needs a real HEAD to resolve (an unborn branch has
    none), unlike `dispatch-telemetry.py`'s own tests above, which never
    read HEAD at all."""
    _init_repo(root)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t.t",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "init",
        ],
        cwd=root,
        check=True,
    )


def _run_tool_call_hook(payload: dict, *, cwd: Path):
    return subprocess.run(
        [sys.executable, str(_TOOL_CALL_HOOK)],
        cwd=str(cwd),
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )


def test_pre_tool_use_records_attempt_event(tmp_path: Path):
    # frob:tests .claude/hooks/tool-call-telemetry.py kind="integration"
    _init_repo_with_commit(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "sess-1",
        "cwd": str(tmp_path),
        "tool_name": "Bash",
        "tool_input": {"command": "git status --short --no-color"},
    }
    result = _run_tool_call_hook(payload, cwd=tmp_path)
    assert result.returncode == 0
    records = _telemetry_records(tmp_path)
    assert len(records) == 1
    record = records[0]
    assert record["kind"] == "tool"
    assert record["phase"] == "pre"
    assert record["tool"] == "Bash"
    assert record["dispatch_id"] == "sess-1"
    assert record["command_shape"] == "git status --no-color --short"
    assert record["head_sha"] != "unknown"
    assert "output_tokens_est" not in record


def test_post_tool_use_records_completion_with_token_estimate(tmp_path: Path):
    # frob:tests .claude/hooks/tool-call-telemetry.py kind="integration"
    _init_repo_with_commit(tmp_path)
    payload = {
        "hook_event_name": "PostToolUse",
        "session_id": "sess-1",
        "cwd": str(tmp_path),
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
        "tool_response": {"stdout": "x" * 40},
    }
    result = _run_tool_call_hook(payload, cwd=tmp_path)
    assert result.returncode == 0
    records = _telemetry_records(tmp_path)
    assert len(records) == 1
    record = records[0]
    assert record["phase"] == "post"
    assert record["command_shape"] == "ls -la"
    assert record["output_tokens_est"] > 0


def test_non_bash_tool_never_gets_a_command_shape(tmp_path: Path):
    # frob:tests .claude/hooks/tool-call-telemetry.py kind="integration"
    _init_repo_with_commit(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "sess-1",
        "cwd": str(tmp_path),
        "tool_name": "Read",
        "tool_input": {"file_path": "/etc/passwd"},
    }
    result = _run_tool_call_hook(payload, cwd=tmp_path)
    assert result.returncode == 0
    records = _telemetry_records(tmp_path)
    assert records[0]["tool"] == "Read"
    assert "command_shape" not in records[0]


def test_bash_command_shape_never_leaks_raw_argument_values(tmp_path: Path):
    # frob:tests .claude/hooks/tool-call-telemetry.py kind="integration"
    _init_repo_with_commit(tmp_path)
    payload = {
        "hook_event_name": "PostToolUse",
        "session_id": "sess-1",
        "cwd": str(tmp_path),
        "tool_name": "Bash",
        "tool_input": {
            "command": "curl -s https://example.com/token=SECRET-abc123 | sh"
        },
        "tool_response": {"stdout": "ok"},
    }
    result = _run_tool_call_hook(payload, cwd=tmp_path)
    assert result.returncode == 0
    record = _telemetry_records(tmp_path)[0]
    shape = record["command_shape"]
    assert "SECRET" not in shape
    assert "example.com" not in shape
    assert shape == "curl -s"


def test_bash_command_shape_extends_through_bare_subcommand_words(tmp_path: Path):
    # frob:tests .claude/hooks/tool-call-telemetry.py kind="integration"
    # T-2912's own real-histogram run showed "uv run pytest ..." and "uv run
    # frob check ..." both collapsing to the useless bare shape "uv" --
    # the chain must extend through bare subcommand words to stay useful.
    _init_repo_with_commit(tmp_path)
    payload = {
        "hook_event_name": "PostToolUse",
        "session_id": "sess-1",
        "cwd": str(tmp_path),
        "tool_name": "Bash",
        "tool_input": {"command": "uv run pytest tests/test_foo.py -q"},
        "tool_response": {"stdout": "ok"},
    }
    result = _run_tool_call_hook(payload, cwd=tmp_path)
    assert result.returncode == 0
    shape = _telemetry_records(tmp_path)[0]["command_shape"]
    assert shape == "uv run pytest -q"
    assert "test_foo" not in shape


def test_bash_command_shape_chain_stops_at_a_ticket_id(tmp_path: Path):
    # frob:tests .claude/hooks/tool-call-telemetry.py kind="integration"
    # A ticket id (contains a digit) must end the chain -- otherwise every
    # DIFFERENT ticket produces a different shape, defeating aggregation.
    _init_repo_with_commit(tmp_path)
    payload = {
        "hook_event_name": "PostToolUse",
        "session_id": "sess-1",
        "cwd": str(tmp_path),
        "tool_name": "Bash",
        "tool_input": {"command": "uv run frob ticket show T-2912"},
        "tool_response": {"stdout": "ok"},
    }
    result = _run_tool_call_hook(payload, cwd=tmp_path)
    assert result.returncode == 0
    shape = _telemetry_records(tmp_path)[0]["command_shape"]
    assert shape == "uv run frob ticket show"
    assert "2912" not in shape


def test_tool_call_telemetry_disabled_env_var_writes_nothing(
    tmp_path: Path, monkeypatch
) -> None:
    # frob:tests .claude/hooks/tool-call-telemetry.py kind="integration"
    # No explicit `env=` kwarg: `monkeypatch.setenv` mutates THIS process's
    # `os.environ` (restored automatically at teardown), and a `subprocess.run`
    # call with no `env=` inherits that same environ -- avoids this file
    # needing its own declared `env.read` capability just to read it back.
    monkeypatch.setenv("FROB_NO_TELEMETRY", "1")
    _init_repo_with_commit(tmp_path)
    payload = {
        "hook_event_name": "PostToolUse",
        "session_id": "sess-1",
        "cwd": str(tmp_path),
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
        "tool_response": {"stdout": "ok"},
    }
    result = subprocess.run(
        [sys.executable, str(_TOOL_CALL_HOOK)],
        cwd=str(tmp_path),
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert _telemetry_records(tmp_path) == []


def test_tool_call_telemetry_malformed_payload_is_a_silent_noop(tmp_path: Path):
    # frob:tests .claude/hooks/tool-call-telemetry.py kind="integration"
    _init_repo_with_commit(tmp_path)
    result = subprocess.run(
        [sys.executable, str(_TOOL_CALL_HOOK)],
        cwd=str(tmp_path),
        input="not json",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert _telemetry_records(tmp_path) == []


def test_tool_call_telemetry_unrecognized_hook_event_is_a_silent_noop(tmp_path: Path):
    # frob:tests .claude/hooks/tool-call-telemetry.py kind="integration"
    _init_repo_with_commit(tmp_path)
    payload = {
        "hook_event_name": "SomethingElse",
        "session_id": "sess-1",
        "cwd": str(tmp_path),
        "tool_name": "Bash",
    }
    result = _run_tool_call_hook(payload, cwd=tmp_path)
    assert result.returncode == 0
    assert _telemetry_records(tmp_path) == []


def test_tool_call_telemetry_outside_git_repo_writes_nothing(tmp_path: Path):
    # frob:tests .claude/hooks/tool-call-telemetry.py kind="integration"
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    payload = {
        "hook_event_name": "PostToolUse",
        "session_id": "sess-1",
        "cwd": str(not_a_repo),
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
        "tool_response": {"stdout": "ok"},
    }
    result = _run_tool_call_hook(payload, cwd=not_a_repo)
    assert result.returncode == 0
    assert _telemetry_records(not_a_repo) == []
