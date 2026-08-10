"""frob.tickets._unlanded -- finished-but-unlanded branch work detector (T-1934).

MEASURED LEAK (T-1934, 2026-08-09): an agent can finish a ticket, commit
everything cleanly in its worktree, and die before ever invoking `frob
ticket land`. Because the tree is clean, `frob worktree sweep`'s dirtiness
heuristic marks the worktree removable -- the BETTER an agent behaved
(committed instead of leaving junk), the MORE likely its finished work is
swept, since sweep never consults branch content vs. main at all. This is
the third of three crash windows this repo's ledger machinery covers:

  1. crash DURING `frob ticket land`     -> `frob.tickets._journal`'s
     intent marker, surfaced by `reconcile`'s `orphaned_land_intents`.
  2. crash AFTER commit, BEFORE land     -> THIS MODULE.
  3. crash BEFORE commit (dirty tree)    -> `frob worktree sweep`'s
     existing `kept:dirty` verdict.

Pure git plumbing, no checkout, no test runs (the ticket's own working
prototype): scan every local branch's `tickets/T-####/` tree for a
`done-report.md` file, or a `ticket.md` whose OWN `state:` field reads
`done`/`dropped`, then resolve that ticket id's state on `main` --
INCLUDING the archive (`tickets/archive/T-####/ticket.md`), never by path
existence alone. A first attempt that keyed on "does this path exist on
main" produced 186 false positives, because a done ticket is ARCHIVED on
main, not left in place (see `tests/unit/test_unlanded_branch_work.py`'s
own regression test for this exact shape). A ticket whose CURRENT
cross-worktree lease `frob.tickets._leases.lease_staleness_reason` judges
still live (a real agent working it right now, elsewhere) is never
reported -- reused directly, not re-derived, per this repo's own
"one staleness predicate" precedent (T-1806).

Report-only, by design (T-1934's REQUIRED section): nothing here lands,
requeues, or removes anything. `frob.tickets._reconcile.reconcile` surfaces
the result as a THIRD anomaly class alongside its existing two (T-0476)
plus the T-0456 orphaned-land-intent class, rather than a fourth standalone
CLI verb -- one place a coordinator already runs to ask "what is
inconsistent?" (a specific correction on this ticket, once the obvious
`frob ticket reconcile`/journal overlap was pointed out mid-dispatch:
sweep/reconcile already own worktree<->lease drift; this module owns
BRANCH-CONTENT-vs-main drift, a dimension neither previously read at all).
`frob.tickets._leases.sweep_worktrees` also consults this module directly
(a `kept:unlanded` verdict, ranked ABOVE the dirty-tree gate) so a clean,
unlanded worktree is never swept just because it behaved.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.tickets._leases import _LeaseRecord, lease_staleness_reason, read_all_leases

_log = get_logger(__name__)

# `tickets/T-<id>/ticket.md` or `tickets/T-<id>/done-report.md`, v2 ledger
# layout (design/ledger-v2.md section 1) -- deliberately excludes
# `tickets/archive/**`, which is a resolved-and-done ticket's home on a
# HEALTHY branch, never a signal of unlanded work on that branch itself.
_TICKET_PATH_RE = re.compile(
    r"^tickets/(T-[0-9A-Za-z][0-9A-Za-z-]*)/(ticket\.md|done-report\.md)$"
)
_STATE_RE = re.compile(r"(?m)^state:\s*(\S+)\s*$")

# The two ledger states `frob.tickets._models.TicketState` treats as
# terminal (`DONE`, `DROPPED`) -- a bare string set rather than importing
# the enum, since every value here comes from a regex match against raw
# YAML frontmatter text (a branch/main blob), never a validated `Ticket`.
_TERMINAL_STATES = frozenset({"done", "dropped"})


class _UnlandedWork(BaseModel):
    """One ticket that reads finished on a branch (`signal`) but is NOT
    terminal on `main` (T-1934) -- `state_on_main` is `None` if `main` has
    no record of the ticket at all (active or archived), which is reported,
    not treated as "nothing to see": an id `main` cannot resolve is exactly
    as unsafe to silently drop as one main knows about and has not
    finished."""

    model_config = {}

    ticket_id: str
    branch: str
    signal: str
    state_on_main: str | None


def _local_branch_names(root: Path) -> tuple[str, ...]:
    """Every local branch under `root` except `main` (T-1934's own
    prototype) -- `()` on any git failure, the same best-effort posture
    every other git-derived read in this package degrades to."""
    spawned = run_argv(("git", "-C", str(root), "branch", "--format=%(refname:short)"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning("tickets: unlanded-work scan: git branch failed under %s", root)
        return ()
    return tuple(
        name
        for line in spawned.danger_ok.stdout.splitlines()
        if (name := line.strip()) and name != "main"
    )


def _blob_text(root: Path, ref: str, path: str) -> str | None:
    """`git show <ref>:<path>`'s stdout, or `None` if the blob does not
    exist at `ref` (or the spawn itself fails) -- the no-checkout read
    every lookup in this module goes through."""
    spawned = run_argv(("git", "-C", str(root), "show", f"{ref}:{path}"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    return spawned.danger_ok.stdout


def _state_from_ticket_md(text: str) -> str | None:
    """The `state:` value from a v2 `ticket.md` blob's YAML frontmatter, or
    `None` if the line is absent/unparseable -- a narrow regex, not a full
    YAML load, since this module never needs anything else out of the
    frontmatter and a malformed OTHER field on a branch (mid-edit, a stale
    schema) must never block reading just this one line."""
    match = _STATE_RE.search(text)
    return match.group(1) if match else None


def _ticket_state_on_main(root: Path, ticket_id: str) -> str | None:
    """`ticket_id`'s `state:` on `main`, checking the ACTIVE path first and
    the ARCHIVE path second (T-1934's core fix over the first, path-only
    prototype: a done ticket is archived to `tickets/archive/<id>/
    ticket.md` on main, not left at `tickets/<id>/ticket.md` -- checking
    active existence alone produced 186 false positives, every one of them
    an archived-done ticket misread as "not on main at all"). `None` if
    neither path resolves on `main`."""
    for path in (
        f"tickets/{ticket_id}/ticket.md",
        f"tickets/archive/{ticket_id}/ticket.md",
    ):
        text = _blob_text(root, "main", path)
        if text is not None:
            return _state_from_ticket_md(text)
    return None


def _finished_signals_on_branch(root: Path, branch: str) -> dict[str, str]:
    """`ticket_id -> signal` for every ticket `branch` carries that LOOKS
    finished, by either of T-1934's REQUIRED-A shapes: `"done-report"` (a
    `tickets/T-####/done-report.md` blob exists on the branch -- the
    stronger, cheaper-to-check signal, since a `done-report.md`'s mere
    presence never happens for an in-progress ticket) or
    `"local-state-done"` (no `done-report.md`, but the branch's OWN
    `ticket.md` reads `state: done`/`state: dropped` -- covers a done
    ticket whose done-report a hand-crafted or scripted commit omitted).
    A single `git ls-tree` lists every candidate path in one spawn; only
    ids that need the second signal get an extra `git show` for their
    `ticket.md` content."""
    spawned = run_argv(
        (
            "git",
            "-C",
            str(root),
            "ls-tree",
            "-r",
            "--name-only",
            branch,
            "--",
            "tickets",
        )
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return {}
    done_report_ids: set[str] = set()
    ticket_md_ids: set[str] = set()
    for line in spawned.danger_ok.stdout.splitlines():
        match = _TICKET_PATH_RE.match(line.strip())
        if match is None:
            continue
        ticket_id, kind = match.group(1), match.group(2)
        if kind == "done-report.md":
            done_report_ids.add(ticket_id)
        else:
            ticket_md_ids.add(ticket_id)
    signals: dict[str, str] = dict.fromkeys(done_report_ids, "done-report")
    for ticket_id in ticket_md_ids - done_report_ids:
        text = _blob_text(root, branch, f"tickets/{ticket_id}/ticket.md")
        if text is None:
            continue
        if _state_from_ticket_md(text) in _TERMINAL_STATES:
            signals[ticket_id] = "local-state-done"
    return signals


def _is_ticket_lease_live(
    root: Path, ticket_id: str, leases: tuple[_LeaseRecord, ...]
) -> bool:
    """`True` iff a CURRENT lease for `ticket_id` exists and `lease_
    staleness_reason` judges it still live (T-1934 acceptance 3) -- reuses
    T-1876's single staleness predicate rather than inventing a second
    liveness notion, per this repo's own T-1806 "one predicate" precedent.
    A ticket with no lease at all, or only a stale one, is NOT excluded --
    only a genuinely live holder silences this detector."""
    for record in leases:
        if record.ticket_id == ticket_id:
            return lease_staleness_reason(root, record) is None
    return False


def _unlanded_findings_for_branch(
    root: Path, branch: str, leases: tuple[_LeaseRecord, ...] | None = None
) -> tuple[_UnlandedWork, ...]:
    """`_UnlandedWork` for every ticket `branch` carries a finished signal
    for (`_finished_signals_on_branch`) whose state on `main` is NOT
    terminal (`_ticket_state_on_main` not in `_TERMINAL_STATES`, including
    `None` -- unresolvable is reported, not assumed safe) and whose lease
    is not currently live (`_is_ticket_lease_live`). `leases` is
    injectable so a caller already holding `read_all_leases(root)` (a
    sweep pass iterating many candidate worktrees) never re-reads it once
    per branch."""
    if leases is None:
        leases = read_all_leases(root)
    findings: list[_UnlandedWork] = []
    for ticket_id, signal in sorted(_finished_signals_on_branch(root, branch).items()):
        if _is_ticket_lease_live(root, ticket_id, leases):
            continue
        state_on_main = _ticket_state_on_main(root, ticket_id)
        if state_on_main in _TERMINAL_STATES:
            continue
        findings.append(
            _UnlandedWork(
                ticket_id=ticket_id,
                branch=branch,
                signal=signal,
                state_on_main=state_on_main,
            )
        )
    return tuple(findings)


def _unlanded_branch_work(root: Path) -> tuple[_UnlandedWork, ...]:
    """Every `_UnlandedWork` finding across EVERY local branch under `root`
    except `main` itself (T-1934 acceptance 1/2/3) -- the read-only,
    report-only entry point `frob.tickets._reconcile.reconcile` surfaces as
    its third anomaly class and `frob ticket doable` summarizes as an "N
    branch(es) carry unlanded ticket work" line (T-1934 REQUIRED-C).
    NEVER lands, requeues, or removes anything -- REQUIRED-DO-NOT of
    T-1934's own brief: unattended landing of a dead agent's branch is how
    unreviewed work would reach `main`, so this stops at reporting.

    Cheap: a `git branch` spawn plus one `git ls-tree` per branch, and one
    `git show` only for ids that need the second signal or a main-side
    state resolution -- no checkout, no test run, matching the ticket's own
    working prototype exactly."""
    leases = read_all_leases(root)
    findings: list[_UnlandedWork] = []
    for branch in _local_branch_names(root):
        findings.extend(_unlanded_findings_for_branch(root, branch, leases))
    return tuple(findings)
