""".claude/hooks/root-write-guard.py: PreToolUse Write/Edit/NotebookEdit hook
that refuses a dispatched agent's file write into the SHARED ROOT (the
primary git checkout) at edit time, before the tree is dirtied.

CANONICAL COPY. This file is git-tracked and is the source of truth; the
`~/.claude/hooks/` copy is written by `sync-claude-config.py` and must never
be hand-edited (it will be overwritten). Edit here, sync outward.

T-2396: the pre-existing `_WORKTREE_LEASE_HOOK_SCRIPT` git hook
(`src/frob/scaffold/project.py`) guards COMMIT time -- by then the shared
root is already dirty and every concurrent `frob ticket land` is already
refusing (DirtyMain). Measured twice in one drive: two agents in one wave
edited the shared root instead of their leased worktree, and a third
agent's land was blocked as a result. This hook closes the gap by firing
on the WRITE itself (`Write`/`Edit`/`NotebookEdit` tool calls), the
earliest point Claude Code's own hook surface can see.

DISCRIMINATOR (must fire for an agent, never for the coordinator or a
human -- both directions matter, T-2396 acceptance 1/2). `FROB_AGENT`
alone is not enough: the T-2071 comment in `_WORKTREE_LEASE_HOOK_SCRIPT`
measured it UNSET in real Agent-tool shells. This hook pairs it with a
FACT-based signal instead of trusting either alone: `FROB_WORKTREE`
(the sibling var the same `frob agent env <worktree-path>` call always
exports alongside `FROB_AGENT`, playbook section 1b) must additionally
resolve to a REAL, currently-registered linked worktree directory per
`git worktree list --porcelain` -- not just a set string, which could be
stale or spoofed. `_worktree_fact` performs that structural check.
`_is_agent_context` fires when EITHER `FROB_AGENT` is truthy OR the
worktree fact independently holds, so a shell missing one of the two
(the exact measured gap) is still caught by the other. A coordinator or
human shell carries neither var -- `frob agent env` is only ever invoked
for a dispatched worktree agent's own shell -- so neither disjunct fires
and the guard stays silent, closing acceptance criterion 2.

SCOPE OF THE REFUSAL. Only a write whose TARGET resolves (via `git
worktree list --porcelain`'s own `worktree ` line) to the PRIMARY
checkout is refused -- a write inside the agent's own leased worktree
(the normal, correct case) is never touched. `tickets.md` and
`tickets/**` are exempted (`_is_ledger_path`): the `frob ticket` CLI's
own ledger auto-commit machinery legitimately writes there from a
worktree context during merge/land bookkeeping, matching the same
carve-out `_WORKTREE_LEASE_HOOK_SCRIPT`'s T-2071 check already uses.
`FROB_LAND_INTERNAL=1` (land's own internal escape hatch, never set by a
worktree agent's own shell) exempts everything, matching every other
land-owned-file guard in this repo (playbook section 4b).

FAILS OPEN, NEVER BLOCKS THE HARNESS ITSELF. Any stdin parse error,
missing `git`, or a `cwd` outside a git repo all degrade to silent
allow (exit 0, no output) -- a hook that can itself crash a turn is
worse than one that misses a refusal, the same posture every other hook
in this directory takes.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
_GUARDED_TOOLS = frozenset({"Write", "Edit", "NotebookEdit"})

# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
_LEDGER_ALLOW = re.compile(r"^(tickets\.md|tickets/.*)$")

# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
REASON = (
    "frob: refusing WRITE to the shared root (T-2396) -- this shell is a "
    "dispatched agent context (FROB_AGENT/FROB_WORKTREE). "
    "Use `frob ticket work <id>` and edit inside your leased worktree "
    "instead; the shared root is coordinator/human territory only. "
    "(tickets.md/tickets/** are exempt; FROB_LAND_INTERNAL=1 covers "
    "land's own internal machinery.)"
)


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
def _git(args: list[str], cwd: str) -> str | None:
    """Run `git <args>` from `cwd`, returning stdout or `None` on any
    failure (missing binary, non-repo cwd, timeout) -- never raises."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
