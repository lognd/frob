""".claude/hooks/pgrep-self-match-guard.py: PreToolUse Bash hook that
refuses a process-table poll whose literal pattern is a substring of the
polling shell's own command line (`pgrep -f "frob check"`), so it can
never report "gone".

Subprocess-only, matching `tests/test_hook_frob_timeout_guard.py`'s
pattern: the hook is a standalone hyphenated script outside the `frob`
package, exercised through its real stdin/stdout contract. The denied
shapes below are the exact poller texts measured live on 2026-09-23
(T-5436); the allowed shapes are every non-self-matching recipe the
refusal names, plus the recorded false-positive candidates (a `-q` flag
before the literal, a variable-built pattern, `git grep` for the text)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# frob:ticket T-5436
_REPO_ROOT = Path(__file__).resolve().parents[1]
# frob:ticket T-5436
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "pgrep-self-match-guard.py"


# frob:ticket T-5436
def _decision(command: str, env: dict[str, str] | None = None) -> str:
    """`deny` or `allow` for a Bash `command` via the hook's real
    PreToolUse contract; `env` replaces the subprocess environment."""
    result = subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps({"tool_input": {"command": command}}),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return "deny" if '"deny"' in result.stdout else "allow"


# frob:ticket T-5436
@pytest.mark.parametrize(
    "command",
    [
        'until ! pgrep -f "frob ticket work T-5364" >/dev/null; do sleep 10; done',
        "while pgrep -f 'worktrees/t-5322/.venv/bin/frob check' >/dev/null; do sleep 5; done",
        'while kill -0 $(pgrep -f "t-5324/.venv/bin/frob check" | head -1); do sleep 5; done',
        'until ! ps aux | grep "frob check --only gates" >/dev/null; do sleep 5; done',
        "pgrep -f file_tickets.py",
        'pgrep -fl "frob check"',
        "ps aux | grep -v grep | grep frob",
    ],
)
def test_self_matching_polls_are_denied(command: str) -> None:
    """Every measured self-matching poller shape is refused: a literal
    pattern is always a substring of the `bash -c` shell running it."""
    assert _decision(command) == "deny"


# frob:ticket T-5436
@pytest.mark.parametrize(
    "command",
    [
        'until ! ps aux | grep -q "[f]rob check --only gates"; do sleep 5; done',
        'P="ticket lan"; P="${P}d --dra"; pgrep -f "$P"',
        'pgrep -f "$PAT" | head -1',
        "pgrep -x git",
        "if ! pgrep -x frob >/dev/null; then echo idle; fi",
        'git grep -n "pgrep -f" -- src',
        "ls; ps -ef | grep [p]ython",
        "ps -o pid= -p 123",
        'ps aux | grep -q -- "[u]v run"',
        'echo "pgrep -f is dangerous"',
        "git commit -F - <<'EOF'\nfeat: deny pgrep -f pollers\n\nps aux | grep frob\nEOF",
        "cat > f.sh <<'EOF'\nwhile pgrep -f \"x\"; do sleep 1; done\nEOF",
    ],
)
def test_non_self_matching_recipes_stay_quiet(command: str) -> None:
    """MUST-STAY-QUIET: `pgrep -x`, variable-built patterns, the bracket
    trick, text searches for the word `pgrep`, and prose inside quotes
    or heredoc bodies (commit messages, echoed text) are allowed."""
    assert _decision(command) == "allow"


# frob:ticket T-5436
def test_override_prefix_and_env_allow() -> None:
    """The single override (`FROB_SELF_MATCH_ACK=1`) works both as a
    command prefix and as an environment variable."""
    assert _decision('FROB_SELF_MATCH_ACK=1 pgrep -f "frob check"') == "allow"
    assert (
        _decision(
            'pgrep -f "frob check"',
            env={"PATH": "/usr/bin:/bin", "FROB_SELF_MATCH_ACK": "1"},
        )
        == "allow"
    )


# frob:ticket T-5436
def test_malformed_payload_is_ignored() -> None:
    """A payload the hook cannot parse never blocks the tool call."""
    result = subprocess.run(
        [sys.executable, str(_HOOK)],
        input="not json",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == ""
