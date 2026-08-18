"""Shared git-worktree + agent-context discriminator for the PreToolUse/
PostToolUse hooks in this directory (T-2487).

CANONICAL COPY. This file is git-tracked and is the source of truth; the
`~/.claude/hooks/` copy is written by `sync-claude-config.py` and must never
be hand-edited (it will be overwritten).

T-2481's `root-write-guard.py` established this exact discriminator first
(`_is_agent_context`/`_worktree_fact`/`_worktree_paths`/`_git`) as a set of
module-private helpers. T-2487 needs the IDENTICAL logic for a second,
independent hook (`root-cleanliness-detector.py`) -- this is the second
copy CLAUDE.md's "no duplication" rule warns against, so it is extracted
here rather than pasted a second time. `root-write-guard.py` itself is
NOT migrated to import this module: it is a just-landed, security-relevant
PreToolUse guard already covered by its own test suite, and editing its
internals purely for reuse -- with no behavior change and no test of its
own to add -- is a real-but-unforced risk for a ticket whose actual job is
the new detector. This is the same "duplicate rather than risk touching a
stable, independently-tested module" trade-off this repo already accepts
for its own hook test files (see `tests/test_hook_root_write_guard.py`'s
own `frob:waive DUP001` precedent on `_run_hook`/`_denial_reason`).

DISCRIMINATOR (must fire for an agent, never for the coordinator or a
human -- both directions matter, T-2396 acceptance 1/2, verified again for
T-2487 in `tests/test_hook_root_cleanliness_detector.py`). `FROB_AGENT`
alone is not enough: the T-2071 comment in `_WORKTREE_LEASE_HOOK_SCRIPT`
measured it UNSET in real Agent-tool shells. This module pairs it with a
FACT-based signal instead of trusting either alone: `FROB_WORKTREE` (the
sibling var the same `frob agent env <worktree-path>` call always exports
alongside `FROB_AGENT`, playbook section 1b) must additionally resolve to
a REAL, currently-registered linked worktree directory per `git worktree
list --porcelain` -- not just a set string, which could be stale or
spoofed. `_worktree_fact` performs that structural check. `_is_agent_
context` fires when EITHER `FROB_AGENT` is truthy OR the worktree fact
independently holds, so a shell missing one of the two (the exact
measured gap) is still caught by the other. A coordinator or human shell
carries neither var -- `frob agent env` is only ever invoked for a
dispatched worktree agent's own shell -- so neither disjunct fires and
callers stay silent.
"""

from __future__ import annotations

import os
import subprocess


# frob:doc docs/guides/claude-hooks.md#_agent_contextpy
# frob:ticket T-2487
# frob:tests tests/test_hook_root_cleanliness_detector.py kind="integration"
# frob:waive DUP001 reason="T-2487: root-write-guard.py::_git carries the IDENTICAL \
# logic -- a deliberate, documented duplication (see this module's own docstring): \
# root-write-guard.py is a just-landed, independently-tested PreToolUse guard, and \
# migrating it to import this module for reuse alone, with no behavior change, was \
# judged not worth the risk to a stable, security-relevant hook for this ticket's \
# actual job (the new detector)"
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


# frob:doc docs/guides/claude-hooks.md#_agent_contextpy
# frob:ticket T-2487
# frob:tests tests/test_hook_root_cleanliness_detector.py kind="integration"
# frob:waive DUP001 reason="T-2487: root-write-guard.py::_worktree_paths carries the \
# IDENTICAL logic -- a deliberate, documented duplication (see this module's own \
# docstring): root-write-guard.py is a just-landed, independently-tested PreToolUse \
# guard, and migrating it to import this module for reuse alone, with no behavior \
# change, was judged not worth the risk to a stable, security-relevant hook for this \
# ticket's actual job (the new detector)"
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


# frob:doc docs/guides/claude-hooks.md#_agent_contextpy
# frob:ticket T-2487
# frob:tests tests/test_hook_root_cleanliness_detector.py kind="integration"
def _worktree_fact(cwd: str) -> bool:
    """True when `FROB_WORKTREE` names a directory that ACTUALLY appears as
    a registered linked worktree in `git worktree list` -- the fact-based
    half of the discriminator (T-2071's lesson: an env var alone can be
    unset in a real agent shell, or in principle stale/spoofed)."""
    # frob:waive SEC110 reason="FROB_WORKTREE is a dispatch-context path marker \
    # (T-0574), carries no sensitive value -- same posture as FROB_AGENT's own \
    # precedent at src/frob/tickets/_leases.py"
    worktree_env = os.environ.get("FROB_WORKTREE")
    if not worktree_env:
        return False
    target = os.path.realpath(worktree_env)
    paths = _worktree_paths(cwd)
    if len(paths) < 2:
        # Only the primary checkout is registered -- no fleet, no lease.
        return False
    return any(os.path.realpath(p) == target for p in paths[1:])


# frob:doc docs/guides/claude-hooks.md#_agent_contextpy
# frob:ticket T-2487
# frob:tests tests/test_hook_root_cleanliness_detector.py kind="integration"
def _is_agent_context(cwd: str) -> bool:
    """The paired discriminator: `FROB_AGENT` truthy OR the independent
    `_worktree_fact` check -- either disjunct alone covers the case where
    the other is unset, per this module's docstring."""
    # frob:waive SEC110 reason="FROB_AGENT is a dispatch-context marker (T-0574), \
    # carries no sensitive value -- same precedent as src/frob/tickets/_leases.py's \
    # own waiver on this exact read"
    if os.environ.get("FROB_AGENT"):
        return True
    return _worktree_fact(cwd)


__all__ = ["_git", "_is_agent_context", "_worktree_fact", "_worktree_paths"]
