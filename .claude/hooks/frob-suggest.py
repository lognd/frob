"""PreToolUse Bash hook: nudge toward the frob equivalent of a raw command.

CANONICAL COPY. This file is git-tracked and is the source of truth; the
`~/.claude/hooks/` copy is written by `sync-claude-config.py` and must never
be hand-edited (it will be overwritten). Edit here, sync outward.

frob is the enforcement layer -- an obligation graph, a git-tracked ticket
queue, and gates that make unaccounted-for work a build failure. A raw
command that bypasses it (`make`, hand-editing the ledger, an unscoped
`pytest`) silently opts out of that accounting. The failure is never loud;
it just means the graph no longer describes reality.

BLOCK ONCE, THEN GET OUT OF THE WAY. The first attempt at a matching command
is denied with a concrete suggestion. Re-running the IDENTICAL command is
allowed, because the caller may have a reason the hook cannot see -- a
suggestion that cannot be overridden is a policy, and this is deliberately
not one.

The marker is created with O_EXCL, so exactly one denial is emitted even
when this script is registered in BOTH project and user settings (both
instances run for the same tool call; whichever creates the marker denies,
the other allows, and a deny wins). A single registration behaves
identically -- the design does not depend on how many copies fire.

Anchoring follows frob-timeout-guard.py's hard-won lesson: match only at
COMMAND POSITION (line start, after a shell connector, or after `uv run`)
so a verb mentioned inside a heredoc, an echo string, or a commit message
never false-positives. That exact false positive has already cost this repo
once.

GLOBAL frob IS NOT LOCAL frob. The globally-installed `frob` on PATH and the
repo's own `uv run frob` are different builds and routinely differ. Rather
than banning bare `frob` outright -- which is wrong whenever the two agree,
and trains the reader to bypass the hook -- this MEASURES the skew and only
objects when the versions actually differ, naming both versions and the
exact reconcile command. See `_frob_version_skew`.

No-ops entirely outside a frob repo (no frob.toml), so it is safe to
register globally.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

#: Markers older than this are pruned, so a command nudged long ago is
#: nudged again rather than silently grandfathered forever.
_MARKER_TTL_S = 12 * 3600

#: Version skew changes only on an install/upgrade, so a long TTL is safe
#: and keeps the two `--version` spawns off the hot path of every Bash call.
_VERSION_TTL_S = 30 * 60

_STATE_DIR = Path.home() / ".claude" / "hooks" / "state" / "frob-suggest"

#: Command position: line start, after a shell connector, or after `uv run`
#: (optionally `timeout N`-wrapped).
#:
#: `(` is deliberately NOT a connector here. It matched prose parentheticals
#: -- "(make targets, ...)" inside a commit message blocked a commit on the
#: very first real use of this hook. A subshell is rare; an English sentence
#: in a quoted string is constant.
_POS = r"(?:^|[;&|]\s*|\buv +run +)(?:timeout +\d+ +)?"

#: Bare `frob` at command position, NOT already routed through `uv run`.
_BARE_FROB = re.compile(r"(?:^|[;&|]\s*)(?:timeout +\d+ +)?frob +", re.M)

#: Quoted spans and heredoc bodies, stripped before matching. Everything a
#: command SAYS is prose; only what it RUNS is a command. Without this, any
#: commit message, echo, or heredoc that names a tool trips its own rule --
#: the exact failure `frob-timeout-guard.py` records having paid for once.
_QUOTED = re.compile(
    r"'[^']*'"                      # single-quoted span
    r"|\"(?:[^\"\\]|\\.)*\""       # double-quoted span (backslash-aware)
    r"|<<-?\s*'?(\w+)'?.*?^\1\b",   # heredoc body, incl. quoted delimiter
    re.S | re.M,
)


def _strip_quoted(command: str) -> str:
    """`command` with quoted spans and heredoc bodies blanked out.

    Matching is done on the REMAINDER, so a rule fires only on what the
    shell would actually execute, never on text the command merely
    carries."""
    return _QUOTED.sub(" ", command)

#: (name, compiled pattern, suggestion). Deliberately narrow: a nudge that
#: fires on routine correct work trains the reader to bypass it, which costs
#: more than the nudge ever saved.
_RULES: list[tuple[str, re.Pattern[str], str]] = [
    (
        "make-target",
        re.compile(_POS + r"make +[a-z]", re.M),
        "Prefer the `uv run frob ...` subcommand over a make target. Workflows "
        "belong in frob subcommands, not GNU-make recipes (cross-platform "
        "directive) -- make is not available everywhere this has to run.",
    ),
    (
        "hand-edit-ledger",
        re.compile(
            r"(?:>>?\s*|sed +-i[^|;&]*|tee +[^|;&]*)[\w./-]*tickets\.md", re.M
        ),
        "Never hand-edit tickets.md. Use the `uv run frob ticket ...` CLI. A "
        "hand-written ledger edit has already broken the tickets.md YAML once "
        "and took every gate down with it.",
    ),
    (
        "unscoped-pytest",
        re.compile(_POS + r"pytest(?!.*(?:tests?/|\.py|::))", re.M),
        "Prefer `uv run frob test` over a bare `pytest`: it runs the TOUCHED "
        "SET rather than the whole suite. If you genuinely need specific "
        "tests, pass their path or node id.",
    ),
    (
        "raw-linters",
        re.compile(_POS + r"(?:ruff|mypy|ty) +(?:check|format)", re.M),
        "Prefer `uv run frob check` over invoking ruff/mypy/ty directly -- it "
        "runs the whole gate family and reports findings in one accountable "
        "place. A single linter passing is not the repo being clean.",
    ),
    (
        "raw-worktree",
        re.compile(_POS + r"git +worktree +add", re.M),
        "Use the EnterWorktree tool (or `uv run frob worktree`) rather than "
        "`git worktree add` -- frob tracks worktree leases, and a worktree it "
        "does not know about will not be swept and can strand a ticket lease.",
    ),
    (
        "raw-coverage",
        re.compile(_POS + r"(?:coverage +run|pytest .*--cov)", re.M),
        "Use `uv run frob coverage` -- it owns the coverage stamp and the "
        "delta baseline. A hand-run coverage pass leaves the recorded "
        "artifact stale, and everything downstream reads it as current.",
    ),
]


def _repo_root(cwd: str) -> Path | None:
    """Nearest ancestor of `cwd` containing `frob.toml`, or `None`.

    Walks up rather than checking `cwd` alone: agents routinely run from a
    subdirectory or a worktree, and a nudge that silently stops applying two
    directories down is worse than no nudge, because its absence reads as
    approval."""
    here = Path(cwd).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "frob.toml").exists():
            return candidate
    return None


def _version_of(argv: list[str], cwd: Path) -> str | None:
    """`argv --version` output, or `None` if it cannot be determined.

    `None` is explicitly NOT a version string and never compares equal to
    one -- "could not measure" must never render as "they agree"."""
    try:
        proc = subprocess.run(  # noqa: S603
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return (proc.stdout or proc.stderr).strip() or None


def _frob_version_skew(root: Path) -> tuple[str, str] | None:
    """`(global_version, local_version)` when the PATH `frob` disagrees with
    the repo's `uv run frob`, else `None` (they agree, or the comparison is
    unavailable).

    Returning `None` when either side cannot be measured is deliberate: an
    unmeasurable comparison is not evidence of skew, and blocking on it
    would make an unrelated environment problem look like a version
    problem. The result is cached for `_VERSION_TTL_S` so the two spawns
    stay off the hot path -- skew only changes on an install or upgrade."""
    key = hashlib.sha256(str(root).encode()).hexdigest()[:16]
    cache = _STATE_DIR / f"version-{key}.json"
    now = time.time()
    try:
        if cache.exists() and now - cache.stat().st_mtime < _VERSION_TTL_S:
            cached = json.loads(cache.read_text(encoding="utf-8"))
            pair = cached.get("skew")
            return (pair[0], pair[1]) if pair else None
    except (OSError, ValueError, TypeError, IndexError):
        pass

    global_v = _version_of(["frob", "--version"], root)
    local_v = _version_of(["uv", "run", "frob", "--version"], root)
    skew = None
    if global_v is not None and local_v is not None and global_v != local_v:
        skew = (global_v, local_v)
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"skew": list(skew) if skew else None}))
    except OSError:
        pass
    return skew


def _prune(now: float) -> None:
    """Drop markers past `_MARKER_TTL_S`. Best-effort: a prune failure must
    never turn into a failure to answer the hook."""
    try:
        for marker in _STATE_DIR.glob("*.marker"):
            if now - marker.stat().st_mtime > _MARKER_TTL_S:
                marker.unlink(missing_ok=True)
    except OSError:
        pass


def _claim(command: str) -> bool:
    """Atomically claim the right to deny `command`.

    `True` means this invocation created the marker and OWNS the single
    denial for this exact command. `False` means it was already nudged (an
    earlier attempt, or the sibling registration racing this one for the
    same tool call) and must be allowed through.

    O_CREAT|O_EXCL is the whole mechanism: the one filesystem primitive that
    makes "exactly one of us wins" true without a lock."""
    digest = hashlib.sha256(command.encode("utf-8", "replace")).hexdigest()[:32]
    marker = _STATE_DIR / f"{digest}.marker"
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False
    except OSError:
        # Cannot record state -> cannot promise the re-run will succeed.
        # Allow: a nudge that can trap the caller in a loop it cannot escape
        # is strictly worse than a missed nudge.
        return False
    try:
        os.write(fd, command.encode("utf-8", "replace")[:4096])
    finally:
        os.close(fd)
    return True


def _match(raw: str, root: Path) -> tuple[str, str] | None:
    """The first rule `raw` trips, as `(name, suggestion)` -- evaluated
    against the command with quoted/heredoc text removed."""
    command = _strip_quoted(raw)
    if _BARE_FROB.search(command):
        skew = _frob_version_skew(root)
        if skew is not None:
            global_v, local_v = skew
            return (
                "frob-version-skew",
                f"The `frob` on PATH is {global_v!r} but this repo's own "
                f"`uv run frob` is {local_v!r}. They are DIFFERENT BUILDS, so "
                "the bare command reports different gate numbers than the "
                "working tree -- acting on its output means acting on the "
                "wrong measurement. Use `uv run frob ...` here, or reconcile "
                "the installs with `uv tool upgrade frob`.",
            )
    for name, pattern, suggestion in _RULES:
        if pattern.search(command):
            return name, suggestion
    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 -- a malformed payload must never block
        return
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command.strip():
        return
    root = _repo_root(payload.get("cwd") or os.getcwd())
    if root is None:
        return

    hit = _match(command, root)
    if hit is None:
        return
    name, suggestion = hit

    _prune(time.time())
    if not _claim(command):
        return  # already nudged for this exact command -- let it through

    reason = (
        f"BLOCKED ONCE by frob-suggest [{name}] -- this looks like work frob "
        f"should account for.\n\n{suggestion}\n\n"
        "If you are SURE the raw command is right, re-run it EXACTLY as "
        "written and it will be allowed; this hook blocks only the first "
        "attempt at a given command. Do not paraphrase to get around the "
        "block -- a reworded command is a new command and blocks again."
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


if __name__ == "__main__":
    main()
