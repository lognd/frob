""".claude/hooks/pending-background-guard.py: Stop hook that refuses to let
a turn end while it is stranding a pending background Bash task (T-2282).

Subprocess-only, matching `tests/test_hook_frob_timeout_guard.py`'s own
pattern -- the hook is a standalone script outside the `frob` package,
exercised through its real stdin/stdout/exit-code contract.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# frob:ticket T-2282
_REPO_ROOT = Path(__file__).resolve().parents[1]
# frob:ticket T-2282
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "pending-background-guard.py"


# frob:ticket T-2282
def _write_transcript(tmp_path: Path, lines: list[str]) -> Path:
    """A transcript JSONL file at `tmp_path` containing one JSON object per
    line of `lines` (already-serialized objects, one per event)."""
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# frob:ticket T-2282
def _run_hook(*, transcript_path: str, stop_hook_active: bool = False):
    """Invoke the hook's real Stop stdin/stdout contract."""
    payload = {
        "stop_hook_active": stop_hook_active,
        "transcript_path": transcript_path,
        "session_id": "test-session",
        "cwd": str(_REPO_ROOT),
    }
    return subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )


_AUTO_BACKGROUND_EVENT = json.dumps(
    {
        "type": "user",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "content": (
                        "Command did not complete within its 120s timeout "
                        "and was moved to the background (ID: bwge3ogaw)."
                    ),
                    "is_error": False,
                }
            ]
        },
        "toolUseResult": {"backgroundTaskId": "bwge3ogaw"},
    }
)

_EXPLICIT_BACKGROUND_EVENT = json.dumps(
    {
        "type": "user",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "content": (
                        "Command running in background with ID: bm2mdahb7. "
                        "Output is being written to: /tmp/x.output. You "
                        "will be notified when it completes."
                    ),
                    "is_error": False,
                }
            ]
        },
    }
)

_COMPLETION_NOTIFICATION_EVENT = json.dumps(
    {
        "type": "user",
        "message": {
            "content": (
                "[SYSTEM NOTIFICATION]<task-notification>"
                "<task-id>bwge3ogaw</task-id><status>completed</status>"
                "</task-notification>"
            )
        },
        "origin": {"kind": "task-notification"},
    }
)


# frob:tests .claude/hooks/pending-background-guard.py::main kind="integration"
# frob:ticket T-2282
def test_auto_backgrounded_task_with_no_resolution_is_blocked(tmp_path):
    """Acceptance 2 (MUST FAIL FIRST before this ticket, since the hook did
    not exist): a turn ending right after the harness auto-backgrounds a
    call, with no completion notification and no poll, is blocked."""
    transcript = _write_transcript(tmp_path, [_AUTO_BACKGROUND_EVENT])
    result = _run_hook(transcript_path=str(transcript))
    assert result.stdout.strip() != ""
    decision = json.loads(result.stdout)
    assert decision["decision"] == "block"


# frob:tests .claude/hooks/pending-background-guard.py::main kind="integration"
# frob:ticket T-2282
def test_explicit_run_in_background_with_no_resolution_is_blocked(tmp_path):
    """Same failure mode via the explicit `run_in_background: true` path
    (T-2239's own incident shape) rather than the harness auto-background
    path -- both must be caught, since this hook fires on the stranding,
    not on how the task was created."""
    transcript = _write_transcript(tmp_path, [_EXPLICIT_BACKGROUND_EVENT])
    result = _run_hook(transcript_path=str(transcript))
    decision = json.loads(result.stdout)
    assert decision["decision"] == "block"


# frob:tests .claude/hooks/pending-background-guard.py::main kind="integration"
# frob:ticket T-2282
def test_resolved_via_completion_notification_is_not_blocked(tmp_path):
    """A background task whose completion notification already arrived in
    the transcript is NOT pending -- must not block."""
    transcript = _write_transcript(
        tmp_path, [_AUTO_BACKGROUND_EVENT, _COMPLETION_NOTIFICATION_EVENT]
    )
    result = _run_hook(transcript_path=str(transcript))
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/pending-background-guard.py::main kind="integration"
# frob:ticket T-2282
def test_reentrant_stop_does_not_block_twice():
    """MUST-STILL-PASS (no deadlock): once this hook has already blocked
    once (`stop_hook_active=True` on the re-invoked Stop event), it must
    not block again even if the same task is still pending -- otherwise a
    genuinely-stuck agent could never report-and-stop."""
    result = _run_hook(
        transcript_path="/nonexistent/does-not-matter.jsonl",
        stop_hook_active=True,
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/pending-background-guard.py::main kind="integration"
# frob:ticket T-2282
def test_reentrant_stop_with_real_pending_task_does_not_block_twice(tmp_path):
    """Same as above but with a REAL pending task in the transcript --
    confirms the re-entrancy check is checked before the transcript is
    even consulted, matching `diagnosis-nudge.py`'s own posture."""
    transcript = _write_transcript(tmp_path, [_AUTO_BACKGROUND_EVENT])
    result = _run_hook(transcript_path=str(transcript), stop_hook_active=True)
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/pending-background-guard.py::main kind="integration"
# frob:ticket T-2282
def test_no_background_task_normal_stop_is_not_blocked(tmp_path):
    """MUST-STILL-PASS: report-and-stop with no background task involved at
    all is never blocked -- the common case."""
    normal_event = json.dumps(
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "Done."}]},
        }
    )
    transcript = _write_transcript(tmp_path, [normal_event])
    result = _run_hook(transcript_path=str(transcript))
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/pending-background-guard.py::main kind="integration"
# frob:ticket T-2282
def test_missing_transcript_file_fails_open():
    """A transcript path that cannot be read must never crash or block --
    this hook must not become a NEW way to get stuck."""
    result = _run_hook(transcript_path="/nonexistent/no-such-file.jsonl")
    assert result.returncode == 0
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/pending-background-guard.py::main kind="integration"
# frob:ticket T-2282
def test_malformed_stdin_fails_open():
    """Malformed JSON on stdin must degrade to silence, not a crash."""
    result = subprocess.run(
        [sys.executable, str(_HOOK)],
        input="not json",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/pending-background-guard.py::main kind="integration"
# frob:ticket T-2282
def test_single_event_described_by_both_start_patterns_is_not_self_resolved(
    tmp_path,
):
    """A single real background-start is described by BOTH the structured
    `backgroundTaskId` field and the human-readable acknowledgement text in
    the SAME transcript line -- this must not read as the id "reappearing
    later" and falsely resolve a still-pending task against itself."""
    transcript = _write_transcript(tmp_path, [_AUTO_BACKGROUND_EVENT])
    result = _run_hook(transcript_path=str(transcript))
    decision = json.loads(result.stdout)
    assert decision["decision"] == "block"
