""".claude/hooks/frob-suggest.py: PreToolUse Bash hook that nudges toward
frob-native equivalents of raw commands (T-2031 extends it to cover
hand-rolled coordinator measurement: `handrolled-floor-count` and
`handrolled-fleet-probe`).

Subprocess-only, matching `tests/test_hook_diagnosis_nudge.py`'s own pattern
-- the hook is a standalone script outside the `frob` package (a hyphenated
filename is not even a valid Python module name), so it is exercised
through its real stdin/stdout/exit-code contract, never imported directly.

Drift between this repo-tracked source and its `~/.claude/hooks/`
materialized copy is covered elsewhere and NOT duplicated here (T-2031
acceptance criterion 6): `tests/unit/test_claude_runner.py`'s
`TestDriftWarning`/`TestDriftReport`/`TestRun` classes exercise
`frob.app.claude_runner.drift_warning`/`drift_report`/`run`, the machinery
behind the "Claude config DRIFT: ... reconcile with `frob claude sync`"
message this file's own edit history tripped mid-ticket."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "frob-suggest.py"


def _init_repo(root: Path) -> None:
    """Create a minimal git repo with a `frob.toml` marker so the hook's
    `_repo_root` walk finds it (the hook no-ops entirely outside a frob
    repo)."""
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    (root / "frob.toml").write_text("", encoding="utf-8")


def _run_hook(command: str, *, home: Path, cwd: Path):
    """Invoke the hook's real PreToolUse stdin/stdout contract for a Bash
    `command`, with `home` isolating the O_EXCL marker state dir per test."""
    payload = {"tool_input": {"command": command}, "cwd": str(cwd)}
    return subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "HOME": str(home)},
    )


def _denial_reason(result) -> str | None:
    """The `permissionDecisionReason` string when the hook denied, else
    `None`."""
    out = result.stdout.strip()
    if not out:
        return None
    payload = json.loads(out)
    return payload.get("hookSpecificOutput", {}).get("permissionDecisionReason")


# frob:tests .claude/hooks/frob-suggest.py::main kind="integration"
def test_check_count_pipeline_is_blocked_naming_check_summary(tmp_path: Path):
    """A `frob check | grep` counting pipeline is blocked once, naming
    `scripts/check_summary.py` -- T-2031 acceptance criterion 1. This exact
    shape (`2>&1` before the pipe) is why the gap class must be `[^|;]*`,
    not `[^|;&]*`: an earlier attempt excluding `&` matched nothing here."""
    home = tmp_path / "home"
    root = tmp_path / "repo"
    _init_repo(root)
    command = (
        'uv run frob check --only gates 2>&1 | grep -E "^(ERROR|FAIL|gate:)" | tail -25'
    )
    result = _run_hook(command, home=home, cwd=root)
    reason = _denial_reason(result)
    assert reason is not None, "expected the pipeline to be blocked"
    assert "check_summary.py" in reason


# frob:tests .claude/hooks/frob-suggest.py::main kind="integration"
def test_fleet_probe_combo_is_blocked_naming_fleet_status(tmp_path: Path):
    """`git status --porcelain` COMBINED with `ps aux | grep` (the actual
    hand-rolled root-dirtiness diagnosis from T-2031's measured recurrence
    2) is blocked once, naming `scripts/fleet_status.py` -- acceptance
    criterion 2."""
    home = tmp_path / "home"
    root = tmp_path / "repo"
    _init_repo(root)
    command = "git status --porcelain && ps aux | grep 'ticket land' | grep -v grep"
    result = _run_hook(command, home=home, cwd=root)
    reason = _denial_reason(result)
    assert reason is not None, "expected the combined probe to be blocked"
    assert "fleet_status.py" in reason


# frob:tests .claude/hooks/frob-suggest.py::main kind="integration"
def test_fleet_probe_combo_with_worktree_list_is_blocked(tmp_path: Path):
    """`git status --porcelain` combined with `git worktree list` (the
    other named liveness probe) is blocked the same way, order-independent
    -- second half of acceptance criterion 2."""
    home = tmp_path / "home"
    root = tmp_path / "repo"
    _init_repo(root)
    command = "git worktree list; git status --porcelain"
    result = _run_hook(command, home=home, cwd=root)
    reason = _denial_reason(result)
    assert reason is not None, "expected the combined probe to be blocked"
    assert "fleet_status.py" in reason


# frob:tests .claude/hooks/frob-suggest.py::main kind="integration"
def test_fleet_probe_combo_with_pgrep_is_blocked(tmp_path: Path):
    """`git status --porcelain` combined with `pgrep` is blocked -- the
    third named liveness probe alternative."""
    home = tmp_path / "home"
    root = tmp_path / "repo"
    _init_repo(root)
    command = "git status --porcelain; pgrep -f 'ticket land'"
    result = _run_hook(command, home=home, cwd=root)
    reason = _denial_reason(result)
    assert reason is not None, "expected the combined probe to be blocked"
    assert "fleet_status.py" in reason


# frob:tests .claude/hooks/frob-suggest.py::main kind="integration"
def test_second_identical_check_pipeline_is_allowed_through(tmp_path: Path):
    """Block-once-then-allow: the SAME `frob check | grep` command a second
    time is let through -- T-2031 acceptance criterion 3."""
    home = tmp_path / "home"
    root = tmp_path / "repo"
    _init_repo(root)
    command = 'uv run frob check --only gates 2>&1 | grep -E "^ERROR" | tail -25'
    first = _run_hook(command, home=home, cwd=root)
    assert _denial_reason(first) is not None
    second = _run_hook(command, home=home, cwd=root)
    assert second.stdout.strip() == ""


# frob:tests .claude/hooks/frob-suggest.py::main kind="integration"
def test_second_identical_fleet_probe_is_allowed_through(tmp_path: Path):
    """Block-once-then-allow for the `handrolled-fleet-probe` rule
    specifically -- T-2031 acceptance criterion 3's other new rule."""
    home = tmp_path / "home"
    root = tmp_path / "repo"
    _init_repo(root)
    command = "git status --porcelain && ps aux | grep frob"
    first = _run_hook(command, home=home, cwd=root)
    assert _denial_reason(first) is not None
    second = _run_hook(command, home=home, cwd=root)
    assert second.stdout.strip() == ""


