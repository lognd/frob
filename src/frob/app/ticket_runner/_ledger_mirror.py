"""T-2563: mirror a worktree's ledger-only ticket edit onto the primary
checkout, so a change every other agent must SEE is visible where they
all look.

`frob ticket scope`/`block`/`attach` (and the other pure-metadata verbs)
auto-commit through `_auto_commit_ledger_after_dispatch`, which commits
in whatever root the verb ran in. From a dispatched worktree that is the
WORKTREE BRANCH, and the edit reaches `main` only if some later `frob
ticket land` happens to carry it -- never, for a ticket whose work is not
landing yet. Three T-2377 bookkeeping fixes reported success this way and
were invisible on main until they were cherry-picked across by hand.

That is the silent-zero family in its most deceptive form: the success
message is TRUE (the commit really was made) and the effect is simply
unreachable from where anyone will look. It matters well beyond
bookkeeping because `scope` IS the write lease in this repo -- a lease
change only the holder can see is worse than no lease change, since the
coordinator and every sibling agent read `main`.
"""
# frob:ticket T-2563

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

from frob import gitio

_log = logging.getLogger(__name__)


# frob:ticket T-2563
#: Verbs whose ENTIRE effect is ledger metadata that the rest of the fleet
#: must be able to read immediately -- these mirror to the primary
#: checkout.
#:
#: The state-machine verbs (`start`/`close`/`drop`/`fail`/`requeue`/
#: `done-report`/`evidence`/`archive`/`reverify`) are deliberately NOT
#: here. Their ledger write describes the progress of work that is still
#: worktree-local, and `frob ticket land` already carries them across
#: atomically with the code they describe; mirroring one would advance
#: `main`'s state machine ahead of the work it claims to have finished --
#: a worse failure than the one this module fixes. `land`/`merge-driver`
#: never reach here at all (`_LEDGER_TRANSACTIONAL_VERBS`).
# frob:doc docs/modules/tickets-lifecycle.md#worktree-ledger-mirror-t-2563
# frob:tests tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorScope.test_state_machine_verbs_are_not_mirrored  # noqa: E501
MIRRORED_LEDGER_VERBS = frozenset(
    {
        "accept",
        "anchor",
        "attach",
        "block",
        "body",
        "component",
        "debt",
        "deprecated",
        "kind",
        "label",
        "priority",
        "review",
        "runs-last",
        "scope",
        "scope-ack",
        "sprint",
        "tier",
    }
)


# frob:ticket T-2563
def _copy_ledger_paths(
    worktree: Path, primary: Path, pathspecs: tuple[str, ...]
) -> bool:
    """Copy `pathspecs` from `worktree` into `primary`, returning whether
    anything was actually copied.

    Only the ticket's own ledger paths move. This is what keeps the
    positive control "source changes must NOT leak to main" true by
    construction rather than by care: nothing outside these pathspecs is
    ever read, so a worktree's in-progress source edits cannot ride along
    even if the tree is filthy.
    """
    copied = False
    for spec in pathspecs:
        src = worktree / spec
        dst = primary / spec
        if src.is_dir():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            copied = True
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied = True
    return copied


# frob:ticket T-2563
def _log_mirror_unavailable(
    ticket_id: str, command: str, primary: Path, reason: str
) -> None:
    """The loud fallback when the mirror cannot proceed.

    Deliberately an ERROR naming the exact recovery command, matching
    `_log_ledger_commit_failure`'s precedent: the local commit HAS
    succeeded by this point, so failing the whole verb would throw away a
    good edit -- but staying quiet would reproduce exactly the silent
    invisibility this module exists to remove.
    """
    _log.error(
        "ticket %s: %s's ledger edit is WORKTREE-LOCAL and NOT visible on "
        "main -- %s. The fleet reads main, so this edit (a scope lease "
        "change, a blocker edge, an attachment) is invisible to every "
        "other agent until it is mirrored. Re-run this verb from %s once "
        "the repository is quiet, or land the ticket.",
        ticket_id,
        command,
        reason,
        primary,
    )


# frob:ticket T-2587
def _resolve_mirror_primary(root: Path, ticket_id: str, command: str) -> Path | None:
    """The primary checkout `command`'s ledger edit must be mirrored onto,
    or `None` if it must not be mirrored at all (no primary resolvable, a
    call that already ran in the primary checkout -- the coordinator's own
    path, which must cost nothing -- or a land in flight).

    Split out of `_mirror_target` (T-2587) so `mirror_promote_to_primary`
    can share this exact resolution/land-guard logic WITHOUT going
    through `MIRRORED_LEDGER_VERBS`'s membership check first --
    `promote`'s mirrored surface is not the single-pathspec shape that
    set assumes (see `mirror_promote_to_primary`'s own docstring), so it
    deliberately has no entry there and is never reached via
    `mirror_ledger_change_to_primary`/`_mirror_target` at all."""
    from frob.tickets._land import _resolve_primary_checkout
    from frob.tickets._leases import refuse_if_land_in_progress

    primary = _resolve_primary_checkout(root)
    if primary is None or primary.resolve() == root.resolve():
        return None

    land_check = refuse_if_land_in_progress(primary)
    if land_check.is_err:
        _log_mirror_unavailable(
            ticket_id,
            command,
            primary,
            f"a land is in progress ({land_check.danger_err})",
        )
        return None
    return primary


