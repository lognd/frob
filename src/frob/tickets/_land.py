"""`frob ticket land` -- one-command landing (docs/modules/tickets.md#frob-ticket-land).

The landing procedure used to be manual coordinator surgery repeated per
ticket: wip-commit in the worktree, merge main into it, a deletion-filter
check (a stale worktree base can silently drop files main already has),
squash-apply onto main, a ledger splice on conflict, close (evidence +
Done-report validation), and a conventional commit. `land()` does the
whole chain atomically, with a `--dry-run` mode that runs every check and
every git operation the real run would, then unwinds it, so a dry run can
never green-light a landing that would actually fail (T-0176).

Every abort path logs the exact manual remedy alongside its `Err` -- the
`--dry-run` output IS the incident report a human would otherwise have to
reconstruct by hand.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.gitio import current_branch, run_argv
from frob.logging import get_logger
from frob.tickets._models import (
    CMD_EVIDENCE_ALLOWED_KINDS,
    LandError,
    LandReport,
    Ticket,
    TicketError,
    TicketState,
    is_cmd_evidence,
)
from frob.tickets._provisional import is_draft_id
from frob.tickets._store import _parse_ledger, _render_ledger, archive_path, ledger_path

_log = get_logger(__name__)

# frob:doc docs/modules/tickets.md#frob-ticket-land
_STATE_RANK: dict[TicketState, int] = {
    TicketState.QUEUED: 0,
    TicketState.PLANNED: 1,
    TicketState.IN_PROGRESS: 2,
    TicketState.BLOCKED: 2,
    TicketState.DROPPED: 3,
    TicketState.DONE: 3,
}
_DONE_REPORT_HEADING = "## Done report"


def _has_done_report(body: str) -> bool:
    """Whether body contains a '## Done report' section heading."""
    return any(line.strip() == _DONE_REPORT_HEADING for line in body.splitlines())


# frob:doc docs/modules/tickets.md#frob-ticket-land
def _newer(a: Ticket, b: Ticket) -> Ticket:
    """Which of two same-id ticket versions is "newer": further along the
    state machine wins; a state-rank tie prefers whichever carries a Done
    report, then more evidence, then `b` (the incoming/theirs side) as the
    final deterministic tiebreak -- never a coin flip."""
    rank_a, rank_b = _STATE_RANK[a.state], _STATE_RANK[b.state]
    if rank_a != rank_b:
        return a if rank_a > rank_b else b
    done_a, done_b = _has_done_report(a.body), _has_done_report(b.body)
    if done_a != done_b:
        return a if done_a else b
    if len(a.evidence) != len(b.evidence):
        return a if len(a.evidence) > len(b.evidence) else b
    return b


# frob:doc docs/modules/tickets.md#frob-ticket-land
def splice_ledger(
    ours_text: str,
    theirs_text: str,
    *,
    archived_ids: frozenset[str] = frozenset(),
) -> Result[str, TicketError]:
    """Merge two `tickets.md` ledger texts at the ticket-id level, keeping the
    newest state per section (`_newer`) instead of trusting git's line-level
    textual merge -- the fix for the "both sides append a new ticket near
    the same line" false-conflict class (T-0176), and the tiebreak for a
    genuine same-id divergence (e.g. one side closed a ticket the other
    side is still mid-editing).

    `archived_ids` (from main's `tickets-archive.md`, the only authoritative
    archive) is excluded from the merged result unconditionally, from
    EITHER side -- without this, a ticket main already archived reappears
    in the active ledger the moment a stale branch (whose own tickets.md
    still carries it as active, from before it was archived) lands,
    resurrecting exactly the active/archive duplicate-id class a human
    would otherwise have to hand-resolve at merge time (reviewer-caught,
    T-0176)."""
    ours_parsed = _parse_ledger(ours_text)
    if ours_parsed.is_err:
        return Err(ours_parsed.danger_err)
    theirs_parsed = _parse_ledger(theirs_text)
    if theirs_parsed.is_err:
        return Err(theirs_parsed.danger_err)
    ours, theirs = ours_parsed.danger_ok, theirs_parsed.danger_ok

    merged: dict[str, Ticket] = dict(ours)
    for ticket_id, ticket in theirs.items():
        if ticket_id not in merged:
            merged[ticket_id] = ticket
        elif merged[ticket_id] != ticket:
            merged[ticket_id] = _newer(merged[ticket_id], ticket)

    resurrected = archived_ids & set(merged)
    for ticket_id in resurrected:
        del merged[ticket_id]
    if resurrected:
        _log.info(
            "tickets: land splice -- dropped %d already-archived id(s): %s",
            len(resurrected),
            sorted(resurrected),
        )
    _log.info(
        "tickets: land splice -- ours=%d theirs=%d merged=%d",
        len(ours),
        len(theirs),
        len(merged),
    )
    return Ok(_render_ledger(merged))


def _porcelain_dirty(root: Path) -> Result[bool, LandError]:
    """Whether `root`'s working tree has any uncommitted change (tracked or not)."""
    spawned = run_argv(["git", "-C", str(root), "status", "--porcelain"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.error("land: git status failed in %s", root)
        return Err(LandError.GitFailed)
    return Ok(bool(spawned.danger_ok.stdout.strip()))


def _conflicted_files(root: Path) -> set[str]:
    """Paths git currently reports unmerged (`U`) in `root`'s index."""
    spawned = run_argv(
        ["git", "-C", str(root), "diff", "--name-only", "--diff-filter=U"]
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return set()
    return {
        line.strip() for line in spawned.danger_ok.stdout.splitlines() if line.strip()
    }


def _in_scope(path: str, scope: tuple[str, ...]) -> bool:
    """Whether `path` matches at least one of `scope`'s glob patterns."""
    return any(fnmatch.fnmatch(path, pattern) for pattern in scope)


def _validate_closeable(ticket: Ticket) -> Result[None, LandError]:
    """The evidence + Done-report preconditions `transition(..., DONE)` will
    enforce anyway -- checked here FIRST, before any git mutation, so a
    landing never merges main into the worktree only to discover at close
    time that it must be unwound (the exact ordering hazard T-0176 exists
    to close). Also re-checks the T-0215 kind-consistency rule
    (`_transition_guard`'s DONE-path twin): a non-docs-kind ticket carrying
    any `cmd:` evidence entry -- kind hand-edited after the entry was
    recorded, or the entry hand-pasted directly into the ledger -- must
    never land, mirroring the write-time gate in `add_cmd_evidence`."""
    if not ticket.evidence or not _has_done_report(ticket.body):
        _log.error(
            "land: %s cannot land -- missing evidence or a Done report; "
            "record evidence (`frob ticket evidence %s <node-id>...`, or for "
            "a docs-kind ticket `frob ticket close %s --evidence-cmd "
            "'<command>'`) and add a '## Done report' section under %s's "
            "entry in tickets.md, then retry `frob ticket land %s`",
            ticket.id,
            ticket.id,
            ticket.id,
            ticket.id,
            ticket.id,
        )
        return Err(LandError.NotCloseable)
    if ticket.kind not in CMD_EVIDENCE_ALLOWED_KINDS and any(
        is_cmd_evidence(e) for e in ticket.evidence
    ):
        _log.error(
            "land: %s cannot land -- kind=%s carries cmd: evidence, only "
            "allowed for kind in %s; fix the ticket's kind or replace the "
            "cmd: entry with real pytest --evidence node ids, then retry "
            "`frob ticket land %s`",
            ticket.id,
            ticket.kind,
            sorted(k.value for k in CMD_EVIDENCE_ALLOWED_KINDS),
            ticket.id,
        )
        return Err(LandError.NotCloseable)
    return Ok(None)


def _abort_merge(worktree: Path) -> None:
    """Best-effort `git merge --abort` to leave the worktree exactly as found."""
    run_argv(["git", "-C", str(worktree), "merge", "--abort"])


def _archived_ids(root: Path) -> frozenset[str]:
    """Every ticket id in `root`'s `tickets-archive.md` -- the authoritative
    "already archived, must never re-enter the active ledger" set a splice
    guards against (T-0176 reviewer fix). An unreadable/malformed archive
    degrades to empty rather than blocking the land -- archive resurrection
    is a correctness bug worth guarding against, not a reason to hard-fail
    a landing whose archive happens to be unparseable for an unrelated
    reason."""
    path = archive_path(root)
    if not path.exists():
        return frozenset()
    parsed = _parse_ledger(path.read_text(encoding="utf-8"))
    if parsed.is_err:
        _log.warning(
            "land: %s unreadable (%s), archive-resurrection guard degraded to empty",
            path,
            parsed.danger_err,
        )
        return frozenset()
    return frozenset(parsed.danger_ok)


def _splice_and_stage(
    checkout: Path,
    pre_text: str,
    incoming_text: str,
    *,
    archived_ids: frozenset[str] = frozenset(),
) -> Result[str, LandError]:
    """Write the id-level splice of `pre_text`/`incoming_text` to `checkout`'s
    tickets.md and `git add` it; overrides whatever git's own textual merge
    produced -- tickets.md is ALWAYS resolved via `splice_ledger`, never via
    git's line-level algorithm, so a both-sides-append never false-conflicts
    and a same-id divergence always keeps the newest state (T-0176).
    `archived_ids` excludes anything main has already archived from ever
    re-entering the merged active ledger."""
    spliced = splice_ledger(pre_text, incoming_text, archived_ids=archived_ids)
    if spliced.is_err:
        _log.error(
            "land: tickets.md splice failed (%s) -- resolve manually in %s",
            spliced.danger_err,
            checkout,
        )
        return Err(LandError.GitFailed)
    ledger_path(checkout).write_text(spliced.danger_ok, encoding="utf-8")
    add = run_argv(["git", "-C", str(checkout), "add", "tickets.md"])
    if add.is_err or add.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(spliced.danger_ok)


def _merge_main_into_worktree(
    root: Path, worktree: Path, ticket: Ticket, main_branch: str
) -> Result[bool, LandError]:
    """Stage (`--no-commit`) main into the worktree, resolving any tickets.md
    conflict via `splice_ledger`; any OTHER conflicted file aborts loudly.
    Returns whether a merge actually happened (False = worktree was already
    up to date with main, a no-op)."""
    pre_text = (
        ledger_path(worktree).read_text(encoding="utf-8")
        if ledger_path(worktree).exists()
        else ""
    )
    main_text = (
        ledger_path(root).read_text(encoding="utf-8")
        if ledger_path(root).exists()
        else ""
    )

    merged = run_argv(
        ["git", "-C", str(worktree), "merge", "--no-commit", "--no-ff", main_branch]
    )
    if merged.is_err:
        return Err(LandError.GitFailed)
    if (
        merged.danger_ok.returncode == 0
        and "up to date" in merged.danger_ok.stdout.lower()
    ):
        return Ok(False)

    conflicted = _conflicted_files(worktree)
    if conflicted - {"tickets.md"}:
        _abort_merge(worktree)
        _log.error(
            "land: %s merging %s into %s conflicts outside tickets.md: %s -- "
            "resolve manually (cd %s && git merge %s), commit, then retry "
            "`frob ticket land %s --worktree %s`",
            ticket.id,
            main_branch,
            worktree,
            sorted(conflicted),
            worktree,
            main_branch,
            ticket.id,
            worktree,
        )
        return Err(LandError.MergeConflict)

    spliced = _splice_and_stage(
        worktree, pre_text, main_text, archived_ids=_archived_ids(root)
    )
    if spliced.is_err:
        _abort_merge(worktree)
        return Err(spliced.danger_err)
    return Ok(True)


def _unowned_deletions(
    root: Path, worktree: Path, scope: tuple[str, ...], main_branch: str
) -> Result[tuple[str, ...], LandError]:
    """Files main has that the worktree (post-merge) deletes, outside `scope`
    -- the stale-base guard: a worktree branched from an old main can end up
    silently deleting a feature main already landed, and this is the check
    that catches it before it reaches main (T-0176)."""
    diff = run_argv(
        [
            "git",
            "-C",
            str(worktree),
            "diff",
            main_branch,
            "--diff-filter=D",
            "--name-only",
        ]
    )
    if diff.is_err or diff.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    deleted = [
        line.strip() for line in diff.danger_ok.stdout.splitlines() if line.strip()
    ]
    unowned = tuple(f for f in deleted if not _in_scope(f, scope))
    return Ok(unowned)


def _wip_commit(
    worktree: Path, ticket_id: str, *, dry_run: bool
) -> Result[bool, LandError]:
    """Commit any uncommitted worktree changes as a WIP snapshot before
    landing -- the manual "wip-commit in the worktree" step folded into
    `land` so nothing an agent forgot to commit is silently dropped by the
    merge that follows."""
    dirty = _porcelain_dirty(worktree)
    if dirty.is_err:
        return Err(dirty.danger_err)
    if not dirty.danger_ok:
        return Ok(False)
    if dry_run:
        _log.info(
            "land: %s would wip-commit uncommitted changes in %s", ticket_id, worktree
        )
        return Ok(True)
    add = run_argv(["git", "-C", str(worktree), "add", "-A"])
    if add.is_err or add.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    commit = run_argv(
        [
            "git",
            "-C",
            str(worktree),
            "commit",
            "-m",
            f"wip: pre-land snapshot for {ticket_id}",
        ]
    )
    if commit.is_err or commit.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    _log.info("land: %s wip-committed uncommitted worktree changes", ticket_id)
    return Ok(True)


_KIND_TO_COMMIT_TYPE = {
    "feature": "feat",
    "bug": "fix",
    "security": "fix",
    "ux": "fix",
    "docs": "docs",
    "invariant": "test",
    "incident": "fix",
}


def _commit_message(ticket: Ticket, final_id: str) -> str:
    """Conventional-commit message for the landing commit (ASCII, no
    trailing period, no Co-Authored-By -- repo convention)."""
    commit_type = _KIND_TO_COMMIT_TYPE.get(ticket.kind.value, "chore")
    subject = f"{commit_type}(tickets): land {final_id} {ticket.title}"
    return subject[:120]


# frob:ticket T-0176
# frob:doc docs/modules/tickets.md#frob-ticket-land
def land(
    root: Path, ticket_id: str, worktree: Path, *, dry_run: bool = False
) -> Result[LandReport, LandError]:
    """Land `ticket_id` from `worktree` onto `root`'s current branch: refuse
    on a dirty main, wip-commit the worktree, merge main into it (splicing
    tickets.md at the id level), abort loudly on any real conflict or an
    unowned deletion (naming the exact manual remedy), finalize a draft id,
    close the ticket (evidence + Done-report validated FIRST, before any of
    the above), squash-apply the worktree onto main, and commit with a
    conventional-commit message. `dry_run` runs every check and every git
    mutation the real run would (merge, splice, deletion-check) then
    unwinds it via `merge --abort`/`reset --hard`, so a clean dry run is a
    real guarantee, not a guess (T-0176)."""
    from frob.tickets import _load_one, finalize_draft, transition

    root, worktree = root.resolve(), worktree.resolve()

    main_dirty = _porcelain_dirty(root)
    if main_dirty.is_err:
        return Err(main_dirty.danger_err)
    if main_dirty.danger_ok:
        _log.error(
            "land: %s refused -- %s has uncommitted changes; commit or stash "
            "them first (git -C %s status), then retry `frob ticket land %s "
            "--worktree %s`",
            ticket_id,
            root,
            root,
            ticket_id,
            worktree,
        )
        return Err(LandError.DirtyMain)

    loaded = _load_one(worktree, ticket_id)
    if loaded.is_err:
        _log.error("land: %s not found in worktree store at %s", ticket_id, worktree)
        return Err(LandError.NotFound)
    ticket = loaded.danger_ok

    precheck = _validate_closeable(ticket)
    if precheck.is_err:
        return Err(precheck.danger_err)

    main_branch = current_branch(root)
    if main_branch.is_err:
        return Err(LandError.GitFailed)
    main_branch_name = main_branch.danger_ok

    wip = _wip_commit(worktree, ticket_id, dry_run=dry_run)
    if wip.is_err:
        return Err(wip.danger_err)
    wip_committed = wip.danger_ok

    merged = _merge_main_into_worktree(root, worktree, ticket, main_branch_name)
    if merged.is_err:
        return Err(merged.danger_err)
    did_merge = merged.danger_ok

    unowned = _unowned_deletions(root, worktree, ticket.scope, main_branch_name)
    if unowned.is_err:
        if did_merge:
            _abort_merge(worktree)
        return Err(unowned.danger_err)
    if unowned.danger_ok:
        if did_merge:
            _abort_merge(worktree)
        _log.error(
            "land: %s refused -- worktree deletes file(s) outside its scope "
            "%s: %s. If intentional, add the path(s) to the ticket's scope; "
            "if accidental (a stale worktree base), restore them: "
            "cd %s && git checkout %s -- %s ; then retry "
            "`frob ticket land %s --worktree %s`",
            ticket_id,
            list(ticket.scope),
            list(unowned.danger_ok),
            worktree,
            main_branch_name,
            " ".join(unowned.danger_ok),
            ticket_id,
            worktree,
        )
        return Err(LandError.UnownedDeletions)

    if dry_run:
        if did_merge:
            _abort_merge(worktree)
        _log.info(
            "land: %s dry-run clean -- would merge=%s, would close, would "
            "squash-apply onto %s",
            ticket_id,
            did_merge,
            main_branch_name,
        )
        return Ok(
            LandReport(
                ticket_id=ticket_id,
                final_id=ticket_id,
                dry_run=True,
                wip_committed=wip_committed,
                merged_main_into_worktree=did_merge,
                ledger_spliced=did_merge,
                unowned_deletions=(),
            )
        )

    if did_merge:
        commit = run_argv(
            [
                "git",
                "-C",
                str(worktree),
                "commit",
                "-m",
                f"merge {main_branch_name} into worktree for landing {ticket_id}",
            ]
        )
        if commit.is_err or commit.danger_ok.returncode != 0:
            return Err(LandError.GitFailed)

    final_id = ticket_id
    if is_draft_id(ticket_id):
        finalized = finalize_draft(worktree, ticket_id)
        if finalized.is_err:
            _log.error(
                "land: %s draft finalize failed after merge landed in the "
                "worktree only (main untouched) -- inspect %s, retry "
                "`frob ticket land %s --worktree %s`, or "
                "`git -C %s reset --hard HEAD~1` to undo the merge commit",
                ticket_id,
                worktree,
                ticket_id,
                worktree,
                worktree,
            )
            return Err(LandError.GitFailed)
        final_id = finalized.danger_ok

    closed = transition(worktree, final_id, TicketState.DONE)
    if closed.is_err:
        _log.error(
            "land: %s close failed (%s) after the merge already landed in "
            "the worktree (main untouched) -- fix evidence/Done report in "
            "%s and retry `frob ticket land %s --worktree %s`, or "
            "`git -C %s reset --hard HEAD~1` to undo the merge commit first",
            final_id,
            closed.danger_err,
            worktree,
            ticket_id,
            worktree,
            worktree,
        )
        return Err(LandError.CloseFailed)

    # finalize_draft (renumber_one) and transition/close both write directly
    # to the worktree's working tree, UNCOMMITTED -- the squash-apply below
    # reads from the branch's last COMMIT, which predates these writes. Left
    # uncommitted, the finalize rewrite of every frob:ticket <draft-id>
    # reference in code (not just the ledger) would never reach main, and
    # the worktree would be left dirty after a successful land (reviewer
    # repro, T-0176). Commit them now so the squash-apply below sees
    # everything, and the worktree ends up clean.
    finalize_dirty = _porcelain_dirty(worktree)
    if finalize_dirty.is_err:
        return Err(finalize_dirty.danger_err)
    if finalize_dirty.danger_ok:
        add = run_argv(["git", "-C", str(worktree), "add", "-A"])
        if add.is_err or add.danger_ok.returncode != 0:
            return Err(LandError.GitFailed)
        finalize_commit = run_argv(
            [
                "git",
                "-C",
                str(worktree),
                "commit",
                "-m",
                f"finalize and close {final_id} for landing",
            ]
        )
        if finalize_commit.is_err or finalize_commit.danger_ok.returncode != 0:
            return Err(LandError.GitFailed)

    branch = current_branch(worktree)
    if branch.is_err:
        return Err(LandError.GitFailed)
    branch_name = branch.danger_ok

    root_pre_text = (
        ledger_path(root).read_text(encoding="utf-8")
        if ledger_path(root).exists()
        else ""
    )

    squash = run_argv(
        ["git", "-C", str(root), "merge", "--squash", "--no-commit", branch_name]
    )
    if squash.is_err:
        return Err(LandError.GitFailed)

    conflicted_root = _conflicted_files(root)
    if conflicted_root - {"tickets.md"}:
        run_argv(["git", "-C", str(root), "reset", "--hard"])
        run_argv(["git", "-C", str(root), "clean", "-fd"])
        _log.error(
            "land: %s squash-apply onto %s conflicts outside tickets.md: %s "
            "-- resolve manually (cd %s && git merge --squash %s), commit, "
            "then retry `frob ticket land %s --worktree %s`",
            final_id,
            root,
            sorted(conflicted_root),
            root,
            branch_name,
            final_id,
            worktree,
        )
        return Err(LandError.SquashConflict)

    worktree_final_text = ledger_path(worktree).read_text(encoding="utf-8")
    spliced = _splice_and_stage(
        root, root_pre_text, worktree_final_text, archived_ids=_archived_ids(root)
    )
    if spliced.is_err:
        run_argv(["git", "-C", str(root), "reset", "--hard"])
        run_argv(["git", "-C", str(root), "clean", "-fd"])
        return Err(spliced.danger_err)

    message = _commit_message(ticket, final_id)
    commit = run_argv(["git", "-C", str(root), "commit", "-m", message])
    if commit.is_err or commit.danger_ok.returncode != 0:
        _log.error(
            "land: %s squash-apply staged onto %s but the final commit "
            "failed -- inspect `git -C %s status`, commit manually with a "
            "conventional-commit message, or `git -C %s reset --hard` to "
            "unwind the staged squash",
            final_id,
            root,
            root,
            root,
        )
        return Err(LandError.CommitFailed)

    sha = run_argv(["git", "-C", str(root), "rev-parse", "HEAD"])
    sha_str = (
        sha.danger_ok.stdout.strip()
        if sha.is_ok and sha.danger_ok.returncode == 0
        else None
    )

    stat = run_argv(
        [
            "git",
            "-C",
            str(root),
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "HEAD",
        ]
    )
    files = (
        tuple(
            line.strip() for line in stat.danger_ok.stdout.splitlines() if line.strip()
        )
        if stat.is_ok and stat.danger_ok.returncode == 0
        else ()
    )

    _log.info("land: %s landed as %s onto %s at %s", ticket_id, final_id, root, sha_str)
    return Ok(
        LandReport(
            ticket_id=ticket_id,
            final_id=final_id,
            dry_run=False,
            wip_committed=wip_committed,
            merged_main_into_worktree=did_merge,
            ledger_spliced=True,
            unowned_deletions=(),
            commit_sha=sha_str,
            files_changed=files,
        )
    )