def _worktree_paths(cwd: str) -> list[str]:
    """Every `worktree ` line's path from `git worktree list --porcelain`,
    run from `cwd` -- the first entry is always the primary checkout."""
    out = _git(["worktree", "list", "--porcelain"], cwd)
    if not out:
        return []
    paths = []
    for line in out.splitlines():
        if line.startswith("worktree "):
            paths.append(line[len("worktree ") :].strip())
    return paths


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
def _worktree_fact(cwd: str) -> bool:
    """True when `FROB_WORKTREE` names a directory that ACTUALLY appears as
    a registered linked worktree in `git worktree list` -- the fact-based
    half of the discriminator (T-2071's lesson: an env var alone can be
    unset in a real agent shell, or in principle stale/spoofed)."""
    worktree_env = os.environ.get("FROB_WORKTREE")
    if not worktree_env:
        return False
    target = os.path.realpath(worktree_env)
    paths = _worktree_paths(cwd)
    if len(paths) < 2:
        # Only the primary checkout is registered -- no fleet, no lease.
        return False
    return any(os.path.realpath(p) == target for p in paths[1:])


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
def _is_agent_context(cwd: str) -> bool:
    """The paired discriminator: `FROB_AGENT` truthy OR the independent
    `_worktree_fact` check -- either disjunct alone covers the case where
    the other is unset, per this module's docstring."""
    if os.environ.get("FROB_AGENT"):
        return True
    return _worktree_fact(cwd)


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
def _is_ledger_path(rel: str) -> bool:
    """True for `tickets.md`/`tickets/**` -- the ledger paths the `frob
    ticket` CLI legitimately writes from a worktree context, exempted the
    same way `_WORKTREE_LEASE_HOOK_SCRIPT`'s T-2071 check exempts them."""
    return bool(_LEDGER_ALLOW.match(rel))


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
def _target_path(tool_name: str, tool_input: dict) -> str:
    """Resolve the file path a `Write`/`Edit`/`NotebookEdit` call targets --
    the first two use `file_path`, `NotebookEdit` uses `notebook_path`."""
    if tool_name == "NotebookEdit":
        return tool_input.get("notebook_path") or ""
    return tool_input.get("file_path") or ""


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
def _deny() -> None:
    """Emit the PreToolUse deny payload -- same shape every other hook in
    this directory uses."""
    # frob:waive RENDER001 reason="standalone Claude Code hook script, no frob import; \
    # stdout IS the hook's JSON-decision contract"
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": REASON,
                }
            }
        )
    )


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:tests tests/test_hook_root_write_guard.py kind="integration"
def main() -> None:
    """Entry point: JSON payload on stdin, a `permissionDecision: deny`
    object on stdout when an agent-context write targets the shared root,
    nothing otherwise. Any parse/lookup failure degrades to silent allow."""
    try:
        payload = json.load(sys.stdin)
    except (OSError, ValueError):
        return
    if not isinstance(payload, dict):
        return
    tool_name = payload.get("tool_name") or ""
    if tool_name not in _GUARDED_TOOLS:
        return
    if os.environ.get("FROB_LAND_INTERNAL"):
        return
    tool_input = payload.get("tool_input") or {}
    file_path = _target_path(tool_name, tool_input)
    if not file_path:
        return
    cwd = payload.get("cwd") or os.getcwd()
    if not _is_agent_context(cwd):
        return
    paths = _worktree_paths(cwd)
    if not paths:
        return
    primary_real = os.path.realpath(paths[0])
    target_real = os.path.realpath(
        file_path if os.path.isabs(file_path) else os.path.join(cwd, file_path)
    )
    try:
        rel = os.path.relpath(target_real, primary_real)
    except ValueError:
        return
    if rel.startswith(".."):
        # Target is not under the primary checkout at all (e.g. genuinely
        # inside the agent's own leased worktree) -- never refuse this.
        return
    rel = rel.replace(os.sep, "/")
    if _is_ledger_path(rel):
        return
    _deny()


if __name__ == "__main__":
    main()
