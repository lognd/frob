"""PreToolUse Bash hook: nudge toward the frob equivalent of a raw command.

CANONICAL COPY. This file is git-tracked and is the source of truth; the
`~/.claude/hooks/` copy is written by `sync-claude-config.py` and must never
be hand-edited (it will be overwritten). Edit here, sync outward.

frob is the enforcement layer -- an obligation graph, a git-tracked ticket
queue, and gates that make unaccounted-for work a build failure. A raw
command that bypasses it (`make`, hand-editing the ledger, an unscoped
`pytest`) silently opts out of that accounting. The failure is never loud;
it just means the graph no longer describes reality.

BLOCK ONCE, THEN GET OUT OF THE WAY -- BUT ESCALATE ON A REPEATED HABIT
(T-2164). The first attempt at a matching command is denied with a concrete
suggestion. Re-running the IDENTICAL command a second time is allowed,
because the caller may have a reason the hook cannot see -- a suggestion
that cannot be overridden is a policy, and this is deliberately not one.
But a THIRD (or later) run of the exact same command within one marker's
TTL window is not a one-off anymore -- it is the caller repeating work the
suggested tool already had the answer to (T-2164's own measured incident:
a confident-but-wrong re-run of a raw probe cost a wasted dispatch, a false
"orphaned lease" conclusion, and a wrong "agent died" diagnosis, three
separate times in one session). From the third attempt onward this asks
for an explicit, typed acknowledgement (`FROB_SUGGEST_ACK=1 <command>`)
rather than allowing silently -- a habit gets interrupted without turning a
single legitimate raw command into a hard, unconditional block.

The marker is created with O_EXCL, so exactly one denial is emitted even
when this script is registered in BOTH project and user settings (both
instances run for the same tool call; whichever creates the marker denies,
the other allows, and a deny wins). The repeat COUNT (`_record_attempt`)
is best-effort -- two sibling registrations racing one tool call can each
OVERCOUNT by up to one (measured live, HOOK-AUDIT.md section 0b: broke the
documented re-run-and-it-passes path). See `sync-claude-config.py`'s
`dedupe_hook_registrations` (T-5124, the real registration fix)
and `_session_key` below (per-agent/session keying).

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shellscan import POS as _POS  # noqa: E402
from _shellscan import strip_and_blank_prefixed_segments as _strip_and_blank
from _shellscan import strip_quoted as _strip_quoted

#: Markers older than this are pruned, so a command nudged long ago is
#: nudged again rather than silently grandfathered forever.
_MARKER_TTL_S = 12 * 3600

#: Version skew changes only on an install/upgrade, so a long TTL is safe
#: and keeps the two `--version` spawns off the hot path of every Bash call.
_VERSION_TTL_S = 30 * 60

_STATE_DIR = Path.home() / ".claude" / "hooks" / "state" / "frob-suggest"

#: Bare `frob` at command position, NOT already routed through `uv run`.
_BARE_FROB = re.compile(r"(?:^|[;&|]\s*)(?:timeout +\d+ +)?frob +", re.M)


#: (name, compiled pattern, suggestion). Deliberately narrow: a nudge that
#: fires on routine correct work trains the reader to bypass it, which costs
#: more than the nudge ever saved.
_RULES: list[tuple[str, re.Pattern[str], str, "re.Pattern[str] | None"]] = [
    (
        "make-target",
        re.compile(_POS + r"make +[a-z]", re.M),
        "Prefer the `uv run frob ...` subcommand over a make target. Workflows "
        "belong in frob subcommands, not GNU-make recipes (cross-platform "
        "directive) -- make is not available everywhere this has to run.",
        None,
    ),
    (
        "hand-edit-ledger",
        # `(?![\w.])` after the literal is required (T-2908 audit): without
        # it the pattern matches "tickets.md" as a bare SUBSTRING, so a
        # completely unrelated file like `tickets.md.example` or
        # `tickets.md.bak` false-positives -- demonstrated directly with
        # `sed -i 's/x/y/' docs/tickets.md.example`.
        re.compile(
            r"(?:>>?\s*|sed +-i[^|;&]*|tee +[^|;&]*)[\w./-]*tickets\.md(?![\w.])",
            re.M,
        ),
        "Never hand-edit tickets.md. Use the `uv run frob ticket ...` CLI. A "
        "hand-written ledger edit has already broken the tickets.md YAML once "
        "and took every gate down with it.",
        None,
    ),
    (
        "unscoped-pytest",
        re.compile(_POS + r"pytest\b", re.M),
        "Prefer `uv run frob test` over a bare `pytest`: it runs the TOUCHED "
        "SET rather than the whole suite. If you genuinely need specific "
        "tests, pass their path or node id.",
        # A path or node id ANYWHERE in the RAW command means the caller
        # already scoped it -- the good case, not the bad one. Read raw:
        # stripping quotes would delete the very proof of scoping.
        re.compile(r"tests?/|\.py\b|::"),
    ),
    (
        "raw-linters",
        re.compile(_POS + r"(?:ruff|mypy|ty) +(?:check|format)", re.M),
        "Prefer `uv run frob check` over invoking ruff/mypy/ty directly -- it "
        "runs the whole gate family and reports findings in one accountable "
        "place. A single linter passing is not the repo being clean.",
        None,
    ),
    (
        "raw-worktree",
        re.compile(_POS + r"git +worktree +add", re.M),
        "Use `uv run frob ticket work T-XXXX` rather than `git worktree "
        "add` -- frob tracks worktree leases, and a worktree it does not "
        "know about will not be swept and can strand a ticket lease. Do "
        "NOT use the EnterWorktree tool for this: it pins the entire "
        "session cwd, hard-blocks concurrent agents, and refuses outright "
        "from a subagent (T-2908) -- exactly the audience this nudge fires "
        "for most often.",
        None,
    ),
    (
        "raw-coverage",
        re.compile(_POS + r"(?:coverage +run|pytest .*--cov)", re.M),
        "Use `uv run frob coverage` -- it owns the coverage stamp and the "
        "delta baseline. A hand-run coverage pass leaves the recorded "
        "artifact stale, and everything downstream reads it as current.",
        None,
    ),
    (
        "recursive-grep",
        re.compile(_POS + r"grep +(?:-\w*[rR]|--recursive)", re.M),
        "Prefer `uv run frob explore xref <symbol>` for a symbol (it reports "
        "the definition AND every file that uses it), or `git grep` for plain "
        "text. A raw recursive `grep` walks .venv/, .git/ and the ~20 agent "
        "worktrees under .claude/worktrees/, so its hit count is not a "
        "statement about this codebase.",
        # A trailing bare path token with a real subdirectory segment (e.g.
        # `grep -rn foo src/frob/strata`) cannot walk .venv/, .git/, or a
        # sibling worktree -- same false-positive shape as `raw-find-name`
        # (T-2908 audit), demonstrated directly: `grep -rn 'foo'
        # src/frob/strata` used to block with no usable alternative. `.`/
        # the repo root still fall through and keep firing.
        #
        # T-2932: the path token is very often followed by a REDIRECT
        # before the pipe/semicolon/EOL (`2>&1 | head -30` is the
        # overwhelmingly common shape for a scoped command whose output
        # gets filtered) -- the original lookahead required the path to
        # be IMMEDIATELY followed by `[|;&]|$`, so `2>&1` between the two
        # defeated it and a genuinely-scoped command still blocked.
        # Tolerate zero or more redirect clauses (`>`, `>>`, `<`, each
        # optionally fd-numbered and/or fd-duplicated -- `2>&1`, `1>&2`,
        # `>out.txt`, `2>/dev/null`) between the path and the final
        # separator, mirroring `handrolled-floor-count`'s own documented
        # "cannot exclude `&` -- `2>&1` is nearly always present" lesson
        # (T-2031) one rule up.
        re.compile(
            r"\s([A-Za-z0-9_][\w.-]*(?:/[A-Za-z0-9_][\w.-]*)+)\s*"
            r"(?:(?:\d*>{1,2}&?\d*|\d*>{1,2}[^\s|;&]*|\d*<[^\s|;&]*)\s*)*"
            r"(?:[|;&]|$)"
        ),
    ),
    (
        "unscoped-symbol-search",
        re.compile(_POS + r"git +grep\b", re.M),
        "For a SYMBOL, prefer `uv run frob explore xref <symbol>` -- it "
        "resolves the definition plus every referencing file through the "
        "call graph, where grep only finds lexical matches and silently "
        "misses re-exports and aliases. Also available: `frob explore "
        "outline <file>` (structural skeleton), `frob explore map` "
        "(whole-project structure), `frob explore docs-search`. If you want "
        "literal text, scope it with `-- <path>` and this nudge stays quiet.",
        # A `-- <path>` restriction means the caller already scoped the
        # search -- the good case. Same design as `unscoped-pytest` above:
        # read RAW, because stripping quotes would delete the proof.
        re.compile(r"--\s+\S"),
    ),
    (
        "raw-find-name",
        re.compile(_POS + r"find +[.\w/][^|;&]*-name\b", re.M),
        "Prefer `uv run frob explore map` for project structure, or "
        "`frob explore outline <file>` for one file's symbols. A raw `find` "
        "descends into .venv/, build artifacts and every agent worktree "
        "unless you exclude them by hand, and the omission is invisible in "
        "the output.",
        # A root that is a concrete subdirectory (has a real path segment
        # before an internal `/`, e.g. `src/frob/strata`) cannot descend
        # into .venv/, build artifacts, or a SIBLING agent worktree the way
        # this rule's stated rationale describes -- that rationale is
        # FALSE for a path-scoped find (T-2908: this rule had NO negative
        # pattern at all and blocked exactly this case). `.`/`./` and a bare
        # repo-root path still fall through and keep firing.
        re.compile(r"find +[A-Za-z0-9_][\w.-]*/[A-Za-z0-9_]"),
    ),
    (
        "handrolled-floor-count",
        # The gap class MUST be `[^|;]*`, NOT `[^|;&]*` (T-2031's own
        # near-miss, caught by running the positive case rather than
        # eyeballing the regex): excluding `&` cannot cross the `2>&1`
        # present in nearly every real `frob check` invocation, so a
        # `[^|;&]*` version matches nothing while looking correct. A guard
        # never exercised against a real input is indistinguishable from
        # one that does not exist.
        re.compile(_POS + r"frob +check\b[^|;]*\|[^|;]*\bgrep\b", re.M),
        # Two SEPARATE backtick spans, deliberately: a single span
        # containing both "frob check --json" AND a literal `|` reads to
        # WIRE003's own alternation-splitting heuristic as `frob` followed
        # by a `|`-delimited verb list, misreading the shell pipe as a
        # glob-alternation separator and flagging "python3"/"scripts" as
        # unresolved frob verbs. Splitting the pipe out of the "frob"
        # backtick span sidesteps that false positive entirely.
        "Prefer `uv run frob check --json` piped into "
        "`python3 scripts/check_summary.py` "
        "over counting findings with a grep pipeline. `frob check --json` "
        "nests severity two levels deep (results[].diagnostics[].severity, "
        "NOT a top-level findings list); reading it at the wrong level -- or "
        "losing the real exit code behind a pipeline -- has already produced "
        "two false '0 errors' reports. check_summary.py encodes the correct "
        "traversal once instead of re-deriving it inline.",
        # Already piping into check_summary.py IS the fix -- do not
        # nudge it. A pipeline that greps a RULE ID (e.g. `LANG003`,
        # `DOC006`) is LISTING findings, not counting them -- that is
        # the single most common legitimate need this rule used to
        # block outright (T-2908: it fired on `| tail -20`,
        # `| grep -vE`, and `| grep LANG003` alike, with no usable
        # alternative for any of them). Stay quiet whenever the raw
        # command names something that looks like a rule id.
        re.compile(r"check_summary\.py|\b[A-Z]{3,12}[0-9]{3}\b"),
    ),
    (
        "handrolled-fleet-probe",
        # Two lookaheads, order-independent: fires only when a root-
        # dirtiness check (`git status --porcelain`) is COMBINED with a
        # liveness/land-in-flight probe (`ps aux`, `pgrep`, or `git
        # worktree list`) in the same command -- either alone is routine
        # hygiene (criterion 7) and must stay quiet.
        re.compile(
            r"(?=.*git +status +--porcelain)"
            r"(?=.*(?:ps +aux\b|pgrep\b|git +worktree +list\b))",
            re.M | re.S,
        ),
        "Prefer `python3 scripts/fleet_status.py` over hand-rolling root "
        "cleanliness / land-in-flight / worktree-liveness with separate "
        "git status / ps aux / pgrep / git worktree list calls. It answers "
        "'is it safe to dispatch, and which worktrees are actually idle?' "
        "in one invocation instead of several hand-derived ones.",
        # Already invoking fleet_status.py IS the fix -- do not nudge it.
        re.compile(r"fleet_status\.py"),
    ),
]


#: A `from <module> import ...` or `import <module>` line, module captured
#: in whichever group matched -- used to tell an EDIT that REWRITES an
#: existing import line (the rename signal) from one that merely adds a
#: brand-new import (no such line in the OLD text at all, T-3069's own
#: must-stay-quiet case).
_IMPORT_LINE = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import\b|import\s+([\w.]+))", re.M)

#: Cross-call state for the Edit-based rename signal lives alongside the
#: Bash marker state (T-3069) -- same TTL, same best-effort-never-fatal
#: contract as the rest of this module.
_RENAME_STATE_DIR = _STATE_DIR / "rename-scan"


def _import_modules(text: str) -> set[str]:
    """Every module dotted-path named by a `from`/`import` statement at the
    START of a line in `text` -- used against an Edit's OLD string to ask
    "was this edit rewriting an existing import of this module", never
    against arbitrary prose (T-3069)."""
    modules: set[str] = set()
    for m in _IMPORT_LINE.finditer(text):
        modules.add(m.group(1) or m.group(2))
    return modules


def _rename_state_path(module: str) -> Path:
    """The state file recording which files have already had an existing
    `module` import hand-rewritten in this window (T-3069) -- keyed by a
    hash of the module name, same shape as `_marker_path`."""
    digest = hashlib.sha256(module.encode("utf-8", "replace")).hexdigest()[:32]
    return _RENAME_STATE_DIR / f"{digest}.json"


def _edit_rename_hit(file_path: str, old_string: str) -> tuple[str, str, str] | None:
    """`(key, name, suggestion)` when this Edit rewrites an existing import
    of some module ALREADY rewritten in a DIFFERENT file within the TTL
    window -- the "same module, multiple files" rename shape (T-3069's
    high-precision signal #2). Records `file_path` against every module it
    touches either way, so the FIRST file to touch a module never fires
    (must-stay-quiet: editing imports in a single file) and only the
    second-and-later DISTINCT file does.

    Returns `None` (and records nothing) when `old_string` contains no
    import line at all -- a brand-new import, or an edit to unrelated code
    (a residue/prose fix), must never contribute to this signal."""
    modules = _import_modules(old_string)
    if not modules:
        return None
    now = time.time()
    try:
        _RENAME_STATE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    hit: tuple[str, str, str] | None = None
    for module in sorted(modules):
        state_path = _rename_state_path(module)
        files: set[str] = set()
        try:
            if state_path.exists() and now - state_path.stat().st_mtime < _MARKER_TTL_S:
                payload = json.loads(state_path.read_text(encoding="utf-8"))
                files = set(payload.get("files", []))
        except (OSError, ValueError, TypeError):
            files = set()
        if hit is None and files and file_path not in files:
            hit = (
                f"edit-rename:{module}",
                "hand-rename-edit-multifile",
                f"This is the second file (after {min(files)!r}) whose "
                f"existing `{module}` import has been hand-rewritten in this "
                "session -- that shape is a rename/move, not an ordinary "
                "import edit. Prefer `uv run frob refactor rename`/`move`/"
                "`split`/`move-module` instead of continuing by hand: a hand "
                f"pass only rewrites Python import lines, and silently "
                f"misses {module}'s non-Python reference surface -- `.strata` "
                "`code=` globs, ticket `scope` globs, `frob:doc`/`frob:tests` "
                "path citations, and `frob.toml` dotted `module:symbol` "
                "config values.",
            )
        files.add(file_path)
        try:
            # frob:ticket T-3059
            # frob:waive PERF004 reason="files grows by one element each iteration, so this is not a hoistable repeated sort of unchanged data -- sorted only for a deterministic on-disk list"  # noqa: E501
            state_path.write_text(
                json.dumps({"files": sorted(files)}), encoding="utf-8"
            )
        except OSError:
            pass
    return hit


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


#: A leading `FROB_SUGGEST_ACK=1 ` on a SEGMENT is the explicit
#: acknowledgement T-2164's escalation asks for on a third-or-later repeat
#: -- stripped before digesting/matching so the SAME underlying command
#: (acked or not) still maps to the same marker and the same repeat count.
#: T-3851: checked per segment (`_segment_is_acked` below), never against
#: the whole raw string -- `_match`'s own `POS`-anchored patterns fire at
#: ANY command position, not only position zero, so an ack anchored only
#: to position zero disagreed with the scan it was meant to answer.
_ACK_PREFIX = re.compile(r"^\s*FROB_SUGGEST_ACK=1\s+")

#: From this many total attempts at the identical command onward, a bare
#: repeat is no longer let through silently -- T-2164 acceptance [1]:
#: "allow the first exact-rerun, refuse or require an explicit
#: acknowledgement on the third within a session."
_ESCALATE_AT_ATTEMPT = 3


# frob:ticket T-5124
def _session_key(payload: dict) -> str:
    """Per-agent-session marker discriminator (T-5124):
    `payload["session_id"]`, else `FROB_AGENT`, else this process's
    parent pid -- HOOK-AUDIT.md section 0b measured the command-string-
    alone key as machine-global across every agent/session/repo. Best-
    effort: an absent session_id falls through to the next one."""
    session_id = payload.get("session_id")
    if isinstance(session_id, str) and session_id:
        return session_id
    return os.environ.get("FROB_AGENT") or f"ppid:{os.getppid()}"


# frob:ticket T-5124
def _marker_path(session_key: str, command: str) -> Path:
    """O_EXCL marker path for `command` within `session_key` (ack prefix
    stripped first, so acked/un-acked runs share one counter -- T-2164);
    `session_key` (T-5124) stops unrelated agents/sessions/repos
    sharing -- and inflating -- one another's counter."""
    digest = hashlib.sha256(
        f"{session_key}\x00{command}".encode("utf-8", "replace")
    ).hexdigest()[:32]
    return _STATE_DIR / f"{digest}.marker"


# frob:ticket T-5124
def _record_attempt(session_key: str, command: str) -> int:
    """Atomically record one more attempt at `command` within
    `session_key` (T-2164's counting, T-5124's per-session key
    added). O_CREAT|O_EXCL is the FIRST-attempt mechanism: one racing
    sibling gets count=1, the other count=2. A corrupt/unreadable marker
    reads as attempt 1 (best-effort)."""
    marker = _marker_path(session_key, command)
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError:
        pass
    else:
        try:
            os.write(
                fd,
                json.dumps({"count": 1, "command": command[:4096]}).encode("utf-8"),
            )
        finally:
            os.close(fd)
        return 1

    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
        count = int(payload.get("count", 1)) + 1
    except (OSError, ValueError, TypeError):
        # Unreadable/corrupt marker: cannot trust a prior count, but the
        # marker's mere EXISTENCE still means this is at least the second
        # attempt (the O_EXCL branch above already handles "first ever").
        count = 2
    try:
        marker.write_text(
            json.dumps({"count": count, "command": command[:4096]}),
            encoding="utf-8",
        )
    except OSError:
        # Cannot persist the new count -- next attempt undercounts by one,
        # same accepted best-effort tradeoff the module docstring names.
        pass
    return count


#: A scripted in-place rewrite (`sed -i`, `perl -pi`, or similar) at
#: command position -- checked against the STRIPPED command (like every
#: other rule), because the tool name/flags themselves are never inside
#: quotes even when their SCRIPT argument is.
_SED_PERL_INPLACE = re.compile(_POS + r"(?:sed|perl)\s+-\w*i\w*\b", re.M)

# frob:ticket T-3615
#: T-3615: the sed/perl -i invocation's OWN quoted script argument,
#: captured directly off RAW (never `command`, which has already blanked
#: it) -- matched against `raw` (never `command`), because this is the
#: one span whose CONTENT (not merely whether it runs) the rule below
#: needs to read. Deliberately narrower than `_SED_PERL_INPLACE`: it
#: requires the invocation's very next token to be a single- or
#: double-quoted string, so an unquoted or otherwise-shaped script
#: argument (rare, and not the T-3069 shape this rule targets) yields no
#: match rather than a guess.
_SED_PERL_INPLACE_SCRIPT_RE = re.compile(
    _POS + r"(?:sed|perl)\s+-\w*i\w*\b"
    r"(?:\s+-\S+)*\s*"  # perl's `-pi -e '...'`: skip any flag tokens in between
    r"(?:'([^']*)'|\"((?:[^\"\\]|\\.)*)\")",
    re.M,
)

#: Already running `frob refactor` in the same command is the fix itself --
#: never nudge that (T-3069 acceptance: "any call already running
#: `frob refactor`").
_FROB_REFACTOR = re.compile(r"frob\s+refactor")


def _sed_perl_script(raw: str) -> str | None:
    """The sed/perl -i invocation's own quoted script text in `raw`, or
    `None` when none is found -- T-3615's fix for `hand-rename-sed`
    scanning the WHOLE raw command line for the word `import`, which
    false-fired on a scratch-file rewrite whose script had nothing to do
    with imports but shared a line with unrelated text that happened to
    contain the word. Restricting the scan to just this captured span is
    the "tokenize the command position, never scan content outside it"
    fix: `import` must appear IN THE SCRIPT BEING RUN, not merely
    somewhere in the same command string. No match (script not
    confidently isolated) means the caller does not flag at all -- when
    in doubt, allow, same posture as every other rule in this module."""
    match = _SED_PERL_INPLACE_SCRIPT_RE.search(raw)
    if not match:
        return None
    return match.group(1) if match.group(1) is not None else match.group(2)


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

    # T-3069's `hand-rename-sed`: deliberately checked against RAW, not
    # `command` -- the whole point is a `sed -i 's/from old import x/from
    # new import x/'` -style script, and that script text is exactly what
    # `_strip_quoted` removes for every other rule. `frob refactor` is
    # checked against RAW too, so a combined `frob refactor ...; sed -i
    # ...` command stays quiet regardless of where in the command the
    # invocation sits. T-3615: `import` is checked only within the sed/
    # perl script's OWN captured argument (`_sed_perl_script`), never the
    # whole raw line -- the pre-fix `re.search(r"\bimport\b", raw)`
    # false-fired on a scratch-file `sed -i` whose script rewrote
    # unrelated text, tripped only because the word "import" appeared
    # elsewhere in the same command.
    sed_script = _sed_perl_script(raw)
    if (
        _SED_PERL_INPLACE.search(command)
        and sed_script is not None
        and re.search(r"\bimport\b", sed_script)
        and not _FROB_REFACTOR.search(raw)
    ):
        return (
            "hand-rename-sed",
            "This looks like a scripted in-place rewrite of an `import` "
            "line. Prefer `uv run frob refactor rename`/`move`/`split`/"
            "`move-module` instead: a hand pass only rewrites Python "
            "import lines, and silently misses the non-Python reference "
            "surface the verb also handles -- `.strata` `code=` globs, "
            "ticket `scope` globs, `frob:doc`/`frob:tests` path citations, "
            "and `frob.toml` dotted `module:symbol` config values.",
        )

    for name, pattern, suggestion, raw_exempt in _RULES:
        if raw_exempt is not None and raw_exempt.search(raw):
            continue
        if pattern.search(command):
            return name, suggestion
    return None


def _deny(reason: str) -> None:
    """Emit the PreToolUse deny payload with `reason` (T-2164 split out of
    `main` so both the first-attempt nudge and the third-attempt escalation
    share one emission path)."""
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


# frob:ticket T-5124
def _escalate(
    session_key: str,
    key: str,
    name: str,
    suggestion: str,
    acked: bool,
    first_hint: str,
    repeat_hint: str,
) -> None:
    """Shared block-once-then-escalate flow (T-2164) for BOTH the Bash-
    command rules and the Edit-based rename rule (T-3069) -- `key` is
    whatever counts as "the same thing recurring" (raw command text, or
    `edit-rename:<module>`); `session_key` (T-5124) scopes that
    to one agent/session; `first_hint`/`repeat_hint` differ between the
    two escape hatches even though the counting logic is identical."""
    _prune(time.time())
    attempt = _record_attempt(session_key, key)

    if attempt == 1:
        # T-3071: the ack is checked on EVERY path, first block included --
        # a caller who already knows the raw command is right should not
        # have to eat one denial just to prove it by re-running the exact
        # same string. Still records the attempt above (so a later
        # unacknowledged repeat of the same command is not misread as a
        # first encounter), but does not deny when acked.
        if acked:
            return
        reason = (
            f"BLOCKED ONCE by frob-suggest [{name}] -- this looks like work frob "
            f"should account for.\n\n{suggestion}\n\n{first_hint}"
        )
        _deny(reason)
        return

    if attempt < _ESCALATE_AT_ATTEMPT or acked:
        return  # first exact-rerun (or an acknowledged later one): let it through

    reason = (
        f"BLOCKED (repeat #{attempt}) by frob-suggest [{name}] -- this exact "
        "shape has now recurred several times in this session. The suggested "
        f"tool likely already had the answer:\n\n{suggestion}\n\n{repeat_hint}"
    )
    _deny(reason)


# frob:ticket T-5124
def _handle_edit(payload: dict, session_key: str) -> None:
    """T-3069's Edit-tool branch (cross-file import-rewrite signal,
    `_edit_rename_hit`) -- separate from the Bash `_match` path since it
    needs the OLD string, not a shell command."""
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    old_string = tool_input.get("old_string") or ""
    if not file_path or not old_string:
        return
    hit = _edit_rename_hit(file_path, old_string)
    if hit is None:
        return
    key, name, suggestion = hit
    # No shell command carries the ack prefix here -- an ambient env var is
    # the closest equivalent escape hatch for a non-Bash tool call, and it
    # is the same variable name so "FROB_SUGGEST_ACK=1" means one thing
    # across the whole hook (T-3069 acceptance: "consistent with the
    # existing hook").
    # frob:waive SEC110 reason="FROB_SUGGEST_ACK is a boolean hook-escape-hatch flag, \
    # not a secret"
    acked = os.environ.get("FROB_SUGGEST_ACK") == "1"
    _escalate(
        session_key,
        key,
        name,
        suggestion,
        acked,
        "If you are SURE the hand edit is right, make the same edit again "
        "and it will be allowed; this hook blocks only the first "
        "unacknowledged attempt at a given rename shape. Set "
        "`FROB_SUGGEST_ACK=1` in the environment beforehand to skip the "
        "re-edit and pass on this very first attempt -- the ack is checked "
        "on every path, first block included.",
        "If this genuinely is not a repeated habit and the hand edit is "
        "still the right call, set `FROB_SUGGEST_ACK=1` in the environment "
        "(consistent with the Bash-command escape) -- that acknowledgement "
        "is checked every time, so later repeats need it again too, not "
        "just once.",
    )


# frob:ticket T-5124
# frob:ticket T-3851
def _handle_bash(payload: dict, root: Path, session_key: str) -> None:
    """The pre-existing Bash-command branch, split out of `main` so
    T-3069's Edit branch has a sibling at the same level; T-3851 replaced
    its whole-string ack anchor with a per-segment one so the
    acknowledgement agrees in scope with `_match`'s own command-position
    trigger scan."""
    raw_command = (payload.get("tool_input") or {}).get("command") or ""
    if not raw_command.strip():
        return

    # T-3375: reads the ack ONLY from the command string (per segment,
    # T-3851), never the process environment -- an inline `VAR=1 cmd`
    # prefix applies to the spawned command, not this separately-spawned
    # hook. `_handle_edit` is the environment-read path instead.
    command, blanked = _strip_and_blank(raw_command, _ACK_PREFIX)

    hit = _match(command, root)
    if hit is None:
        return
    name, suggestion = hit
    # Acked when the trigger disappears once every acked segment is
    # blanked -- i.e. every segment that made the rule fire was itself
    # acked. An UNRELATED segment's ack (T-3851's must-fire fixture)
    # still fires here: blanking it leaves the real trigger intact.
    acked = _match(blanked, root) is None
    _escalate(
        session_key,
        command,
        name,
        suggestion,
        acked,
        "If you are SURE the raw command is right, re-run it EXACTLY as "
        "written and it will be allowed; this hook blocks only the first "
        "unacknowledged attempt at a given command. Do not paraphrase to "
        "get around the block -- a reworded command is a new command and "
        "blocks again. Or prefix it with `FROB_SUGGEST_ACK=1 ` up front "
        "(e.g. "
        f"`FROB_SUGGEST_ACK=1 {command}`) to skip the re-run and pass on "
        "this very first attempt -- the ack is checked on every path, this "
        "first block included.",
        "If this genuinely is not a repeated habit and the raw command is "
        "still the right call, prefix it with `FROB_SUGGEST_ACK=1 ` (e.g. "
        f"`FROB_SUGGEST_ACK=1 {command}`) to run it anyway -- that "
        "acknowledgement is checked every time, so later repeats need it "
        "again too, not just once.",
    )


# frob:doc docs/guides/claude-hooks.md#frob-suggestpy
# frob:ticket T-5124
# frob:tests tests/test_hook_frob_suggest.py kind="integration"
def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 -- a malformed payload must never block
        return
    root = _repo_root(payload.get("cwd") or os.getcwd())
    if root is None:
        return

    # T-3069: this hook is now registered for both Bash and Edit
    # (.claude/settings.json's "Bash|Edit" matcher) -- an absent
    # `tool_name` means an older payload shape and is treated as Bash,
    # matching this hook's behaviour before T-3069 introduced the branch.
    session_key = _session_key(payload)
    if payload.get("tool_name") == "Edit":
        _handle_edit(payload, session_key)
        return
    _handle_bash(payload, root, session_key)


if __name__ == "__main__":
    main()
