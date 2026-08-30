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
import re
import shlex
import subprocess
import sys

# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
_GUARDED_TOOLS = frozenset({"Write", "Edit", "NotebookEdit", "Bash"})

# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
_LEDGER_ALLOW = re.compile(r"^(tickets\.md|tickets/.*)$")

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
#: T-2481: known MUTATING `frob ticket` subcommands -- deliberately excludes
#: read-only ones (`list`, `show`, `doable`, `wave`, `contention`, `board`,
#: `epic`, `brief`, `flow`, `merge-driver`, `runs-last`) so a query command
#: is never mistaken for a write. Sourced from `frob ticket --help`'s own
#: subcommand list; kept as a plain set here rather than importing frob's
#: argparse tree, since this hook is a standalone script run via `python3`
#: with no guarantee `frob` is even installed in the invoking shell.
_MUTATING_TICKET_VERBS = frozenset(
    {
        "new",
        "plan",
        "requeue",
        "start",
        "work",
        "sweep",
        "reconcile",
        "migrate",
        "renumber",
        "promote",
        "land",
        "attach",
        "block",
        "close",
        "fail",
        "evidence",
        "drop",
        "archive",
        "reverify",
        "sweep-async",
        "done-report",
        "scope",
        "scope-ack",
        "anchor",
        "priority",
        "kind",
        "component",
        "label",
        "accept",
        "review",
        "sprint",
        "tier",
        "body",
        "debt",
        "deprecated",
    }
)

# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
#: T-2481: matches `frob ticket <mutating-verb>` (optionally `uv run frob`/
#: `python -m frob` prefixed) anywhere in a command string.
_TICKET_VERB_RE = re.compile(
    r"\bfrob\s+ticket\s+("
    + "|".join(re.escape(v) for v in _MUTATING_TICKET_VERBS)
    + r")\b"
)

# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
#: T-2481: a leading `cd <dir>` segment (chained with `&&`/`;`), captured so
#: an effective cwd can be computed without a real shell parser.
_LEADING_CD_RE = re.compile(r"^\s*cd\s+(\"[^\"]+\"|'[^']+'|\S+)\s*(?:&&|;)")

# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-3421
#: T-3421: heredoc BODY text is data the shell never executes -- blanked
#: to a space before tokenizing so an unquoted `>`/`>>` inside a heredoc
#: body (e.g. a Python heredoc printing example shell syntax) can never
#: be mistaken for a real redirect operator token. Mirrors the identical
#: heredoc alternative in `_shellscan._QUOTED`, applied here because this
#: module's own tokenizer (unlike `_shellscan.strip_quoted`) must keep
#: quote characters' CONTENT intact, not blank it -- see `_shell_tokens`.
_HEREDOC_BODY_RE = re.compile(r"<<-?\s*'?(\w+)'?.*?^\1\b", re.S | re.M)

#: T-3421: real filesystem-write redirect operators, as TOKENS (never raw
#: text) -- the next token is the candidate write target.
_WRITE_REDIRECT_OPS = frozenset({">", ">>", "&>", "&>>"})
#: T-3421: file-descriptor-duplication operators (`cmd 2>&1`, `cmd >&2`) --
#: NEVER a filesystem write; shlex separates the leading fd digit (if any)
#: from this operator, so this check does not need to see it.
_FD_DUP_REDIRECT_OPS = frozenset({">&"})