# frob:ticket T-2563
# frob:doc docs/modules/tickets-lifecycle.md#worktree-ledger-mirror-t-2563
def _mirror_target(root: Path, ticket_id: str, command: str) -> Path | None:
    """The primary checkout this edit must be mirrored onto, or `None` if
    `command` is not a `MIRRORED_LEDGER_VERBS` member (delegates the rest
    of the "should this run?" decision to `_resolve_mirror_primary`,
    T-2587)."""
    if command not in MIRRORED_LEDGER_VERBS:
        return None
    return _resolve_mirror_primary(root, ticket_id, command)


# frob:ticket T-2563
# frob:doc docs/modules/tickets-lifecycle.md#worktree-ledger-mirror-t-2563
def _commit_mirrored_paths(
    primary: Path, pathspecs: tuple[str, ...], ticket_id: str, command: str
) -> None:
    """`git add` + `git commit` the mirrored pathspecs in `primary`.

    Pathspec-limited on BOTH halves so a concurrent land staging content
    in the shared root cannot be swept into this commit as a passenger.
    """
    from frob.tickets._leases import _without_agent_commit_guard

    added = gitio.run_argv(["git", "-C", str(primary), "add", *pathspecs])
    if added.is_err or added.danger_ok.returncode != 0:
        _log_mirror_unavailable(ticket_id, command, primary, "git add failed")
        return
    with _without_agent_commit_guard():
        committed = gitio.run_argv(
            [
                "git",
                "-C",
                str(primary),
                "commit",
                "-m",
                f"chore(tickets): mirror {command} {ticket_id} from worktree",
                "--",
                *pathspecs,
            ]
        )
    if committed.is_err or committed.danger_ok.returncode != 0:
        status = gitio.run_argv(
            ["git", "-C", str(primary), "status", "--porcelain", "--", *pathspecs]
        )
        clean = (
            status.is_ok
            and status.danger_ok.returncode == 0
            and not status.danger_ok.stdout.strip()
        )
        if not clean:
            _log_mirror_unavailable(ticket_id, command, primary, "git commit failed")
        return

    _log.info(
        "ticket %s: %s mirrored onto the primary checkout %s -- visible to "
        "the fleet now, not only after this ticket lands",
        ticket_id,
        command,
        primary,
    )


# frob:ticket T-2563
# frob:doc docs/modules/tickets-lifecycle.md#worktree-ledger-mirror-t-2563
# frob:tests tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain.test_scope_edit_from_worktree_is_visible_on_primary  # noqa: E501
# frob:tests tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorCarriesNothingElse.test_worktree_source_changes_do_not_leak_to_primary  # noqa: E501
def mirror_ledger_change_to_primary(root: Path, ticket_id: str, command: str) -> None:
    """Copy `ticket_id`'s ledger files from the worktree `root` onto the
    primary checkout and commit them there, so a ledger-only edit made
    from a worktree is visible to the whole fleet immediately."""
    from frob.tickets._leases import _ledger_pathspecs
    from frob.tickets._store import ledger_lock

    primary = _mirror_target(root, ticket_id, command)
    if primary is None:
        return

    pathspecs = _ledger_pathspecs(root, ticket_id)
    if not pathspecs:
        return

    with ledger_lock(primary):
        if not _copy_ledger_paths(root, primary, pathspecs):
            return
        _commit_mirrored_paths(primary, pathspecs, ticket_id, command)


# frob:ticket T-2587
_PROMOTE_COMMIT_RE = re.compile(r"^chore\(tickets\): promote (\S+) -> (\S+)$")


# frob:ticket T-2587
def _last_promote_rename(root: Path, draft_id: str) -> str | None:
    """The `final_id` `_commit_promote_rename` (T-2197,
    `frob.tickets._draft_finalize`) just minted for `draft_id` in `root`,
    read back from that commit's own deterministic subject line -- or
    `None` if `root`'s current HEAD is not that commit.

    Deliberately reads the already-committed, already-tested commit
    message rather than importing `_draft_finalize`'s internals:
    `finalize_draft`/`_commit_and_warn_promote` live in
    `src/frob/tickets/_draft_finalize.py`, which is outside T-2587's
    declared scope (`_ledger_mirror.py` and this package's `__init__.py`
    only). Driving the mirror off the public commit-message contract
    keeps this module's write surface exactly where the ticket scoped
    it, at the cost of a narrow textual contract with
    `_commit_promote_rename`'s message format -- acceptable since that
    format is itself covered by `tests/system/test_cli_ticket_promote.py`
    and any change to it would be a deliberate, reviewed edit, not
    silent drift."""
    subject = gitio.run_argv(["git", "-C", str(root), "log", "-1", "--format=%s"])
    if subject.is_err or subject.danger_ok.returncode != 0:
        return None
    match = _PROMOTE_COMMIT_RE.match(subject.danger_ok.stdout.strip())
    if match is None or match.group(1) != draft_id:
        return None
    return match.group(2)


