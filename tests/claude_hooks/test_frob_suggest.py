"""Tests for the frob-suggest hook and its settings installer (T-5101)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[2] / "scripts" / "claude-hooks"
sys.path.insert(0, str(HOOKS))
import frob_hook_settings as fhs  # noqa: E402

SCRIPT = Path("/h/frob-suggest.py")
CMD = "git worktree add ../x"


def run_hook(repo: Path, home: Path, command: str, session="s1", call="", env=None):
    """Run the hook as Claude Code does; returns parsed stdout or None."""
    payload = {"cwd": str(repo), "session_id": session, "tool_name": "Bash",
               "tool_input": {"command": command}}
    if call:
        payload["tool_use_id"] = call
    out = subprocess.run(
        [sys.executable, str(HOOKS / "frob-suggest.py")], input=json.dumps(payload),
        capture_output=True, text=True, env={"HOME": str(home), "PATH": "/usr/bin:/bin", **(env or {})},
        check=True,
    ).stdout
    return json.loads(out) if out.strip() else None


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    (r / "frob.toml").write_text("")
    return r


def rows(repo: Path):
    f = repo / ".frob" / "telemetry.jsonl"
    return [json.loads(line) for line in f.read_text().splitlines()] if f.exists() else []


def denied(out) -> bool:
    return bool(out) and out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_decisions_are_logged_to_telemetry(repo, tmp_path):
    assert denied(run_hook(repo, tmp_path, CMD))
    assert not denied(run_hook(repo, tmp_path, CMD))
    got = rows(repo)
    assert [r["decision"] for r in got] == ["block", "allow-rerun"]
    r = got[0]
    assert r["kind"] == "hook" and r["hook"] == "frob-suggest" and r["rule"] == "raw-worktree"
    assert r["agent"] == "s1" and r["shape"] == "git worktree add"


def test_per_rule_allow_only_suppresses_that_rule(repo, tmp_path):
    assert not denied(run_hook(repo, tmp_path, f"FROB_SUGGEST_ALLOW=raw-worktree {CMD}"))
    assert denied(run_hook(repo, tmp_path, f"FROB_SUGGEST_ALLOW=raw-linters {CMD}", session="s2"))
    assert rows(repo)[0]["decision"] == "allow-token"


def test_stale_ack_is_ignored_with_notice(repo, tmp_path):
    out = run_hook(repo, tmp_path, f"FROB_SUGGEST_ACK=1 {CMD}")
    assert denied(out)
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "FROB_SUGGEST_ACK=1 is retired" in reason
    assert "prefix it with `FROB_SUGGEST_ACK" not in reason
    assert "ignored-ack" in [r["decision"] for r in rows(repo)]


def test_duplicate_registration_does_not_overcount(repo, tmp_path):
    assert denied(run_hook(repo, tmp_path, CMD, call="c1"))
    assert denied(run_hook(repo, tmp_path, CMD, call="c1"))  # sibling instance, same call
    assert not denied(run_hook(repo, tmp_path, CMD, call="c2"))  # genuine rerun allowed


# ---- settings installer matrix ----

USER_HOOK = {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 /u/other.py"}]}
USER_EXTRA = {"matcher": "Read", "hooks": [{"type": "command", "command": "python3 /u/extra.py"}]}
PRE = {"permissions": {"allow": ["Bash(ls)"]}, "env": {"A": "1"},
       "hooks": {"PreToolUse": [USER_HOOK], "Stop": []}}


def count_frob(path: Path) -> int:
    data = json.loads(path.read_text())
    return sum(fhs._is_frob(h) for g in data["hooks"]["PreToolUse"] for h in g["hooks"])


@pytest.mark.parametrize("start", [None, {}, PRE], ids=["none", "empty", "preexisting"])
def test_install_uninstall_matrix(tmp_path, start):
    p = tmp_path / "settings.json"
    if start is not None:
        p.write_text(json.dumps(start))
    fhs.install(p, SCRIPT)
    assert count_frob(p) == 1
    first = p.read_bytes()
    assert fhs.install(p, SCRIPT) is False
    assert p.read_bytes() == first

    # user edits after install: add hook, add key, reorder
    data = json.loads(p.read_text())
    pre = data["hooks"]["PreToolUse"]
    pre.insert(0, USER_EXTRA)
    pre.reverse()
    data["model"] = "sonnet"
    p.write_text(fhs._dump(data))
    others = [g for g in pre if not any(fhs._is_frob(h) for h in g["hooks"])]

    assert fhs.uninstall(p) is True
    after = json.loads(p.read_text())
    assert after["model"] == "sonnet"
    assert after["hooks"]["PreToolUse"] == others
    for k in ("permissions", "env"):
        if start and k in start:
            assert after[k] == start[k]
    gone = p.read_bytes()
    assert fhs.uninstall(p) is False
    assert p.read_bytes() == gone

    fhs.install(p, SCRIPT)
    assert count_frob(p) == 1


def test_uninstall_without_frob_is_noop(tmp_path):
    p = tmp_path / "settings.json"
    assert fhs.uninstall(p) is False and not p.exists()
    p.write_text(json.dumps(PRE))
    before = p.read_bytes()
    assert fhs.uninstall(p) is False
    assert p.read_bytes() == before


def test_preexisting_empty_group_is_not_cleaned(tmp_path):
    p = tmp_path / "settings.json"
    empty = {"matcher": "Bash", "hooks": []}
    p.write_text(json.dumps({"hooks": {"PreToolUse": [empty]}}))
    fhs.install(p, SCRIPT)
    fhs.uninstall(p)
    assert json.loads(p.read_text())["hooks"]["PreToolUse"] == [empty]


def test_frob_created_group_is_removed(tmp_path):
    p = tmp_path / "settings.json"
    fhs.install(p, SCRIPT)
    fhs.uninstall(p)
    assert json.loads(p.read_text()) == {}


def test_double_registration_collapsed_on_install(tmp_path):
    p = tmp_path / "settings.json"
    legacy = {"type": "command", "command": "python3 /home/x/.claude/hooks/frob-suggest.py"}
    p.write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [legacy]}, USER_HOOK,
        {"matcher": "Edit", "hooks": [dict(legacy)]}]}}))
    fhs.install(p, SCRIPT)
    assert count_frob(p) == 1
    assert USER_HOOK in json.loads(p.read_text())["hooks"]["PreToolUse"]


def test_write_is_atomic_with_backup(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps(PRE))
    fhs.install(p, SCRIPT)
    assert json.loads((tmp_path / "settings.json.frob-bak").read_text()) == PRE
    assert not list(tmp_path.glob("*.tmp"))