#: T-3421: a simple `NAME=value` assignment token, so a later `$NAME`/
#: `${NAME}` redirect target can be resolved against it -- the "redirect
#: whose target comes from a variable" must-fire fixture. One level only,
#: no recursive/command-substitution expansion attempted.
_VAR_ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.S)
_VAR_REF_RE = re.compile(r"^\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?$")


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-3421
def _shell_tokens(command: str) -> list[str] | None:
    """`command` split into shell tokens via `shlex` (POSIX quoting rules,
    `punctuation_chars=True` so `>`/`>>`/`&>`/`;`/`|`/`&`/`(`/`)` are their
    own tokens whenever the shell would treat them as operators) -- the
    actual fix this ticket is about. A character sequence that LOOKS like
    a redirect but sits inside a quoted string or a heredoc body is,
    after `shlex`, just part of an ordinary word token, never a separate
    operator token -- so the walk below only ever sees redirects the
    shell itself would parse as redirects. Heredoc bodies are blanked
    first (`_HEREDOC_BODY_RE`): `shlex` has no concept of heredoc syntax,
    so without this a body's own unquoted `>` would still misparse as a
    real operator. Returns `None` on anything `shlex` cannot tokenize at
    all (unbalanced quotes) -- ambiguous, so callers must allow rather
    than guess, same posture as `_unambiguous_target`."""
    without_heredocs = _HEREDOC_BODY_RE.sub(" ", command)
    lexer = shlex.shlex(without_heredocs, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return None


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-3421
def _simple_var_assignments(tokens: list[str]) -> dict[str, str]:
    """Every `NAME=value`-shaped token in `tokens`, as a `{NAME: value}`
    map -- the last assignment to a given name wins, matching shell
    semantics for straight-line (non-branching) assignment sequences."""
    assignments: dict[str, str] = {}
    for token in tokens:
        match = _VAR_ASSIGN_RE.match(token)
        if match:
            assignments[match.group(1)] = match.group(2)
    return assignments


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-3421
def _resolve_var_ref(raw_target: str, assignments: dict[str, str]) -> str:
    """`raw_target` unchanged, UNLESS it is exactly a `$NAME`/`${NAME}`
    reference to a name `assignments` actually captured earlier in the
    SAME command -- then the assigned value, substituted once. A `$NAME`
    with no matching assignment (an inherited/ambient env var) is left
    as-is, so it still falls through to `_unambiguous_target`'s existing
    `$`-is-ambiguous-so-allow rule -- this only ever ADDS detection for a
    same-command traced value, never removes the existing fail-safe."""
    match = _VAR_REF_RE.match(raw_target)
    if not match:
        return raw_target
    return assignments.get(match.group(1), raw_target)


#: T-3421: tokens that start a new pipeline segment -- used to find
#: `tee`/`sed -i`'s COMMAND-POSITION token, mirroring `_shellscan.POS`'s
#: connector set (this module cannot import that hook-local module
#: across the two hooks' separate materialized copies, so the equivalent
#: connector set is declared locally here instead).
_SEGMENT_CONNECTORS = frozenset({";", "&&", "||", "&", "|", "(", ")"})


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-3421
def _segments(tokens: list[str]) -> list[list[str]]:
    """`tokens` split into pipeline segments at `_SEGMENT_CONNECTORS`
    tokens (the connectors themselves dropped) -- each segment is one
    simple command's own token run, the unit `tee`/`sed -i` detection
    below reasons about."""
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token in _SEGMENT_CONNECTORS:
            segments.append([])
        else:
            segments[-1].append(token)
    return [seg for seg in segments if seg]


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-3421
def _redirect_targets(tokens: list[str]) -> list[str]:
    """Every candidate write-target TOKEN in `tokens`: the argument right
    after a `>`/`>>`/`&>`/`&>>` operator token (never after a `>&` fd-dup
    operator, and never when the following token itself starts with `&`
    -- a fd-duplication target, not a path), plus `tee`'s non-flag
    argument(s) and `sed -i`'s last non-flag argument, each found in
    COMMAND POSITION within one pipeline segment (`_segments`). Scans
    EVERY occurrence, not just the first -- a command with two redirects
    must not let an early, harmless one hide a later one that targets the
    checkout."""
    targets: list[str] = []
    for i, token in enumerate(tokens):
        if token in _FD_DUP_REDIRECT_OPS:
            continue
        if token in _WRITE_REDIRECT_OPS and i + 1 < len(tokens):
            candidate = tokens[i + 1]
            if not candidate.startswith("&"):
                targets.append(candidate)
    for segment in _segments(tokens):
        if not segment:
            continue
        head = segment[0]
        if head == "tee":
            for arg in segment[1:]:
                if not arg.startswith("-"):
                    targets.append(arg)
        elif head == "sed" and any(
            flag == "-i" or flag.startswith("-i") for flag in segment[1:]
        ):
            non_flags = [arg for arg in segment[1:] if not arg.startswith("-")]
            if non_flags:
                targets.append(non_flags[-1])
    return targets

# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
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
    run from `cwd` -- the first entry is always the primary checkout.
    Returns `[]` only when `git` itself could not be run (missing binary,
    non-repo cwd, timeout) -- a real repo always reports at least its own
    primary checkout, so an empty result is unambiguously "could not
    measure", never "no worktrees exist", and callers fail open on it."""
    out = _git(["worktree", "list", "--porcelain"], cwd)
    if not out:
        return []
    paths = []
    for line in out.splitlines():
        if line.startswith("worktree "):
            paths.append(line[len("worktree ") :].strip())
    return paths


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2895
#: T-2895: relative to the primary checkout root, the on-disk coordinator
#: marker `_coordinator_marker_set` checks for. This hook process is
#: spawned fresh per PreToolUse call by the harness (`.claude/settings.
#: json`), so it never inherits an `export FROB_COORDINATOR=1` a Bash tool
#: call makes for its OWN subprocess -- there is no process relationship
#: through which that env var could ever reach here, which is why the
#: env-only check below could never actually work as the advertised
#: escape hatch. A file under `.frob/` is this repo's existing pattern
#: for state that must survive across separately-spawned processes (see
#: every other `.frob/*.lock`/`*-pending` marker `frob ticket land` itself
#: reads and writes), so the coordinator marker now uses the same
#: mechanism: `mkdir -p .frob && touch .frob/coordinator-mode` from the
#: primary checkout turns it on; `rm .frob/coordinator-mode` turns it
#: off. `.frob/` is already gitignored repo-local state (never tracked),
#: exactly the right lifetime for a marker meant to persist for "this
#: clone, right now" without leaking into git history.
_COORDINATOR_MARKER_REL = os.path.join(".frob", "coordinator-mode")


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2850
# frob:ticket T-2895
def _coordinator_marker_set(primary_root: str) -> bool:
    """True when `FROB_COORDINATOR=1` (or any truthy value) is set, OR
    `<primary_root>/.frob/coordinator-mode` exists on disk -- T-2850's
    opt-in positive marker for a human/coordinator shell that legitimately
    writes to the primary checkout directly. T-2895 added the file check:
    the env var alone can never reach THIS process in real usage (see
    `_COORDINATOR_MARKER_REL`'s docstring), so the file is now the
    mechanism that actually works end-to-end; the env var check is kept
    for direct invocations (tests, a wrapper that execs this hook as a
    true child) where inheritance genuinely does hold. Nothing in the
    dispatch or `frob ticket work` pipeline ever sets either, unlike
    `FROB_AGENT`/`FROB_WORKTREE`, so presence of either cannot be an
    accidental false negative the way the pre-T-2850 discriminator's
    absence could."""
    # frob:waive SEC110 reason="FROB_COORDINATOR is a dispatch-context marker \
    # (T-2850), carries no sensitive value -- same posture as FROB_AGENT/ \
    # FROB_WORKTREE/FROB_LAND_INTERNAL's own precedent waivers in this file"
    if os.environ.get("FROB_COORDINATOR"):
        return True
    return os.path.exists(os.path.join(primary_root, _COORDINATOR_MARKER_REL))


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
def _strip_quotes(raw: str) -> str:
    """Strip one layer of matching `'...'`/`"..."` quoting from `raw` -- the
    candidate-path captures above may include the quotes verbatim."""
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        return raw[1:-1]
    return raw


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
def _leading_cd_target(command: str) -> str | None:
    """The directory a command's leading `cd <dir> &&`/`cd <dir>;` segment
    names, or `None` if the command has no such prefix -- the "cd into a
    worktree in the same call" shape this hook must still allow."""
    match = _LEADING_CD_RE.match(command)
    if not match:
        return None
    return _strip_quotes(match.group(1))


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
def _resolve_relative(raw: str, base: str) -> str:
    """Join `raw` onto `base` when it is relative, else return `raw`
    unchanged -- the one path-join rule every resolver below shares.
    `raw` is `~`-expanded first (T-2895): `os.path.isabs("~/x")` is
    `False`, so a home-relative path was previously joined onto `base`
    instead of expanded, making an outside-the-repo target falsely
    resolve under the primary checkout whenever `base` was the repo
    root -- the root cause of the cwd-keyed false refusal T-2895 fixes."""
    expanded = os.path.expanduser(raw)
    return expanded if os.path.isabs(expanded) else os.path.join(base, expanded)


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
def _under_any(path: str, roots: list[str]) -> bool:
    """True when `path` equals or sits under any directory in `roots`."""
    return any(path == root or path.startswith(root + os.sep) for root in roots)


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
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
# frob:ticket T-2860
#: T-2860: matches a `--worktree <path>` / `--worktree=<path>` flag anywhere
#: in a command string, capturing the (possibly quoted) path in group 1.
_WORKTREE_FLAG_RE = re.compile(r"--worktree(?:=|\s+)(\"[^\"]+\"|'[^']+'|[^\s;&|><]+)")


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2860
def _land_worktree_flag_target(command: str) -> str | None:
    """The `--worktree` flag's argument value in `command` with one layer
    of quoting stripped, or `None` when the flag is absent."""
    match = _WORKTREE_FLAG_RE.search(command)
    if not match:
        return None
    return _strip_quotes(match.group(1))


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2860
def _is_legitimate_land(
    command: str, effective_cwd: str, worktree_reals: list[str]
) -> bool:
    """True when `command` is a `frob ticket land` invocation whose
    `--worktree` flag resolves to a REAL, currently-registered linked
    worktree (per `worktree_reals`, sourced from `git worktree list
    --porcelain` the same way every other worktree fact in this hook is) --
    T-2860's fix for the fleet's core operation (`frob ticket land <id>
    --worktree <wt>`, run from the root by design so it can merge and clean
    up the worktree) being indistinguishable, pre-fix, from an arbitrary
    root-mutating `frob ticket` call. Reuses `_worktree_paths`'s existing
    structural fact-check rather than trusting the flag's text alone: a
    `--worktree` naming a nonexistent or unregistered directory does NOT
    qualify, so this cannot be satisfied by an attacker-controlled or
    just-wrong path string. Ambiguous flag values (`$`, backtick, glob --
    `_unambiguous_target`) are rejected, same posture as every other target
    resolution in this file: when in doubt about the fact, do not grant the
    exemption."""
    match = _TICKET_VERB_RE.search(command)
    if not match or match.group(1) != "land":
        return False
    raw = _land_worktree_flag_target(command)
    if raw is None:
        return False
    target = _unambiguous_target(raw)
    if target is None:
        return False
    resolved = os.path.realpath(_resolve_relative(target, effective_cwd))
    return _under_any(resolved, worktree_reals)


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
def _bash_ticket_verb_targets_root(
    command: str, effective_cwd: str, primary_real: str, worktree_reals: list[str]
) -> bool:
    """Shape 1: a `frob ticket <mutating-verb>` with no `--path` in the
    command, whose effective cwd resolves under the primary checkout --
    UNLESS it is a legitimate `land` naming a real registered worktree
    (`_is_legitimate_land`, T-2860), or any OTHER mutating verb (T-2895):
    every verb in `_MUTATING_TICKET_VERBS` except `land` only ever writes
    the ledger (`tickets.md`/`tickets/**`) through the `frob ticket` CLI's
    own machinery -- the same class of write `_is_ledger_path` already
    exempts on the `Write`/`Edit` tool path -- so refusing them here made
    the module docstring's and `REASON`'s "tickets.md/tickets/** are
    exempt" claim false for the one invocation shape (`Bash`, not
    `Write`/`Edit`) most `frob ticket` verbs are actually run through.
    `land` alone keeps the narrow structural check (`_is_legitimate_land`)
    because it is the one verb in this set that legitimately writes
    non-ledger content in the root by design (the merge itself)."""
    if "--path" in command:
        return False
    match = _TICKET_VERB_RE.search(command)
    if not match:
        return False
    if match.group(1) != "land":
        return False
    if _is_legitimate_land(command, effective_cwd, worktree_reals):
        return False
    effective_real = os.path.realpath(effective_cwd)
    return _under_any(effective_real, [primary_real])


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
# frob:ticket T-3421
def _bash_redirect_targets_root(
    command: str, effective_cwd: str, primary_real: str, worktree_reals: list[str]
) -> bool:
    """Shape 2: a `>`/`>>`/`&>`/`&>>`/`tee`/`sed -i` whose target resolves
    under the primary checkout. T-3421: tokenized (`_shell_tokens`), not
    matched against raw text -- a redirect-looking character sequence
    inside a quoted string or a heredoc body is never a token the walk in
    `_redirect_targets` can see, so it can no longer trip this shape the
    way the pre-fix regex scan did. `command` failing to tokenize at all
    (`_shell_tokens` returns `None`, e.g. unbalanced quoting) is
    ambiguous -- allow, never guess. Checks EVERY candidate target, not
    just the first, so an early harmless redirect can never mask a later
    one that targets the checkout."""
    tokens = _shell_tokens(command)
    if tokens is None:
        return False
    assignments = _simple_var_assignments(tokens)
    for raw_target in _redirect_targets(tokens):
        resolved_target = _resolve_var_ref(raw_target, assignments)
        if _resolves_under_primary(
            resolved_target, effective_cwd, primary_real, worktree_reals
        ):
            return True
    return False


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2481
def _bash_targets_root(
    command: str, payload_cwd: str, primary_real: str, worktree_reals: list[str]
) -> bool:
    """True only when `command` matches one of the two narrow, high-
    frequency shapes T-2481 measured (`_bash_ticket_verb_targets_root` or
    `_bash_redirect_targets_root`) -- every other command, including
    anything this hook cannot confidently parse, returns `False` (allow).
    This is the "when in doubt, allow" rule from this module's docstring,
    applied as code -- unaffected by T-2850's default inversion, which only
    changes what happens once a target IS confidently identified."""
    effective_cwd = _effective_cwd(command, payload_cwd)
    if effective_cwd is None:
        return False
    effective_real = os.path.realpath(effective_cwd)
    if _under_any(effective_real, worktree_reals):
        # The command already cd'd into a leased (or any real linked)
        # worktree -- allow, this is the must-still-allow shape.
        return False
    return _bash_ticket_verb_targets_root(
        command, effective_cwd, primary_real, worktree_reals
    ) or _bash_redirect_targets_root(
        command, effective_cwd, primary_real, worktree_reals
    )


# frob:doc docs/guides/claude-hooks.md#root-write-guardpy
# frob:ticket T-2850
def _root_write_worktree_paths(cwd: str) -> list[str] | None:
    """`_worktree_paths(cwd)`, or `None` when the coordinator marker is set
    or the lookup itself could not be measured (fail open) -- the one "is
    this even worth evaluating" guard both `_handle_bash` and
    `_handle_file_write` share, factored out so neither mixes it with its
    own I/O/decision body (`ARCH103`). Replaces the pre-T-2850
    `_agent_worktree_paths` (which gated on `_is_agent_context` instead of
    the coordinator marker) -- the default this hook applies is now DENY,
    so what used to gate "should I even look" now only gates the two
    explicit escapes (marker set, or nothing to measure). T-2895: the
    marker check now runs AFTER the worktree-paths lookup, since the file
    half of `_coordinator_marker_set` needs `paths[0]` (the primary
    checkout root) to know where to look; when the lookup itself fails
    (empty `paths`), this already returns `None` (fail open) regardless
    of the marker, so the reordering changes no observable behavior for
    that case."""
    paths = _worktree_paths(cwd)
    if not paths:
        return None
    if _coordinator_marker_set(paths[0]):
        return None
    return paths


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