# frob:tests .claude/hooks/frob-suggest.py::main kind="integration"
def test_plain_check_only_gates_is_not_blocked(tmp_path: Path):
    """`uv run frob check --only gates` alone, with no counting pipeline,
    must NOT be blocked -- T-2031 acceptance criterion 4/7 (the
    false-positive trap: a rule that fires on ordinary `frob check` usage
    trains the operator to pattern-dodge it)."""
    home = tmp_path / "home"
    root = tmp_path / "repo"
    _init_repo(root)
    result = _run_hook("uv run frob check --only gates", home=home, cwd=root)
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-suggest.py::main kind="integration"
def test_check_piped_to_tail_only_is_not_blocked(tmp_path: Path):
    """`... 2>&1 | tail -30` with no `grep` in the pipeline must NOT be
    blocked -- acceptance criterion 7's second required negative case."""
    home = tmp_path / "home"
    root = tmp_path / "repo"
    _init_repo(root)
    result = _run_hook(
        "uv run frob check --only gates 2>&1 | tail -30", home=home, cwd=root
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-suggest.py::main kind="integration"
def test_git_grep_piped_to_grep_is_not_blocked_by_new_rules(tmp_path: Path):
    """`git grep ... | grep ...` must NOT be blocked by either new rule --
    acceptance criterion 7's third required negative case. (The pre-
    existing `unscoped-symbol-search` rule may still fire on the bare `git
    grep` itself; that rule is not new and not this ticket's concern -- only
    confirm neither NEW rule's suggestion text appears.)"""
    home = tmp_path / "home"
    root = tmp_path / "repo"
    _init_repo(root)
    result = _run_hook('git grep -n "foo" -- src/ | grep bar', home=home, cwd=root)
    reason = _denial_reason(result)
    if reason is not None:
        assert "check_summary.py" not in reason
        assert "fleet_status.py" not in reason


# frob:tests .claude/hooks/frob-suggest.py::main kind="integration"
def test_plain_git_status_porcelain_is_not_blocked(tmp_path: Path):
    """A bare `git status --porcelain` (no liveness probe combined in) is
    routine hygiene, not the fleet-probe shape, and must not be blocked --
    acceptance criterion 7's fourth required negative case."""
    home = tmp_path / "home"
    root = tmp_path / "repo"
    _init_repo(root)
    result = _run_hook("git status --porcelain", home=home, cwd=root)
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-suggest.py::main kind="integration"
def test_bare_ps_aux_grep_alone_is_not_blocked(tmp_path: Path):
    """`ps aux | grep ...` alone, without `git status --porcelain`
    combined in, is not the fleet-probe shape either (only ONE of the two
    root-state signals) and must not be blocked."""
    home = tmp_path / "home"
    root = tmp_path / "repo"
    _init_repo(root)
    result = _run_hook(
        "ps aux | grep 'ticket land' | grep -v grep", home=home, cwd=root
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-suggest.py::main kind="integration"
def test_check_summary_invocation_itself_is_not_blocked(tmp_path: Path):
    """Piping into `check_summary.py` IS the fix -- the rule must not nudge
    its own remedy."""
    home = tmp_path / "home"
    root = tmp_path / "repo"
    _init_repo(root)
    command = "uv run frob check --json | python3 scripts/check_summary.py"
    result = _run_hook(command, home=home, cwd=root)
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-suggest.py::main kind="integration"
def test_fleet_status_invocation_itself_is_not_blocked(tmp_path: Path):
    """A command that already invokes `fleet_status.py` alongside a
    root-state probe must not be nudged toward itself."""
    home = tmp_path / "home"
    root = tmp_path / "repo"
    _init_repo(root)
    command = (
        "git status --porcelain && ps aux | grep frob && "
        "python3 scripts/fleet_status.py"
    )
    result = _run_hook(command, home=home, cwd=root)
    assert result.stdout.strip() == ""
