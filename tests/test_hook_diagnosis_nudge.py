""".claude/hooks/diagnosis-nudge.py: Stop-event diagnosis-nudge hook (T-1734).

Subprocess-only, matching `tests/test_telemetry_hook_script.py`'s own
pattern for `scripts/frob-telemetry-hook` -- the hook is a standalone
script outside the `frob` package (a hyphenated filename is not even a
valid Python module name), so it is exercised through its real stdin/
stdout/exit-code contract, never imported directly."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "diagnosis-nudge.py"


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)


def _run_hook(payload: dict, *, home: Path, cwd: Path | None = None):
    return subprocess.run(
        [sys.executable, str(_HOOK)],
        cwd=str(cwd) if cwd else None,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "HOME": str(home)},
    )


# frob:waive PII012 reason="T-1734: a software-defect finding, not a medical term"
def test_nudges_on_diagnosis_and_prints_system_message(tmp_path: Path):
    # frob:tests .claude/hooks/diagnosis-nudge.py kind="integration"
    home = tmp_path / "home"
    payload = {
        "last_assistant_message": "Root cause is the missing merge-base check.",
        "session_id": "s1",
    }
    result = _run_hook(payload, home=home)
    assert result.returncode == 0
    out = json.loads(result.stdout.strip())
    assert "systemMessage" in out
    assert "root cause is" in out["systemMessage"].lower()


def test_never_blocks_on_malformed_stdin(tmp_path: Path):
    # frob:tests .claude/hooks/diagnosis-nudge.py kind="integration"
    home = tmp_path / "home"
    result = subprocess.run(
        [sys.executable, str(_HOOK)],
        input="not json",
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "HOME": str(home)},
    )
    assert result.returncode == 0
    assert result.stdout == ""


# frob:waive PII012 reason="T-1734: a software-defect finding, not a medical term"
def test_no_message_when_no_diagnosis(tmp_path: Path):
    # frob:tests .claude/hooks/diagnosis-nudge.py kind="integration"
    home = tmp_path / "home"
    payload = {"last_assistant_message": "Landed the ticket cleanly."}
    result = _run_hook(payload, home=home)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_ordinary_bug_mention_does_not_nudge(tmp_path: Path):
    # frob:tests .claude/hooks/diagnosis-nudge.py kind="integration"
    # T-1734's own explicit warning: bare "bug"/"broken"/"should fix" as
    # substrings fire on every code review -- must NOT match alone.
    home = tmp_path / "home"
    payload = {
        "last_assistant_message": "Fixed the bug in the parser, see the Done report.",
    }
    result = _run_hook(payload, home=home)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_stop_hook_active_never_emits(tmp_path: Path):
    # frob:tests .claude/hooks/diagnosis-nudge.py kind="integration"
    home = tmp_path / "home"
    payload = {
        "stop_hook_active": True,
        "last_assistant_message": "Root cause is the missing merge-base check.",
    }
    result = _run_hook(payload, home=home)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_rate_limited_within_window(tmp_path: Path):
    # frob:tests .claude/hooks/diagnosis-nudge.py kind="integration"
    home = tmp_path / "home"
    payload = {
        "last_assistant_message": "Root cause is the missing merge-base check.",
        "session_id": "s1",
    }
    first = _run_hook(payload, home=home)
    assert first.stdout.strip() != ""
    second = _run_hook(payload, home=home)
    assert second.returncode == 0
    assert second.stdout.strip() == ""


def test_recently_filed_ticket_suppresses_nudge(tmp_path: Path):
    # frob:tests .claude/hooks/diagnosis-nudge.py kind="integration"
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    _init_repo(repo)
    telemetry = repo / ".frob" / "telemetry.jsonl"
    telemetry.parent.mkdir(parents=True)
    from datetime import UTC, datetime

    now_iso = datetime.now(UTC).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )
    telemetry.write_text(
        json.dumps(
            {
                "kind": "cli",
                "subcommand": "ticket",
                "args_head": "new --title x",
                "iso_ts": now_iso,
            }
        )
        + "\n"
    )
    payload = {
        "last_assistant_message": "Root cause is the missing merge-base check.",
        "session_id": "s2",
        "cwd": str(repo),
    }
    result = _run_hook(payload, home=home, cwd=repo)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_no_ticket_filed_still_nudges(tmp_path: Path):
    # frob:tests .claude/hooks/diagnosis-nudge.py kind="integration"
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    _init_repo(repo)
    payload = {
        "last_assistant_message": "Root cause is the missing merge-base check.",
        "session_id": "s3",
        "cwd": str(repo),
    }
    result = _run_hook(payload, home=home, cwd=repo)
    assert result.returncode == 0
    assert result.stdout.strip() != ""


def test_probe_removed_from_tracked_repo(tmp_path: Path):
    # frob:tests .claude/hooks/diagnosis-nudge.py kind="integration"
    # T-1734 acceptance criterion 5: the temporary Stop-event probe (and
    # its registration) must be gone once the real hook lands -- this
    # asserts against the REPO's own tracked config (the only part of
    # "remove the probe" a portable regression test can check; the
    # `~/.claude/` deletion is a one-time operator action, done as part
    # of landing this ticket, not something CI can re-verify per machine).
    probe_script = _REPO_ROOT / ".claude" / "hooks" / "_stop-probe.py"
    assert not probe_script.exists(), "the temporary probe script must be deleted"

    settings = json.loads(
        (_REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    stop_hooks = settings.get("hooks", {}).get("Stop", [])
    commands = [
        h.get("command", "")
        for entry in stop_hooks
        for h in entry.get("hooks", [])
    ]
    assert not any("_stop-probe" in cmd for cmd in commands), (
        "no Stop hook may still reference the retired probe script"
    )
    assert any("diagnosis-nudge.py" in cmd for cmd in commands), (
        "the real diagnosis-nudge hook must be registered on Stop"
    )
