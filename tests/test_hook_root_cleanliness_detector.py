""".claude/hooks/root-cleanliness-detector.py: PostToolUse Bash hook that
reports (never blocks) when the shared root is dirty right after a Bash
call in agent context (T-2487).

Subprocess-only, matching `tests/test_hook_root_write_guard.py`'s own
pattern -- the hook is a standalone script outside the `frob` package, so
it is exercised through its real stdin/stdout contract, never imported
directly.

Every fixture builds a REAL throwaway git repo with a REAL nested linked
worktree (`primary/.claude/worktrees/agent-wt`, this repo's actual
deployment topology per T-2412/T-2442) AND a `.gitignore` excluding
`.claude/worktrees/` -- matching this repo's own tracked `.gitignore`
(`.gitignore:33`). Without that ignore entry, the worktree's own
administrative directory shows up as untracked dirt in the primary
checkout's `git status --porcelain`, which is a TEST FIXTURE artifact,
not a real-world false positive (confirmed empirically against the real
frob repo checkout during development: a clean root produces zero output
here). Omitting the `.gitignore` from the fixture would have shipped a
green suite that never actually exercised the "clean root -> silent"
case."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# frob:ticket T-2487
_REPO_ROOT = Path(__file__).resolve().parents[1]
# frob:ticket T-2487
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "root-cleanliness-detector.py"


# frob:ticket T-2487
def _git(args: list[str], cwd: Path) -> None:
    """Run a `git` command in `cwd`, raising on any non-zero exit -- test
    fixture plumbing only, not the hook's own logic."""
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


# frob:ticket T-2487
def _make_repo_with_nested_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """Build a real throwaway git repo at `tmp_path/primary`, with
    `.gitignore` excluding `.claude/worktrees/` (matching this repo's own
    tracked `.gitignore`), and one real linked worktree NESTED inside it
    at `primary/.claude/worktrees/agent-wt` -- this repo's actual
    deployment topology."""
    primary = tmp_path / "primary"
    primary.mkdir()
    _git(["init"], primary)
    _git(["config", "user.email", "t@example.com"], primary)
    _git(["config", "user.name", "T"], primary)
    (primary / ".gitignore").write_text(".claude/worktrees/\n", encoding="utf-8")
    (primary / "README.md").write_text("x\n", encoding="utf-8")
    _git(["add", "README.md", ".gitignore"], primary)
    _git(["commit", "-m", "init"], primary)
    worktree = primary / ".claude" / "worktrees" / "agent-wt"
    worktree.parent.mkdir(parents=True)
    _git(["worktree", "add", "-b", "agent-branch", str(worktree)], primary)
    return primary, worktree


# frob:waive DUP001 reason="T-2487: same precedent as test_hook_root_write_guard.py's \
# own _run_hook/_denial_reason -- each standalone-hook test file exercises a DIFFERENT \
# hook's real stdin/stdout subprocess contract independently; extracting a shared \
# helper would couple two independently-evolving hook test files for a few lines of \
# subprocess plumbing, not a real behavioral duplication worth centralizing"
# frob:ticket T-2487
def _run_hook(*, cwd: Path, env: dict[str, str], tool_name: str = "Bash"):
    """Invoke the hook's real PostToolUse stdin/stdout contract for a
    `tool_name` call from `cwd`, under `env` (REPLACES the subprocess
    environment so `FROB_AGENT`/`FROB_WORKTREE`/`FROB_LAND_INTERNAL` are
    controlled deterministically)."""
    payload = {
        "tool_name": tool_name,
        "tool_input": {"command": "echo hi"},
        "cwd": str(cwd),
    }
    return subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
        env=env,
    )


# frob:ticket T-2487
def _system_message(result) -> str | None:
    """The `systemMessage` string when the hook reported, else `None`."""
    out = result.stdout.strip()
    if not out:
        return None
    payload = json.loads(out)
    return payload.get("systemMessage")


