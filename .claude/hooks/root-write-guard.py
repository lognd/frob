""".claude/hooks/root-write-guard.py: PreToolUse Write/Edit/NotebookEdit/Bash
hook that refuses a dispatched agent's file write into the SHARED ROOT (the
primary git checkout) at edit time, before the tree is dirtied.

T-2481: THREE separate incidents in one session dirtied the shared root
through `Bash` -- a `frob ticket done-report` with no `cd <worktree> &&` in
the same call, direct edits in the root, and a `python3` heredoc missing
its `cd` prefix -- and none of them tripped this hook, because `Bash` was
never a guarded tool. The root cause generalises: the harness resets `cwd`
between Bash calls, so a sequence that `cd`s once and issues follow-up
commands assuming that directory silently operates on the root instead.

A Bash command's write target is not a declared field the way `Write`'s
`file_path` is -- it must be inferred from the command TEXT, and inference
is exactly the lexical guessing this repo forbids elsewhere (see
`.claude/hooks/_shellscan.py`'s own docstring for the same tension). So
`_bash_targets_root` is deliberately narrow: it detects only the two
high-frequency shapes actually observed (a `frob ticket <mutating-verb>`
invocation with neither a `cd` into a registered worktree in the same
command nor an explicit `--path`; a `>`/`>>`/`tee`/`sed -i` whose target
resolves under the primary checkout) and returns "no target" (allow) for
anything else, INCLUDING a command it cannot confidently parse. When in
doubt, allow -- a guard that blocks legitimate commands gets disabled by
whoever it obstructs, and a disabled guard protects nothing.

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
# frob:ticket T-2481
_GUARDED_TOOLS = frozenset({"Write", "Edit", "NotebookEdit", "Bash"})

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
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
#: T-2481: known MUTATING `frob ticket` subcommands -- deliberately excludes
#: read-only ones (`list`, `show`, `doable`, `wave`, `contention`, `board`,
#: `epic`, `brief`, `flow`, `merge-driver`, `runs-last`) so a query command
#: is never mistaken for a write. Sourced from `frob ticket --help`'s own
#: subcommand list; kept as a plain set here rather than importing frob's
#: argparse tree, since this hook is a standalone script run via `python3`
#: with no guarantee `frob` is even installed in the invoking shell.
_MUTATING_TICKET_VERBS = frozenset(
    {
        "new", "plan", "requeue", "start", "work", "sweep", "reconcile",
        "migrate", "renumber", "promote", "land", "attach", "block",
        "close", "fail", "evidence", "drop", "archive", "reverify",
        "sweep-async", "done-report", "scope", "scope-ack", "anchor",
        "priority", "kind", "component", "label", "accept", "review",
        "sprint", "tier", "body", "debt", "deprecated",
    }
)

# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
#: T-2481: matches `frob ticket <mutating-verb>` (optionally `uv run frob`/
#: `python -m frob` prefixed) anywhere in a command string.
_TICKET_VERB_RE = re.compile(
    r"\bfrob\s+ticket\s+("
    + "|".join(re.escape(v) for v in _MUTATING_TICKET_VERBS)
    + r")\b"
)

# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
#: T-2481: a leading `cd <dir>` segment (chained with `&&`/`;`), captured so
#: an effective cwd can be computed without a real shell parser.
_LEADING_CD_RE = re.compile(r"^\s*cd\s+(\"[^\"]+\"|'[^']+'|\S+)\s*(?:&&|;)")

# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
#: T-2481: redirect/in-place-edit targets this hook is willing to infer --
#: deliberately narrow (see module docstring). Each pattern captures ONE
#: candidate target path in group 1.
_REDIRECT_TARGET_RES = (
    re.compile(r">>?\s*(\"[^\"]+\"|'[^']+'|[^\s;&|><]+)"),
    re.compile(r"\btee\b(?:\s+-a)?\s+(\"[^\"]+\"|'[^']+'|[^\s;&|><]+)"),
    re.compile(r"\bsed\s+-i\S*\s+.*?\s(\"[^\"]+\"|'[^']+'|[^\s;&|><]+)\s*$"),
)

# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
#: T-2481: any of these appearing in a candidate path (or in the whole
#: command, for the `frob ticket` case) makes static resolution unreliable
#: -- treat as ambiguous and ALLOW rather than guess (acceptance 4).
_AMBIGUOUS_PATH_CHARS = re.compile(r"[*?$`]")


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
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
def _strip_quotes(raw: str) -> str:
    """Strip one layer of matching `'...'`/`"..."` quoting from `raw` -- the
    candidate-path captures above may include the quotes verbatim."""
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        return raw[1:-1]
    return raw


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
def _leading_cd_target(command: str) -> str | None:
    """The directory a command's leading `cd <dir> &&`/`cd <dir>;` segment
    names, or `None` if the command has no such prefix -- the "cd into a
    worktree in the same call" shape acceptance criterion 2 requires this
    hook to still allow."""
    match = _LEADING_CD_RE.match(command)
    if not match:
        return None
    return _strip_quotes(match.group(1))


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
def _resolve_relative(raw: str, base: str) -> str:
    """Join `raw` onto `base` when it is relative, else return `raw`
    unchanged -- the one path-join rule every resolver below shares."""
    return raw if os.path.isabs(raw) else os.path.join(base, raw)


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
def _under_any(path: str, roots: list[str]) -> bool:
    """True when `path` equals or sits under any directory in `roots`."""
    return any(path == root or path.startswith(root + os.sep) for root in roots)


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
def _unambiguous_target(raw_target: str) -> str | None:
    """`raw_target` with one layer of quoting stripped, or `None` when it
    contains a `$`/backtick/glob character this hook declines to resolve
    (acceptance 4: ambiguous -> allow, never guess)."""
    target = _strip_quotes(raw_target)
    if _AMBIGUOUS_PATH_CHARS.search(target):
        return None
    return target


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
def _effective_cwd(command: str, payload_cwd: str) -> str | None:
    """The directory a Bash command's write actually lands in: the leading
    `cd <dir>` target if the command starts with one, else `payload_cwd`
    unchanged. Returns `None` (ambiguous) when a leading `cd` target is not
    a resolvable target per `_unambiguous_target`."""
    cd_target = _leading_cd_target(command)
    if cd_target is None:
        return payload_cwd
    target = _unambiguous_target(cd_target)
    if target is None:
        return None
    return _resolve_relative(target, payload_cwd)


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
def _resolves_under_primary(
    raw_target: str, effective_cwd: str, primary_real: str, worktree_reals: list[str]
) -> bool:
    """True when `raw_target` (a candidate write path, possibly relative)
    resolves under `primary_real` and NOT under any of `worktree_reals` --
    the shared conservative resolution both Bash detectors below use.
    Returns `False` (never refuse) on anything `_unambiguous_target`
    declines to resolve."""
    target = _unambiguous_target(raw_target)
    if target is None:
        return False
    resolved = os.path.realpath(_resolve_relative(target, effective_cwd))
    if _under_any(resolved, worktree_reals):
        return False
    return _under_any(resolved, [primary_real])


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
def _bash_ticket_verb_targets_root(
    command: str, effective_cwd: str, primary_real: str
) -> bool:
    """Shape 1: a `frob ticket <mutating-verb>` with no `--path` in the
    command, whose effective cwd resolves under the primary checkout."""
    if "--path" in command:
        return False
    if not _TICKET_VERB_RE.search(command):
        return False
    effective_real = os.path.realpath(effective_cwd)
    return _under_any(effective_real, [primary_real])


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
def _bash_redirect_targets_root(
    command: str, effective_cwd: str, primary_real: str, worktree_reals: list[str]
) -> bool:
    """Shape 2: a `>`/`>>`/`tee`/`sed -i` whose FIRST matched target
    resolves under the primary checkout (`_resolves_under_primary`)."""
    for pattern in _REDIRECT_TARGET_RES:
        match = pattern.search(command)
        if match and _resolves_under_primary(
            match.group(1), effective_cwd, primary_real, worktree_reals
        ):
            return True
    return False


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
def _bash_targets_root(
    command: str, payload_cwd: str, primary_real: str, worktree_reals: list[str]
) -> bool:
    """True only when `command` matches one of the two narrow, high-
    frequency shapes T-2481 measured (`_bash_ticket_verb_targets_root` or
    `_bash_redirect_targets_root`) -- every other command, including
    anything this hook cannot confidently parse, returns `False` (allow).
    This is the "when in doubt, allow" rule from this module's docstring,
    applied as code."""
    effective_cwd = _effective_cwd(command, payload_cwd)
    if effective_cwd is None:
        return False
    effective_real = os.path.realpath(effective_cwd)
    if _under_any(effective_real, worktree_reals):
        # The command already cd'd into a leased worktree -- allow, this is
        # acceptance criterion 2's must-still-allow shape.
        return False
    return _bash_ticket_verb_targets_root(
        command, effective_cwd, primary_real
    ) or _bash_redirect_targets_root(
        command, effective_cwd, primary_real, worktree_reals
    )


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
def _agent_worktree_paths(cwd: str) -> list[str] | None:
    """`_worktree_paths(cwd)` gated behind `_is_agent_context`, or `None`
    when either check comes back negative -- the one "is this even worth
    evaluating" guard both `_handle_bash` and `_handle_file_write` share,
    factored out so neither mixes it with its own I/O/decision body
    (`ARCH103`)."""
    if not _is_agent_context(cwd):
        return None
    paths = _worktree_paths(cwd)
    return paths or None


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
def _handle_bash(command: str, cwd: str) -> None:
    """`main`'s `Bash`-tool branch, split out to keep `main` under the
    length/complexity thresholds `ARCH001`/`ARCH103` enforce: refuses via
    `_deny()` when `_bash_targets_root` finds one of the two narrow shapes
    this hook detects, does nothing otherwise (including a negative
    `_agent_worktree_paths`)."""
    paths = _agent_worktree_paths(cwd)
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
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
def _file_write_targets_root(file_path: str, cwd: str, paths: list[str]) -> bool:
    """The pure decision half of `_handle_file_write`: `True` when
    `file_path` (resolved against `cwd`) lands under the primary checkout
    (`paths[0]`), is NOT inside any registered linked worktree (T-2412 --
    checked via `paths`, not path-shape inference), and is not a ledger
    path."""
    target_real = os.path.realpath(_resolve_relative(file_path, cwd))
    primary_real = os.path.realpath(paths[0])
    worktree_reals = [os.path.realpath(p) for p in paths[1:]]
    if _under_any(target_real, worktree_reals):
        return False
    try:
        rel = os.path.relpath(target_real, primary_real)
    except ValueError:
        return False
    if rel.startswith(".."):
        # Target is not under the primary checkout at all (a worktree sited
        # outside it) -- never refuse this.
        return False
    return not _is_ledger_path(rel.replace(os.sep, "/"))


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:waive COV005 reason="T-2481: brand-new private helper, not a helper extracted \
# from a public def -- see src/frob/gates/_coverage_sites.py's own COV005 waiver \
# precedent for the same false-positive shape"
def _handle_file_write(file_path: str, cwd: str) -> None:
    """`main`'s `Write`/`Edit`/`NotebookEdit` branch, split out to keep
    `main` under the length/complexity thresholds `ARCH001`/`ARCH103`
    enforce -- the original T-2396 logic, unchanged: refuses via `_deny()`
    only when `_file_write_targets_root` holds (and `_agent_worktree_paths`
    found something to evaluate at all)."""
    paths = _agent_worktree_paths(cwd)
    if paths is not None and _file_write_targets_root(file_path, cwd, paths):
        _deny()


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
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
