""".claude/hooks/root-write-guard.py: PreToolUse Write/Edit/NotebookEdit/Bash
hook that refuses ANY write into the SHARED ROOT (the primary git checkout)
at edit time, before the tree is dirtied, UNLESS an explicit positive
marker or a small, measured exemption list applies.

T-2850: DEFAULT INVERTED. Two dispatched agents, in one session, edited the
PRIMARY CHECKOUT directly (307 and 278 insertions respectively) and this
hook fired for neither, each time blocking every other agent's land until
a human noticed and hand-walked recovery. In both incidents
`.claude/worktrees/*<ticket>*` did not exist yet -- the agent had never
run `frob ticket work`, which is the ONLY thing that ever sets `FROB_AGENT`
or `FROB_WORKTREE` (`frob agent env`, invoked as part of `frob ticket
work`). The hook's PRE-T-2850 discriminator, `_is_agent_context`, fired on
EITHER of those two vars -- and an agent between dispatch and `ticket work`
carries NEITHER, making it environmentally identical to the coordinator's
own shell. No env-var pairing can separate those two cases, because they
are not actually different environments. That was not a bug in the
discriminator's logic; it was the CONTRACT being wrong: "never fire for
the coordinator or a human" cannot coexist with "always fire for an agent"
once the dangerous window is a state with no agent-only signal in it at
all.

The fix is not a better discriminator -- it is a different default. This
hook now refuses every write into the primary checkout UNLESS one of a
short, explicit allowlist holds:

  1. `FROB_LAND_INTERNAL=1` -- land's own internal machinery (unchanged
     from before T-2850).
  2. The write target is `tickets.md` / `tickets/**` -- the `frob ticket`
     CLI's own ledger auto-commit machinery (unchanged from before
     T-2850).
  3. The write target resolves inside a REAL, currently-registered linked
     worktree (`git worktree list --porcelain`) -- an agent's own leased
     worktree is never touched, regardless of which shell is writing to
     it (unchanged from before T-2850, but no longer conditioned on a
     FROB_AGENT/FROB_WORKTREE match -- any writer inside a real worktree
     is fine, because a write INSIDE a worktree was never the danger; a
     write into the ROOT was).
  4. `FROB_COORDINATOR=1` is set -- the new, explicit, opt-in positive
     marker this ticket adds. Set this once in a human/coordinator shell's
     own environment (e.g. shell rc) to keep writing to the primary
     checkout freely. There is no way to synthesize this marker
     accidentally: unlike `FROB_AGENT`/`FROB_WORKTREE`, nothing in the
     dispatch or `frob ticket work` pipeline ever sets it, so its absence
     cannot regress into a false negative the way the old pairing did.
  5. T-2860: a `frob ticket land <id> --worktree <path>` invocation whose
     `--worktree` value resolves to a REAL, currently-registered linked
     worktree (`_is_legitimate_land`) -- landing IS a root write by design
     (it merges a worktree's branch into the primary checkout and can
     remove the worktree), and as originally shipped this hook made T-2850's
     own `land` a member of `_MUTATING_TICKET_VERBS` refuse it exactly like
     any other unmarked root write, leaving no way to land without setting
     `FROB_COORDINATOR=1` -- a global bypass that reopens exemption 4's
     hazard for every other command in the same shell for as long as it
     stays set. This exemption is scoped to `land` alone and re-validates
     the SAME structural fact exemption 3 already trusts (a real entry in
     `git worktree list --porcelain`), so a `--worktree` naming a directory
     that is not an actual registered worktree gets no exemption at all.

The asymmetry driving this (from the ticket, restated here since it is the
whole design rationale): a false BLOCK costs one confused turn and a clear
error message naming the exact recovery. A false ALLOW costs the ENTIRE
FLEET its ability to land until a human notices -- twice, in one session,
multi-hour each. Given that no signal exists that reliably tells a
pre-worktree agent apart from a human, the only sound default is to
refuse both, and let the ONE actor who legitimately needs to write to the
root (the coordinator) opt in explicitly.

`REASON` (the refusal text) carries the exact recovery recipe measured to
work twice in the incidents that motivated this ticket, plus the
`FROB_COORDINATOR=1` escape hatch for a genuine false positive -- this
still honors the module's other standing rule (see below) that "a guard
that blocks legitimate commands gets disabled by whoever it obstructs":
the fix for that risk is a precise, actionable message, never a return to
default-allow.

A Bash command's write target is not a declared field the way `Write`'s
`file_path` is -- it must be inferred from the command TEXT, and
inference is exactly the lexical guessing this repo forbids elsewhere
(see `.claude/hooks/_shellscan.py`'s own docstring for the same tension).
So `_bash_targets_root` is deliberately narrow: it detects only the two
high-frequency shapes actually observed (a `frob ticket <mutating-verb>`
invocation with neither a `cd` into a registered worktree in the same
command nor an explicit `--path`; a `>`/`>>`/`tee`/`sed -i` whose target
resolves under the primary checkout) and returns "no target" (allow) for
anything else, INCLUDING a command it cannot confidently parse. This
narrowness is UNCHANGED by T-2850 -- the default that flipped is what
happens once a target IS identified as hitting the root, not how
aggressively targets are identified in the first place. When in doubt
about WHAT a command targets, still allow; once a target is confidently
identified as the primary checkout, now deny by default rather than
allow by default.

CANONICAL COPY. This file is git-tracked and is the source of truth; the
`~/.claude/hooks/` copy is written by `sync-claude-config.py` and must
never be hand-edited (it will be overwritten). Edit here, sync outward.
The SAME is true of its sibling `_root_write_guard_lib.py`.

ENTRY POINT / HELPER SPLIT (T-3626, LARGE001): this file now holds only
the entry surface -- `main`, its two per-tool-family branches
(`_handle_bash`/`_handle_file_write`), and `_deny` -- plus the constants
tightly coupled to that surface (`_GUARDED_TOOLS`, `REASON`). Every pure
target-resolution/shell-tokenization/worktree-fact helper those branches
call lives in `_root_write_guard_lib.py`, imported the same
`sys.path.insert` + bare-module-name way `frob-suggest.py`/
`root-cleanliness-detector.py` already import their own hook-local helper
modules (`_shellscan`/`_agent_context`). The entry CONTRACT -- stdin JSON
in, a `permissionDecision: deny` payload on stdout when (and only when) a
write targets the shared root with no exemption, silent allow otherwise --
is byte-for-byte unchanged by this split.

FAILS OPEN, NEVER BLOCKS THE HARNESS ITSELF. Any stdin parse error,
missing `git`, or a `cwd` outside a git repo all degrade to silent
allow (exit 0, no output) -- a hook that can itself crash a turn is
worse than one that misses a refusal, the same posture every other hook
in this directory takes. This is unchanged by T-2850: the inversion only
changes what happens once the hook CAN measure the write's target and
context; it never changes what happens when it cannot measure at all.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _root_write_guard_lib import (  # noqa: E402
    _bash_targets_root,
    _file_write_targets_root,
    _root_write_worktree_paths,
    _target_path,
)

# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
_GUARDED_TOOLS = frozenset({"Write", "Edit", "NotebookEdit", "Bash"})

# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2850
#: The recovery recipe measured to work twice on the incidents that
#: motivated T-2850 -- `git diff` out of the root, apply into the
#: worktree, THEN restore the root from the index. Deliberately the BARE
#: `git checkout -- <path>` form, never `git checkout <branch> -- <path>`:
#: the latter copies the whole file and can silently revert fixes landed
#: since divergence (playbook, "checkout branch -- file silently
#: reverts").
REASON = (
    "frob: refusing WRITE to the shared root (T-2850) -- writes to the "
    "primary checkout are default-DENIED now, not just for detected "
    "agent shells, because no environment signal reliably tells a "
    "pre-worktree agent apart from a human. Run `frob ticket work <id>` "
    "and edit inside your leased worktree instead. "
    "(tickets.md/tickets/** are exempt, including every `frob ticket` "
    "verb except `land` run directly from the root; FROB_LAND_INTERNAL=1 "
    "covers land's own internal machinery; a genuine coordinator/human "
    "shell that needs to write here directly runs "
    "`mkdir -p .frob && touch .frob/coordinator-mode` once -- a PLAIN "
    "FROB_COORDINATOR=1 shell export does NOT work here, because this "
    "hook is a separately-spawned process that never inherits it; "
    "`rm .frob/coordinator-mode` turns the marker back off.) "
    "If this refusal came AFTER a write already landed content in the "
    "root, recover it into your worktree rather than losing it: "
    "  git diff HEAD -- <paths> > /tmp/rescue.patch   # verify non-empty\n"
    "  cd <worktree> && git apply --3way /tmp/rescue.patch\n"
    "  # verify content present, THEN:\n"
    "  cd <root> && git checkout -- <paths>   # bare form -- restores from "
    "the index, never `git checkout <branch> -- <path>` (that form can "
    "silently revert fixes landed since divergence)."
)


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
def _handle_bash(command: str, cwd: str) -> None:
    """`main`'s `Bash`-tool branch, split out to keep `main` under the
    length/complexity thresholds `ARCH001`/`ARCH103` enforce: refuses via
    `_deny()` when `_bash_targets_root` finds one of the two narrow shapes
    this hook detects, does nothing otherwise (including a negative
    `_root_write_worktree_paths`)."""
    paths = _root_write_worktree_paths(cwd)
    if paths is None:
        return
    primary_real = os.path.realpath(paths[0])
    worktree_reals = [os.path.realpath(p) for p in paths[1:]]
    if _bash_targets_root(command, cwd, primary_real, worktree_reals):
        _deny()


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
def _deny() -> None:
    """Emit the PreToolUse deny payload -- same shape every other hook in
    this directory uses."""
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
# frob:ticket T-2481
def _handle_file_write(file_path: str, cwd: str) -> None:
    """`main`'s `Write`/`Edit`/`NotebookEdit` branch, split out to keep
    `main` under the length/complexity thresholds `ARCH001`/`ARCH103`
    enforce: refuses via `_deny()` only when `_file_write_targets_root`
    holds (and `_root_write_worktree_paths` found something to evaluate at
    all)."""
    paths = _root_write_worktree_paths(cwd)
    if paths is not None and _file_write_targets_root(file_path, cwd, paths):
        _deny()


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:tests tests/test_hook_root_write_guard.py kind="integration"
def main() -> None:
    """Entry point: JSON payload on stdin, a `permissionDecision: deny`
    object on stdout when a write targets the shared root and no exemption
    applies, nothing otherwise. Any parse/lookup failure degrades to
    silent allow."""
    try:
        payload = json.load(sys.stdin)
    except (OSError, ValueError):
        return
    if not isinstance(payload, dict):
        return
    tool_name = payload.get("tool_name") or ""
    if tool_name not in _GUARDED_TOOLS:
        return
    # frob:waive SEC110 reason="FROB_LAND_INTERNAL is a dispatch-context marker, \
    # carries no sensitive value -- same posture as the FROB_COORDINATOR waiver above"
    if os.environ.get("FROB_LAND_INTERNAL"):
        return
    tool_input = payload.get("tool_input") or {}
    cwd = payload.get("cwd") or os.getcwd()

    if tool_name == "Bash":
        command = tool_input.get("command") or ""
        if command:
            _handle_bash(command, cwd)
        return

    file_path = _target_path(tool_name, tool_input)
    if file_path:
        _handle_file_write(file_path, cwd)


if __name__ == "__main__":
    main()