# frob:tests .claude/hooks/root-cleanliness-detector.py::main kind="integration"
# frob:ticket T-2487
def test_clean_root_in_agent_context_is_silent(tmp_path):
    """Must-still-allow control: a clean primary checkout, agent context,
    right after a Bash call -- no report at all."""
    primary, worktree = _make_repo_with_nested_worktree(tmp_path)
    env = {"FROB_AGENT": "1", "FROB_WORKTREE": str(worktree)}
    result = _run_hook(cwd=primary, env=env)
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-cleanliness-detector.py::main kind="integration"
# frob:ticket T-2487
def test_dirty_root_in_agent_context_is_reported(tmp_path):
    """Must-fire positive control: a dirtied primary checkout (one
    modified tracked file, one untracked file), agent context, right
    after a Bash call -- reports BOTH paths with their exact recovery
    commands."""
    primary, worktree = _make_repo_with_nested_worktree(tmp_path)
    (primary / "README.md").write_text("x\nmore\n", encoding="utf-8")
    (primary / "stray.txt").write_text("dirty\n", encoding="utf-8")
    env = {"FROB_AGENT": "1", "FROB_WORKTREE": str(worktree)}
    result = _run_hook(cwd=primary, env=env)
    message = _system_message(result)
    assert message is not None
    assert 'README.md -> git checkout -- "README.md"' in message
    assert 'stray.txt -> git clean -fd -- "stray.txt"' in message


# frob:tests .claude/hooks/root-cleanliness-detector.py::main kind="integration"
# frob:ticket T-2487
def test_dirty_root_from_human_or_coordinator_shell_is_silent(tmp_path):
    """Must-still-allow-human control (other direction, symmetric to
    T-2396/T-2481): the identical dirt, with no FROB_AGENT/FROB_WORKTREE
    at all -- the discriminator must stay silent for a coordinator/human
    shell."""
    primary, _worktree = _make_repo_with_nested_worktree(tmp_path)
    (primary / "stray.txt").write_text("dirty\n", encoding="utf-8")
    result = _run_hook(cwd=primary, env={})
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-cleanliness-detector.py::main kind="integration"
# frob:ticket T-2487
def test_dirty_root_reported_even_when_cwd_is_the_worktree(tmp_path):
    """The check targets the PRIMARY checkout specifically (via `git
    worktree list`'s own first entry), not whatever `cwd` the Bash call
    happened to run from -- dirt in the primary is reported even when this
    particular call's cwd was the agent's own (clean) worktree."""
    primary, worktree = _make_repo_with_nested_worktree(tmp_path)
    (primary / "stray.txt").write_text("dirty\n", encoding="utf-8")
    env = {"FROB_AGENT": "1", "FROB_WORKTREE": str(worktree)}
    result = _run_hook(cwd=worktree, env=env)
    assert _system_message(result) is not None


# frob:tests .claude/hooks/root-cleanliness-detector.py::main kind="integration"
# frob:ticket T-2487
def test_frob_land_internal_exempts_dirty_root(tmp_path):
    """`FROB_LAND_INTERNAL=1` (land's own internal escape hatch) exempts
    everything, matching `root-write-guard.py`'s own precedent (playbook
    section 4b)."""
    primary, worktree = _make_repo_with_nested_worktree(tmp_path)
    (primary / "stray.txt").write_text("dirty\n", encoding="utf-8")
    env = {
        "FROB_AGENT": "1",
        "FROB_WORKTREE": str(worktree),
        "FROB_LAND_INTERNAL": "1",
    }
    result = _run_hook(cwd=primary, env=env)
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-cleanliness-detector.py::main kind="integration"
# frob:ticket T-2487
def test_non_bash_tool_is_ignored(tmp_path):
    """A tool name outside `_GUARDED_TOOLS` (e.g. `Read`) is never
    evaluated at all, even against a dirty root in agent context -- this
    hook only ever fires after a Bash call."""
    primary, worktree = _make_repo_with_nested_worktree(tmp_path)
    (primary / "stray.txt").write_text("dirty\n", encoding="utf-8")
    result = _run_hook(
        cwd=primary,
        env={"FROB_AGENT": "1", "FROB_WORKTREE": str(worktree)},
        tool_name="Read",
    )
    assert result.stdout.strip() == ""
