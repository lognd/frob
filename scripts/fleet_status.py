"""Report coordinator fleet state: root cleanliness, leases, worktree liveness.

WHY THIS EXISTS. Dispatching onto a dirty root DirtyMain-blocks every agent,
and removing a worktree whose agent is still live destroys its work. Both
have cost this fleet real time. This is the one-shot check that answers
"is it safe to dispatch, and which worktrees are actually idle?".

Liveness is inferred from each worktree's last commit age -- an agent that
has not committed in a long while is PROBABLY retired, but treat this as a
hint, not proof. `frob worktree remove` performs the authoritative
lease-and-liveness check and refuses when it is not safe; prefer it over
raw `git worktree remove`, which has deleted a live agent's checkout here.

T-2133 extends this with the missing PER-TICKET question: given T-####,
is it actually dispatchable right now? `ticket_readiness` answers that
directly from `.git/frob-leases/<id>.json` (the live, authoritative
scope/holder) and `main:tickets/<id>/ticket.md` (the committed record),
rather than a coordinator hand-rolling the same three git probes -- and
getting them wrong, twice, in ways this ticket's own body documents.

Usage:
    python3 scripts/fleet_status.py [--idle-minutes N] [--ticket T-####]
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from _require_python import require_python  # noqa: E402

require_python(__file__)

# ruff: noqa: E402 -- every import below MUST follow the require_python(__file__)
# guard above: T-2236 requires this script to fail with a clear version message
# on a too-old interpreter BEFORE it imports anything that would raise a
# confusing SyntaxError instead.
import argparse
import fnmatch
import json
import os
import re
import subprocess
import time
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - python <3.11 on PATH
    tomllib = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]

# frob:doc docs/guides/coordinator-scripts.md#fleet_status-constants
#: Repo root, derived from this script's own location.
REPO = Path(__file__).resolve().parent.parent
# frob:doc docs/guides/coordinator-scripts.md#fleet_status-constants
#: Where per-worktree checkouts live (`.claude/worktrees/<name>`).
WORKTREES = REPO / ".claude" / "worktrees"
# frob:doc docs/guides/coordinator-scripts.md#fleet_status-constants
#: Where held cross-worktree scope leases are recorded, one JSON file each.
LEASES = REPO / ".git" / "frob-leases"
# frob:doc docs/guides/coordinator-scripts.md#fleet_status-constants
#: Where the live, per-ticket ledger files live (`tickets/<id>/ticket.md`) --
#: `tickets/archive/**` holds terminal tickets and is excluded by `rotting_
#: tickets` below (a terminal ticket cannot be "rotting" in the queued/
#: planned sense TICK004 measures).
TICKETS_DIR = REPO / "tickets"
# frob:doc docs/guides/coordinator-scripts.md#fleet_status-constants
#: Per-priority rot-day thresholds (T-0411's TICK004 gate), mirroring
#: `frob.gates._tickets_gate._TICK004_DEFAULT_ROT_DAYS` -- duplicated here
#: in plain-dict form (this script's own "no `frob` import" contract)
#: rather than imported, since importing the `frob` package would defeat
#: the point of a script meant to run under any interpreter on PATH.
_ROT_DAYS_DEFAULT = {"critical": 3, "high": 7, "medium": 30, "low": 90}
#: Priority rank for sorting rotting tickets highest-priority-first --
#: mirrors the same ordering `frob ticket doable` (T-0411) already uses.
_PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _git(args: list[str], cwd: Path) -> str:
    """Run git in `cwd`, returning stripped stdout ('' on any failure)."""
    try:
        done = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


#: Porcelain status codes for which `git status`'s fast stat-comparison
#: path can produce a false "modified" (T-2586) -- a plain, untracked-free
#: "M"/"MM" report (whitespace already collapsed by the `str.split()`
#: parse below, so a leading-space-only "M " unstaged-only code and a
#: bare "M" staged-only code both normalize to "M" here). Any OTHER code
#: (`??` untracked, `A`/`D`/`R`/`C` add/delete/rename/copy) is trusted
#: verbatim: those are derived from tree/index PRESENCE, not a stat
#: comparison, so they cannot be fooled by a CRLF-vs-LF byte-count
#: mismatch the way a content-unchanged rewrite of an existing tracked
#: file can.
_STAT_SHORTCUT_CODES = frozenset({"M", "MM"})


# frob:doc docs/guides/coordinator-scripts.md#root_dirt
# frob:ticket T-1863
# frob:ticket T-2586
# frob:tests tests/unit/test_coordinator_scripts.py::TestRootDirt.test_clean_repo
# frob:tests tests/unit/test_coordinator_scripts.py::TestRootDirt.test_dirty_repo
# frob:tests tests/unit/test_coordinator_scripts.py::TestRootDirt.test_phantom_modified_entry_dropped kind="unit"  # noqa: E501
# frob:tests tests/unit/test_coordinator_scripts.py::TestRootDirt.test_genuine_modified_entry_kept kind="unit"  # noqa: E501
# frob:tests tests/unit/test_coordinator_scripts.py::TestRootDirt.test_untracked_entry_never_reverified kind="unit"  # noqa: E501
def root_dirt() -> list[str]:
    """Porcelain lines for the root checkout, content-confirmed; empty
    means safe to dispatch.

    T-2586: `git status --porcelain`'s fast path can flag a tracked path
    "M" from a stat mismatch (mtime/size) alone, without comparing
    content -- with `core.autocrlf=true` and no `.gitattributes`
    normalization for a given path, a tool that rewrites a tracked file
    with byte-identical LOGICAL content (the index stores LF; the
    working tree gets CRLF on checkout) trips exactly this: `git status`
    reports modified, `git diff` (which normalizes line endings the same
    way checkout did before comparing) reports nothing changed. Every
    stat-shortcut-susceptible candidate (`_STAT_SHORTCUT_CODES`) is
    re-verified against `git diff --stat HEAD -- <path>` -- the same
    normalizing comparison `git diff` uses -- and dropped as a phantom
    if that comes back empty. Untracked (`??`) and added/deleted/
    renamed paths are never stat-shortcut candidates in the first place
    (git derives those from tree/index PRESENCE, not a stat comparison),
    so they are trusted as-is and never re-verified -- this is what
    keeps a genuinely dirty root, or the retry-loop untracked-residue
    case, reported correctly in both directions."""
    _git(["update-index", "-q", "--refresh"], REPO)
    out = _git(["status", "--short", "--porcelain"], REPO)
    candidates = [line for line in out.splitlines() if line.strip()]
    confirmed = []
    for line in candidates:
        parts = line.split(maxsplit=1)
        code = parts[0] if parts else ""
        path = parts[1].strip() if len(parts) > 1 else ""
        if path and code in _STAT_SHORTCUT_CODES:
            if not _git(["diff", "--stat", "HEAD", "--", path], REPO):
                continue  # phantom: stat differs, content does not (T-2586)
        confirmed.append(line)
    return confirmed


# frob:doc docs/guides/coordinator-scripts.md#quarantine
#: The T-1693 quarantine circuit breaker's current record (`frob.verify.
#: _quarantine`'s own store) -- read directly as raw JSON, mirroring
#: `LEASES`'s own pattern, so this script stays import-light rather than
#: depending on the `frob` package being installed.
QUARANTINE = REPO / ".frob" / "quarantine.json"
# frob:doc docs/guides/coordinator-scripts.md#verify_queue_state
# frob:ticket T-2126
#: The verify-queue/watermark stores `frob.verify._watermark` owns --
#: read directly as raw JSON, mirroring QUARANTINE's own raw-file
#: convention immediately above (this script never imports frob.* by
#: design, so it stays usable even when the native extensions/venv are
#: not built).
VERIFY_QUEUE = REPO / ".frob" / "verify-queue.json"
# frob:doc docs/guides/coordinator-scripts.md#verify_queue_state
VERIFY_WATERMARK = REPO / ".frob" / "verify-watermark.json"


# frob:doc docs/guides/coordinator-scripts.md#leases
# frob:ticket T-1863
# frob:tests tests/unit/test_coordinator_scripts.py::TestLeases.test_reads_lease_records
# frob:tests tests/unit/test_coordinator_scripts.py::TestLeases.test_no_lease_dir
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLeases.test_unreadable_lease_file
def leases() -> list[dict]:
    """Every held scope lease, as parsed lease records."""
    if not LEASES.is_dir():
        return []
    records = []
    for path in sorted(LEASES.glob("*.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            records.append({"ticket_id": path.stem, "worktree": "<unreadable>"})
    return records


# frob:doc docs/guides/coordinator-scripts.md#_iter_in_progress_ticket_frontmatter
# frob:ticket T-2654
def _iter_in_progress_ticket_frontmatter():
    """Yield `(ticket_dir, parsed_frontmatter)` for every `state:
    in-progress` ticket under `TICKETS_DIR` (skipping `archive/`) -- the
    shared directory-walk-plus-parse loop `in_progress_ticket_scope_
    leases` and `blocked_in_progress_leases` (T-2654) both need, split
    out (DUP001: the two used to duplicate this loop at 95% similarity)
    so a future third consumer of 'every in-progress ticket's own
    frontmatter' does not have to duplicate it a second time. An
    unreadable `ticket.md` is silently skipped (matches both callers'
    prior behavior) rather than raising -- a single corrupt ledger file
    must not take down the whole fleet-status report."""
    if not TICKETS_DIR.is_dir():
        return
    for ticket_dir in sorted(p for p in TICKETS_DIR.iterdir() if p.is_dir()):
        if ticket_dir.name == "archive":
            continue
        ledger_path = ticket_dir / "ticket.md"
        if not ledger_path.is_file():
            continue
        try:
            text = ledger_path.read_text(encoding="utf-8")
        except OSError:
            continue
        parsed = _parse_ticket_frontmatter_text(text)
        if parsed.get("state") != "in-progress":
            continue
        yield ticket_dir, parsed


# frob:doc docs/guides/coordinator-scripts.md#in_progress_ticket_scope_leases
# frob:ticket T-2651
# frob:ticket T-2654
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeases.test_no_workt\
# ree_flagged_as_leak
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeases.test_live_wor\
# ktree_named_not_leaked
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeases.test_queued_t\
# icket_excluded
def in_progress_ticket_scope_leases() -> list[dict]:
    """T-2651: every `state: in-progress` ticket under `TICKETS_DIR`, read
    directly from its own local ledger file, as `{"ticket_id", "scope",
    "worktree", "leaked"}`.

    THE authoritative source: `leases()` above enumerates `.git/frob-
    leases/*.json` files, which frob's own `read_all_leases` opportunis-
    tically UNLINKS the moment ANY OTHER ticket's lease scan confirms the
    file's recorded `worktree` path no longer exists on disk
    (`frob.tickets._leases._live_leases_pruning_stale`) -- correct for the
    ordinary case (an agent finished and its worktree was removed), but
    silently wrong for a ticket that is still `in-progress` with nobody
    working it (blocked-and-abandoned, or a worktree removed by hand
    without releasing the lease first). That is precisely the leak this
    exists to surface: T-2377 sat `in-progress` holding
    `docs/modules/gates.md` for nine hours after its own worktree was
    removed, and `leases()` never listed it at all because the file was
    already gone -- while `frob ticket start`'s own collision check (which
    reads ticket state/scope directly off the ledger, never the lease
    file, `frob.tickets._scope._scope_add_queue_conflict`) refused for
    real on exactly this ticket.

    A lease is a property of an in-progress ticket's declared scope
    (T-0453) -- a worktree is merely where the work usually happens, so
    this reads scope/state from the ledger FIRST and treats a worktree as
    an annotation, not the trigger. `worktree` is populated best-effort
    (`ticket_lease`'s own file, if it still exists and resolves to a live
    path, else a `worktrees_touching_ticket` scope-correlated scan) --
    `None` (and `leaked=True`) only when NEITHER source can name one, the
    exact 'in-progress with no worktree anywhere' shape that was
    previously invisible.

    Deliberately does NOT call the O(n^2) start-time collision check
    (`scope_lease_conflict`) per ticket pair -- this just enumerates the
    same underlying fact (in-progress ticket + declared scope) the
    collision check already reads, once per ticket, linear in the number
    of in-progress tickets."""
    entries: list[dict] = []
    for ticket_dir, parsed in _iter_in_progress_ticket_frontmatter():
        ticket_id = ticket_dir.name
        scope = parsed.get("scope", [])
        worktree = _resolve_worktree_for_in_progress_ticket(ticket_id, scope)
        entries.append(
            {
                "ticket_id": ticket_id,
                "scope": scope,
                "worktree": worktree,
                "leaked": worktree is None,
            }
        )
    return entries


# frob:doc docs/guides/coordinator-scripts.md#blocked_in_progress_leases
# frob:ticket T-2654
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestBlockedInProgressLeases.test_in_progress_\
# with_open_blocker_flagged
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestBlockedInProgressLeases.test_in_progress_\
# with_no_blockers_not_flagged
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestBlockedInProgressLeases.test_in_progress_\
# with_only_terminal_blockers_not_flagged
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestBlockedInProgressLeases.test_queued_ticke\
# t_with_open_blocker_not_flagged
def blocked_in_progress_leases() -> list[dict]:
    """T-2654: every `state: in-progress` ticket under `TICKETS_DIR` whose
    `blocked_by` still names an OPEN blocker -- distinct from (and cheaper
    to detect than) the no-worktree leak `in_progress_ticket_scope_leases`
    (T-2651) already reports, since this does not depend on worktree
    liveness at all. A ticket that is both `in-progress` and blocked by an
    open blocker cannot proceed by definition (a blocker gate refuses its
    own close/land until the blocker resolves) -- any lease it holds is
    pure waste for as long as that holds. This is exactly the T-2377
    shape T-2651's own body flagged as a related-but-distinct check: that
    ticket sat `in-progress`, `blocked_by=[T-2568]` (still `queued`), for
    nine hours, holding a live write lease on `docs/modules/gates.md` the
    entire time -- discoverable here without ever needing its worktree to
    be removed first.

    Shares `in_progress_ticket_scope_leases`'s own ledger-read loop via
    `_iter_in_progress_ticket_frontmatter` (DUP001, T-2654: the two used
    to duplicate this walk directly at 95% similarity) plus
    `_classify_blockers_local` (T-2449, the local-disk blocker classifier
    already used by `_rotting_entry`) so 'still open' here means the same
    thing it means everywhere else in this script: a blocker whose own
    local ledger state exists and is not `done`/`dropped`. An UNRESOLVED
    blocker (id does not resolve on local disk at all) is deliberately
    NOT flagged here -- that is a different failure mode (a typo or a
    blocker filed but never a real ticket) with its own detector
    (`TICK004`-adjacent rot checks); conflating it here would blur two
    distinct fix actions into one line. `state: queued`/`planned`
    tickets are never flagged regardless of their own `blocked_by` -- a
    lease binds only at `in-progress` (T-0453), so a queued ticket
    blocked by something open holds no lease yet and has nothing to
    flag."""
    entries: list[dict] = []
    for ticket_dir, parsed in _iter_in_progress_ticket_frontmatter():
        open_blockers, _unresolved = _classify_blockers_local(
            parsed.get("blocked_by", []), TICKETS_DIR
        )
        if not open_blockers:
            continue
        entries.append(
            {
                "ticket_id": ticket_dir.name,
                "open_blockers": open_blockers,
            }
        )
    return entries


# frob:doc docs/guides/coordinator-scripts.md#_resolve_worktree_for_in_progress_ticket
# frob:ticket T-2651
# frob:ticket T-2655
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeases.test_no_workt\
# ree_flagged_as_leak
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeases.test_live_wor\
# ktree_named_not_leaked
def _resolve_worktree_for_in_progress_ticket(
    ticket_id: str, scope: Sequence[str]
) -> str | None:
    """Best-effort worktree NAME for `ticket_id` (`in_progress_ticket_
    scope_leases`'s own annotation half): prefer the recorded lease
    file's own `worktree` field (`ticket_lease`) when it still exists AND
    resolves to a directory that is still on disk, else fall back to a
    scope-correlated scan (`worktrees_touching_ticket`) that finds a live
    worktree with an unlanded commit actually implementing this ticket's
    scope. `None` when neither source can name one -- the leak signature
    `in_progress_ticket_scope_leases` reports."""
    lease = ticket_lease(ticket_id)
    if lease is not None:
        recorded = lease.get("worktree")
        if recorded and recorded not in ("<unreadable>",):
            recorded_path = Path(recorded)
            if recorded_path.is_dir():
                return recorded_path.name
    hits = worktrees_touching_ticket(ticket_id, scope)
    return hits[0] if hits else None


# frob:doc docs/guides/coordinator-scripts.md#worktrees
# frob:ticket T-1863
# frob:tests tests/unit/test_coordinator_scripts.py::TestWorktrees.test_reports_idle_age
# frob:tests tests/unit/test_coordinator_scripts.py::TestWorktrees.test_no_worktree_dir
def worktrees(idle_seconds: int) -> list[tuple[str, int, bool]]:
    """Return (name, seconds-since-last-commit, looks_idle) per worktree."""
    if not WORKTREES.is_dir():
        return []
    rows = []
    now = time.time()
    for path in sorted(p for p in WORKTREES.iterdir() if p.is_dir()):
        stamp = _git(["log", "-1", "--format=%ct"], path)
        age = int(now - int(stamp)) if stamp.isdigit() else -1
        rows.append((path.name, age, age >= idle_seconds))
    return rows


#: T-2599: source-bearing paths the stranded/stale content test restricts
#: itself to -- everything else (tickets/**, CHANGELOG.md, .frob/, ...) is
#: ledger/derived state that legitimately differs per-worktree and is not
#: "content" in the sense this test cares about.
_STRANDED_CONTENT_PATHS: tuple[str, ...] = ("src", "tests", "docs", "scripts")

#: T-2599: a worktree directory name that is exactly a lowercased ticket
#: id (`t-2599`, this repo's `frob ticket work`/`EnterWorktree` naming
#: convention) resolves to that ticket for the ACTIVE short-circuit; any
#: other name (`dev-friction`, `gate-internals`, a hand-named series
#: worktree) has no resolvable ticket and always falls through to the
#: content test.
_TICKET_NAMED_WORKTREE_RE = re.compile(r"^t-(\d+)$")


# frob:doc docs/guides/coordinator-scripts.md#_worktree_ticket_id
# frob:ticket T-2599
# frob:tests tests/unit/test_coordinator_scripts.py::TestWorktreeTicketId.test_ticket_named_worktree_resolves  # noqa: E501
# frob:tests tests/unit/test_coordinator_scripts.py::TestWorktreeTicketId.test_ad_hoc_named_worktree_resolves_to_none  # noqa: E501
def _worktree_ticket_id(name: str) -> str | None:
    """`"T-2599"` for a worktree directory literally named `t-2599`, else
    `None` -- see `_TICKET_NAMED_WORKTREE_RE`."""
    m = _TICKET_NAMED_WORKTREE_RE.match(name)
    return f"T-{m.group(1)}" if m else None


#: `frob ticket` states that mean nobody is expected to still be working a
#: ticket -- anything ELSE (queued/planned/in-progress) marks the owning
#: worktree ACTIVE regardless of what its diff looks like (T-2599's
#: positive control: an ACTIVE worktree is never proposed for removal).
_TERMINAL_TICKET_STATES = frozenset({"done", "dropped", "failed"})

#: T-2617: a worktree's `+`-side diff is deletion-dominated -- overwhelming
#: evidence it is simply BEHIND main (main moved on and rewrote/removed
#: most of what the worktree still carries), not that the worktree holds
#: unlanded work of its own. Measured against the ticket's own real-data
#: complaint: `t-2576`'s landed diff is 985 deletions against 17
#: insertions (ratio ~58), `t-2593`'s is 558 against 11 (ratio ~51),
#: `gate-internals`' is 110259 against 12618 (ratio ~8.7) -- all comfortably
#: past this threshold. The deliberately-constructed STRANDED positive
#: control (new content, no matching deletions) sits at a ratio near 0 and
#: never trips it. Chosen conservatively above the measured ratios' floor
#: (~8.7) so it does not swallow a smaller, genuinely mixed stranded+stale
#: diff; a diff that does NOT clear this bar still goes through the
#: per-line presence check below, so this is a fast STALE short-circuit
#: for the overwhelming case, not a substitute for that check.
_DELETION_DOMINANT_RATIO = 3.0


# frob:doc docs/guides/coordinator-scripts.md#worktree_content_classification
# frob:ticket T-2599
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification.test_stranded_new_content_not_on_main  # noqa: E501
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification.test_stale_when_content_fully_landed_despite_many_commits  # noqa: E501
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification.test_stale_when_only_behind_main  # noqa: E501
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestWorktreeContentClassification.test_active_ticket_never_stranded_or_stale  # noqa: E501
def worktree_content_classification(
    path: Path, *, ticket_id: str | None = None
) -> tuple[str, list[str]]:
    """Classify one worktree at `path` as `"STRANDED"`, `"STALE"`, or
    `"ACTIVE"` against `main` (T-2599, refined T-2617), returning
    `(verdict, samples)` where `samples` is up to 5 example added lines
    backing a `STRANDED` verdict (empty otherwise). Full rationale,
    including the three measured-wrong naive tests and T-2617's own
    real-data false-positive finding, lives at `docs/guides/
    coordinator-scripts.md#worktree_content_classification` (`frob:doc`
    below) rather than duplicated here -- summary: `ticket_id` resolves
    to `"ACTIVE"` for any non-terminal ticket state, or to `"STALE"` for
    a terminal ticket whose `land_commit` is an ancestor of `main`
    (T-2617's exact fix for a renamed/superseded symbol misreading as
    stranded); failing both, a deletion-dominant diff
    (`_is_deletion_dominant`, T-2617's magnitude fallback for a
    ticketless worktree) is also `"STALE"`; only then does the original
    per-line presence check (`_lines_absent_from_main`) decide
    `STRANDED` vs `STALE`, deliberately conservative toward
    over-reporting `STRANDED` since this is a report-only classifier
    that never deletes anything itself."""
    if ticket_id is not None:
        frontmatter = ticket_frontmatter_on_main(ticket_id)
        if frontmatter is not None:
            if frontmatter.get("state") not in _TERMINAL_TICKET_STATES:
                return "ACTIVE", []
            land_commit = frontmatter.get("land_commit")
            if land_commit and _is_ancestor_of_main(land_commit, path):
                return "STALE", []
    diff = _git(["diff", "main", "HEAD", "--", *_STRANDED_CONTENT_PATHS], path)
    if not diff.strip():
        return "STALE", []
    added_by_file = _added_lines_by_file(diff)
    if not added_by_file:
        return "STALE", []
    if _is_deletion_dominant(path):
        return "STALE", []
    stranded = _lines_absent_from_main(path, added_by_file)
    if stranded:
        return "STRANDED", stranded[:5]
    return "STALE", []


# frob:ticket T-2617
def _is_ancestor_of_main(commit: str, path: Path) -> bool:
    """`True` if `commit` is an ancestor of (or equal to) `main`'s current
    tip, i.e. its content is genuinely reachable from main right now --
    `worktree_content_classification`'s `land_commit`-precision short-
    circuit. `git merge-base --is-ancestor` exits 0 for a true ancestor,
    non-zero otherwise (including when `commit` does not resolve at all,
    e.g. a stale/garbage-collected sha); `_git` already collapses any
    non-zero exit to `""`, so a bare presence check on its own exit is not
    enough here -- `subprocess.run` is called directly so the return code
    itself is read, since `--is-ancestor` prints nothing on success."""
    try:
        done = subprocess.run(
            ["git", "-C", str(path), "merge-base", "--is-ancestor", commit, "main"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


# frob:ticket T-2617
def _is_deletion_dominant(path: Path) -> bool:
    """`True` if `main..HEAD`'s restricted-path diff (`_STRANDED_CONTENT_
    PATHS`) has at least `_DELETION_DOMINANT_RATIO` times as many deleted
    lines as added lines -- `worktree_content_classification`'s magnitude
    fallback for a worktree with no ticket (or an un-stamped one) to
    resolve a precise `land_commit` ancestry check against. `git diff
    --numstat` reports `<added>\\t<deleted>\\t<path>` per file (a binary
    file reports `-` for both columns, skipped here since this classifier
    only ever restricts to text source paths); zero added lines with any
    deletions present is trivially dominant (the earlier `not added_by_
    file` check in the caller already handles the zero-added case, but
    this function is also directly testable on its own)."""
    numstat = _git(
        ["diff", "--numstat", "main", "HEAD", "--", *_STRANDED_CONTENT_PATHS], path
    )
    added_total = 0
    deleted_total = 0
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        added, deleted = parts[0], parts[1]
        if added.isdigit():
            added_total += int(added)
        if deleted.isdigit():
            deleted_total += int(deleted)
    if added_total == 0:
        return deleted_total > 0
    return (deleted_total / added_total) >= _DELETION_DOMINANT_RATIO


# frob:ticket T-2599
def _added_lines_by_file(diff: str) -> dict[str, list[str]]:
    """`{path: [added-line-text, ...]}` for every `+` (non-`+++`-header)
    line in `diff`, grouped by the `+++ b/<path>` header it fell under --
    `worktree_content_classification`'s own diff-parsing half (ARCH001
    split, zero behavior change). A `+++ /dev/null` header (a worktree-
    side deletion) never produces new content, so lines under it are
    dropped by construction, not filtered separately."""
    added_by_file: dict[str, list[str]] = {}
    current_file: str | None = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            rest = line[4:]
            current_file = rest[2:] if rest.startswith("b/") else None
        elif (
            current_file is not None
            and line.startswith("+")
            and not line.startswith("+++")
        ):
            text = line[1:].strip()
            if text:
                added_by_file.setdefault(current_file, []).append(text)
    return added_by_file


# frob:ticket T-2599
def _lines_absent_from_main(
    path: Path, added_by_file: dict[str, list[str]]
) -> list[str]:
    """`"<file>: <text>"` for every added line whose exact text is not
    present anywhere in `main`'s CURRENT version of that same file --
    `worktree_content_classification`'s own presence-check half (ARCH001
    split, zero behavior change)."""
    stranded: list[str] = []
    for fname, added_lines in added_by_file.items():
        main_content = _git(["show", f"main:{fname}"], path)
        main_lines = {ln.strip() for ln in main_content.splitlines()}
        for text in added_lines:
            if text not in main_lines:
                stranded.append(f"{fname}: {text}")
    return stranded


# frob:doc docs/guides/coordinator-scripts.md#ticket_lease
# frob:ticket T-2133
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestTicketLease.test_reads_a_live_lease
# frob:tests tests/unit/test_coordinator_scripts.py::TestTicketLease.test_no_lease_file
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestTicketLease.test_unreadable_lease_file
def ticket_lease(ticket_id: str) -> dict | None:
    """The single live lease record for `ticket_id` (`.git/frob-leases/
    <id>.json`), or `None` if no lease file exists at all -- the SAME file
    `leases()` above enumerates in bulk, read directly by id instead, so a
    caller checking one specific ticket does not have to scan and filter
    every held lease. `recorded_at` and `scope` are exactly the fields
    T-2133's own incident needed and did not have a one-call answer for:
    a coordinator dispatched T-2114 believing its lease "should be free
    now" while another worktree still held it, mid-implementation, with a
    Done report already written on its own branch -- a wasted dispatch
    this function exists to make impossible to repeat. An unreadable/
    malformed lease file reads as `{"ticket_id": ..., "worktree":
    "<unreadable>"}`, mirroring `leases()`'s own defensive shape, never
    raised (a lease file is peer-writable, T-0780)."""
    path = LEASES / f"{ticket_id}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"ticket_id": ticket_id, "worktree": "<unreadable>"}


# frob:doc docs/guides/coordinator-scripts.md#_parse_ticket_frontmatter_text
# frob:ticket T-2449
def _parse_ticket_frontmatter_text(text: str) -> dict:
    """`{"state": ..., "scope": [...], "blocked_by": [...], "land_commit":
    ...}` parsed from a ticket.md's own YAML frontmatter TEXT -- the
    pure-parse half of `ticket_frontmatter_on_main`, split out (T-2449) so
    the SAME parser runs regardless of which `git show` path (active or
    archived) supplied the text; previously this logic lived inline in
    `ticket_frontmatter_on_main` and only ever ran against the
    active-ledger path. Hand-parsed (no `import yaml`, matching this
    script's own 'no frob import' module-docstring contract) against the
    narrow shape `frob ticket` actually writes: a flat `key: value` line
    for `state`/`land_commit`, and `scope:`/`blocked_by:` blocks of
    `- item` list lines directly beneath each key (a ticket with no
    blockers omits the `blocked_by:` key entirely rather than writing an
    empty block, so its absence parses to `[]`). T-2617: `land_commit` is
    the merge commit `frob ticket land` stamps onto a ticket once it is
    finalized (`Ticket.land_commit`, `_record_land_commit`) -- read here
    so `worktree_content_classification` can tell a genuinely-landed
    terminal ticket's worktree apart from a diff-shape guess; absent
    (`None`) for a ticket that never landed (queued/planned/in-progress,
    or a terminal state some other way, e.g. a manually-edited ledger)."""
    lines = text.splitlines()
    state = None
    land_commit: str | None = None
    scope: list[str] = []
    blocked_by: list[str] = []
    block: list[str] | None = None
    for line in lines:
        if line.startswith("state:"):
            state = line.split(":", 1)[1].strip()
            block = None
            continue
        if line.startswith("land_commit:"):
            value = line.split(":", 1)[1].strip()
            land_commit = value or None
            block = None
            continue
        if line == "scope:":
            block = scope
            continue
        if line == "blocked_by:":
            block = blocked_by
            continue
        if block is not None:
            stripped = line.strip()
            if not stripped.startswith("- "):
                block = None
                continue
            item = stripped[2:].strip()
            if len(item) >= 2 and item[0] == item[-1] and item[0] in "'\"":
                item = item[1:-1]
            block.append(item)
    return {
        "state": state,
        "scope": scope,
        "blocked_by": blocked_by,
        "land_commit": land_commit,
    }


# frob:doc docs/guides/coordinator-scripts.md#ticket_frontmatter_on_main
# frob:ticket T-2133
# frob:ticket T-2449
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain.test_reads_state_\
# and_scope
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain.test_missing_tick\
# et_returns_none
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain.test_falls_back_t\
# o_archive_when_active_ledger_has_no_such_ticket
def ticket_frontmatter_on_main(ticket_id: str) -> dict | None:
    """`{"state": ..., "scope": [...], "blocked_by": [...], "land_commit":
    ...}` parsed from `main:tickets/<id>/ticket.md`'s YAML frontmatter,
    falling back to
    `main:tickets/archive/<id>/ticket.md` (T-2449) when the active path
    resolves to nothing, or `None` if the ticket exists in NEITHER
    location. T-2449's own measured incident: a ticket whose blockers had
    been completed AND ARCHIVED read as permanently blocked forever --
    this function used to only ever look in the active ledger directory,
    so a completed-and-archived blocker was indistinguishable from a
    missing one, and `_open_blocker_ids` resolved that ambiguity as
    'still blocking'. `frob.tickets.load_queue` (the real ledger resolver,
    pinned by `tests/test_ticket_land.py::TestArchiveV2::
    test_archived_v2_ticket_still_resolves_as_blocker`) already merges
    both locations -- this mirrors that exact two-location resolution
    order in plain form rather than `import frob` (this script's own 'no
    frob import' module-docstring contract, load-bearing: the script must
    stay usable under any `python3` on PATH, not just this project's own
    built venv/editable install -- verified via `scripts/
    _require_python.py`'s own module docstring, which requires this
    script run correctly even under an interpreter far older than what
    `frob` itself needs).

    T-2133's own incident: a coordinator read `main:tickets/<id>/
    ticket.md`'s scope twice believing it was the ticket's LIVE scope,
    when the authoritative live value (if a lease is held) is the lease
    record's own `scope` field, which can have diverged via `frob ticket
    scope` inside a worktree that has not landed yet -- this function
    reads the STATIC, main-committed side of that comparison;
    `ticket_readiness` below is what actually compares the two.

    T-2196: `blocked_by` is read here (not just `state`/`scope`) so
    `ticket_readiness` can factor open blockers into its `dispatchable`
    verdict -- previously this function never even looked at the field,
    so a blocked ticket's own edges were invisible to the readiness
    check no matter what."""
    text = _git(["show", f"main:tickets/{ticket_id}/ticket.md"], REPO)
    if not text:
        text = _git(["show", f"main:tickets/archive/{ticket_id}/ticket.md"], REPO)
    if not text:
        return None
    return _parse_ticket_frontmatter_text(text)


# frob:doc docs/guides/coordinator-scripts.md#lease-classification-constants
# frob:ticket T-2222
#: Mirrors `frob.tickets._leases.LEASE_TTL_SECONDS` (6 hours) exactly --
#: duplicated here in plain form rather than imported (this script's own
#: "no `frob` import" contract, module docstring / T-2222's own scope
#: note) so a lease's own age is judged by the SAME horizon the authoritative
#: `frob.tickets._leases.is_lease_ttl_expired` uses, not a second, silently
#: divergent threshold.
_LEASE_TTL_SECONDS = 6 * 60 * 60


# frob:doc docs/guides/coordinator-scripts.md#_lease_age_seconds
# frob:ticket T-2222
def _lease_age_seconds(record: dict, *, now: datetime | None = None) -> float | None:
    """Seconds elapsed since `record["recorded_at"]`, or `None` if that
    field is missing/unparseable as ISO-8601 (defensive -- a lease file is
    peer-writable, T-0780, mirroring `frob.tickets._leases.lease_age_
    seconds`'s own contract exactly). `now` is injectable for tests."""
    recorded_at = record.get("recorded_at")
    if not isinstance(recorded_at, str):
        return None
    try:
        recorded = datetime.fromisoformat(recorded_at)
    except ValueError:
        return None
    if recorded.tzinfo is None:
        recorded = recorded.replace(tzinfo=UTC)
    current = now if now is not None else datetime.now(UTC)
    return (current - recorded).total_seconds()


# frob:doc docs/guides/coordinator-scripts.md#_scan_for_live_worktree_process
# frob:ticket T-2222
def _scan_for_live_worktree_process(
    path: Path, proc: Path = Path("/proc")
) -> int | None:
    """The first live pid whose `/proc/<pid>/cwd` resolves to `path`, or
    `None` if none does -- mirrors `frob.tickets._leases.scan_for_live_
    worktree_process`'s own `/proc` walk exactly (same primitive
    `land_lock_holder_pids` above already uses for a different question,
    'who holds `land.lock` open' vs this function's 'is anything cwd'd
    into this worktree'). `/proc` missing, an unreadable pid, or simply no
    match all return `None`, never a refusal by themselves -- an inability
    to scan must never itself become 'proven dead' (same posture as the
    authoritative implementation this mirrors)."""
    if not proc.is_dir():
        return None
    try:
        resolved = path.resolve()
    except OSError:
        return None
    try:
        entries = list(proc.iterdir())
    except OSError:
        return None
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            cwd = Path(os.readlink(f"/proc/{entry.name}/cwd")).resolve()
        except OSError:
            continue
        if cwd == resolved:
            return int(entry.name)
    return None


# frob:doc docs/guides/coordinator-scripts.md#lease_classification
# frob:ticket T-2222
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLeaseClassification.test_live_lease_stays\
# _live
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLeaseClassification.test_holder_dead_is_r\
# eclaimable
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLeaseClassification.test_ticket_terminal_\
# is_reclaimable
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLeaseClassification.test_path_gone_is_rec\
# laimable
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLeaseClassification.test_root_worktree_is\
# _structurally_unreclaimable
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLeaseClassification.test_classification_i\
# s_strictly_read_only
def lease_classification(record: dict) -> str:
    """T-2222: classify one held lease record as `"live"`, `"reclaimable"`,
    or `"root-resident"` -- the missing distinction `leases()` never made,
    which let a raw file COUNT read as a live-agent count (measured: 6
    leases, only 4 live agents; T-1382 was reclaimable via holder-dead,
    T-1686 is a permanent root-resident residue, T-2007's own accepted-
    permanent-residue finding).

    Mirrors `frob.tickets._leases.lease_staleness_reason`'s own ordering
    (path-gone/ticket-gone/ticket-terminal/holder-dead -> reclaimable),
    checked cheapest-first, duplicated here in plain form rather than
    imported per this script's "no `frob` import" contract, plus one
    addition (acceptance [3]): a `worktree` that resolves to THIS repo's
    own root reports `"root-resident"`, derived from comparing the
    record's own field against the resolved repo root, NEVER a ticket-id
    allowlist -- a live shell is routinely cwd'd into the shared root
    (T-1686: 53 processes at once), so the ordinary liveness scan would
    read it as permanently live; it is never reclaimable but also never
    counted as a real dispatched AGENT. `"live"` is everything else, and
    is the ONLY bucket a concurrency count should be computed from
    (acceptance [2])."""
    worktree = record.get("worktree", "")
    wt_path = Path(worktree) if worktree else None
    if wt_path is None or not wt_path.exists():
        return "reclaimable"  # path-gone

    ticket_id = record.get("ticket_id", "")
    main_info = ticket_frontmatter_on_main(ticket_id) if ticket_id else None
    if main_info is None:
        return "reclaimable"  # ticket-gone
    if main_info["state"] in ("done", "dropped"):
        return "reclaimable"  # ticket-terminal

    try:
        is_root = wt_path.resolve() == REPO.resolve()
    except OSError:
        is_root = False
    if is_root:
        return "root-resident"

    age = _lease_age_seconds(record)
    if (
        age is not None
        and age > _LEASE_TTL_SECONDS
        and _scan_for_live_worktree_process(wt_path) is None
    ):
        return "reclaimable"  # holder-dead

    return "live"


# frob:doc docs/guides/coordinator-scripts.md#live_lease_count
# frob:ticket T-2222
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLeaseClassification.test_live_lease_stays\
# _live
def live_lease_count(held: Sequence[dict]) -> int:
    """How many of `held` (`leases()`'s own records) classify as `"live"`
    (`lease_classification`) -- the number a concurrency GUIDANCE clause
    must be computed from, never `len(held)` (T-2222 acceptance [2]:
    `leases()`'s raw count silently includes reclaimable and root-resident
    entries, which is exactly how '6 leases' read as '4 live agents' in
    the measured incident this ticket fixes)."""
    return sum(1 for record in held if lease_classification(record) == "live")


# frob:doc docs/guides/coordinator-scripts.md#_matches_any_scope_glob
# frob:ticket T-2179
def _matches_any_scope_glob(path: str, scope_globs: Sequence[str]) -> bool:
    """Whether `path` matches any of `scope_globs` -- `fnmatch.fnmatch`,
    the same glob semantics `frob ticket scope`'s own globs use (a `*`/`**`
    pattern, not a regex)."""
    return any(fnmatch.fnmatch(path, glob) for glob in scope_globs)


# frob:doc docs/guides/coordinator-scripts.md#worktrees_touching_ticket
# frob:ticket T-2133
# frob:ticket T-2179
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket.test_finds_a_bran\
# ch_with_unlanded_commits
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket.test_empty_when_n\
# othing_touches_it
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket.test_ledger_only_\
# churn_is_not_reported
def worktrees_touching_ticket(ticket_id: str, scope_globs: Sequence[str]) -> list[str]:
    """Names of live worktrees whose branch carries an unlanded commit
    that, in that SAME commit's own diff, BOTH (a) touches
    `tickets/<id>/` (correlates the commit to this ticket at all) AND (b)
    touches at least one file matching `scope_globs` (the ticket's own
    declared scope) -- genuine implementation evidence, not merely a
    ledger edit that happens to share a branch history with unrelated
    scope-touching commits.

    T-2172 follow-up (the coordinator's own incident): the original
    version reported ANY worktree with a `tickets/<id>/`-touching commit
    as "already implemented" -- `--ticket T-2114` printed SEVEN branches
    (t-2071, t-2099, t-2105, t-2107, t-2109, t-2110, t2049-series), none
    of which had implemented T-2114 at all. T-2114 briefly collided with a
    different ticket id before being renumbered to T-2140, so every one of
    those branches had touched `tickets/T-2114/ticket.md` purely as
    collision-recovery renumbering churn -- never the ticket's own scope.
    T-2179 narrowed this from "any commit touches the ticket dir" AND
    "the WHOLE branch diff touches scope" to the same two conditions
    checked at the WHOLE-BRANCH level, which fixed the T-2114 case but
    left a second false-positive shape open (T-2181, this ticket's own
    residue): whole-branch correlation still credits a branch whose
    ticket-dir-touching commit and its scope-touching commit are two
    DIFFERENT commits for two DIFFERENT tickets that merely happen to
    share a branch -- measured for real, `--ticket T-2114` reported
    `t-2107` and `t2049-series`, which each touched
    `src/frob/app/ticket_runner/_land_cmd.py` for their OWN ticket
    (T-2108, T-2049) in a commit that never touches `tickets/T-2114/` at
    all, alongside a SEPARATE bookkeeping commit that touches
    `tickets/T-2114/` (e.g. a `blocked_by`/renumbering edit) and never
    touches `_land_cmd.py`. Whole-branch overlap of the two conditions is
    exactly file-overlap reasoning at branch granularity -- correlation
    now happens PER COMMIT (`git show --name-only` on each commit that
    itself touches `tickets/<id>/`) so a commit must carry BOTH signals
    together to count as evidence, never two unrelated commits stitched
    together by sharing a branch.

    An empty `scope_globs` (ticket not on `main` yet, or `main` records no
    scope at all) can never satisfy condition (b), so it always reports
    empty rather than falling back to the old any-`tickets/<id>/`-commit
    behavior -- "no known scope to check against" must read as "cannot
    confirm implementation", not as "implementation confirmed"."""
    if not WORKTREES.is_dir() or not scope_globs:
        return []
    hits = []
    for path in sorted(p for p in WORKTREES.iterdir() if p.is_dir()):
        ticket_touch = _git(
            ["log", "main..HEAD", "--format=%H", "--", f"tickets/{ticket_id}/"],
            path,
        )
        commit_shas = [
            line.strip() for line in ticket_touch.splitlines() if line.strip()
        ]
        for sha in commit_shas:
            commit_diff = _git(["show", "--name-only", "--format=", sha], path)
            touched_files = commit_diff.splitlines()
            if any(_matches_any_scope_glob(f, scope_globs) for f in touched_files):
                hits.append(path.name)
                break
    return hits


# frob:doc docs/guides/coordinator-scripts.md#ticket_readiness
# frob:ticket T-2133
# frob:ticket T-2179
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestTicketReadiness.test_dispatchable_when_no\
# _lease_no_commits_no_divergence
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestTicketReadiness.test_not_dispatchable_whe\
# n_a_live_lease_exists
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestTicketReadiness.test_not_dispatchable_whe\
# n_another_branch_already_has_commits
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestTicketReadiness.test_flags_scope_divergen\
# ce_between_the_live_lease_and_main


# frob:doc docs/guides/coordinator-scripts.md#_classify_blockers
# frob:ticket T-2449
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestClassifyBlockers.test_done_blocker_is_clo\
# sed
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestClassifyBlockers.test_archived_done_block\
# er_is_closed
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestClassifyBlockers.test_in_progress_blocker\
# _is_open
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestClassifyBlockers.test_missing_blocker_is_\
# unresolved_not_open
def _classify_blockers(blocked_by: Sequence[str]) -> tuple[list[str], list[str]]:
    """`(open_ids, unresolved_ids)` -- T-2449's replacement for the old
    `_open_blocker_ids`, which collapsed two distinct facts into one
    'still open' bucket: a blocker whose id resolves to a real, non-
    terminal ticket (genuinely OPEN, must keep blocking dispatch) and a
    blocker id that resolves NOWHERE -- neither the active ledger nor
    `tickets/archive/**` (UNRESOLVED: a typo, a blocker cited before it
    was ever filed, or -- before this ticket's `ticket_frontmatter_on_
    main` archive fallback -- a completed-and-archived blocker
    misdiagnosed as missing). Fail-loudly (T-2391): an unresolved id is
    UNMEASURED, not blocked -- it is reported in its own list rather than
    silently merged into `open_ids`, even though (acceptance [2]'s own
    wording is about REPORTING, not about safety) the caller still
    treats a non-empty `unresolved_ids` as dispatch-blocking, same as
    `open_ids` -- 'cannot confirm this blocker is resolved' must never
    be read as 'resolved'."""
    open_ids: list[str] = []
    unresolved_ids: list[str] = []
    for blocker_id in blocked_by:
        blocker_info = ticket_frontmatter_on_main(blocker_id)
        if blocker_info is None:
            unresolved_ids.append(blocker_id)
            continue
        if blocker_info["state"] not in ("done", "dropped"):
            open_ids.append(blocker_id)
    return open_ids, unresolved_ids


# frob:doc docs/guides/coordinator-scripts.md#_expand_scope_globs_to_paths
# frob:ticket T-2225
def _expand_scope_globs_to_paths(root: Path, globs: Sequence[str]) -> set[Path]:
    """Expand `globs` (scope glob patterns, e.g. `src/frob/**`) against
    the REAL filesystem under `root`, returning the resolved absolute
    path of every matched FILE -- T-2225's own fix for the "compare
    scopes as strings" defect shape: a live lease on `src/frob/tickets/
    _land.py` collides with a scope entry of `src/frob/**`, and no
    lexical/substring comparison of those two texts detects that (the
    glob has to be walked against real files to know what it covers).
    `root.glob(pattern)` (pathlib, supports `**` recursive segments)
    handles both a literal path glob (matches at most one file) and a
    wildcard one; a pattern that cannot be globbed at all (leading `/`,
    invalid syntax) is skipped rather than raising -- a best-effort scope
    expansion, matching this script's existing fail-quiet posture. A
    pattern ending in a bare `**` (a common scope-writing shape, e.g.
    `src/frob/**`) also tries `<pattern>/*` -- pathlib's own `**` semantics
    match every directory recursively but NOT the files inside the
    deepest one unless a further segment follows it (verified: `Path.
    glob('src/frob/**')` alone returns directories only), so the bare
    form would silently expand to zero files without this."""
    paths: set[Path] = set()
    patterns_to_try = set()
    for pattern in globs:
        patterns_to_try.add(pattern)
        if pattern.endswith("**"):
            patterns_to_try.add(f"{pattern}/*")
    for pattern in patterns_to_try:
        try:
            matches = root.glob(pattern)
        except (OSError, ValueError, NotImplementedError):
            continue
        for match in matches:
            if match.is_file():
                paths.add(match.resolve())
    return paths


# frob:doc docs/guides/coordinator-scripts.md#_land_ticket_collisions
# frob:ticket T-2281
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions.test_land_in_progres\
# s_ticket_with_no_lease_still_collides
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions.test_land_ticket_dis\
# joint_scope_is_not_a_collision
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions.test_land_ticket_id_\
# matching_a_live_lease_is_not_double_reported
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions.test_the_ticket_s_ow\
# n_id_in_land_ticket_ids_is_never_self_collision
def _land_ticket_collisions(
    my_files: set[Path],
    land_ticket_ids: Sequence[str],
    exclude_ids: set[str],
) -> list[dict]:
    """`scope_lease_collisions`'s T-2281 half: which of `land_ticket_ids`
    (`land_invocations()`'s own ticket ids -- a live process genuinely
    landing that ticket right now) collide with `my_files`, EXCLUDING
    `exclude_ids` (ids already reported via a live lease -- checked at
    more precise, lease-recorded scope, never double-counted here). Each
    id's scope is read from `main` since no lease exists to read it from
    during this window -- see `scope_lease_collisions`'s own docstring
    for the incident this closes."""
    collisions: list[dict] = []
    for other_id in land_ticket_ids:
        if other_id in exclude_ids:
            continue
        other_main = ticket_frontmatter_on_main(other_id)
        if other_main is None:
            continue
        other_files = _expand_scope_globs_to_paths(REPO, other_main.get("scope", []))
        overlap = my_files & other_files
        if overlap:
            collisions.append({"ticket_id": other_id, "paths": overlap})
    return collisions


# frob:doc docs/guides/coordinator-scripts.md#scope_lease_collisions
# frob:ticket T-2225
# frob:ticket T-2281
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions.test_glob_scope_coll\
# ides_with_a_literal_lease_file
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions.test_no_collision_wh\
# en_files_are_disjoint
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestScopeLeaseCollisions.test_a_reclaimable_l\
# ease_is_never_a_collision
def scope_lease_collisions(
    ticket_id: str,
    effective_scope: Sequence[str],
    held: Sequence[dict],
    land_ticket_ids: Sequence[str] = (),
) -> list[dict]:
    """T-2225: which OTHER held leases collide with `effective_scope` (a
    ticket's own scope globs) at the RESOLVED-FILE level, restricted to
    leases `lease_classification` (T-2222, reused here rather than
    re-implemented) calls `"live"` -- a reclaimable or root-resident
    lease is not actually held by anyone and must never count as a
    collision (acceptance [4]). Both sides are expanded via `_expand_
    scope_globs_to_paths` and intersected as concrete file paths, never
    compared as glob TEXT -- the measured incident this fixes: a scope of
    `src/frob/**` and a live lease's own scope of `src/frob/tickets/
    _land.py` are lexically unrelated strings but genuinely overlapping
    file sets.

    T-2281: `land_ticket_ids` (`_land_ticket_collisions`, own docstring
    has the full incident/rationale) is a SECOND, independent occupancy
    source -- `held` (`leases()`) alone is BLIND to the window between a
    land's local worktree close and its squash reaching the primary
    checkout, during which a ticket whose files are genuinely still
    contended holds no lease at all.

    Returns one dict per colliding OTHER ticket:
    `{"ticket_id": ..., "paths": [str, ...]}` (sorted, deduplicated) --
    `[]` means no collision (the must-still-pass case)."""
    my_files = _expand_scope_globs_to_paths(REPO, effective_scope)
    if not my_files:
        return []
    collisions: list[dict] = []
    seen_ids: set[str] = set()
    for record in held:
        other_id = record.get("ticket_id")
        if other_id is None or other_id == ticket_id:
            continue
        if lease_classification(record) != "live":
            continue
        other_files = _expand_scope_globs_to_paths(REPO, record.get("scope", []))
        overlap = my_files & other_files
        if overlap:
            collisions.append({"ticket_id": other_id, "paths": overlap})
            seen_ids.add(other_id)
    collisions.extend(
        _land_ticket_collisions(my_files, land_ticket_ids, seen_ids | {ticket_id})
    )
    # PERF004: sort each collision's paths once, outside the per-lease loop
    # above, rather than calling sorted() per iteration inside it.
    for collision in collisions:
        # frob:waive PERF004 reason="paths is this collision's own distinct overlap \
        # set (a different ticket's file intersection each iteration), not a shared \
        # collection re-sorted identically across iterations -- same posture as every \
        # other per-key-distinct-set PERF004 waiver in this codebase"
        collision["paths"] = sorted(str(p) for p in collision["paths"])
    return collisions


# frob:doc docs/guides/coordinator-scripts.md#_scope_diverges_from_lease
# frob:ticket T-2196
# frob:ticket T-2213
def _scope_diverges_from_lease(
    lease: dict | None, main_scope: list[str] | None
) -> bool:
    """`True` when a live `lease` exists AND its `scope` differs from
    `main_scope` (`main`'s declared scope) -- T-2133's own "single
    highest-value signal": a coordinator reading `main:tickets/<id>/
    ticket.md` alone, while a lease has since narrowed (or widened) the
    real working scope inside a worktree, draws a stale conclusion about
    what the ticket actually touches (observed twice: once nearly
    releasing a healthy lease, once asking an agent to redo a narrowing
    it had already done)."""
    return (
        lease is not None
        and main_scope is not None
        and set(lease.get("scope", [])) != set(main_scope)
    )


# frob:doc docs/guides/coordinator-scripts.md#_ticket_dispatchable
# frob:ticket T-2196
# frob:ticket T-2213
def _ticket_dispatchable(
    *,
    main_exists: bool,
    lease: dict | None,
    worktrees_with_commits: list[str],
    state_on_main: str | None,
    open_blockers: list[str],
    unresolved_blockers: list[str],
    scope_diverges: bool,
    scope_collisions: list[dict],
) -> bool:
    """T-2196 fixed the defect class this predicate embodies -- "the
    report knows more than the verdict uses". Every fact `ticket_
    readiness` measures gates the verdict here, not a subset:
    `main_exists` (a ticket absent from `main` is never dispatchable, no
    matter how clean everything else looks -- the T-2195 incident T-2196
    was filed from: a coordinator dispatched an agent to a ticket id that
    did not exist on `main` yet, and the old verdict endorsed it), no
    live `lease` may be held, no sibling worktree may already carry
    scope-matching commits, `state_on_main` must not be
    `done`/`dropped`/`in-progress`, `open_blockers` must be empty,
    `scope_diverges` must be `False`, and (T-2225) `scope_collisions`
    must be empty. `True` only when every one of those checks passes.

    T-2449: `unresolved_blockers` (a blocker id that resolves NOWHERE,
    `_classify_blockers`'s own second list) must ALSO be empty -- 'cannot
    confirm this blocker is resolved' is never treated as 'safe to
    dispatch', the same conservative posture `open_blockers` already
    enforces, just reported under a distinct name (acceptance [2]) rather
    than silently merged into it."""
    return (
        main_exists
        and lease is None
        and not worktrees_with_commits
        and state_on_main not in ("done", "dropped", "in-progress")
        and not open_blockers
        and not unresolved_blockers
        and not scope_diverges
        and not scope_collisions
    )


# frob:doc docs/guides/coordinator-scripts.md#ticket_readiness
# frob:ticket T-2196
# frob:ticket T-2213
def ticket_readiness(ticket_id: str) -> dict:
    """T-2133's single per-ticket answer to "given T-####, is it actually
    dispatchable?" -- combines `ticket_lease`, `ticket_frontmatter_on_main`,
    `worktrees_touching_ticket`, `_classify_blockers`, and
    `scope_lease_collisions` into one dict, gathering the distinct
    questions those functions already answer independently: is it leased
    (`lease`), does it exist on `main` and in what state (`main`), does
    the live lease's scope diverge from `main`'s declared scope
    (`scope_diverges`, via `_scope_diverges_from_lease`), has a sibling
    branch already implemented it (`worktrees_with_commits`), is it
    blocked (`open_blockers`, T-2449: plus `unresolved_blockers`, reported
    distinctly from a genuinely open one), and does another live lease's
    scope collide with this one's (`scope_lease_collisions`, T-2225). The
    `dispatchable` verdict (`_ticket_dispatchable`) is the ONLY field
    that combines these facts; see its own docstring for exactly which
    combination it requires. T-2213 (ARCH001 split): this function stays
    the thin orchestrator that gathers the facts and calls the two
    extracted predicates above -- see them for the actual decision logic
    each answers."""
    lease = ticket_lease(ticket_id)
    main_info = ticket_frontmatter_on_main(ticket_id)
    main_scope = main_info["scope"] if main_info is not None else None
    scope_diverges = _scope_diverges_from_lease(lease, main_scope)
    # T-draft-05563e8d: the LIVE scope (lease, if held) is what a real
    # implementation commit would actually touch -- mirrors the "trust
    # the lease, not the ticket file" rule `scope_diverges` already
    # established, applied here to the implementation-evidence check too.
    effective_scope = lease.get("scope", []) if lease is not None else main_scope
    worktrees_with_commits = worktrees_touching_ticket(ticket_id, effective_scope or ())
    state_on_main = main_info["state"] if main_info is not None else None
    open_blockers, unresolved_blockers = (
        _classify_blockers(main_info.get("blocked_by", []))
        if main_info is not None
        else ([], [])
    )
    scope_collisions = scope_lease_collisions(
        ticket_id,
        effective_scope or (),
        leases(),
        [inv["ticket_id"] for inv in land_invocations()],
    )
    dispatchable = _ticket_dispatchable(
        main_exists=main_info is not None,
        lease=lease,
        worktrees_with_commits=worktrees_with_commits,
        state_on_main=state_on_main,
        open_blockers=open_blockers,
        unresolved_blockers=unresolved_blockers,
        scope_diverges=scope_diverges,
        scope_collisions=scope_collisions,
    )
    return {
        "ticket_id": ticket_id,
        "lease": lease,
        "main": main_info,
        "scope_diverges": scope_diverges,
        "worktrees_with_commits": worktrees_with_commits,
        "open_blockers": open_blockers,
        "unresolved_blockers": unresolved_blockers,
        "scope_lease_collisions": scope_collisions,
        "dispatchable": dispatchable,
    }


# frob:doc docs/guides/coordinator-scripts.md#effective_scope
# frob:ticket T-2180
def _effective_scope(readiness: dict) -> list[str]:
    """The scope glob list a ticket is ACTUALLY working under right now:
    its live lease's `scope` if a lease is held (mirrors `ticket_
    readiness`'s own "trust the lease, not the ticket file" rule), else
    `main`'s declared scope, else `[]` when the ticket does not exist on
    `main` at all. Shared by `scope_intersections` below so a pairwise
    comparison never accidentally compares a stale `main`-only scope
    against a sibling's live, narrowed-in-worktree one."""
    lease = readiness["lease"]
    if lease is not None:
        return list(lease.get("scope", []))
    main_info = readiness["main"]
    if main_info is not None:
        return list(main_info["scope"])
    return []


# frob:doc docs/guides/coordinator-scripts.md#_globs_overlap
# frob:ticket T-2180
def _globs_overlap(a: str, b: str) -> bool:
    """Whether two scope globs can ever match the same path -- exact
    equality, or one side being a LITERAL path (no `*`/`?`/`[` wildcard
    character) that the other side's glob matches via `fnmatch.fnmatch`.
    Not a general glob-intersection solver (two genuinely different
    wildcard patterns with no literal side are reported as non-
    overlapping even if some path could satisfy both) -- deliberately
    conservative, matching the shapes `frob ticket scope` actually writes
    (mostly literal paths, occasionally a `dir/*` prefix): never CLAIMS
    an overlap it cannot demonstrate, so a report from this function is
    always real evidence, never a guess."""
    if a == b:
        return True
    wildcard_chars = set("*?[")
    if not (set(a) & wildcard_chars) and fnmatch.fnmatch(a, b):
        return True
    if not (set(b) & wildcard_chars) and fnmatch.fnmatch(b, a):
        return True
    return False


# frob:doc docs/guides/coordinator-scripts.md#scope_intersections
# frob:ticket T-2180
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestScopeIntersections.test_reports_overlappi\
# ng_pair
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestScopeIntersections.test_no_overlap_report\
# s_empty
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestScopeIntersections.test_checks_against_a_\
# held_lease_outside_the_requested_set
def scope_intersections(ticket_ids: Sequence[str]) -> list[dict]:
    """PAIRWISE scope-glob intersection across every id in `ticket_ids`,
    using each ticket's EFFECTIVE scope (`_effective_scope`) -- compared
    as resolved glob patterns via `_globs_overlap`, never ticket titles
    or file-name similarity, which is exactly the reasoning `worktrees_
    touching_ticket`'s own T-2181 fix just rejected at the file level.
    Also checks each requested id's effective scope against every
    currently held lease NOT already in `ticket_ids`, so a coordinator
    vetting a wave for internal contention sees external contention
    against an already in-flight lease too.

    Measured need: a five-ticket docs series all scoped to
    `docs/modules/tickets.md`, then T-1748 and T-1780 both claiming that
    same file -- the second collision hard-refused T-1780 at `start` via
    `_refuse_on_scope_lease_collision`, with no `--steal` override, after
    the dispatch had already happened. This function exists to make that
    check BEFORE dispatch, not after a wasted `ticket start`.

    Returns one dict per colliding pair: `{"a": id, "b": id,
    "overlapping_globs": [(glob_a, glob_b), ...]}` -- an empty list means
    no pairwise or lease-external contention was found."""
    readiness = {tid: ticket_readiness(tid) for tid in ticket_ids}
    scopes = {tid: _effective_scope(r) for tid, r in readiness.items()}

    collisions: list[dict] = []
    ids = list(ticket_ids)
    requested_ids = set(ids)  # O(1) membership below, not a per-lease linear scan
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            overlaps = [
                (ga, gb)
                for ga in scopes[a]
                for gb in scopes[b]
                if _globs_overlap(ga, gb)
            ]
            if overlaps:
                collisions.append({"a": a, "b": b, "overlapping_globs": overlaps})

    held = leases()
    for tid in ids:
        for record in held:
            other_id = record.get("ticket_id")
            # frob:waive PERF003 reason="bounded by the number of ids passed on the \
            # CLI (a wave dispatch, single digits) times the number of currently held \
            # leases (this repo's own fleet size, never scale-sensitive) -- not a \
            # cross join over a large or growing collection"
            if other_id is None or other_id == tid or other_id in requested_ids:
                continue
            overlaps = [
                (ga, gb)
                for ga in scopes[tid]
                for gb in record.get("scope", [])
                if _globs_overlap(ga, gb)
            ]
            if overlaps:
                collisions.append(
                    {"a": tid, "b": other_id, "overlapping_globs": overlaps}
                )
    return collisions


# frob:doc docs/guides/coordinator-scripts.md#_parse_ps_cpu_time
# frob:ticket T-2180
def _parse_ps_cpu_time(value: str) -> int:
    """Parse `ps`'s own TIME column (`[[dd-]hh:]mm:ss`) into total whole
    seconds. Returns 0 on anything unparseable rather than raising --
    this feeds a best-effort fleet report, not a gate."""
    try:
        days = 0
        rest = value
        if "-" in value:
            days_s, rest = value.split("-", 1)
            days = int(days_s)
        parts = [int(p) for p in rest.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0)
        hours, minutes, seconds = parts[-3:]
        return days * 86400 + hours * 3600 + minutes * 60 + seconds
    except (ValueError, IndexError):
        return 0


#: Matches the ticket id in a real `frob ticket land T-#### ...`
#: invocation -- the id is a POSITIONAL argument immediately after
#: `land` (confirmed against `frob ticket land`'s own argparse usage:
#: `id` is a bare positional, there is no `--ticket` flag on this
#: subcommand at all -- an earlier version of this regex looked for
#: `--ticket T-####` and matched NOTHING against real land invocations,
#: which collapsed every row to `ticket_id=None` and made the whole
#: fan-out-collapse fix inert: a coordinator measured 13 reported rows
#: for ONE real land, the exact 4x-style inflation this ticket exists to
#: eliminate). `--ticket[= ]` is kept as a fallback for any other
#: `frob ...` invocation shape that does use a flag.
_LAND_ARGV_TICKET_RE = re.compile(
    r"\bticket\s+land\s+([A-Za-z]+-\d+)\b|--ticket[= ]+([A-Za-z]+-\d+)\b"
)


def _parse_land_argv_ticket_id(argv: str) -> str | None:
    """Extract the ticket id from a `land_process_rows` argv string via
    `_LAND_ARGV_TICKET_RE`'s two alternatives (positional first, `--ticket`
    flag second), returning whichever group matched, or `None` if
    neither did."""
    match = _LAND_ARGV_TICKET_RE.search(argv)
    if match is None:
        return None
    return match.group(1) or match.group(2)


# frob:doc docs/guides/coordinator-scripts.md#land_process_rows
# frob:ticket T-2475
#: `/proc/<pid>/cmdline`'s NUL-delimited token pair identifying a REAL
#: `... ticket land ...` invocation -- `ticket` and `land` as two
#: SEPARATE argv elements, mirroring `_FROB_CHECK_TOKEN_RE`/
#: `_CHECK_TOKEN_RE`'s own token-not-substring contract below (T-2473).
#: This is the structural check `_LAND_ARGV_TICKET_RE`'s text-substring
#: match cannot make: a coordinator's own wait-loop shell running
#: `pgrep -f "frob ticket land T-2408"` has `ticket` and `land` GLUED
#: inside one single argv element (the quoted pattern string handed to
#: `-f`), never as two adjacent elements -- `ps -eo args`'s space-joined
#: text renders both shapes identically, which is exactly why the
#: text-only match misclassified the watcher as the land itself.
_LAND_CMDLINE_TOKEN_RE = re.compile(rb"\x00ticket\x00land\x00")


# frob:doc docs/guides/coordinator-scripts.md#land_process_rows
# frob:ticket T-2475
def _pid_has_land_argv_tokens(pid: int, proc: Path = Path("/proc")) -> bool | None:
    """`True`/`False` if `pid`'s `/proc/<pid>/cmdline` structurally DOES
    or DOES NOT contain `ticket`/`land` as two separate, adjacent argv
    elements (`_LAND_CMDLINE_TOKEN_RE`) -- `None` if the cmdline could
    not be read (pid already exited, `/proc` unavailable/unreadable),
    which the caller must treat as 'cannot confirm', never as 'confirmed
    absent' (fail-loudly, T-2391) -- `land_process_rows` falls back to
    its own text-substring verdict in that case rather than silently
    dropping a row it cannot structurally re-check."""
    try:
        raw = (proc / str(pid) / "cmdline").read_bytes()
    except OSError:
        return None
    if not raw.startswith(b"\x00"):
        raw = b"\x00" + raw
    if not raw.endswith(b"\x00"):
        raw += b"\x00"
    return _LAND_CMDLINE_TOKEN_RE.search(raw) is not None


# frob:doc docs/guides/coordinator-scripts.md#land_process_rows
# frob:ticket T-2180
# frob:ticket T-2475
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLandProcessRows.test_parses_matching_rows\
# _and_skips_others
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLandProcessRows.test_watcher_pgrep_patter\
# n_is_not_counted_as_a_land
def land_process_rows(proc: Path = Path("/proc")) -> list[dict]:
    """Every live process whose argv contains a `ticket land` invocation,
    parsed from `ps -eo pid,etimes,time,args`'s own structured columns:
    pid, elapsed seconds, cumulative CPU time (raw `ps` TIME string), and
    the full argv. This is the raw per-PROCESS table a single real `frob
    ticket land` fans out across -- the bash wrapper, `timeout`, `uv
    run`, and the actual python process, section 13 of the agent
    playbook's own T-1344 measurement puts this at roughly 4 rows per
    land. `land_invocations` below collapses these rows to distinct
    invocations; counting ROWS here as invocations is exactly the
    overcounting bug this ticket exists to fix (two agents independently
    reported '15-16 concurrent lands' when there were 4).

    T-2475: `ps -eo args`'s own text is a space-JOINED rendering that
    cannot tell a real invocation (`ticket`/`land` as two separate argv
    elements) from a process whose command line merely CONTAINS that
    text glued inside ONE argv element -- e.g. a coordinator's own
    wait-loop shell running `pgrep -f "frob ticket land T-2408"` reads
    identically to a real land in `ps -eo args` text, and was measured
    misclassified as a live land (elapsed=306s, cpu=0s -- the watcher,
    not the work) while the real land had already finished. Every row
    that passes the initial cheap text pre-filter is now RE-VERIFIED
    structurally against `/proc/<pid>/cmdline`'s own NUL-delimited argv
    (`_pid_has_land_argv_tokens`) before being kept; a row whose
    structural check comes back `False` (glued substring, not a real
    invocation) is dropped here, before `land_invocations` ever sees it.
    A row whose pid could not be re-read (`None` -- already exited, or
    `/proc` unavailable on this host) is kept on the strength of the
    text pre-filter alone, matching this function's pre-T-2475 behavior
    exactly in the case it cannot improve on -- 'cannot confirm' is
    never treated as 'confirmed a false positive' (fail-loudly, T-2391).

    Known residual limitation (playbook section 13, narrowed by T-2475):
    a row whose ticket id cannot be parsed from its argv
    (`_parse_land_argv_ticket_id` returns `None`) is still dropped by
    `land_invocations`, not reported (T-2193) -- this row-level function
    still returns everything it can structurally confirm (or cannot
    disconfirm); the id-parse filtering happens one layer up. A caller
    auditing raw process-table rows directly (bypassing `land_
    invocations`'s own filtering) still sees whatever survives here."""
    try:
        done = subprocess.run(
            ["ps", "-eo", "pid,etimes,time,args"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if done.returncode != 0:
        return []
    rows = []
    for line in done.stdout.splitlines()[1:]:
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid_s, etimes_s, cputime_s, argv = parts
        if not re.search(r"\bticket\s+land\b", argv):
            continue
        try:
            pid = int(pid_s)
            etimes = int(etimes_s)
        except ValueError:
            continue
        # T-2475: a structural `False` (glued substring inside one argv
        # element, e.g. a `pgrep -f "... ticket land ..."` watcher) drops
        # the row here; `None` (cannot re-confirm) or `True` both keep it.
        if _pid_has_land_argv_tokens(pid, proc) is False:
            continue
        rows.append({"pid": pid, "etimes": etimes, "cputime": cputime_s, "argv": argv})
    return rows


# frob:doc docs/guides/coordinator-scripts.md#_all_process_ppid_cpu
def _all_process_ppid_cpu() -> dict[int, tuple[int, int]]:
    """`{pid: (ppid, cpu_seconds)}` for every live process, ONE `ps -eo
    pid,ppid,time` call -- the snapshot `_descendant_cpu_seconds` builds
    a child-lookup table from, so summing a land's whole process tree
    costs one extra `ps` invocation total, never one per descendant.
    Structured columns only, matching this file's existing `ps -eo
    pid,etimes,time,args` usage in `land_process_rows` -- never a text
    line-count (`ps aux | grep -c ...`), the class of bug that already
    produced a 4x land-count miscount here once."""
    try:
        done = subprocess.run(
            ["ps", "-eo", "pid,ppid,time"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if done.returncode != 0:
        return {}
    table: dict[int, tuple[int, int]] = {}
    for line in done.stdout.splitlines()[1:]:
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        pid_s, ppid_s, cputime_s = parts
        try:
            pid = int(pid_s)
            ppid = int(ppid_s)
        except ValueError:
            continue
        table[pid] = (ppid, _parse_ps_cpu_time(cputime_s))
    return table


# frob:doc docs/guides/coordinator-scripts.md#_descendant_cpu_seconds
def _descendant_cpu_seconds(
    root_pids: list[int], table: dict[int, tuple[int, int]]
) -> int:
    """Sum of `table`'s own cpu-seconds for every LIVE descendant of
    `root_pids` (never `root_pids` themselves) -- a land's tracked pids
    (bash wrapper, `timeout`, `uv run`, the python process) are each a
    real row in `land_process_rows`'s own `cpu_s`, but a healthy land
    running `frob check` as a CHILD of the python process accumulates
    real CPU time on a pid this land's own row never counts, reading as
    a near-zero-CPU stall. This walks `table`'s ppid links (built once by
    `_all_process_ppid_cpu`, never a second `ps` call per pid) to total
    every descendant's own time, so `land_invocations`' `child_cpu_s`
    reflects the whole tree's activity, not just the 4 tracked rows."""
    children_of: dict[int, list[int]] = {}
    for pid, (ppid, _cpu) in table.items():
        children_of.setdefault(ppid, []).append(pid)
    total = 0
    seen = set(root_pids)
    stack = list(root_pids)
    while stack:
        pid = stack.pop()
        for child in children_of.get(pid, []):
            if child in seen:
                continue
            seen.add(child)
            total += table[child][1]
            stack.append(child)
    return total


# frob:doc docs/guides/coordinator-scripts.md#land_invocations
# frob:ticket T-2180
# frob:ticket T-2193
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLandInvocations.test_collapses_process_fa\
# n_out_by_ticket_id
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLandInvocations.test_must_pass_control_on\
# e_land_many_processes_reports_one
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLandInvocations.test_rows_with_no_ticket_\
# id_are_dropped_not_reported
def land_invocations() -> list[dict]:
    """Distinct `frob ticket land` INVOCATIONS, keyed on the ticket id
    parsed from each process row's own argv -- collapsing
    `land_process_rows`'s ~4-rows-per-land fan-out down to one entry per
    real land. `ps aux | grep -c "frob ticket land"` returns roughly 4
    per land; this is the fix: distinct invocations keyed on ticket id
    from the process table's own structured fields, never a line count.

    A row whose argv parses NO ticket id (`_parse_land_argv_ticket_id`
    returns `None`) is DROPPED here, not reported as its own invocation.
    Measured incident (T-2193): an earlier version reported every such
    row as a `ticket_id=None` entry, on the theory that an uncorrelated
    row should be disclosed rather than silently discarded -- but in
    practice this let a single long-lived process whose command line
    merely CONTAINS the text 'ticket land' (a coordinator's own wait-loop
    shell running `pgrep -f "frob ticket land T-..."`) inflate `LANDS IN
    FLIGHT` by one forever, and (compounded by the regex bug this same
    incident also fixed -- see `_LAND_ARGV_TICKET_RE`'s own comment)
    turned EVERY row into a `ticket_id=None` singleton, reporting 13 rows
    for one real land where a live coordinator was watching: 13 where the
    truth was 1. Without a ticket id there is nothing to deduplicate a
    row against, so it cannot be reported as a distinct INVOCATION at
    all -- it is process-table noise, not evidence of a land. A caller
    that wants to audit raw rows for exactly this shape still has
    `land_process_rows` directly.

    Each entry: `ticket_id`, `pids` (every pid in the row group),
    `elapsed_s` (the MAX `etimes` across the group -- the longest-lived
    row is the one that actually started the invocation), `cpu_s` (the
    MAX parsed CPU time across the group), and `child_cpu_s` (summed
    across every LIVE descendant of the group's own pids,
    `_descendant_cpu_seconds`). CPU time is reported precisely because
    content alone cannot distinguish a live land from a dead attempt's
    residue -- a killed land's staged diff is byte-identical across
    retries because it is the same work -- but CPU time discriminates
    immediately: a wedged/dead process stops accumulating CPU while a
    live one keeps climbing. `child_cpu_s` exists because `cpu_s` alone
    reads a healthy land running `frob check` as a CHILD process as a
    near-zero-CPU stall -- the tracked pids (bash wrapper, `timeout`,
    `uv run`, the python process) accumulate almost no CPU of their own
    while the real work happens one process down."""
    rows = land_process_rows()
    groups: dict[str, list[dict]] = {}
    for row in rows:
        ticket_id = _parse_land_argv_ticket_id(row["argv"])
        if ticket_id is None:
            continue
        groups.setdefault(ticket_id, []).append(row)

    ppid_cpu_table = _all_process_ppid_cpu() if groups else {}
    invocations = [
        {
            "ticket_id": ticket_id,
            "pids": [r["pid"] for r in group_rows],
            "elapsed_s": max(r["etimes"] for r in group_rows),
            "cpu_s": max(_parse_ps_cpu_time(r["cputime"]) for r in group_rows),
            "child_cpu_s": _descendant_cpu_seconds(
                [r["pid"] for r in group_rows], ppid_cpu_table
            ),
        }
        for ticket_id, group_rows in groups.items()
    ]
    invocations.sort(key=lambda inv: inv["ticket_id"])
    return invocations


# frob:doc docs/guides/coordinator-scripts.md#land_lock_holder_pids
# frob:ticket T-2180
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLandLockHolderPids.test_finds_a_pid_holdi\
# ng_the_lock_open
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLandLockHolderPids.test_no_live_holder_re\
# turns_empty
def land_lock_holder_pids(root: Path, proc: Path = Path("/proc")) -> list[int]:
    """Live pids that currently hold `root`'s `.frob/land.lock` file OPEN,
    found by scanning `<proc>/<pid>/fd/*` for a symlink that resolves to
    the lock's own absolute path -- NOT the pid recorded inside the lock
    file's own JSON (pids are reused, so a stale recorded pid can name a
    live but unrelated process) and NOT the lock file's modification age
    (a legitimate land genuinely exceeds 1500s under load, so age alone
    cannot tell a stuck lock from a slow one). `flock` is released by the
    kernel the instant its holder process dies -- so "is any live pid's
    fd table still pointing at the lock file" is a live, race-free
    liveness check, not an inference. `proc` is injectable for tests
    (`/proc` by default); an unreadable-or-absent `proc` returns `[]`
    rather than raising, matching this script's fail-quiet-not-fail-loud
    posture for a best-effort report."""
    lock_path = (root / ".frob" / "land.lock").resolve()
    if not proc.is_dir():
        return []
    holders: list[int] = []
    try:
        pid_dirs = list(proc.iterdir())
    except OSError:
        return []
    for pid_dir in pid_dirs:
        if not pid_dir.name.isdigit():
            continue
        fd_dir = pid_dir / "fd"
        try:
            fds = list(fd_dir.iterdir())
        except OSError:
            continue
        for fd in fds:
            try:
                target = fd.resolve()
            except OSError:
                continue
            if target == lock_path:
                holders.append(int(pid_dir.name))
                break
    return holders


#: Below this many concurrent agents, host load is not this repo's own
#: recorded operational constraint -- see `host_load` for the incident.
_AGENT_CAP_GUIDANCE = "3-4 agent"


# frob:doc docs/guides/coordinator-scripts.md#host_load
# frob:ticket T-2180
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestHostLoad.test_reads_loadavg_and_mem_avail\
# able
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestHostLoad.test_missing_proc_files_return_n\
# one
def host_load(proc: Path = Path("/proc")) -> tuple[float, int] | None:
    """`(one_minute_load_average, mem_available_kb)` read from `<proc>/
    loadavg` and `<proc>/meminfo`'s own STRUCTURED fields -- never by
    parsing `free`/`uptime`'s rendered output, whose column layout varies
    by version and locale. Returns `None` if either file is missing or
    unparseable (a non-Linux host, or a sandboxed `/proc`), which the
    caller must treat as "unknown", not "0 load / plenty of memory".

    `meminfo`'s `MemAvailable` field, not `MemFree`, is deliberately what
    gets read: a busy-but-healthy Linux host commonly shows `MemFree`
    near 0 with most memory held as reclaimable page cache --
    `MemAvailable` is the kernel's own estimate of what a new process can
    actually get, and reading `MemFree` instead raises a false alarm on
    every busy host, which teaches an operator to ignore the alarm even
    when it is real. This mirrors a real incident: six concurrent agents
    on a host with a documented 3-4 agent operational cap (an OOM killer
    has terminated a session here before) went unnoticed until someone
    went looking by hand -- the same 'a real constraint measured
    somewhere nobody reads at decision time' shape as the pre-T-2049
    quarantine and the pre-T-2182 ticket-rot gap."""
    loadavg_path = proc / "loadavg"
    meminfo_path = proc / "meminfo"
    try:
        load_1min = float(loadavg_path.read_text(encoding="utf-8").split()[0])
    except (OSError, ValueError, IndexError):
        return None
    mem_available_kb = None
    try:
        for line in meminfo_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                mem_available_kb = int(line.split()[1])
                break
    except (OSError, ValueError, IndexError):
        return None
    if mem_available_kb is None:
        return None
    return load_1min, mem_available_kb


#: T-2249: measured basis. The incident this ticket fixes had 6,291,456 KB
#: (6GB) of swap in use, with 0 free RAM, while `MemAvailable` still read
#: a healthy 11.5GB -- real pressure the existing LOAD/MEM line could not
#: show. 1GB (1,048,576 KB) is set well below that measured incident (so
#: it still fires) and well above the few-MB of swap a healthy Linux host
#: routinely has resident from boot-time/idle-process paging (so a
#: machine that legitimately uses "some" swap, per the ticket's own
#: caution, does not false-positive) -- NOT "any swap at all".
_SWAP_PRESSURE_FLOOR_KB = 1024 * 1024


# frob:doc docs/guides/coordinator-scripts.md#swap_pressure
# frob:ticket T-2249
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestSwapPressure.test_reads_swap_used_and_tot\
# al
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestSwapPressure.test_swap_total_zero_never_c\
# rashes_or_claims_pressure
def swap_pressure(proc: Path = Path("/proc")) -> tuple[int, int] | None:
    """`(swap_used_kb, swap_total_kb)` read from `<proc>/meminfo`'s own
    `SwapTotal`/`SwapFree` fields -- the same file `host_load` already
    reads `MemAvailable` from, no new `/proc` file and no subprocess
    (`free` is deliberately never shelled out to, matching this script's
    import-light contract). `swap_used_kb = SwapTotal - SwapFree`, the
    same arithmetic `free`'s own 'used' column uses. Returns `None` if
    the file is missing/unparseable, which the caller must treat as
    "unknown", never "0 swap in use". `swap_total_kb == 0` (no swap
    configured at all) is a real, valid case -- NOT an error -- and the
    caller (`_swap_guidance`) must never divide by it or claim pressure
    from it; see that function's own must-still-pass control."""
    meminfo_path = proc / "meminfo"
    swap_total_kb = None
    swap_free_kb = None
    try:
        for line in meminfo_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("SwapTotal:"):
                swap_total_kb = int(line.split()[1])
            elif line.startswith("SwapFree:"):
                swap_free_kb = int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    if swap_total_kb is None or swap_free_kb is None:
        return None
    return max(swap_total_kb - swap_free_kb, 0), swap_total_kb


# frob:doc docs/guides/coordinator-scripts.md#orphaned_forkserver_count
# frob:ticket T-2443
#: `/proc/<pid>/cmdline` substring identifying a `multiprocessing.
#: forkserver` helper process -- mirrors `frob.process._reap.
#: _FORKSERVER_CMDLINE_RE` exactly (duplicated here in plain form rather
#: than imported, per this script's own "no `frob` import" module-docstring
#: contract, same posture as `_ROT_DAYS_DEFAULT`'s duplication of
#: `frob.gates._tickets_gate`'s rot-day thresholds just above).
_FORKSERVER_CMDLINE_RE = re.compile(r"multiprocessing\.forkserver")


#: T-2517: how old (wall-clock seconds) a forkserver must be before it is
#: reported STALE. 1 hour -- well past any real check's own runtime (the
#: heaviest measured `frob check` stage total is ~209s, playbook section
#: 13), so a forkserver still alive past this age is not mid-service, and
#: well above the "reused within the next check" window a coordinator's
#: own dispatch cadence would otherwise false-positive on. Matches the
#: measured incident this ticket was filed from: 82 of 148 forkservers
#: were older than 1 hour, holding essentially all of the host's 12GB of
#: in-use swap between them.
_FORKSERVER_STALE_AFTER_S = 3600.0


# frob:doc docs/guides/coordinator-scripts.md#_forkserver_snapshot
# frob:ticket T-2443
# frob:ticket T-2517
def _forkserver_age_s(
    fields: list[str], uptime_s: float | None, clk_tck: int
) -> float | None:
    """`fields` is `_forkserver_snapshot`'s own post-")" split of one
    `/proc/<pid>/stat` line; `fields[19]` is starttime (field 22 overall,
    clock ticks since boot). Returns `None` (never a fabricated age) if
    `uptime_s` is unknown, the field is missing, or the ticks value does
    not parse -- ARCH001 split of `_forkserver_snapshot` (T-2517), no
    behavior change from inlining this at the call site."""
    if uptime_s is None or len(fields) < 20 or not clk_tck:
        return None
    try:
        starttime_ticks = int(fields[19])
        return uptime_s - (starttime_ticks / clk_tck)
    except (ValueError, ZeroDivisionError):
        return None


def _forkserver_vmswap_kb(entry: Path) -> int:
    """`VmSwap:` (kb) from `<entry>/status`, or `0` if the file is
    missing/unparseable -- degrades that ONE process's contribution, never
    raises. ARCH001 split of `_forkserver_snapshot` (T-2517)."""
    try:
        for line in (entry / "status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmSwap:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        pass
    return 0


def _parse_forkserver_entry(
    entry: Path, uptime_s: float | None, clk_tck: int
) -> dict[str, int | float | None] | None:
    """One `/proc/<pid>` entry -> `{pid, ppid, age_s, vmswap_kb}`, or
    `None` if `entry` is not a live `multiprocessing.forkserver` process
    (not a pid dir, cmdline does not match, or `stat` is unreadable/
    unparseable). ARCH001 split of `_forkserver_snapshot` (T-2517): the
    per-entry parsing logic, unchanged from what `_forkserver_snapshot`
    used to do inline."""
    if not entry.name.isdigit():
        return None
    try:
        cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ")
    except OSError:
        return None
    if not _FORKSERVER_CMDLINE_RE.search(cmdline.decode("utf-8", errors="replace")):
        return None
    try:
        stat_text = (entry / "stat").read_text(encoding="utf-8")
    except OSError:
        return None
    close_paren = stat_text.rfind(")")
    if close_paren == -1:
        return None
    # Fields after ")": [state, ppid, pgrp, ..., starttime, ...] -- ppid
    # is fields[1], starttime (field 22 overall) is fields[19].
    fields = stat_text[close_paren + 2 :].split()
    if len(fields) < 2:
        return None
    try:
        ppid = int(fields[1])
    except ValueError:
        return None
    return {
        "pid": int(entry.name),
        "ppid": ppid,
        "age_s": _forkserver_age_s(fields, uptime_s, clk_tck),
        "vmswap_kb": _forkserver_vmswap_kb(entry),
    }


def _forkserver_snapshot(
    proc: Path = Path("/proc"),
) -> list[dict[str, int | float | None]] | None:
    """One `/proc` walk collecting every live `multiprocessing.forkserver`
    helper's `pid`/`ppid`/`age_s`/`vmswap_kb` (via `_parse_forkserver_
    entry`), shared by `orphaned_forkserver_count`, `stale_forkserver_
    count`, and `forkserver_swap_held_kb` (T-2517) so reporting all three
    numbers costs one scan, not three. `age_s`/`vmswap_kb` degrade to
    `None`/`0` per-entry on a missing/unparseable file, never abort the
    whole scan -- see `_forkserver_age_s`/`_forkserver_vmswap_kb`'s own
    docstrings for exactly which reads those are. Returns `None` only
    when `/proc` itself is missing/unreadable, mirroring every other
    best-effort `/proc`-scanning function in this module. Motivating
    incident (T-2517): `ORPHANED FORKSERVERS: 0` while 82 stale pools
    held 12GB of swap, because the orphan-only signal (reparented to
    init) missed every one of them -- they all still had a live
    agent-shell parent."""
    if not proc.is_dir():
        return None
    try:
        entries = list(proc.iterdir())
    except OSError:
        return None
    uptime_s: float | None
    try:
        uptime_s = float((proc / "uptime").read_text(encoding="utf-8").split()[0])
    except (OSError, ValueError, IndexError):
        uptime_s = None
    try:
        clk_tck = os.sysconf("SC_CLK_TCK")
    except (ValueError, OSError):
        clk_tck = 100
    procs: list[dict[str, int | float | None]] = []
    for entry in entries:
        parsed = _parse_forkserver_entry(entry, uptime_s, clk_tck)
        if parsed is not None:
            procs.append(parsed)
    return procs


# frob:doc docs/guides/coordinator-scripts.md#orphaned_forkserver_count
# frob:ticket T-2443
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount.test_counts_forks\
# erver_reparented_to_init
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount.test_ignores_fork\
# server_with_live_parent
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount.test_ignores_non_\
# forkserver_processes
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount.test_missing_proc\
# _returns_none
def orphaned_forkserver_count(proc: Path = Path("/proc")) -> int | None:
    """How many live `multiprocessing.forkserver` helper processes on this
    host are reparented to init (ppid == 1, i.e. their creating process is
    dead) -- the exact, process-table-measured signature of T-2443's own
    incident: `frob check` killed by this fleet's routine `timeout 540
    ...` wrapper used to leave its process-pool workers (and therefore the
    forkserver helper they keep alive) running forever, 94 of them
    reparented to `/init` at measurement time, holding 17.3GB of swap. Read
    directly from `/proc` (no `frob` import, no subprocess -- matching
    `host_load`/`swap_pressure`'s own contract exactly) so an operator
    staring at `_swap_guidance`'s '1 agent (SWAP ...)' clause can see
    WHETHER this specific, actionable leak is the cause, rather than
    guessing. Returns `None` if `/proc` is missing/unreadable (a non-Linux
    host, a sandboxed container) -- the caller must treat that as
    'unknown', never '0 orphans', mirroring every other best-effort
    `/proc`-scanning function in this module.

    T-2517 CAUTION this function's own name invites: "orphaned" here means
    ONLY init-reparented (ppid == 1). A forkserver whose parent is still
    alive but idle for an hour is NOT counted here -- see `stale_
    forkserver_count` for that (deliberately separate) signal; T-2517's
    own incident is exactly a reader collapsing the two and reading
    `ORPHANED FORKSERVERS: 0` as "nothing to reclaim" while 12GB of swap
    sat in live-parented pools this function structurally cannot see."""
    snapshot = _forkserver_snapshot(proc)
    if snapshot is None:
        return None
    return sum(1 for p in snapshot if p["ppid"] == 1)


# frob:doc docs/guides/coordinator-scripts.md#stale_forkserver_count
# frob:ticket T-2517
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount.test_counts_old_fork\
# server_when_no_checks_running
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount.test_ignores_young_f\
# orkserver
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount.test_never_counts_an\
# ything_while_a_check_is_running
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount.test_unknown_concurr\
# ent_checks_never_counts_anything
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount.test_missing_proc_re\
# turns_none
def stale_forkserver_count(
    proc: Path = Path("/proc"),
    *,
    concurrent_checks: int | None,
    stale_after_s: float = _FORKSERVER_STALE_AFTER_S,
) -> int | None:
    """How many live `multiprocessing.forkserver` helpers are STALE (T-2517):
    older than `stale_after_s` (default 1 hour) with no `frob check`
    currently running on the host, REGARDLESS of whether their parent
    process is still alive. This is the signal `orphaned_forkserver_count`
    structurally cannot report -- T-2517's own incident measured 82 of 148
    forkservers past this age, all still parented to a live agent shell,
    holding 12GB of swap while the orphan count read a clean 0.

    `concurrent_checks` is the caller's own `concurrent_check_count`
    reading, passed in rather than re-measured here so both numbers in one
    report come from the same instant. Per the ticket's own explicit
    caution against building a reaper on a wrong precondition: a
    forkserver with a live parent MAY belong to a check about to start, so
    this ONLY counts anything when `concurrent_checks == 0` -- `None`
    (unknown) or any positive count both make every forkserver read as
    "not stale, cannot tell" (0), never a guess. This function performs no
    reclamation of any kind; it only reports the count an operator (or a
    future, separately-designed reaper) would act on.

    Returns `None` only when `/proc` itself is unreadable, matching every
    other best-effort function in this module."""
    snapshot = _forkserver_snapshot(proc)
    if snapshot is None:
        return None
    if concurrent_checks != 0:
        return 0
    return sum(
        1 for p in snapshot if p["age_s"] is not None and p["age_s"] >= stale_after_s
    )


# frob:doc docs/guides/coordinator-scripts.md#forkserver_swap_held_kb
# frob:ticket T-2517
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestForkserverSwapHeldKb.test_sums_vmswap_acr\
# oss_every_forkserver
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestForkserverSwapHeldKb.test_missing_status_\
# file_degrades_that_entry_to_zero_not_a_crash
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestForkserverSwapHeldKb.test_missing_proc_re\
# turns_none
def forkserver_swap_held_kb(proc: Path = Path("/proc")) -> int | None:
    """Sum of `VmSwap` (kb) across every live `multiprocessing.forkserver`
    helper on the host, orphaned or not, stale or not (T-2517) -- the
    third of the three numbers the ticket requires reported separately,
    never collapsed into the orphan/stale counts. RSS is deliberately
    never read for this: a swapped-out process reports near-zero RSS
    while still holding real memory, which is exactly the measurement
    that would have hidden T-2517's own 12GB incident a second time.
    Returns `None` only when `/proc` itself is unreadable; a per-process
    `status` file that cannot be read degrades THAT process's contribution
    to 0kb (a partial reading, not a crash), matching `_forkserver_
    snapshot`'s own per-entry resilience contract."""
    snapshot = _forkserver_snapshot(proc)
    if snapshot is None:
        return None
    return sum(int(p["vmswap_kb"] or 0) for p in snapshot)


# frob:doc docs/guides/coordinator-scripts.md#concurrent_check_count
# frob:ticket T-2473
#: `cmdline` token-pair identifying a live `frob check` invocation --
#: duplicated in plain form from `frob.process._reap._FROB_TOKEN_RE`/
#: `_CHECK_TOKEN_RE` (this script's own "no `frob` import" contract, the
#: same posture `_FORKSERVER_CMDLINE_RE` above already takes for T-2443).
_FROB_CHECK_TOKEN_RE = re.compile(rb"(?:^|/)frob\x00")
_CHECK_TOKEN_RE = re.compile(rb"\x00check\x00|\x00check$")


# frob:doc docs/guides/coordinator-scripts.md#concurrent_check_count
# frob:ticket T-2473
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestConcurrentCheckCount.test_counts_check_pr\
# ocesses
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestConcurrentCheckCount.test_ignores_non_che\
# ck_processes
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestConcurrentCheckCount.test_missing_proc_re\
# turns_none
def concurrent_check_count(proc: Path = Path("/proc")) -> int | None:
    """How many live `frob check` processes are running on this host right
    now (T-2473) -- the number a coordinator needs to decide whether to
    dispatch another agent, previously invisible short of deriving it by
    hand with `ps` (T-2473's own filed measurement: 12 concurrent checks
    went unnoticed until someone checked manually). Unlike `frob.process.
    _reap.count_running_checks` (T-2473's advisory log line INSIDE a
    running check, which excludes itself), this counts EVERY live check
    process including any this script's own invocation might overlap with
    -- `fleet_status.py` is not itself a `frob check` process, so there is
    no self-exclusion case here. Returns `None` if `/proc` is missing/
    unreadable, mirroring `orphaned_forkserver_count`'s own best-effort-
    degrades-to-None contract exactly."""
    if not proc.is_dir():
        return None
    try:
        entries = list(proc.iterdir())
    except OSError:
        return None
    count = 0
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if not raw.endswith(b"\x00"):
            raw += b"\x00"
        if _FROB_CHECK_TOKEN_RE.search(raw) and _CHECK_TOKEN_RE.search(raw):
            count += 1
    return count


# frob:doc docs/guides/coordinator-scripts.md#_swap_guidance
# frob:ticket T-2249
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestSwapGuidance.test_swap_above_floor_overri\
# des_the_static_guidance
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestSwapGuidance.test_swap_below_floor_keeps_\
# the_static_guidance
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestSwapGuidance.test_unknown_swap_keeps_the_\
# static_guidance
def _swap_guidance(swap: tuple[int, int] | None) -> str:
    """The concurrency GUIDANCE clause text -- `_AGENT_CAP_GUIDANCE`
    UNLESS `swap` (`swap_pressure`'s own reading) shows real pressure
    (`swap_used_kb >= _SWAP_PRESSURE_FLOOR_KB`), in which case it names
    the pressure directly instead of the static agent-count string. T-
    2249: the defect this fixes is the GUIDANCE keying on the wrong
    quantity (`MemAvailable`, which reads healthy while swap is already
    in heavy use) -- this is the one place that quantity changes, so a
    coordinator reading only the guidance clause (not the raw numbers)
    still sees the real constraint. `swap is None` (unknown) or `swap[1]
    == 0` (no swap configured, a real and common case, never an error)
    both fall through to the ordinary static guidance -- swap pressure is
    additive information, never claimed from an absence of data."""
    if swap is not None:
        swap_used_kb, swap_total_kb = swap
        if swap_total_kb > 0 and swap_used_kb >= _SWAP_PRESSURE_FLOOR_KB:
            swap_used_gb = swap_used_kb / (1024 * 1024)
            return (
                f"1 agent (SWAP {swap_used_gb:.1f}GB in use -- real memory"
                " pressure MemAvailable does not show)"
            )
    return f"{_AGENT_CAP_GUIDANCE} concurrent"


# frob:doc docs/guides/coordinator-scripts.md#_rot_day_thresholds
# frob:ticket T-2182
def _rot_day_thresholds() -> dict[str, int]:
    """Per-priority rot-day thresholds, from `frob.toml`'s `[tickets]`
    table (`rot_days_critical`/`rot_days_high`/`rot_days_medium`/
    `rot_days_low`) when present and parseable, else `_ROT_DAYS_DEFAULT`
    -- mirrors `frob.gates._tickets_gate._tick004_rot_thresholds`'s own
    fail-open-to-defaults shape exactly, so this script's rotting-ticket
    count agrees with TICK004's own gate finding rather than silently
    drifting from it. Degrades to defaults (never raises) when `tomllib`
    is unavailable (python <3.11 on `PATH`) or `frob.toml` is missing/
    malformed."""
    if tomllib is None:
        return dict(_ROT_DAYS_DEFAULT)
    toml_path = REPO / "frob.toml"
    if not toml_path.exists():
        return dict(_ROT_DAYS_DEFAULT)
    try:
        with toml_path.open("rb") as fh:
            table = tomllib.load(fh).get("tickets", {})
        return {
            priority: int(table.get(f"rot_days_{priority}", default))
            for priority, default in _ROT_DAYS_DEFAULT.items()
        }
    except (OSError, ValueError, TypeError):
        return dict(_ROT_DAYS_DEFAULT)


# frob:doc docs/guides/coordinator-scripts.md#_parse_ticket_ledger_fields
# frob:ticket T-2449
def _parse_ticket_ledger_fields(text: str) -> tuple[dict[str, str], list[str]]:
    """`({flat "key: value" fields}, blocked_by list)` -- the per-line scan
    half of `_parse_ticket_ledger_file` (T-2449, ARCH001 split: adding
    `blocked_by:` block parsing pushed the combined function over the
    60-line threshold). `blocked_by:` is a `- item` list block, same
    shape `_parse_ticket_frontmatter_text` already parses for the
    `main:`-committed side."""
    fields: dict[str, str] = {}
    blocked_by: list[str] = []
    in_blocked_by = False
    for line in text.splitlines():
        if line == "---":
            continue
        if line == "blocked_by:":
            in_blocked_by = True
            continue
        if in_blocked_by:
            stripped = line.strip()
            if stripped.startswith("- "):
                item = stripped[2:].strip()
                if len(item) >= 2 and item[0] == item[-1] and item[0] in "'\"":
                    item = item[1:-1]
                blocked_by.append(item)
                continue
            in_blocked_by = False
        for key in (
            "id",
            "state",
            "priority",
            "tier",
            "created",
            "runs_last",
            "parent",
        ):
            prefix = f"{key}:"
            if line.startswith(prefix):
                value = line[len(prefix) :].strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                    value = value[1:-1]
                fields[key] = value
    return fields, blocked_by


# frob:doc docs/guides/coordinator-scripts.md#_parse_ticket_ledger_file
# frob:ticket T-2182
# frob:ticket T-2200
# frob:ticket T-2449
def _parse_ticket_ledger_file(path: Path) -> dict | None:
    """`{"id", "state", "priority", "tier", "created", "runs_last",
    "parent", "blocked_by"}` hand-parsed directly from a `tickets/<id>/
    ticket.md` file's own frontmatter, reading a LOCAL file on disk
    (never `git show main:...`, since `rotting_tickets` reports the
    live, uncommitted ledger state a dispatch decision actually depends
    on). `None` if the file is unreadable or `id`/`state`/`priority`/
    `created` cannot all be parsed. `tier` defaults to `ticket`,
    `runs_last` (T-2200) to `False`, `parent` (T-2229) to `None`,
    `blocked_by` (T-2449) to `[]` -- all read as STRUCTURED ledger
    fields, never inferred from `title` text; see docs/guides/
    coordinator-scripts.md#_parse_ticket_ledger_file for the incidents
    each default guards against. `blocked_by:` is a `- item` list block
    (same shape `_parse_ticket_frontmatter_text` already parses for the
    `main:`-committed side) -- read here too so `rotting_tickets` can
    exclude a genuinely-still-blocked leaf from NEEDS DISPATCH (T-2449
    acceptance [3])."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    fields, blocked_by = _parse_ticket_ledger_fields(text)
    if not {"id", "state", "priority", "created"} <= fields.keys():
        return None
    parent = fields.get("parent", "").strip()
    return {
        "id": fields["id"],
        "state": fields["state"],
        "priority": fields["priority"],
        "tier": fields.get("tier", "ticket"),
        "blocked_by": blocked_by,
        "created": fields["created"],
        "runs_last": fields.get("runs_last", "false").strip().lower() == "true",
        # T-2229: 'null'/'~'/empty all mean "no parent" (see doc anchor).
        "parent": None if parent in ("", "null", "~") else parent,
    }


#: Terminal ticket states -- mirrors `frob.tickets._models`'s own
#: `TicketState.DONE`/`DROPPED`, kept as bare strings here rather than
#: importing the model (this script is deliberately import-light).
_TERMINAL_STATES = ("done", "dropped")


# frob:doc docs/guides/coordinator-scripts.md#_epics_with_active_children
# frob:ticket T-2229
def _epics_with_active_children() -> set[str]:
    """Ticket ids that have at least one OTHER ticket under `TICKETS_DIR`
    carrying `parent == <this id>` in a non-terminal state (`_TERMINAL_
    STATES`) -- read as the STRUCTURED `parent` field off each CHILD
    ticket record (`_parse_ticket_ledger_file`), never inferred from
    title text or a hand-authored epic-id allowlist (T-2229: do not fix
    it this way). ONE scan over every ticket dir (not just rotting ones,
    since a child keeping an epic decomposed need not itself be rotting)
    -- shared by `rotting_tickets` so the TICKET ROT section's 'already
    decomposed' bucket agrees with `frob.gates._tickets_gate._tick004_
    queue_rot`'s own `_has_active_child` predicate exactly (same field,
    same terminal-state definition)."""
    if not TICKETS_DIR.is_dir():
        return set()
    active_parents: set[str] = set()
    for ticket_dir in sorted(p for p in TICKETS_DIR.iterdir() if p.is_dir()):
        if ticket_dir.name == "archive":
            continue
        ledger_path = ticket_dir / "ticket.md"
        if not ledger_path.is_file():
            continue
        parsed = _parse_ticket_ledger_file(ledger_path)
        if parsed is None or parsed["parent"] is None:
            continue
        if parsed["state"] in _TERMINAL_STATES:
            continue
        active_parents.add(parsed["parent"])
    return active_parents


# frob:doc docs/guides/coordinator-scripts.md#_epics_with_any_children
# frob:ticket T-2468
def _epics_with_any_children() -> set[str]:
    """Ticket ids that have AT LEAST ONE child ticket ANYWHERE -- active
    `TICKETS_DIR` or `tickets/archive/**` -- regardless of that child's
    state. Distinct from `_epics_with_active_children`, which only counts
    a NON-terminal child and never looks in `archive/` at all: an epic
    whose every child has landed and archived (T-1135's shape) reads as
    zero active children under that predicate even though it plainly has
    children, which is exactly why it was misclassified as NEEDS
    DECOMPOSITION (T-2468) instead of NEEDS CLOSE. `_print_ticket_rot`
    combines this with `has_active_child` to tell three states apart:
    no children at all (still NEEDS DECOMPOSITION), children exist but
    none active (NEEDS CLOSE), and an active child exists (DECOMPOSED,
    BEING WORKED, unchanged)."""
    parents: set[str] = set()
    if TICKETS_DIR.is_dir():
        for ticket_dir in sorted(p for p in TICKETS_DIR.iterdir() if p.is_dir()):
            if ticket_dir.name == "archive":
                continue
            ledger_path = ticket_dir / "ticket.md"
            if not ledger_path.is_file():
                continue
            parsed = _parse_ticket_ledger_file(ledger_path)
            if parsed is None or parsed["parent"] is None:
                continue
            parents.add(parsed["parent"])
    archive_dir = TICKETS_DIR / "archive"
    if archive_dir.is_dir():
        for ticket_dir in sorted(p for p in archive_dir.iterdir() if p.is_dir()):
            ledger_path = ticket_dir / "ticket.md"
            if not ledger_path.is_file():
                continue
            parsed = _parse_ticket_ledger_file(ledger_path)
            if parsed is None or parsed["parent"] is None:
                continue
            parents.add(parsed["parent"])
    return parents


# frob:doc docs/guides/coordinator-scripts.md#rotting_tickets
# frob:ticket T-2182
# frob:ticket T-2229
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestRottingTickets.test_flags_a_ticket_past_i\
# ts_priority_threshold
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestRottingTickets.test_ignores_tickets_still\
# _under_threshold
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestRottingTickets.test_only_queued_and_plann\
# ed_states_are_considered
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestRottingTickets.test_distinguishes_epic_an\
# d_story_tier_from_ticket_tier
def rotting_tickets() -> list[dict]:
    """Every QUEUED/PLANNED ticket under `TICKETS_DIR` (excluding
    `tickets/archive/**`) whose priority-specific rot-day threshold
    (`_rot_day_thresholds`) has been crossed since its own `created`
    date -- derived entirely from structured ledger fields, mirroring
    `frob.gates._tickets_gate._tick004_queue_rot`'s own selection exactly
    so this script's count agrees with the gate's own finding. Each
    entry: `id`, `priority`, `tier`, `state`, `age_days`,
    `threshold_days`, `runs_last` (T-2200), `has_active_child` (T-2229),
    `has_any_child` (T-2468); see
    docs/guides/coordinator-scripts.md#rotting_tickets for the exact
    field semantics. Malformed `created` dates are skipped rather than
    guessed at."""
    if not TICKETS_DIR.is_dir():
        return []
    thresholds = _rot_day_thresholds()
    today = date.today()
    active_parents = _epics_with_active_children()
    any_child_parents = _epics_with_any_children()
    rotting: list[dict] = []
    for ticket_dir in sorted(p for p in TICKETS_DIR.iterdir() if p.is_dir()):
        if ticket_dir.name == "archive":
            continue
        entry = _rotting_entry(
            ticket_dir, thresholds, today, active_parents, any_child_parents
        )
        if entry is not None:
            rotting.append(entry)
    rotting.sort(key=lambda t: (_PRIORITY_RANK.get(t["priority"], 99), -t["age_days"]))
    return rotting


# frob:doc docs/guides/coordinator-scripts.md#_local_ledger_state
# frob:ticket T-2449
def _local_ledger_state(ticket_id: str, tickets_dir: Path = TICKETS_DIR) -> str | None:
    """`ticket_id`'s `state:` field read from the LOCAL, uncommitted
    ledger -- `tickets_dir/<id>/ticket.md` first, then `tickets_dir/
    archive/<id>/ticket.md` (T-2449's own archive-fallback fix, mirrored
    here for the local-disk side the same way `ticket_frontmatter_on_
    main` does it for the `main:`-committed side). `None` if the id
    resolves in NEITHER location -- the caller must treat that as
    unresolved, never as 'still open' (fail-loudly, T-2391)."""
    for candidate in (
        tickets_dir / ticket_id / "ticket.md",
        tickets_dir / "archive" / ticket_id / "ticket.md",
    ):
        if candidate.is_file():
            parsed = _parse_ticket_ledger_file(candidate)
            if parsed is not None:
                return parsed["state"]
    return None


# frob:doc docs/guides/coordinator-scripts.md#_classify_blockers_local
# frob:ticket T-2449
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestClassifyBlockersLocal.test_done_archived_\
# blocker_is_closed
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestClassifyBlockersLocal.test_queued_blocker\
# _is_open
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestClassifyBlockersLocal.test_missing_blocke\
# r_is_unresolved
def _classify_blockers_local(
    blocked_by: Sequence[str], tickets_dir: Path = TICKETS_DIR
) -> tuple[list[str], list[str]]:
    """`(open_ids, unresolved_ids)` -- the LOCAL-disk twin of
    `_classify_blockers` (T-2449), used by `_rotting_entry` so the NEEDS
    DISPATCH bucket agrees with `ticket_readiness`'s own dispatchability
    verdict (acceptance [3]) without paying for a `git show` per blocker
    id on every rot-detector pass."""
    open_ids: list[str] = []
    unresolved_ids: list[str] = []
    for blocker_id in blocked_by:
        state = _local_ledger_state(blocker_id, tickets_dir)
        if state is None:
            unresolved_ids.append(blocker_id)
        elif state not in ("done", "dropped"):
            open_ids.append(blocker_id)
    return open_ids, unresolved_ids


# frob:doc docs/guides/coordinator-scripts.md#_rotting_entry
# frob:ticket T-2229
# frob:ticket T-2449
# frob:ticket T-2468
def _rotting_entry(
    ticket_dir: Path,
    thresholds: dict[str, int],
    today: date,
    active_parents: set[str],
    any_child_parents: set[str],
) -> dict | None:
    """One `rotting_tickets` entry for `ticket_dir`, or `None` if it is
    unreadable/malformed, not QUEUED/PLANNED, or still under its
    priority's threshold -- the per-file half of `rotting_tickets`,
    split out to keep the directory-walk/sort half readable on its own.
    T-2449: also carries `open_blockers`/`unresolved_blockers`
    (`_classify_blockers_local`) so `_print_ticket_rot` can keep a
    still-blocked leaf out of NEEDS DISPATCH (acceptance [3]). T-2468:
    also carries `has_any_child` (`_epics_with_any_children`, active +
    archived, any state) alongside `has_active_child` so `_print_ticket_
    rot` can tell 'no children ever filed' (still NEEDS DECOMPOSITION)
    apart from 'children exist but all terminal' (NEEDS CLOSE)."""
    ledger_path = ticket_dir / "ticket.md"
    if not ledger_path.is_file():
        return None
    parsed = _parse_ticket_ledger_file(ledger_path)
    if parsed is None or parsed["state"] not in ("queued", "planned"):
        return None
    try:
        created = date.fromisoformat(parsed["created"])
    except ValueError:
        return None
    threshold = thresholds.get(parsed["priority"])
    if threshold is None:
        return None
    age_days = (today - created).days
    if age_days <= threshold:
        return None
    open_blockers, unresolved_blockers = _classify_blockers_local(
        parsed.get("blocked_by", []), ticket_dir.parent
    )
    return {
        "id": parsed["id"],
        "priority": parsed["priority"],
        "tier": parsed["tier"],
        "state": parsed["state"],
        "age_days": age_days,
        "threshold_days": threshold,
        "runs_last": parsed["runs_last"],
        "has_active_child": parsed["id"] in active_parents,
        "has_any_child": parsed["id"] in any_child_parents,
        "open_blockers": open_blockers,
        "unresolved_blockers": unresolved_blockers,
    }


def _rot_bucket_lines(heading: str, tickets: list[dict], detail: str = "") -> list[str]:
    """Every line one TICKET ROT bucket renders to (T-2341's ARCH103
    split of `_print_rot_bucket`'s formatting/branching half from its I/O
    half below): a `  HEADING (N):` line, then one `    id ...` line per
    ticket with its priority/state/age, plus `detail` appended verbatim
    (already ticket-specific text, or ''), or `[]` if `tickets` is empty.
    `tier=` is included per-ticket, for every non-leaf ticket in the
    bucket (`t["tier"] != "ticket"`) -- T-2475: this used to be a single
    bucket-wide flag keyed off `tickets[0]` alone, which silently hid the
    tier on every OTHER non-leaf entry in a bucket that mixes leaf and
    non-leaf tickets (BLOCKED, once T-2475 routes a still-blocked
    epic/story there alongside blocked leaves) -- pure computation, no
    I/O, so it is independently testable."""
    if not tickets:
        return []
    lines = [f"  {heading} ({len(tickets)}):"]
    for t in tickets:
        tier_part = f"tier={t['tier']} " if t["tier"] != "ticket" else ""
        lines.append(
            f"    {t['id']} {tier_part}priority={t['priority']} state={t['state']} "
            f"age={t['age_days']}d (threshold {t['threshold_days']}d)"
            + (f" -- {detail.format(id=t['id'])}" if detail else "")
        )
    return lines


# frob:doc docs/guides/coordinator-scripts.md#_print_rot_bucket
# frob:ticket T-2229
def _print_rot_bucket(heading: str, tickets: list[dict], detail: str = "") -> None:
    """Print one TICKET ROT bucket (`_print_ticket_rot`'s own shared
    rendering) -- thin I/O wrapper over `_rot_bucket_lines`' pure
    formatting/branching (T-2341's ARCH103 split)."""
    for line in _rot_bucket_lines(heading, tickets, detail):
        print(line)


# frob:doc docs/guides/coordinator-scripts.md#_print_ticket_rot
# frob:ticket T-2182
# frob:ticket T-2200
# frob:ticket T-2229
# frob:ticket T-2475
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintTicketRot.test_splits_by_tier_under_\
# distinct_action_headings
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintTicketRot.test_runs_last_ticket_gets\
# _its_own_deferred_bucket_not_needs_dispatch
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintTicketRot.test_decomposed_epic_print\
# s_under_its_own_heading_not_needs_decomposition
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintTicketRot.test_epic_all_terminal_chi\
# ldren_prints_under_needs_close
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintTicketRot.test_epic_with_no_children\
# _at_all_still_prints_under_needs_decomposition
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintTicketRot.test_blocked_story_with_te\
# rminal_child_prints_under_blocked_not_needs_close
def _print_ticket_rot() -> None:
    """Print the TICKET ROT section: `rotting_tickets`'s own count, split
    into headings by required ACTION -- 'NEEDS DISPATCH' (a leaf ticket,
    not `runs_last`, with no unresolved blocked_by edge -- T-2449), 'BLOCKED
    (dependency not yet resolved)' (T-2449: a leaf ticket whose
    `blocked_by` still names an open or unresolved id -- previously such a
    ticket appeared under NEEDS DISPATCH while `ticket_readiness` reported
    `dispatchable: False` for the exact same id, the T-2449 incident:
    T-1696 was flagged for dispatch on three consecutive coordinator ticks
    while every attempt was refused; T-2475: a non-leaf with its OWN
    still-open/unresolved `blocked_by` edge lands here too, checked
    BEFORE the NEEDS CLOSE split below ever runs on it -- T-1599's live
    shape, a story with one archived-done child covering only part of
    the work and the rest genuinely blocked, must never read as
    closeable just because one child happens to be terminal), 'DEFERRED
    (RUNS LAST)' (T-2200: `frob ticket start` structurally refuses a
    `runs_last` ticket, so 'NEEDS DISPATCH' is an action the tool itself
    rejects), 'NEEDS CLOSE' (T-2468: an epic/story with at least one
    child ANYWHERE -- active or archived -- but none of them
    non-terminal, AND no open/unresolved `blocked_by` edge of its own
    (T-2475); the epic's own work is done, it just needs a rollup Done
    report and a close, not more decomposition -- T-1135/T-1137/T-1219
    sat here mislabelled for three weeks before this bucket existed),
    'NEEDS DECOMPOSITION' (a
    genuinely undecomposed epic/story -- no child ticket exists yet,
    anywhere, for it; T-2468 acceptance [1]: this bucket must NOT go
    empty just because NEEDS CLOSE now siphons off the finished-epic
    case), and 'DECOMPOSED, BEING WORKED' (T-2229: an epic/story with a
    non-terminal child already -- 'work it' has already effectively been
    done). No bucket is ever silently dropped: a ticket's age past
    threshold is always real,
    disclosed information, even when the recommended action is 'wait' or
    'check the children' rather than 'dispatch it'. See docs/guides/
    coordinator-scripts.md#_print_ticket_rot for the measured incidents
    each bucket split fixes. Printed unconditionally inside
    `_print_fleet_report`."""
    rotting = rotting_tickets()
    print(f"TICKET ROT: {len(rotting)}")
    ticket_tier = [
        t for t in rotting if t["tier"] == "ticket" and not t.get("runs_last")
    ]
    # T-2449 acceptance [3]: a leaf with an open OR unresolved blocker can
    # never land in NEEDS DISPATCH -- structurally, not incidentally, so
    # this split can never regress independently of `ticket_readiness`.
    still_blocked = [
        t for t in ticket_tier if t.get("open_blockers") or t.get("unresolved_blockers")
    ]
    leaves = [t for t in ticket_tier if t not in still_blocked]
    deferred = [t for t in rotting if t["tier"] == "ticket" and t.get("runs_last")]
    non_leaves = [t for t in rotting if t["tier"] != "ticket"]
    # T-2475: a non-leaf with its OWN still-open/unresolved blocked_by
    # edge (T-1599's live shape: an archived-done child covers only part
    # of the story, the rest is genuinely open and blocked) must never
    # land in NEEDS CLOSE -- there is no rollup to write, the work is not
    # finished. Route it into the same BLOCKED bucket a blocked leaf
    # already uses, BEFORE the has_active_child/has_any_child split below
    # ever runs on it, so a terminal-children-but-blocked story cannot
    # reach NEEDS CLOSE via that later split no matter how its children
    # look.
    non_leaves_blocked = [
        t for t in non_leaves if t.get("open_blockers") or t.get("unresolved_blockers")
    ]
    non_leaves = [t for t in non_leaves if t not in non_leaves_blocked]
    still_blocked = still_blocked + non_leaves_blocked
    # T-2468: split non-leaves into three, not two -- 'no children at all
    # yet' (still NEEDS DECOMPOSITION, acceptance [1]) is a different
    # action from 'children exist but every one is terminal' (NEEDS
    # CLOSE, acceptance [0]); an active (non-terminal) child still wins
    # first as DECOMPOSED, BEING WORKED, unchanged from before.
    decomposed = [t for t in non_leaves if t.get("has_active_child")]
    needs_close = [
        t
        for t in non_leaves
        if not t.get("has_active_child") and t.get("has_any_child")
    ]
    undecomposed = [
        t
        for t in non_leaves
        if not t.get("has_active_child") and not t.get("has_any_child")
    ]
    _print_rot_bucket("NEEDS DISPATCH", leaves)
    _print_rot_bucket(
        "BLOCKED (dependency not yet resolved)",
        still_blocked,
        "blocked_by names an id that is still open or does not resolve "
        "in either the active ledger or the archive; `--ticket {id}` "
        "names exactly which",
    )
    _print_rot_bucket(
        "DEFERRED (RUNS LAST)",
        deferred,
        "not dispatchable via `frob ticket start` while other tickets are "
        "open (RunsLastBlocked); re-prioritize or clear runs_last if this "
        "is stuck",
    )
    _print_rot_bucket(
        "NEEDS CLOSE",
        needs_close,
        "every child ticket is terminal (done/dropped, active ledger + "
        "archive) but {id} itself is still open; write a rollup Done "
        "report and close it, not decompose further",
    )
    _print_rot_bucket("NEEDS DECOMPOSITION", undecomposed)
    _print_rot_bucket(
        "DECOMPOSED, BEING WORKED",
        decomposed,
        "a non-terminal child ticket already carries parent={id}; check "
        "the children's progress, not this ticket",
    )


# frob:doc docs/guides/coordinator-scripts.md#quarantine
# frob:ticket T-2049
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestQuarantineState.test_reports_raised_with_\
# undisposed_count
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestQuarantineState.test_reports_clear_when_s\
# tore_says_cleared
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestQuarantineState.test_reports_clear_when_n\
# o_file
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestQuarantineState.test_unreadable_store_is_\
# unknown_never_clear
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestQuarantineState.test_non_dict_record_is_u\
# nknown
def quarantine_state() -> tuple[str, int]:
    """T-2049: `("raised" | "clear" | "unknown", undisposed_count)` for
    QUARANTINE -- the T-1693 quarantine circuit breaker's state, read
    where `fleet_status.py` is already looked at before a wave is
    dispatched (rather than only surfacing inside `frob ticket land`'s
    own multi-hundred-line output, the placement that let a raised
    quarantine cost roughly an hour of fleet-wide land throughput before
    anyone noticed, T-2049's own incident).

    A missing file means quarantine has never been raised: `"clear"`.
    An UNREADABLE or malformed file is `"unknown"`, never `"clear"` --
    `frob.verify._quarantine`'s own "cannot verify is never verified"
    rule applies here too: misreading unknown as clear would tell an
    operator it is safe to dispatch when it is not. `undisposed_count`
    counts findings whose `disposition` is still empty (mirrors `frob.
    verify._quarantine._all_findings_disposed`'s own check, duplicated
    here in raw-JSON form rather than importing that module, matching
    this script's existing subprocess/raw-file-only style)."""
    if not QUARANTINE.exists():
        return "clear", 0
    try:
        record = json.loads(QUARANTINE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "unknown", 0
    if not isinstance(record, dict):
        return "unknown", 0
    if record.get("cleared_at") is not None:
        return "clear", 0
    findings = record.get("findings")
    if not isinstance(findings, list):
        return "unknown", 0
    undisposed = sum(
        1 for f in findings if isinstance(f, dict) and not f.get("disposition")
    )
    return "raised", undisposed


# frob:doc docs/guides/coordinator-scripts.md#verify_queue_state
# frob:ticket T-2126
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestVerifyQueueState.test_reports_depth_and_o\
# ldest_age
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestVerifyQueueState.test_zero_depth_when_no_\
# file
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestVerifyQueueState.test_unreadable_queue_is\
# _unknown_never_zero
def verify_queue_state(*, now: datetime | None = None) -> tuple[int, float | None]:
    """`(depth, oldest_age_s)` for `.frob/verify-queue.json` -- T-2126,
    symmetric to `quarantine_state` immediately above: queue depth/age
    feeds `frob.verify._backpressure.block_until_watermark_advances`
    (the same function `_apply_backpressure` calls right after the
    quarantine override), so a deep/stale queue silently lengthens every
    land the same "silently changes land cost, and nothing prints it
    where a coordinator already looks before dispatch" way T-2049's own
    QUARANTINE line already fixed for the quarantine case -- this ticket
    was filed to measure whether the symmetry argument alone (T-2049's
    acceptance[4]) justifies adding it without waiting for a documented
    incident first, and concluded it does now that `frob verify status`
    (T-2290) already surfaces the identical depth/commits-since-watermark
    pair for the same reason.

    Depth alone (`len(entries)`) is a QUEUE-ENTRY count -- one per `frob
    ticket land` intent, which `frob verify status`'s own T-2290 docstring
    notes can undercount the real commit gap once a commit reaches `main`
    without going through a queued land. This script deliberately reports
    only depth/oldest-age here, not the full commit-gap reconciliation
    `commits_since_watermark` computes (a `git rev-list` spawn) -- adding
    that would duplicate `frob verify status`'s own number rather than
    add a distinct, ALWAYS-available-before-dispatch signal; a coordinator
    who wants the reconciled commit count already has `frob verify
    status` for that.

    A MISSING file means nothing is queued: `(0, None)`. An UNREADABLE or
    malformed file returns `(-1, None)` -- never a silent `(0, None)`,
    matching `quarantine_state`'s own "cannot verify is never verified"
    posture: misreading unknown as empty would tell a coordinator it is
    safe to dispatch when the real depth could not be determined at
    all."""
    if not VERIFY_QUEUE.exists():
        return 0, None
    try:
        entries = json.loads(VERIFY_QUEUE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return -1, None
    if not isinstance(entries, list):
        return -1, None
    oldest_age_s: float | None = None
    current = now if now is not None else datetime.now(UTC)
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        enqueued_at = entry.get("enqueued_at")
        if not isinstance(enqueued_at, str):
            continue
        try:
            enqueued = datetime.fromisoformat(enqueued_at)
        except ValueError:
            continue
        if enqueued.tzinfo is None:
            enqueued = enqueued.replace(tzinfo=UTC)
        age = (current - enqueued).total_seconds()
        if oldest_age_s is None or age > oldest_age_s:
            oldest_age_s = age
    return len(entries), oldest_age_s


# frob:doc docs/guides/coordinator-scripts.md#_ticket_readiness_lines
# frob:ticket T-2172
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintTicketReadiness.test_prints_dispatch\
# able_true
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintTicketReadiness.test_prints_lease_sc\
# ope_divergence_and_sibling_commits
def _ticket_readiness_lines(readiness: dict) -> list[str]:
    """Render one `TICKET <id>` readiness block (lease, main state/scope,
    scope divergence, open blockers, sibling-branch commits, final
    verdict) as plain text lines, doing none of the actual printing --
    the PURE-COMPUTE half of what used to be one function (ARCH103,
    T-2172: the combined shape mixed I/O, string-formatting, and 4
    decision points in one body, which is exactly the three-concerns-in-
    one-function smell this gate exists to catch). Keeping the
    formatting/branching logic here, with no `print` call anywhere in
    this function, is what lets `_print_ticket_readiness` below stay
    I/O-only.

    T-2196: the `main: ticket does not exist on main` line and the final
    `dispatchable: False` it now always pairs with are printed by the
    SAME code path (`main_info is None` gates both `ticket_readiness`'s
    verdict and this line) -- previously the line printed a true
    observation while the verdict below it silently ignored that
    observation, reading as `dispatchable: True` on the very next line
    (this ticket's own reproduction). Same fix shape for `open_blockers`:
    the reason is now stated in the same terms as the measured fact, not
    left as a bare `False`."""
    ticket_id = readiness["ticket_id"]
    lines = [f"TICKET {ticket_id}"]
    lease = readiness["lease"]
    if lease is None:
        lines.append("  lease: none")
    else:
        lines.append(
            f"  lease: recorded_at={lease.get('recorded_at')} "
            f"worktree={lease.get('worktree')} scope={lease.get('scope')}"
        )
    main_info = readiness["main"]
    if main_info is None:
        lines.append("  main: ticket does not exist on main")
    else:
        lines.append(f"  main: state={main_info['state']} scope={main_info['scope']}")
    if readiness["scope_diverges"]:
        lines.append(
            "  SCOPE DIVERGES -- the live lease's scope differs from "
            "main's declared scope; trust the lease, not the ticket file"
        )
    open_blockers = readiness.get("open_blockers", [])
    if open_blockers:
        lines.append(f"  BLOCKED BY (still open): {', '.join(open_blockers)}")
    # T-2449: reported under a DISTINCT heading from "still open" -- an
    # unresolved id (resolves in neither the active ledger nor the
    # archive) is unmeasured, not confirmed-blocking; conflating the two
    # is exactly the fail-loudly violation this ticket fixes.
    unresolved_blockers = readiness.get("unresolved_blockers", [])
    if unresolved_blockers:
        lines.append(
            "  BLOCKED BY (UNRESOLVED id, cannot confirm -- resolves in "
            f"neither the active ledger nor the archive): "
            f"{', '.join(unresolved_blockers)}"
        )
    commits = readiness["worktrees_with_commits"]
    if commits:
        lines.append(f"  ALREADY IMPLEMENTED on: {', '.join(commits)}")
    scope_collisions = readiness.get("scope_lease_collisions", [])
    for collision in scope_collisions:
        paths = ", ".join(collision["paths"])
        lines.append(
            f"  SCOPE COLLISION with live lease {collision['ticket_id']}: {paths}"
        )
    lines.append(f"  dispatchable: {readiness['dispatchable']}")
    return lines


# frob:doc docs/guides/coordinator-scripts.md#_print_ticket_readiness
# frob:ticket T-2172
def _print_ticket_readiness(readiness: dict) -> bool:
    """Print `_ticket_readiness_lines`'s rendered block and return
    `readiness["dispatchable"]` -- the I/O-ONLY half of the ARCH103 split
    above: this function does no string formatting and no branching of
    its own beyond the one loop over already-rendered lines, so it never
    re-triggers the mixed-concern signal `_ticket_readiness_lines` was
    split out to fix. T-2133: printed FIRST, ahead of the general ROOT/
    QUARANTINE/LEASES/WORKTREES report, so "is T-#### dispatchable" --
    the whole reason `--ticket` exists -- is the first thing a
    coordinator's eye lands on rather than buried below unrelated
    fleet-wide state."""
    for line in _ticket_readiness_lines(readiness):
        print(line)
    return readiness["dispatchable"]


# frob:doc docs/guides/coordinator-scripts.md#_land_status_lines
# frob:ticket T-2180
# frob:ticket T-2222
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintLandStatus.test_prints_invocations_a\
# nd_live_lock_holder
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintLandStatus.test_prints_no_live_holde\
# r_as_normal_resting_state_not_stale
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintLandStatus.test_guidance_line_uses_l\
# ive_count_not_raw_count
def _land_status_lines(
    invocations: list[dict],
    holder_pids: list[int],
    lock_exists: bool,
    load: tuple[float, int] | None,
    held_lease_count: int,
    live_lease_count_: int,
    swap: tuple[int, int] | None = None,
    orphaned_forkservers: int | None = None,
    concurrent_checks: int | None = None,
    stale_forkservers: int | None = None,
    forkserver_swap_kb: int | None = None,
) -> list[str]:
    """Render the LANDS/LAND LOCK/LOAD block as plain text lines from
    already-computed inputs -- the PURE-COMPUTE half of the ARCH103 split
    (mirrors `_ticket_readiness_lines`'s own precedent, T-2172): no
    `print` call, no I/O, so `_print_land_status` below stays I/O-only.
    `invocations` are `land_invocations`'s own dicts (ticket id, pids,
    elapsed, cpu, child_cpu). `holder_pids`/`lock_exists` distinguish a
    live-held lock from a resting/free one. `load` is `host_load`'s
    `(1-minute load average, MemAvailable kb)`, or `None` when unknown.
    `swap` is `swap_pressure`'s own `(swap_used_kb, swap_total_kb)`, or
    `None` when unknown (T-2249). `orphaned_forkservers` is `orphaned_
    forkserver_count`'s own reading, or `None` when `/proc` is unreadable
    (T-2443) -- surfaced alongside the swap-pressure guidance so '1 agent
    (SWAP ...)' turns from an unexplained number into an actionable one: a
    coordinator seeing both together knows whether the specific, fixable
    T-2443 leak is the cause before spending time investigating anything
    else.

    T-2517: `stale_forkservers` (`stale_forkserver_count`'s own reading)
    and `forkserver_swap_kb` (`forkserver_swap_held_kb`'s own reading) are
    printed as their OWN separate lines, never folded into `orphaned_
    forkservers` -- collapsing them was the exact incident this ticket was
    filed from (`ORPHANED FORKSERVERS: 0` read as "nothing wrong" while
    82 stale, live-parented pools held 12GB of swap that the orphan-only
    reading structurally could not see). All three stay independently
    "unknown"-vs-real-zero, matching every other best-effort number this
    function already renders.

    T-2222: `held_lease_count` (the raw `len(leases())`) and `live_lease_
    count_` (`live_lease_count(leases())`, T-2222's own live-vs-reclaimable
    classification) are BOTH shown, but the concurrency GUIDANCE clause
    (`_swap_guidance`, T-2249) is computed from `live_lease_count_` and
    `swap` together, never the raw lease count alone -- the measured
    incident this fixes: '6 lease(s) -- guidance is 3-4 agent concurrent'
    read as 6 live agents when only 4 were. The trailing underscore on
    the parameter avoids shadowing the module-level `live_lease_count`
    function of the same name.

    Two folded-in fixes, neither separately ticketed (both observed
    causing a wrong read of this exact section): the LAND LOCK line for
    an idle, no-live-holder lock file now reads as the NORMAL resting
    state (flock is kernel-released on holder death) rather than
    'stale', which had already contributed to one retracted ticket
    claiming a deadlock; and each land's `cpu=` figure now also reports
    `child_cpu_s` (`land_invocations`' own field) when nonzero, so a
    healthy land running `frob check` as a child process no longer reads
    as a near-zero-CPU stall."""
    lines = [f"LANDS IN FLIGHT: {len(invocations)}"]
    for inv in invocations:
        # T-2193: land_invocations() drops any row it cannot parse a
        # ticket id from, so ticket_id is always real here -- never None.
        pids = ",".join(str(p) for p in inv["pids"])
        child_cpu_s = inv.get("child_cpu_s", 0)
        child_part = f" (+{child_cpu_s}s in children)" if child_cpu_s else ""
        lines.append(
            f"  {inv['ticket_id']} pids={pids} elapsed={inv['elapsed_s']}s "
            f"cpu={inv['cpu_s']}s{child_part}"
        )

    if holder_pids:
        lines.append(f"LAND LOCK: held, live holder pid(s)={holder_pids}")
    elif lock_exists:
        lines.append(
            "LAND LOCK: file exists, no live holder -- normal resting "
            "state (flock releases instantly on holder death; the "
            "recorded pid may be reused, do not trust it or lock age)"
        )
    else:
        lines.append("LAND LOCK: free")

    if load is None:
        lines.append("LOAD: unknown (/proc/loadavg or /proc/meminfo unreadable)")
    else:
        load_1min, mem_available_kb = load
        mem_available_gb = mem_available_kb / (1024 * 1024)
        lines.append(
            f"LOAD {load_1min:.1f}  MEM {mem_available_gb:.1f}GB avail  "
            f"{live_lease_count_} live lease(s) ({held_lease_count} total) "
            f"-- guidance is {_swap_guidance(swap)}"
        )
    lines.extend(
        _forkserver_status_lines(
            orphaned_forkservers,
            stale_forkservers,
            forkserver_swap_kb,
            concurrent_checks,
        )
    )
    return lines


def _forkserver_status_lines(
    orphaned_forkservers: int | None,
    stale_forkservers: int | None,
    forkserver_swap_kb: int | None,
    concurrent_checks: int | None,
) -> list[str]:
    """The four forkserver/check lines (`ORPHANED FORKSERVERS`, `STALE
    FORKSERVERS`, `SWAP HELD BY FORKSERVERS`, `CONCURRENT CHECKS`) --
    ARCH001 split of `_land_status_lines` (T-2517), pure formatting, no
    behavior change from inlining. T-2517: the three forkserver numbers
    stay on THREE separate lines, never collapsed into one -- see `_land_
    status_lines`'s own docstring for why."""
    lines: list[str] = []
    if orphaned_forkservers is None:
        lines.append("ORPHANED FORKSERVERS: unknown (/proc unreadable)")
    elif orphaned_forkservers > 0:
        lines.append(
            f"ORPHANED FORKSERVERS: {orphaned_forkservers} reparented to "
            "init (T-2443 leak signature -- SIGTERM them or wait for the "
            "next `frob check`'s own startup reaper)"
        )
    else:
        lines.append("ORPHANED FORKSERVERS: 0")
    if stale_forkservers is None:
        lines.append("STALE FORKSERVERS: unknown (/proc unreadable)")
    elif stale_forkservers > 0:
        lines.append(
            f"STALE FORKSERVERS: {stale_forkservers} idle >1h with no check "
            "running (T-2517 leak signature -- SIGTERM them; safe only "
            "because CONCURRENT CHECKS is 0 right now)"
        )
    else:
        lines.append("STALE FORKSERVERS: 0")
    if forkserver_swap_kb is None:
        lines.append("SWAP HELD BY FORKSERVERS: unknown (/proc unreadable)")
    else:
        lines.append(
            f"SWAP HELD BY FORKSERVERS: {forkserver_swap_kb / (1024 * 1024):.1f}GB "
            "(sum of VmSwap, orphaned+stale+live-parented alike, T-2517)"
        )
    if concurrent_checks is None:
        lines.append("CONCURRENT CHECKS: unknown (/proc unreadable)")
    else:
        lines.append(f"CONCURRENT CHECKS: {concurrent_checks} (T-2473, advisory)")
    return lines


# frob:doc docs/guides/coordinator-scripts.md#_print_land_status
# frob:ticket T-2180
# frob:ticket T-2222
def _print_land_status() -> None:
    """Print the LANDS section: distinct `land_invocations` (T-2180's own
    fix for the ~4x process-line overcount), each with its pids, elapsed
    time, and CPU time, followed by `land.lock` holder liveness from
    `land_lock_holder_pids`'s `/proc` scan, followed by a LOAD line
    (`host_load`'s 1-minute load average and `MemAvailable`, alongside the
    live-vs-total held-lease counts, T-2222) against this host's recorded
    3-4 concurrent agent operational guidance, followed by a CONCURRENT
    CHECKS line (`concurrent_check_count`, T-2473) -- the number of live
    `frob check` processes on this host, previously invisible short of a
    manual `ps` scan (T-2473's own filed measurement: 12 concurrent
    checks went unnoticed until someone checked by hand). Advisory only:
    this script reports the count, it never limits or queues anything.
    Printed unconditionally
    inside `_print_fleet_report`, in the standing report a coordinator
    already runs before every dispatch and every land -- acceptance [4]'s
    own 'automatic over commands' requirement: `frob ticket wave --agents
    N` already computes this kind of thing and gets skipped because it is
    a separate command a coordinator has to remember to run. The LOAD line
    was added alongside the other two because it reads the same process-
    table-adjacent state and answers the same standing question this
    section already exists to answer ('is it safe to dispatch another
    agent right now') -- six concurrent agents against a documented 3-4
    agent cap went unnoticed on this host until someone checked by
    hand. T-2517: also computes `concurrent_check_count` ONCE and passes it
    into `stale_forkserver_count` (whose own "0 unless no check is
    running" precondition needs that exact reading, not a re-measured
    one) alongside `forkserver_swap_held_kb` -- three separate forkserver
    numbers (orphaned/stale/swap-held), never collapsed into one, per the
    ticket's own explicit requirement. ARCH103 (T-2172 precedent): all
    formatting/branching lives in `_land_status_lines`; this function only
    gathers inputs and prints."""
    invocations = land_invocations()
    holder_pids = land_lock_holder_pids(REPO)
    lock_path = REPO / ".frob" / "land.lock"
    load = host_load()
    swap = swap_pressure()
    held = leases()
    concurrent_checks = concurrent_check_count()
    for line in _land_status_lines(
        invocations,
        holder_pids,
        lock_path.exists(),
        load,
        len(held),
        live_lease_count(held),
        swap,
        orphaned_forkserver_count(),
        concurrent_checks,
        stale_forkserver_count(concurrent_checks=concurrent_checks),
        forkserver_swap_held_kb(),
    ):
        print(line)


# frob:doc docs/guides/coordinator-scripts.md#_print_fleet_report
# frob:ticket T-2172
# frob:ticket T-2180
# frob:doc docs/guides/coordinator-scripts.md#verify_queue_state
# frob:ticket T-2126
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestFleetStatusMainVerifyQueue.test_prints_de\
# pth_and_age_when_nonempty
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestFleetStatusMainVerifyQueue.test_prints_em\
# pty_when_zero_depth
def _print_verify_queue_line() -> None:
    """Print the VERIFY QUEUE line `_print_fleet_report` places right
    after QUARANTINE (T-2126) -- split into its own function (ARCH001,
    same reasoning as every other `_print_*` helper this module already
    factors out) rather than inlined."""
    depth, oldest_age_s = verify_queue_state()
    if depth < 0:
        # frob:waive RENDER001 reason="this whole script deliberately never imports \
        # frob.* (must stay usable without a built venv/native extensions) -- every \
        # other print() in this file is the same bare-stdout style, grandfathered by \
        # RENDER001's does-not-worsen gate only because it predates T-2280; this is a \
        # NEW site in the identical, already-established style, not a new exception"
        print("VERIFY QUEUE UNKNOWN -- .frob/verify-queue.json unreadable")
    elif depth == 0:
        # frob:waive RENDER001 reason="same as above -- established bare-print style"
        print("VERIFY QUEUE empty")
    else:
        age_note = (
            f", oldest {oldest_age_s:.0f}s old" if oldest_age_s is not None else ""
        )
        # frob:waive RENDER001 reason="same as above -- established bare-print style"
        print(f"VERIFY QUEUE depth={depth}{age_note}")


# frob:ticket T-2182
# frob:ticket T-2222
# frob:ticket T-2654
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintFleetReport.test_prints_all_four_sec\
# tions
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintFleetReport.test_leases_section_show\
# s_classification_per_lease
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintFleetReport.test_leases_section_repo\
# rts_ledger_leak_missing_from_held
def _print_fleet_report(dirt: list[str], idle_seconds: int) -> None:
    """Print the ROOT/LANDS/QUARANTINE/LEASES/WORKTREES sections `main`
    used to print inline -- split out (ARCH001/ARCH103, T-2172) as the
    other half of `main`'s decomposition, alongside
    `_print_ticket_readiness` above. `dirt` is passed in rather than
    recomputed so `main` (the caller) stays the single place that calls
    `root_dirt()` and can reuse the result for its own exit-code
    decision. T-2180 added the LANDS section between ROOT and QUARANTINE
    -- "which lands are in flight" is exactly the kind of fleet-wide,
    always-relevant state the other four sections already are. T-2182
    added the TICKET ROT section right after LANDS, for the same reason:
    a coordinator already reads this report before every dispatch, and
    ticket rot is exactly the kind of "forgot we have a stack of things"
    signal that belongs where dispatch decisions are actually made.

    T-2222: the LEASES section now prints each record's own `lease_
    classification` (`"live"`/`"reclaimable"`/`"root-resident"`) next to
    it, and the section header itself carries both the raw count and the
    live count -- a lease that reads as reclaimable or root-resident is
    never silently indistinguishable from a live agent's own lease here,
    the same fix `_land_status_lines`'s LOAD line above already applies
    to the concurrency guidance clause.

    T-2126 added the VERIFY QUEUE line right after QUARANTINE, same
    reasoning: queue depth/age silently changes land cost the same way
    a raised quarantine does, and belongs where a coordinator already
    looks before dispatch.

    T-2654: the LEASES section itself is now printed by
    `_print_leases_section` (pulled out the same way
    `_print_worktrees_section` already was, to keep this function's own
    line count from growing every time LEASES gains a new signal) -- its
    header also reports a `blocked-open` count
    (`blocked_in_progress_leases`), and any row for an in-progress
    ticket whose own `blocked_by` still names an open blocker gets a
    `[BLOCKED-OPEN: ...]` suffix -- distinct from the `LEAK` tag, since
    this does not depend on worktree liveness at all: a lease held by a
    ticket that cannot proceed (blocked, in-progress) is pure waste
    whether or not its worktree is still findable."""
    print(f"ROOT {'DIRTY -- do not dispatch' if dirt else 'CLEAN'}")
    for line in dirt:
        print(f"  {line}")

    _print_land_status()
    _print_ticket_rot()

    state, undisposed = quarantine_state()
    if state == "raised":
        print(
            f"QUARANTINE RAISED -- {undisposed} undisposed finding(s); deferred "
            "landing is OFF, every land runs fully-synchronous verification "
            "(T-1693) -- clear with `frob verify dispose`"
        )
    elif state == "unknown":
        print(
            "QUARANTINE UNKNOWN -- .frob/quarantine.json unreadable; treat as "
            "raised (cannot verify is never verified)"
        )
    else:
        print("QUARANTINE clear")

    _print_verify_queue_line()

    _print_leases_section()

    _print_worktrees_section(idle_seconds)


# frob:doc docs/guides/coordinator-scripts.md#_leases_report
# frob:ticket T-2654
def _leases_report() -> tuple[str, list[str]]:
    """Compute the `LEASES` section's header line and row strings --
    the gather half of the ARCH001/ARCH103 `_print_fleet_report` split
    (T-2654), kept separate from `_print_leases_section`'s own I/O so
    the decision-point-heavy combination logic and the printing loop
    are each a single, simple concern rather than one function mixing
    I/O, string-formatting, AND every decision point (ARCH103's own
    complaint when this lived in one function). Combines three sources
    into one row set: `leases()` (`held`, file-based),
    `in_progress_ticket_scope_leases()` (T-2651's ledger-read fallback
    for a lease whose file was pruned -- `missing`, `LEAK`-tagged when
    `leaked`), and `blocked_in_progress_leases()` (T-2654: an
    in-progress ticket whose `blocked_by` still names an open blocker --
    `BLOCKED-OPEN`-tagged, independent of whether a worktree/lease-file
    can be found at all, since a blocked ticket's lease is pure waste
    regardless)."""
    held = leases()
    live_count = live_lease_count(held)
    held_ids = {record.get("ticket_id") for record in held}
    # T-2651: `held` is file-based (`.git/frob-leases/*.json`) and can be
    # BLIND to a lease whose file has already been pruned while its
    # ticket is still in-progress -- the leak signature. Enumerate
    # in-progress tickets directly off the ledger and report any that
    # `held` missed, distinctly.
    ledger_leases = in_progress_ticket_scope_leases()
    missing = [e for e in ledger_leases if e["ticket_id"] not in held_ids]
    leaked = [e for e in missing if e["leaked"]]
    # T-2654: separate from the no-worktree LEAK signature above -- an
    # in-progress ticket whose own blockers are still open cannot proceed
    # regardless of whether its worktree is still findable, so any lease
    # it holds is pure waste too.
    blocked_by_id = {
        entry["ticket_id"]: entry["open_blockers"]
        for entry in blocked_in_progress_leases()
    }
    header = (
        f"LEASES {len(held) + len(missing)} ({live_count} live, "
        f"{len(leaked)} leaked, {len(blocked_by_id)} blocked-open)"
    )
    rows = [
        _lease_row(
            str(record.get("ticket_id")),
            Path(record.get("worktree", "?")).name,
            lease_classification(record),
            blocked_by_id,
        )
        for record in held
    ] + [
        _lease_row(
            entry["ticket_id"],
            entry["worktree"] or "<no worktree>",
            "LEAK" if entry["leaked"] else "live",
            blocked_by_id,
        )
        for entry in missing
    ]
    return header, rows


# frob:doc docs/guides/coordinator-scripts.md#_print_leases_section
# frob:ticket T-2654
def _print_leases_section() -> None:
    """Print the `LEASES` section: `_print_fleet_report`'s own LEASES
    block, pulled out (ARCH001/ARCH103, T-2654) alongside the existing
    `_print_worktrees_section` split so the parent function's line count
    does not grow every time this section gains a new signal -- T-2654's
    own `blocked_in_progress_leases` addition is exactly that kind of
    growth. All the gathering/combination logic lives in `_leases_report`
    above; this is pure I/O over its result."""
    header, rows = _leases_report()
    print(header)
    for row in rows:
        print(row)


# frob:doc docs/guides/coordinator-scripts.md#_lease_row
# frob:ticket T-2654
def _lease_row(
    ticket_id: str, worktree_name: str, classification: str, blocked_by_id: dict
) -> str:
    """One `LEASES` section row: `"  T-#### -> name  [classification]"`,
    plus a trailing `[BLOCKED-OPEN: ...]` suffix (T-2654) when
    `ticket_id` is a key in `blocked_by_id` (`blocked_in_progress_
    leases()`'s own `{ticket_id: open_blockers}` map) -- shared by both
    the held-lease and ledger-missing loops in `_print_leases_section` so
    the two loops do not each duplicate the same suffix logic."""
    line = f"  {ticket_id} -> {worktree_name}  [{classification}]"
    if ticket_id in blocked_by_id:
        line += f"  [BLOCKED-OPEN: {', '.join(blocked_by_id[ticket_id])}]"
    return line


# frob:doc docs/guides/coordinator-scripts.md#_print_worktrees_section
# frob:ticket T-2599
def _print_worktrees_section(idle_seconds: int) -> None:
    """Print the `WORKTREES (STRANDED: N)` section and one line per
    worktree, each idle-looking one tagged with its
    `worktree_content_classification` verdict -- `_print_fleet_report`'s
    own WORKTREES block, pulled out (ARCH001 split, zero behavior
    change) so classifying every idle worktree's content happens ONCE
    per worktree (a `stranded_count` pre-pass followed by a separate
    print loop used to call `worktree_content_classification` twice per
    idle worktree; this computes each verdict once and reuses it for
    both the header count and its own row)."""
    wt_rows = worktrees(idle_seconds)
    verdicts: dict[str, str] = {}
    for name, _age, idle in wt_rows:
        if idle:
            verdicts[name] = worktree_content_classification(
                WORKTREES / name, ticket_id=_worktree_ticket_id(name)
            )[0]
    stranded_count = sum(1 for v in verdicts.values() if v == "STRANDED")
    print(f"WORKTREES (STRANDED: {stranded_count})")
    for name, age, idle in wt_rows:
        mins = "unknown" if age < 0 else f"{age // 60}m"
        tail = "  IDLE?" if idle else ""
        if idle:
            tail += f"  [{verdicts[name]}]"
        # frob:waive RENDER001 reason="pre-existing bare print, unchanged text -- \
        # T-2126's own new _print_verify_queue_line() insertion above shifted this \
        # line's number relative to merge-base, which the does-not-worsen gate reads \
        # as a new site; same established bare-stdout style as every other print in \
        # this deliberately frob.*-import-free script"
        print(f"  {name:28} last-commit {mins:>9}{tail}")


# frob:doc docs/guides/coordinator-scripts.md#_print_all_ticket_readiness
# frob:ticket T-2180
def _print_all_ticket_readiness(tickets: list[str]) -> bool:
    """Print `_print_ticket_readiness` for every id in `tickets`, in
    order, returning `True` only if ALL of them are dispatchable --
    `main`'s own multi-`--ticket` loop, pulled out (ARCH103, same
    precedent as `_print_fleet_report`'s own T-2172 split) so `main`
    stays a thin sequence of calls rather than mixing this loop's own
    branching into its already-multi-concern body."""
    ticket_ok = True
    for ticket_id in tickets:
        ticket_ok = _print_ticket_readiness(ticket_readiness(ticket_id)) and ticket_ok
    return ticket_ok


# frob:doc docs/guides/coordinator-scripts.md#_print_scope_intersections
# frob:ticket T-2180
def _print_scope_intersections(tickets: list[str]) -> None:
    """Print `scope_intersections(tickets)`'s own `SCOPE INTERSECTIONS:
    N` count and each colliding pair -- `main`'s own 2+-`--ticket`
    branch, pulled out (ARCH103) alongside `_print_all_ticket_readiness`
    above."""
    collisions = scope_intersections(tickets)
    # frob:waive RENDER001 reason="pre-existing bare print, unchanged text -- shifted \
    # by T-2126's own new _print_verify_queue_line() insertion above, same line-drift \
    # false-positive as the WORKTREES print in _print_fleet_report"
    print(f"SCOPE INTERSECTIONS: {len(collisions)}")
    for collision in collisions:
        globs = ", ".join(
            f"{ga!r}<->{gb!r}" for ga, gb in collision["overlapping_globs"]
        )
        # frob:waive RENDER001 reason="same line-drift false-positive as above"
        print(f"  {collision['a']} x {collision['b']}: {globs}")


# frob:doc docs/guides/coordinator-scripts.md#fleet_status-main
# frob:ticket T-1863
# frob:ticket T-2172
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestFleetStatusMain.test_exit_zero_when_clean
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestFleetStatusMain.test_exit_one_when_dirty
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestFleetStatusMainQuarantine.test_prints_rai\
# sed_with_undisposed_count_and_consequence
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestFleetStatusMainQuarantine.test_prints_cle\
# ar
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestFleetStatusMainQuarantine.test_prints_unk\
# nown_as_unsafe
def main() -> int:
    """Print (T-2172: ticket readiness FIRST, when `--ticket` is
    given, ahead of the general fleet report) root/lease/worktree/
    quarantine state; exit 1 when root is dirty OR (T-2133) `--ticket
    T-####` was given and `ticket_readiness` says it is not dispatchable.
    T-2049: the quarantine line is printed unconditionally (not just on
    --verbose or similar) because this is the ONE place a coordinator
    already looks before dispatching a wave -- see `quarantine_state`'s
    own docstring for the incident this answers.

    T-2172 (ARCH001/ARCH103): this function used to inline all
    of ROOT/QUARANTINE/LEASES/WORKTREES/TICKET printing itself (78
    lines, 14 decision points) -- now it only parses args, calls
    `root_dirt()` once, and delegates the two print blocks to
    `_print_ticket_readiness` and `_print_fleet_report`, keeping the
    ordering/exit-code decision (the actual logic worth reading in one
    place) as the only thing left here.

    T-2180: `--ticket` now accepts MULTIPLE ids (repeatable flag) --
    each is printed via `_print_ticket_readiness` in turn, and when 2+
    are given, `scope_intersections` prints every pairwise (and
    lease-external) scope collision across the whole set, so a
    coordinator can vet a wave for contention before dispatching it, in
    the same standing report rather than a separate command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--idle-minutes", type=int, default=20)
    parser.add_argument(
        "--ticket",
        action="append",
        default=None,
        help="T-2133: also print per-ticket readiness (lease, main scope/"
        "state divergence, sibling-branch commits) FIRST, ahead of the "
        "general report, and gate the exit code on "
        "ticket_readiness()['dispatchable'], not just root cleanliness. "
        "Repeatable (T-2180): passing --ticket more than once also "
        "prints every pairwise scope intersection across the given ids.",
    )
    args = parser.parse_args()

    tickets: list[str] = args.ticket or []
    ticket_ok = _print_all_ticket_readiness(tickets)
    if len(tickets) > 1:
        _print_scope_intersections(tickets)

    dirt = root_dirt()
    _print_fleet_report(dirt, args.idle_minutes * 60)

    return 1 if (dirt or not ticket_ok) else 0


if __name__ == "__main__":
    raise SystemExit(main())
