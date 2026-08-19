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
def _copy_ledger_paths(worktree: Path, primary: Path, pathspecs: tuple[str, ...]) -> bool:
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


# frob:ticket T-2563
# frob:doc docs/modules/tickets-lifecycle.md#worktree-ledger-mirror-t-2563
def _mirror_target(root: Path, ticket_id: str, command: str) -> Path | None:
    """The primary checkout this edit must be mirrored onto, or `None` if
    it must not be mirrored at all.

    Split out of `mirror_ledger_change_to_primary` for ARCH001, and it
    carries the whole "should this run?" decision: a non-mirrored verb, a
    call that already ran in the primary checkout (the coordinator's own
    path, which must cost nothing), or a land in flight.
    """
    if command not in MIRRORED_LEDGER_VERBS:
        return None

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
