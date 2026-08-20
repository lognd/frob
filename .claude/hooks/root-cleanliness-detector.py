""".claude/hooks/root-cleanliness-detector.py: PostToolUse Bash hook that
REPORTS (never blocks) when a dispatched agent's shell has left the shared
root (the primary git checkout) dirty right after a Bash call (T-2487).

CANONICAL COPY. This file is git-tracked and is the source of truth; the
`~/.claude/hooks/` copy is written by `sync-claude-config.py` and must never
be hand-edited (it will be overwritten). Edit here, sync outward.

T-2481 fixed the three MEASURED shapes of root-dirtying Bash command
(`frob ticket <verb>` with no `cd`/`--path`, and `>`/`>>`/`tee`/`sed -i`
redirects) with a PreToolUse guard that infers write targets from command
TEXT -- necessarily narrow, since a Bash command's target is not a
declared field the way `Write`'s `file_path` is, and guessing wider risks
blocking legitimate work (T-2481 acceptance 4).

THIS HOOK IS THE COMPLEMENTARY HALF, a different mechanism entirely: it
does not try to infer a write target from text at all. It runs AFTER the
Bash call finishes and asks the one question that actually matters --
"is the shared root dirty right now" -- via `git status --porcelain`,
sidestepping every shape T-2481's guard had to enumerate (a python
heredoc, a Rust/C++ build artifact, anything else no regex would catch).
A FOURTH root-dirtying incident during T-2481's own dispatch window is
the direct evidence for this: three agents that same day were caught LATE,
at land time, via a DirtyMain refusal naming files they did not
recognise; the fourth ran `git status` immediately afterward on its own
initiative, saw the dirt within a minute, and reverted with `git checkout
--` before anything was staged. Same mistake, wildly different blast
radius -- the only difference was WHEN it was noticed. This hook makes
that noticing automatic and immediate instead of relying on an agent
remembering to check.

BECAUSE IT ONLY REPORTS, IT HAS NO OVERBLOCK FAILURE MODE. A PostToolUse
hook cannot refuse a tool call that has already run (Claude Code's own
contract -- `PostToolUse` supports no `decision`/`permissionDecision`
fields at all, unlike `PreToolUse`), so there is no risk symmetric to
T-2481's "guessed wrong and blocked legitimate work": the worst this hook
can do is add a message the agent did not need. It is deliberately a
detector, not a guard.

DISCRIMINATOR: reuses `.claude/hooks/_agent_context.py`'s `_is_agent_
context` unchanged -- same FROB_AGENT/FROB_WORKTREE-fact pairing T-2396/
T-2481 already proved fires for a dispatched agent and stays silent for a
coordinator or human shell, verified again here in both directions
(`tests/test_hook_root_cleanliness_detector.py`).

WHAT COUNTS AS DIRT. `git status --porcelain` against the PRIMARY
checkout (never a linked worktree -- an agent's OWN worktree is expected
to be dirty, that is normal mid-ticket state). `.frob/` and other
gitignored paths never appear in `--porcelain` output by default, so
routine local cache/state writes are not false positives. `FROB_LAND_
INTERNAL=1` (land's own internal escape hatch) exempts everything,
matching `root-write-guard.py`'s own precedent -- a land in progress
legitimately dirties the primary checkout as part of its own commit
machinery.

THE MESSAGE IS ACTIONABLE, ON PURPOSE. It names every dirtied path (from
`--porcelain`'s own status codes) and gives the exact recovery command for
each shape: `git checkout -- <path>` for a tracked modification, `git
clean -fd -- <path>` (or `rm`) for something untracked -- so an agent can
self-correct in the same turn, not diagnose from scratch at land time.
Emitted via `systemMessage` (T-2487: PostToolUse's own documented, non-
blocking feedback channel -- confirmed against Claude Code's hooks
reference: PostToolUse supports no `decision`/`hookSpecificOutput` fields,
only the universal `systemMessage`/`continue` pair), so it reaches the
agent in-turn without any pretense of blocking anything.

FAILS OPEN, NEVER BLOCKS THE HARNESS ITSELF. Any stdin parse error,
missing `git`, or a `cwd` outside a git repo all degrade to silent exit 0
-- a hook that can itself crash a turn is worse than one that misses a
report, the same posture every other hook in this directory takes.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agent_context import _git, _is_agent_context, _worktree_paths  # noqa: E402

# frob:doc docs/guides/claude-hooks.md#root-cleanliness-detectorpy
# frob:ticket T-2487
_GUARDED_TOOLS = frozenset({"Bash"})

# frob:doc docs/guides/claude-hooks.md#root-cleanliness-detectorpy
# frob:ticket T-2487
#: `git status --porcelain` prefix -> the recovery command shape. `?? ` is
#: untracked; every other two-char status code covers a tracked path (some
#: kind of add/modify/delete/rename in the index and/or worktree) and is
#: reverted the same way. Checked longest-prefix-first is unnecessary here
#: since every code is exactly 2 chars wide per porcelain's own format.
_UNTRACKED_PREFIX = "?? "


# frob:doc docs/guides/claude-hooks.md#root-cleanliness-detectorpy
# frob:ticket T-2487
def _dirty_entries(primary: str) -> list[tuple[str, str]]:
    """`(status, path)` pairs from `git status --porcelain` run against
    `primary` -- `[]` on a clean tree or any git failure (fails open, per
    module docstring)."""
    out = _git(["status", "--porcelain"], primary)
    if not out:
        return []
    entries = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        entries.append((line[:2], line[3:]))
    return entries


# frob:doc docs/guides/claude-hooks.md#root-cleanliness-detectorpy
# frob:ticket T-2487
def _recovery_command(status: str, path: str) -> str:
    """The exact one-line recovery command for a single dirty `path`,
    keyed off its porcelain `status` code -- `git clean -fd --` for
    something untracked, `git checkout --` for anything already tracked
    (covers modified/added/deleted/renamed alike, matching `git status`'s
    own advice for a tracked change)."""
    if status == _UNTRACKED_PREFIX.rstrip():
        return f'git clean -fd -- "{path}"'
    return f'git checkout -- "{path}"'


# frob:doc docs/guides/claude-hooks.md#root-cleanliness-detectorpy
# frob:ticket T-2487
def _report(entries: list[tuple[str, str]]) -> str:
    """The `systemMessage` text for a non-empty `entries` list -- names
    every dirtied path and its exact recovery command, so the agent can
    self-correct in this same turn instead of discovering it at land
    time."""
    lines = [
        "frob: the SHARED ROOT (primary checkout) is dirty right after a "
        "Bash call in agent context (T-2487) -- this is very likely a cwd "
        "mixup: the harness resets cwd between Bash calls, so a command "
        "that assumed a prior `cd <worktree>` silently ran in the root "
        "instead. Fix now, before this compounds:",
    ]
    for status, path in entries:
        code = status.strip() or "??"
        recovery = _recovery_command(status, path)
        lines.append(f"  [{code}] {path} -> {recovery}")
    lines.append(
        "If this dirt is deliberate (rare -- coordinator/human work), "
        "ignore this message; it never blocks anything."
    )
    return "\n".join(lines)


# frob:doc docs/guides/claude-hooks.md#root-cleanliness-detectorpy
# frob:ticket T-2487
def _decision(payload: dict) -> dict | None:
    """The hook's full decision for `payload` -- `None` for "say nothing",
    else the `{"systemMessage": ...}` object to print. Split out of `main`
    so the logic is testable without a subprocess round-trip alone."""
    tool_name = payload.get("tool_name") or ""
    if tool_name not in _GUARDED_TOOLS:
        return None
    # frob:waive SEC110 reason="FROB_LAND_INTERNAL is a dispatch-context marker, \
    # carries no sensitive value -- same posture as root-write-guard.py's own waiver \
    # on this exact read"
    if os.environ.get("FROB_LAND_INTERNAL"):
        return None
    cwd = payload.get("cwd") or os.getcwd()
    if not _is_agent_context(cwd):
        return None
    paths = _worktree_paths(cwd)
    if not paths:
        return None
    primary = paths[0]
    entries = _dirty_entries(primary)
    if not entries:
        return None
    return {"systemMessage": _report(entries), "continue": True}


# frob:doc docs/guides/claude-hooks.md#root-cleanliness-detectorpy
# frob:ticket T-2487
# frob:tests tests/test_hook_root_cleanliness_detector.py kind="integration"
# frob:waive DUP001 reason="T-2487: pending-background-guard.py::main shares the same \
# stdin-JSON-read/decide/print/fail-open shape every standalone hook's main() in this \
# directory carries (root-write-guard.py, frob-suggest.py, etc. all repeat it too) -- \
# this is the hook ENTRY-POINT boilerplate every independent script needs, not a \
# shared behavior worth centralizing across files that must each keep working if any \
# other one is deleted"
def main() -> int:
    """Entry point: JSON payload on stdin, a `systemMessage` object on
    stdout when the primary checkout is dirty in agent context right after
    a Bash call, nothing otherwise. Any parse/lookup failure degrades to
    silent exit 0 -- this hook must never be the reason a turn cannot
    proceed."""
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except (OSError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0
    decision = _decision(payload)
    if decision is not None:
        print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
