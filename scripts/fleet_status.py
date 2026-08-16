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


# frob:doc docs/guides/coordinator-scripts.md#root_dirt
# frob:ticket T-1863
# frob:tests tests/unit/test_coordinator_scripts.py::TestRootDirt.test_clean_repo
# frob:tests tests/unit/test_coordinator_scripts.py::TestRootDirt.test_dirty_repo
def root_dirt() -> list[str]:
    """Porcelain lines for the root checkout; empty means safe to dispatch."""
    out = _git(["status", "--short", "--porcelain"], REPO)
    return [line for line in out.splitlines() if line.strip()]


# frob:doc docs/guides/coordinator-scripts.md#quarantine
#: The T-1693 quarantine circuit breaker's current record (`frob.verify.
#: _quarantine`'s own store) -- read directly as raw JSON, mirroring
#: `LEASES`'s own pattern, so this script stays import-light rather than
#: depending on the `frob` package being installed.
QUARANTINE = REPO / ".frob" / "quarantine.json"


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


# frob:doc docs/guides/coordinator-scripts.md#ticket_frontmatter_on_main
# frob:ticket T-2133
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain.test_reads_state_\
# and_scope
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain.test_missing_tick\
# et_returns_none
def ticket_frontmatter_on_main(ticket_id: str) -> dict | None:
    """`{"state": ..., "scope": [...], "blocked_by": [...]}` parsed from
    `main:tickets/<id>/ticket.md`'s YAML frontmatter, or `None` if the
    ticket does not exist on `main` at all. Hand-parsed (no `import yaml`,
    matching this script's own "no `frob` import, plain stdlib" contract
    from its module docstring) against the narrow shape `frob ticket`
    actually writes: a flat `key: value` line for `state`, and `scope:`/
    `blocked_by:` blocks of `- item` list lines directly beneath each key
    (a ticket with no blockers omits the `blocked_by:` key entirely rather
    than writing an empty block, so its absence parses to `[]`, same as
    the tests' own mocked shape that never sets the key at all -- see
    `ticket_readiness`'s `.get("blocked_by", [])` read of this dict).
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
        return None
    lines = text.splitlines()
    state = None
    scope: list[str] = []
    blocked_by: list[str] = []
    block: list[str] | None = None
    for line in lines:
        if line.startswith("state:"):
            state = line.split(":", 1)[1].strip()
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
    return {"state": state, "scope": scope, "blocked_by": blocked_by}


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
def _open_blocker_ids(blocked_by: Sequence[str]) -> list[str]:
    """Which of `blocked_by`'s ticket ids are still OPEN on `main` -- not
    `done`/`dropped`. An id that does not resolve on `main` at all (a
    typo, or a blocker cited before it was ever filed) counts as open
    too: it is certainly not `done`/`dropped`, and treating "cannot even
    confirm this blocker is resolved" as "resolved" would recreate the
    exact `dispatchable: True` overclaim T-2196 exists to close, one
    level removed. T-2196: this is the "blocked_by edges" half of the
    audit its own acceptance criterion [2] asks for -- previously
    `ticket_readiness` never looked at `blocked_by` at all, so a ticket
    correctly blocked on an open dependency still read as dispatchable."""
    open_ids: list[str] = []
    for blocker_id in blocked_by:
        blocker_info = ticket_frontmatter_on_main(blocker_id)
        blocker_state = blocker_info["state"] if blocker_info is not None else None
        if blocker_state not in ("done", "dropped"):
            open_ids.append(blocker_id)
    return open_ids


# frob:ticket T-2196
def ticket_readiness(ticket_id: str) -> dict:
    """T-2133: the single per-ticket answer to "given T-####, is it
    actually dispatchable?" -- `fleet_status.py` already answers the
    fleet-wide half of pre-dispatch safety (root cleanliness, quarantine,
    idle worktrees); this is the missing per-ticket half, combining
    `ticket_lease`, `ticket_frontmatter_on_main`, and
    `worktrees_touching_ticket` into one dict:

    - `lease`: the live lease record (`ticket_lease`), or `None`.
    - `main`: `ticket_frontmatter_on_main`'s `{"state", "scope",
      "blocked_by"}`, or `None` if the ticket does not exist on `main`
      yet.
    - `scope_diverges`: `True` when a live lease exists AND its `scope`
      differs from `main`'s declared scope -- T-2133's own "single
      highest-value signal": a coordinator reading `main:tickets/<id>/
      ticket.md` alone, while a lease has since narrowed (or widened) the
      real working scope inside a worktree, draws a stale conclusion
      about what the ticket actually touches (observed twice: once nearly
      releasing a healthy lease, once asking an agent to redo a narrowing
      it had already done).
    - `worktrees_with_commits`: from `worktrees_touching_ticket`, checked
      against the LIVE lease's scope when one is held (else `main`'s
      declared scope, same "trust the lease" rule `scope_diverges` above
      already applies) -- a non-empty list means the ticket is already
      implemented elsewhere (a real commit touching declared-scope files),
      not merely a ledger edit or a lease.
    - `open_blockers`: ids from `main`'s `blocked_by` that are not yet
      `done`/`dropped` on `main` (`_open_blocker_ids`) -- `[]` when the
      ticket does not exist on `main` (nothing to read `blocked_by` off
      of yet).
    - `dispatchable`: T-2196 fixed the defect class this field used to
      embody -- "the report knows more than the verdict uses". Every
      fact this function MEASURES now gates the verdict, not a subset:
      `main` must actually EXIST (a ticket absent from `main` is never
      dispatchable, no matter how clean everything else looks -- the
      T-2195 incident this ticket was filed from: a coordinator dispatched
      an agent to a ticket id that did not exist on `main` yet, and the
      old verdict endorsed it), no live lease may be held, no sibling
      worktree may already carry scope-matching commits, `main`'s own
      state must not be `done`/`dropped`/`in-progress`, `blocked_by` must
      have no open blocker, and the lease's scope must not have diverged
      from `main`'s declared scope. `True` only when every one of those
      checks passes. This is the field a caller (or `main`'s own exit
      code) gates dispatch on."""
    lease = ticket_lease(ticket_id)
    main_info = ticket_frontmatter_on_main(ticket_id)
    main_scope = main_info["scope"] if main_info is not None else None
    scope_diverges = (
        lease is not None
        and main_scope is not None
        and set(lease.get("scope", [])) != set(main_scope)
    )
    # T-draft-05563e8d: the LIVE scope (lease, if held) is what a real
    # implementation commit would actually touch -- mirrors the "trust
    # the lease, not the ticket file" rule `scope_diverges` already
    # established, applied here to the implementation-evidence check too.
    effective_scope = lease.get("scope", []) if lease is not None else main_scope
    worktrees_with_commits = worktrees_touching_ticket(ticket_id, effective_scope or ())
    state_on_main = main_info["state"] if main_info is not None else None
    open_blockers = (
        _open_blocker_ids(main_info.get("blocked_by", []))
        if main_info is not None
        else []
    )
    dispatchable = (
        main_info is not None
        and lease is None
        and not worktrees_with_commits
        and state_on_main not in ("done", "dropped", "in-progress")
        and not open_blockers
        and not scope_diverges
    )
    return {
        "ticket_id": ticket_id,
        "lease": lease,
        "main": main_info,
        "scope_diverges": scope_diverges,
        "worktrees_with_commits": worktrees_with_commits,
        "open_blockers": open_blockers,
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
# frob:ticket T-2180
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestLandProcessRows.test_parses_matching_rows\
# _and_skips_others
def land_process_rows() -> list[dict]:
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

    Known residual limitation (playbook section 13): a plain argv
    substring match cannot distinguish a REAL `frob ticket land`
    invocation from another process whose command line merely CONTAINS
    that text -- e.g. a coordinator's own wait-loop shell running
    `pgrep -f "frob ticket land T-..."`. Such a row parses no ticket id
    (`_parse_land_argv_ticket_id` returns `None`) and `land_invocations`
    DROPS any row it cannot parse a ticket id from (T-2193: an earlier
    version reported it as its own `ticket_id=None` invocation instead,
    which still inflated the reported count by one per such row --
    dropping it is the fix), so this residual noise never reaches the
    printed report at all. A caller auditing raw process-table rows
    directly (bypassing `land_invocations`'s own filtering) still sees
    it here."""
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
        rows.append({"pid": pid, "etimes": etimes, "cputime": cputime_s, "argv": argv})
    return rows


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
    row is the one that actually started the invocation), and `cpu_s`
    (the MAX parsed CPU time across the group). CPU time is reported
    precisely because content alone cannot distinguish a live land from a
    dead attempt's residue -- a killed land's staged diff is byte-
    identical across retries because it is the same work -- but CPU time
    discriminates immediately: a wedged/dead process stops accumulating
    CPU while a live one keeps climbing."""
    rows = land_process_rows()
    groups: dict[str, list[dict]] = {}
    for row in rows:
        ticket_id = _parse_land_argv_ticket_id(row["argv"])
        if ticket_id is None:
            continue
        groups.setdefault(ticket_id, []).append(row)

    invocations = [
        {
            "ticket_id": ticket_id,
            "pids": [r["pid"] for r in group_rows],
            "elapsed_s": max(r["etimes"] for r in group_rows),
            "cpu_s": max(_parse_ps_cpu_time(r["cputime"]) for r in group_rows),
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


# frob:doc docs/guides/coordinator-scripts.md#_parse_ticket_ledger_file
# frob:ticket T-2182
# frob:ticket T-2200
def _parse_ticket_ledger_file(path: Path) -> dict | None:
    """`{"id", "state", "priority", "tier", "created", "runs_last"}`
    parsed directly from a `tickets/<id>/ticket.md` file's own YAML
    frontmatter -- hand-parsed flat `key: value` lines (matching `ticket_
    frontmatter_on_main`'s own "no `import yaml`" contract), reading a
    LOCAL file on disk rather than `git show main:...` since `rotting_
    tickets` below reports the live, uncommitted ledger state a
    coordinator's own dispatch decision actually depends on. Returns
    `None` if the file is unreadable, or if `id`/`state`/`priority`/
    `created` cannot all be parsed -- a ticket this function cannot fully
    read is excluded from the rotting set entirely rather than guessed at
    (a missing `tier:` line defaults to `ticket`, mirroring `TicketTier`'s
    own default for a ledger row written before tiers existed, per
    `frob.tickets._models`'s own docstring).

    T-2200: `runs_last` is read as the STRUCTURED ledger field
    `frob ticket new --runs-last`/`frob ticket runs-last` writes (`runs_
    last: true`/`runs_last: false`), never inferred from the ticket's
    title text -- T-1614's own title happens to start with the literal
    string 'RUNS LAST', which is exactly the lexical shortcut that would
    silently miss every OTHER `runs_last` ticket whose title does not
    happen to say so. A missing `runs_last:` line (a ledger row written
    before the field existed) defaults to `False`, matching `Ticket.
    runs_last`'s own model default in `frob.tickets._models`."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if line == "---":
            continue
        for key in ("id", "state", "priority", "tier", "created", "runs_last"):
            prefix = f"{key}:"
            if line.startswith(prefix):
                value = line[len(prefix) :].strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                    value = value[1:-1]
                fields[key] = value
    if not {"id", "state", "priority", "created"} <= fields.keys():
        return None
    return {
        "id": fields["id"],
        "state": fields["state"],
        "priority": fields["priority"],
        "tier": fields.get("tier", "ticket"),
        "created": fields["created"],
        "runs_last": fields.get("runs_last", "false").strip().lower() == "true",
    }


# frob:doc docs/guides/coordinator-scripts.md#rotting_tickets
# frob:ticket T-2182
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
    `tickets/archive/**`, which holds only terminal tickets) whose
    priority-specific rot-day threshold (`_rot_day_thresholds`) has been
    crossed since its own `created` date -- derived ENTIRELY from the
    ledger's own structured fields (state, priority, the `created`
    timestamp) compared against the configured thresholds, never by
    parsing `frob check`'s rendered TICK004 diagnostic text, which is a
    rendering that changes wording independent of this comparison
    (acceptance [1]). Mirrors `frob.gates._tickets_gate._tick004_queue_
    rot`'s own selection exactly (same states considered, same threshold
    source) so this script's count agrees with the gate's own finding
    rather than silently drifting from it.

    Each entry: `id`, `priority`, `tier` ('ticket'/'story'/'epic'),
    `state`, `age_days`, `threshold_days`, `runs_last` (T-2200). Malformed
    `created` dates (unparseable, or a ticket file `_parse_ticket_ledger_
    file` could not fully read) are skipped rather than guessed at."""
    if not TICKETS_DIR.is_dir():
        return []
    thresholds = _rot_day_thresholds()
    today = date.today()
    rotting: list[dict] = []
    for ticket_dir in sorted(p for p in TICKETS_DIR.iterdir() if p.is_dir()):
        if ticket_dir.name == "archive":
            continue
        ledger_path = ticket_dir / "ticket.md"
        if not ledger_path.is_file():
            continue
        parsed = _parse_ticket_ledger_file(ledger_path)
        if parsed is None:
            continue
        if parsed["state"] not in ("queued", "planned"):
            continue
        try:
            created = date.fromisoformat(parsed["created"])
        except ValueError:
            continue
        threshold = thresholds.get(parsed["priority"])
        if threshold is None:
            continue
        age_days = (today - created).days
        if age_days <= threshold:
            continue
        rotting.append(
            {
                "id": parsed["id"],
                "priority": parsed["priority"],
                "tier": parsed["tier"],
                "state": parsed["state"],
                "age_days": age_days,
                "threshold_days": threshold,
                "runs_last": parsed["runs_last"],
            }
        )
    rotting.sort(key=lambda t: (_PRIORITY_RANK.get(t["priority"], 99), -t["age_days"]))
    return rotting


# frob:doc docs/guides/coordinator-scripts.md#_print_ticket_rot
# frob:ticket T-2182
# frob:ticket T-2200
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintTicketRot.test_splits_by_tier_under_\
# distinct_action_headings
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintTicketRot.test_runs_last_ticket_gets\
# _its_own_deferred_bucket_not_needs_dispatch
def _print_ticket_rot() -> None:
    """Print the TICKET ROT section: `rotting_tickets`'s own count, split
    into headings by required ACTION (acceptance [3]/[4]) -- 'NEEDS
    DISPATCH' for a leaf ticket (`tier=ticket`) that is NOT `runs_last`
    (nobody dispatched it; the fix IS to dispatch it), 'NEEDS
    DECOMPOSITION' for `tier=epic`/`tier=story` (not directly workable;
    'work it' is the wrong instruction for two thirds of a real measured
    set, T-0411/T-2182's own incident: 10 of 15 rotting tickets were
    epics, 1 a story, only 4 leaf tickets -- reporting them as one
    undifferentiated count is exactly what read as noise for a whole
    session), and 'DEFERRED (RUNS LAST)' (T-2200) for a leaf ticket that
    IS `runs_last` -- `frob ticket start` structurally REFUSES any `runs_
    last` ticket while other tickets are open (`RunsLastBlocked`), so
    listing it under 'NEEDS DISPATCH' recommends an action the tool
    itself rejects (T-1614's own real incident: 11 days old, listed under
    NEEDS DISPATCH, refused with RunsLastBlocked on the very next attempt
    to start it). A `runs_last` ticket is NEVER dropped from the report
    silently -- its age past threshold is still real information (the
    queue it is deliberately waiting behind is not draining) -- it just
    names the real, different action instead of 'dispatch it'.

    Printed unconditionally inside `_print_fleet_report`, in the standing
    report a coordinator already runs -- not behind a separate command
    (acceptance [0]/[2]): TICK004 already fires in `frob check`'s gate
    layer, but sat as 11 lines inside a 19-error list and was read as
    noise there; surfacing the same structured comparison here, with the
    action named per row, is the fix. Epics are NOT exempted (acceptance
    [4]) -- a rotting epic is reported, just under its own heading naming
    the different action it needs."""
    rotting = rotting_tickets()
    print(f"TICKET ROT: {len(rotting)}")
    leaves = [
        t for t in rotting if t["tier"] == "ticket" and not t.get("runs_last")
    ]
    deferred = [t for t in rotting if t["tier"] == "ticket" and t.get("runs_last")]
    non_leaves = [t for t in rotting if t["tier"] != "ticket"]
    if leaves:
        print(f"  NEEDS DISPATCH ({len(leaves)}):")
        for t in leaves:
            print(
                f"    {t['id']} priority={t['priority']} state={t['state']} "
                f"age={t['age_days']}d (threshold {t['threshold_days']}d)"
            )
    if deferred:
        print(f"  DEFERRED (RUNS LAST) ({len(deferred)}):")
        for t in deferred:
            print(
                f"    {t['id']} priority={t['priority']} state={t['state']} "
                f"age={t['age_days']}d (threshold {t['threshold_days']}d) -- "
                "not dispatchable via `frob ticket start` while other "
                "tickets are open (RunsLastBlocked); re-prioritize or clear "
                "runs_last if this is stuck"
            )
    if non_leaves:
        print(f"  NEEDS DECOMPOSITION ({len(non_leaves)}):")
        for t in non_leaves:
            print(
                f"    {t['id']} tier={t['tier']} priority={t['priority']} "
                f"state={t['state']} age={t['age_days']}d "
                f"(threshold {t['threshold_days']}d)"
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
    commits = readiness["worktrees_with_commits"]
    if commits:
        lines.append(f"  ALREADY IMPLEMENTED on: {', '.join(commits)}")
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
# tests/unit/test_coordinator_scripts.py::TestPrintLandStatus.test_prints_stale_lock_wh\
# en_no_live_holder
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
) -> list[str]:
    """Render the LANDS/LAND LOCK/LOAD block as plain text lines from
    already-computed inputs -- the PURE-COMPUTE half of the ARCH103 split
    (mirrors `_ticket_readiness_lines`'s own precedent, T-2172): no
    `print` call, no I/O, so `_print_land_status` below stays I/O-only.
    `invocations` are `land_invocations`'s own dicts (ticket id, pids,
    elapsed, cpu). `holder_pids`/`lock_exists` distinguish a live-held
    lock from a stale one from a free one. `load` is `host_load`'s
    `(1-minute load average, MemAvailable kb)`, or `None` when unknown.

    T-2222: `held_lease_count` (the raw `len(leases())`) and `live_lease_
    count_` (`live_lease_count(leases())`, T-2222's own live-vs-reclaimable
    classification) are BOTH shown, but the concurrency GUIDANCE clause is
    computed from `live_lease_count_` alone -- the measured incident this
    fixes: '6 lease(s) -- guidance is 3-4 agent concurrent' read as 6 live
    agents when only 4 were (two were reclaimable/root-resident), and the
    coordinator held dispatch on that overstated number. The trailing
    underscore on the parameter avoids shadowing the module-level
    `live_lease_count` function of the same name."""
    lines = [f"LANDS IN FLIGHT: {len(invocations)}"]
    for inv in invocations:
        # T-2193: land_invocations() drops any row it cannot parse a
        # ticket id from, so ticket_id is always real here -- never None.
        pids = ",".join(str(p) for p in inv["pids"])
        lines.append(
            f"  {inv['ticket_id']} pids={pids} elapsed={inv['elapsed_s']}s "
            f"cpu={inv['cpu_s']}s"
        )

    if holder_pids:
        lines.append(f"LAND LOCK: held, live holder pid(s)={holder_pids}")
    elif lock_exists:
        lines.append(
            "LAND LOCK: file exists but NO live process holds it open -- "
            "stale (recorded pid may be reused; do not trust it or lock age)"
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
            f"-- guidance is {_AGENT_CAP_GUIDANCE} concurrent"
        )
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
    3-4 concurrent agent operational guidance. Printed unconditionally
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
    hand. ARCH103 (T-2172 precedent): all formatting/branching lives in
    `_land_status_lines`; this function only gathers inputs and prints."""
    invocations = land_invocations()
    holder_pids = land_lock_holder_pids(REPO)
    lock_path = REPO / ".frob" / "land.lock"
    load = host_load()
    held = leases()
    for line in _land_status_lines(
        invocations,
        holder_pids,
        lock_path.exists(),
        load,
        len(held),
        live_lease_count(held),
    ):
        print(line)


# frob:doc docs/guides/coordinator-scripts.md#_print_fleet_report
# frob:ticket T-2172
# frob:ticket T-2180
# frob:ticket T-2182
# frob:ticket T-2222
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintFleetReport.test_prints_all_four_sec\
# tions
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintFleetReport.test_leases_section_show\
# s_classification_per_lease
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
    to the concurrency guidance clause."""
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

    held = leases()
    live_count = live_lease_count(held)
    print(f"LEASES {len(held)} ({live_count} live)")
    for record in held:
        name = Path(record.get("worktree", "?")).name
        classification = lease_classification(record)
        print(f"  {record.get('ticket_id')} -> {name}  [{classification}]")

    print("WORKTREES")
    for name, age, idle in worktrees(idle_seconds):
        mins = "unknown" if age < 0 else f"{age // 60}m"
        print(f"  {name:28} last-commit {mins:>9}{'  IDLE?' if idle else ''}")


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
    print(f"SCOPE INTERSECTIONS: {len(collisions)}")
    for collision in collisions:
        globs = ", ".join(
            f"{ga!r}<->{gb!r}" for ga, gb in collision["overlapping_globs"]
        )
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
