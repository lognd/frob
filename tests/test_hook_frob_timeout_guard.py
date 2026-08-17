""".claude/hooks/frob-timeout-guard.py: PreToolUse Bash hook that refuses a
long-running frob verb invoked without a large tool-level `timeout`.

Subprocess-only, matching `tests/test_hook_frob_suggest.py`'s own pattern --
the hook is a standalone script outside the `frob` package (a hyphenated
filename is not even a valid Python module name), so it is exercised
through its real stdin/stdout/exit-code contract, never imported directly.

T-2248: extends coverage from the four originally-guarded verbs (`ticket
land`, `ticket done-report`, `check`, `test`) to also cover `ticket work`
and `ticket new`, both measured exceeding the 120s foreground cap the same
way (T-2248 ticket body). Every test here also stands as a MUST-STILL-PASS
control for the four pre-existing verbs, the two recorded false-positive
shapes (prose heredoc, quoted-string command), and the fast-verb negative
case -- T-2248 acceptance criterion 3."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# frob:ticket T-2248
_REPO_ROOT = Path(__file__).resolve().parents[1]
# frob:ticket T-2248
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "frob-timeout-guard.py"


# frob:ticket T-2248
def _run_hook(
    command: str,
    *,
    timeout_ms: int = 0,
    run_in_background: bool | None = None,
    env: dict[str, str] | None = None,
):
    """Invoke the hook's real PreToolUse stdin/stdout contract for a Bash
    `command` with the given tool-level `timeout` (0 == unset) and optional
    `run_in_background` flag. `env`, when given, REPLACES the subprocess
    environment (T-2282: needed to control `FROB_AGENT` deterministically,
    independent of whatever the calling shell happens to have set)."""
    tool_input: dict = {"command": command}
    if timeout_ms:
        tool_input["timeout"] = timeout_ms
    if run_in_background is not None:
        tool_input["run_in_background"] = run_in_background
    payload = {"tool_input": tool_input}
    return subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


# frob:ticket T-2248
def _denial_reason(result) -> str | None:
    """The `permissionDecisionReason` string when the hook denied, else
    `None`."""
    out = result.stdout.strip()
    if not out:
        return None
    payload = json.loads(out)
    return payload.get("hookSpecificOutput", {}).get("permissionDecisionReason")


# frob:tests .claude/hooks/frob-timeout-guard.py::main kind="integration"
# frob:ticket T-2248
def test_ticket_work_under_min_timeout_is_blocked():
    """T-2248 acceptance criterion 1: `uv run frob ticket work T-XXXX` with
    no (or too-small) tool timeout is blocked -- failed before this ticket
    because the pattern lacked `work`."""
    result = _run_hook("uv run frob ticket work T-2248")
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/frob-timeout-guard.py::main kind="integration"
# frob:ticket T-2248
def test_ticket_new_under_min_timeout_is_blocked():
    """T-2248 acceptance criterion 2: `frob ticket new` with no tool timeout
    is blocked -- failed before this ticket because the pattern lacked
    `new`."""
    result = _run_hook("uv run frob ticket new --title 'x' --kind bug")
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/frob-timeout-guard.py::main kind="integration"
# frob:ticket T-2248
def test_ticket_work_with_large_timeout_is_allowed():
    """Acceptance criterion 4: a matching command with tool timeout >=
    MIN_TIMEOUT_MS is still allowed through unchanged."""
    result = _run_hook("uv run frob ticket work T-2248", timeout_ms=600000)
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-timeout-guard.py::main kind="integration"
# frob:ticket T-2248
def test_ticket_new_with_large_timeout_is_allowed():
    """Same as above, for `ticket new`."""
    result = _run_hook(
        "uv run frob ticket new --title 'x' --kind bug", timeout_ms=600000
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-timeout-guard.py::main kind="integration"
# frob:ticket T-2248
def test_ticket_land_still_blocks_under_min_timeout():
    """MUST-STILL-PASS control: one of the four originally-guarded verbs
    (`ticket land`) still blocks."""
    result = _run_hook("uv run frob ticket land T-2248")
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/frob-timeout-guard.py::main kind="integration"
# frob:ticket T-2248
def test_ticket_done_report_still_blocks_under_min_timeout():
    """MUST-STILL-PASS control: `ticket done-report` still blocks."""
    result = _run_hook("uv run frob ticket done-report T-2248")
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/frob-timeout-guard.py::main kind="integration"
# frob:ticket T-2248
def test_check_still_blocks_under_min_timeout():
    """MUST-STILL-PASS control: `frob check` still blocks."""
    result = _run_hook("uv run frob check --only gates-fast")
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/frob-timeout-guard.py::main kind="integration"
# frob:ticket T-2248
def test_test_verb_still_blocks_under_min_timeout():
    """MUST-STILL-PASS control: `frob test` still blocks."""
    result = _run_hook("uv run frob test --base main")
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/frob-timeout-guard.py::main kind="integration"
# frob:ticket T-2248
def test_fast_verb_ticket_show_is_not_blocked():
    """MUST-STILL-PASS control: a fast verb (`ticket show`) is never
    blocked, even with no tool timeout at all -- guarding it would train a
    reflexive huge timeout on every frob invocation, defeating the guard
    where it matters."""
    result = _run_hook("uv run frob ticket show T-2248")
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-timeout-guard.py::main kind="integration"
# frob:ticket T-2248
def test_fast_verb_verify_status_is_not_blocked():
    """MUST-STILL-PASS control: a fast verb (`verify status`) is never
    blocked."""
    result = _run_hook("uv run frob verify status")
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-timeout-guard.py::main kind="integration"
# frob:ticket T-2248
def test_prose_heredoc_mentioning_guarded_verb_is_not_blocked():
    """MUST-STILL-PASS control: the first recorded false positive -- a
    heredoc mentioning a guarded verb in prose, not at command position --
    must not fire."""
    command = (
        "cat <<'EOF'\n"
        "Remember: uv run frob ticket work T-XXXX needs a big timeout.\n"
        "EOF\n"
    )
    result = _run_hook(command)
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-timeout-guard.py::main kind="integration"
# frob:ticket T-2248
def test_quoted_string_command_is_not_blocked():
    """MUST-STILL-PASS control: the second recorded false positive -- a
    command carrying a guarded verb inside a quoted string -- must not
    fire."""
    command = 'echo "uv run frob test --base main"'
    result = _run_hook(command)
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-timeout-guard.py::main kind="integration"
# frob:ticket T-2282
def test_explicit_run_in_background_blocked_for_agent_regardless_of_command():
    """T-2282 acceptance 3: `run_in_background=true` is refused in agent
    context (`FROB_AGENT` set) even for a command with NO name matching
    any enumerated pattern -- the exact shape (`python3
    scripts/fleet_status.py`) that bypassed the T-2248 verb-list guard."""
    env = {**os.environ, "FROB_AGENT": "1"}
    result = _run_hook(
        "python3 scripts/fleet_status.py", run_in_background=True, env=env
    )
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/frob-timeout-guard.py::main kind="integration"
# frob:ticket T-2282
def test_explicit_run_in_background_allowed_for_coordinator():
    """MUST-STILL-PASS: with `FROB_AGENT` unset (coordinator's own shell),
    an explicit `run_in_background=true` is NOT blocked -- the coordinator
    can still background a long measurement."""
    env = {k: v for k, v in os.environ.items() if k != "FROB_AGENT"}
    result = _run_hook(
        "python3 scripts/fleet_status.py", run_in_background=True, env=env
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-timeout-guard.py::main kind="integration"
# frob:ticket T-2282
def test_run_in_background_false_not_blocked_for_agent():
    """MUST-STILL-PASS: `run_in_background=false` (the ordinary,
    non-backgrounded call) is unaffected by the new check even in agent
    context."""
    env = {**os.environ, "FROB_AGENT": "1"}
    result = _run_hook(
        "python3 scripts/fleet_status.py", run_in_background=False, env=env
    )
    assert result.stdout.strip() == ""