# frob:ticket T-2587
def _remove_stale_draft_ledger_dir(primary: Path, draft_id: str) -> str | None:
    """Delete `draft_id`'s now-vacated v2 per-ticket ledger directory on
    `primary` if present, returning the pathspec to stage its removal, or
    `None` if there was nothing there to remove.

    v1/monofile mode never has a separate per-ticket path to delete here
    -- the rename is already reflected inside the `tickets.md` content
    `_copy_ledger_paths` copies wholesale. A draft is minted off the
    default branch (T-1637/`_provisional.is_draft_id`), so `primary`
    normally never had a `tickets/T-draft-.../` directory to begin with;
    this only fires on the rarer path where one was independently mirrored
    or committed there before promotion, and staying defensive here costs
    nothing on the common path."""
    from frob.tickets._store import _store_mode

    if _store_mode(primary) != "v2":
        return None
    stale = primary / "tickets" / draft_id
    if not stale.exists():
        return None
    shutil.rmtree(stale)
    return f"tickets/{draft_id}"


# frob:ticket T-2587
# frob:doc docs/modules/tickets-lifecycle.md#worktree-ledger-mirror-t-2563
# frob:tests tests/unit/test_ticket_runner_ledger_mirror.py::TestPromoteMirror.test_promote_from_worktree_is_visible_on_primary_without_a_land  # noqa: E501
# frob:tests tests/unit/test_ticket_runner_ledger_mirror.py::TestPromoteMirror.test_promote_mirror_does_not_leak_source_changes_or_duplicate_the_draft  # noqa: E501
def mirror_promote_to_primary(root: Path, draft_id: str) -> bool:
    """T-2587: mirror a `frob ticket promote` rename's LEDGER pathspecs
    onto the primary checkout, so the promoted final id is visible to the
    fleet immediately instead of only once this worktree's ticket lands
    -- the gap T-2197 could only log a loud warning about
    (`_warn_if_promote_not_visible_on_primary`, `frob.tickets.
    _draft_finalize`).

    Deliberately narrower than `mirror_ledger_change_to_primary`:
    `promote` is a git RENAME across potentially many `frob:ticket`/
    `frob:tests`/... code-reference lines throughout the tracked tree
    (`renumber_one`'s `report.files_changed`), not just the ticket's own
    ledger pathspec every `MIRRORED_LEDGER_VERBS` member writes.
    Mirroring the FULL rename the same pathspec-limited way risks
    carrying a dirty worktree's unrelated uncommitted SOURCE edits onto
    main -- the exact hazard `_copy_ledger_paths`'s own docstring already
    documents as why this module stays ledger-only. So this mirrors ONLY
    the ledger: `draft_id`'s v2 directory removed if present on `primary`,
    `final_id`'s ledger pathspecs copied in from `root` -- the cross-file
    code-reference rewrite stays worktree-local until this ticket's own
    work actually lands, exactly like any other in-progress ticket's
    uncommitted-elsewhere code edits already do today. This is a
    deliberately narrower mirrored surface than the other verbs get, not
    an oversight left for a later ticket -- see this repo's T-2587
    ticket body for why folding `promote` into `MIRRORED_LEDGER_VERBS`
    outright, or unifying it with `_LEDGER_TRANSACTIONAL_VERBS`, was
    rejected for now.

    Not reachable via `MIRRORED_LEDGER_VERBS`/`_mirror_target` at all --
    call this directly (from `frob.app.ticket_runner.
    _auto_commit_ledger_after_dispatch`'s `"promote"` special case, since
    `promote` owns its own commit sequence and is excluded from the
    generic per-verb sweep like every other `_LEDGER_TRANSACTIONAL_VERBS`
    member).

    Returns whether anything was actually mirrored (`False` when `root`'s
    HEAD is not a promote-rename commit for `draft_id`, there is no
    primary to mirror onto, a land is in progress, or there was nothing
    to move)."""
    final_id = _last_promote_rename(root, draft_id)
    if final_id is None:
        return False

    primary = _resolve_mirror_primary(root, final_id, "promote")
    if primary is None:
        return False

    from frob.tickets._leases import _ledger_pathspecs
    from frob.tickets._store import ledger_lock

    new_pathspecs = _ledger_pathspecs(root, final_id)
    if not new_pathspecs:
        return False

    with ledger_lock(primary):
        moved = _copy_ledger_paths(root, primary, new_pathspecs)
        stale_pathspec = _remove_stale_draft_ledger_dir(primary, draft_id)
        if not moved and stale_pathspec is None:
            return False
        pathspecs = tuple(new_pathspecs) + ((stale_pathspec,) if stale_pathspec else ())
        _commit_mirrored_paths(primary, pathspecs, final_id, "promote")
        return True
