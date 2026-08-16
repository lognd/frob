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
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path

# frob:doc docs/guides/coordinator-scripts.md#fleet_status-constants
#: Repo root, derived from this script's own location.
REPO = Path(__file__).resolve().parent.parent
# frob:doc docs/guides/coordinator-scripts.md#fleet_status-constants
#: Where per-worktree checkouts live (`.claude/worktrees/<name>`).
WORKTREES = REPO / ".claude" / "worktrees"
# frob:doc docs/guides/coordinator-scripts.md#fleet_status-constants
#: Where held cross-worktree scope leases are recorded, one JSON file each.
LEASES = REPO / ".git" / "frob-leases"


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
    """`{"state": ..., "scope": [...]}` parsed from `main:tickets/<id>/
    ticket.md`'s YAML frontmatter, or `None` if the ticket does not exist
    on `main` at all. Hand-parsed (no `import yaml`, matching this
    script's own "no `frob` import, plain stdlib" contract from its module
    docstring) against the narrow shape `frob ticket` actually writes: a
    flat `key: value` line for `state`, and a `scope:` block of `- 'glob'`
    list lines directly beneath it. T-2133's own incident: a coordinator
    read `main:tickets/<id>/ticket.md`'s scope twice believing it was the
    ticket's LIVE scope, when the authoritative live value (if a lease is
    held) is the lease record's own `scope` field, which can have
    diverged via `frob ticket scope` inside a worktree that has not
    landed yet -- this function reads the STATIC, main-committed side of
    that comparison; `ticket_readiness` below is what actually compares
    the two."""
    text = _git(["show", f"main:tickets/{ticket_id}/ticket.md"], REPO)
    if not text:
        return None
    lines = text.splitlines()
    state = None
    scope: list[str] = []
    in_scope_block = False
    for line in lines:
        if line.startswith("state:"):
            state = line.split(":", 1)[1].strip()
            in_scope_block = False
            continue
        if line == "scope:":
            in_scope_block = True
            continue
        if in_scope_block:
            stripped = line.strip()
            if not stripped.startswith("- "):
                in_scope_block = False
                continue
            item = stripped[2:].strip()
            if len(item) >= 2 and item[0] == item[-1] and item[0] in "'\"":
                item = item[1:-1]
            scope.append(item)
    return {"state": state, "scope": scope}


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
    """Names of live worktrees whose branch carries an unlanded commit that
    BOTH (a) touches `tickets/<id>/` (correlates the commit to this ticket
    at all) AND (b) touches at least one file matching `scope_globs` (the
    ticket's own declared scope) somewhere in the branch's full `main...
    HEAD` diff -- genuine implementation evidence, not merely a ledger
    edit.

    T-2172 follow-up (the coordinator's own incident): the original
    version reported ANY worktree with a `tickets/<id>/`-touching commit
    as "already implemented" -- `--ticket T-2114` printed SEVEN branches
    (t-2071, t-2099, t-2105, t-2107, t-2109, t-2110, t2049-series), none
    of which had implemented T-2114 at all. T-2114 briefly collided with a
    different ticket id before being renumbered to T-2140, so every one of
    those branches had touched `tickets/T-2114/ticket.md` purely as
    collision-recovery renumbering churn -- never the ticket's own scope.
    A coordinator trusting that line would skip real, undone work believing
    it already existed -- worse than printing nothing, since a false
    "already implemented" is exactly the kind of wrong answer that gets
    trusted without a second look. Requiring BOTH conditions -- still
    correlated to this specific id (condition a keeps an unrelated
    ticket's own scope-glob collision from producing a false positive too)
    AND touching real declared-scope files (condition b) -- makes the
    T-2114 case correctly report nothing, since none of those branches'
    diffs touch `src/frob/app/ticket_runner/_land_cmd.py` (T-2114's own
    scope).

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
            ["log", "main..HEAD", "--oneline", "--", f"tickets/{ticket_id}/"], path
        )
        if not ticket_touch.strip():
            continue
        full_diff = _git(["diff", "--name-only", "main...HEAD"], path)
        touched_files = full_diff.splitlines()
        if any(_matches_any_scope_glob(f, scope_globs) for f in touched_files):
            hits.append(path.name)
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
def ticket_readiness(ticket_id: str) -> dict:
    """T-2133: the single per-ticket answer to "given T-####, is it
    actually dispatchable?" -- `fleet_status.py` already answers the
    fleet-wide half of pre-dispatch safety (root cleanliness, quarantine,
    idle worktrees); this is the missing per-ticket half, combining
    `ticket_lease`, `ticket_frontmatter_on_main`, and
    `worktrees_touching_ticket` into one dict:

    - `lease`: the live lease record (`ticket_lease`), or `None`.
    - `main`: `ticket_frontmatter_on_main`'s `{"state", "scope"}`, or
      `None` if the ticket does not exist on `main` yet.
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
    - `dispatchable`: `False` whenever a live lease is held, OR another
      worktree already carries SCOPE-matching commits for this ticket, OR
      `main` declares it in a state a fresh dispatch cannot productively
      start from (`done`/`dropped`/`in-progress`) -- `True` otherwise.
      This is the field a caller (or `main`'s own exit code) gates
      dispatch on."""
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
    worktrees_with_commits = worktrees_touching_ticket(
        ticket_id, effective_scope or ()
    )
    state_on_main = main_info["state"] if main_info is not None else None
    dispatchable = (
        lease is None
        and not worktrees_with_commits
        and state_on_main not in ("done", "dropped", "in-progress")
    )
    return {
        "ticket_id": ticket_id,
        "lease": lease,
        "main": main_info,
        "scope_diverges": scope_diverges,
        "worktrees_with_commits": worktrees_with_commits,
        "dispatchable": dispatchable,
    }


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
    scope divergence, sibling-branch commits, final verdict) as plain
    text lines, doing none of the actual printing -- the PURE-COMPUTE
    half of what used to be one function (ARCH103, T-2172: the
    combined shape mixed I/O, string-formatting, and 4 decision points in
    one body, which is exactly the three-concerns-in-one-function smell
    this gate exists to catch). Keeping the formatting/branching logic
    here, with no `print` call anywhere in this function, is what lets
    `_print_ticket_readiness` below stay I/O-only."""
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


# frob:doc docs/guides/coordinator-scripts.md#_print_fleet_report
# frob:ticket T-2172
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestPrintFleetReport.test_prints_all_four_sec\
# tions
def _print_fleet_report(dirt: list[str], idle_seconds: int) -> None:
    """Print the ROOT/QUARANTINE/LEASES/WORKTREES sections `main` used to
    print inline -- split out (ARCH001/ARCH103, T-2172) as the
    other half of `main`'s decomposition, alongside
    `_print_ticket_readiness` above. `dirt` is passed in rather than
    recomputed so `main` (the caller) stays the single place that calls
    `root_dirt()` and can reuse the result for its own exit-code
    decision."""
    print(f"ROOT {'DIRTY -- do not dispatch' if dirt else 'CLEAN'}")
    for line in dirt:
        print(f"  {line}")

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
    print(f"LEASES {len(held)}")
    for record in held:
        name = Path(record.get("worktree", "?")).name
        print(f"  {record.get('ticket_id')} -> {name}")

    print("WORKTREES")
    for name, age, idle in worktrees(idle_seconds):
        mins = "unknown" if age < 0 else f"{age // 60}m"
        print(f"  {name:28} last-commit {mins:>9}{'  IDLE?' if idle else ''}")


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
    place) as the only thing left here."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--idle-minutes", type=int, default=20)
    parser.add_argument(
        "--ticket",
        default=None,
        help="T-2133: also print per-ticket readiness (lease, main scope/"
        "state divergence, sibling-branch commits) FIRST, ahead of the "
        "general report, and gate the exit code on "
        "ticket_readiness()['dispatchable'], not just root cleanliness.",
    )
    args = parser.parse_args()

    ticket_ok = True
    if args.ticket is not None:
        ticket_ok = _print_ticket_readiness(ticket_readiness(args.ticket))

    dirt = root_dirt()
    _print_fleet_report(dirt, args.idle_minutes * 60)

    return 1 if (dirt or not ticket_ok) else 0


if __name__ == "__main__":
    raise SystemExit(main())
