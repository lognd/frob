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

T-2603: every `frob ticket` verb's ledger-write behaviour is declared
exactly once, in `LEDGER_VERB_STRATEGY` below, rather than being
reconstructed from membership across two separate frozensets
(`_LEDGER_TRANSACTIONAL_VERBS`, T-1615; `MIRRORED_LEDGER_VERBS`, T-2563)
plus `promote`'s own bespoke special case (T-2587). See
`LedgerWriteStrategy`'s own docstring for why these five values -- not
three, not the two-orthogonal-booleans shape T-2587's agent originally
declined to unify -- are the ones that generalise cleanly, and
`docs/modules/tickets-lifecycle.md#one-verb-table-not-two-sets-t-2603`
for the full enumeration this table replaces.
"""
# frob:ticket T-2563
# frob:ticket T-2603

from __future__ import annotations

import enum
import logging
import re
import shutil
from pathlib import Path

from frob import gitio

_log = logging.getLogger(__name__)


# frob:ticket T-2603
# frob:doc docs/modules/tickets-lifecycle.md#one-verb-table-not-two-sets-t-2603
# frob:tests \
# tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy.test_promote_kind
class LedgerWriteStrategy(enum.Enum):
    """The one property every `frob ticket` verb's ledger write needs
    declared: what `_auto_commit_ledger_after_dispatch` must do with it.

    T-2603 replaces `_LEDGER_TRANSACTIONAL_VERBS` + `MIRRORED_LEDGER_VERBS`
    + `promote`'s special case with ONE table keyed by this enum, on the
    strength of an exhaustive per-verb audit (all 48 real
    `_ticket_dispatch_table()` keys, cross-checked against
    `tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable`'s
    own independent classification) showing every verb's mechanical
    behaviour reduces to exactly one of these five shapes -- never a case
    where the same enum value means two different things depending on
    which verb key you look up, which is the failure mode T-2587's agent
    was right to refuse to paper over with a premature unification.

    OWN_TRANSACTION: the verb commits a complete, possibly multi-file
        transaction itself (`land`, `merge-driver`, `renumber`,
        `sweep-async`) -- `_auto_commit_ledger_after_dispatch`'s generic
        sweep must never touch it, and no mirror runs through this
        module either. A stray single-file ledger commit spliced in from
        outside would corrupt a transaction that has to land as one
        atomic change.
    OWN_TRANSACTION_LEDGER_MIRROR: same as `OWN_TRANSACTION` (`promote`
        is the only member -- it IS `renumber_one` under the hood) but a
        DEDICATED ledger-only mirror (`mirror_promote_to_primary`) runs
        afterward, reading back the rename's own commit message rather
        than copying a fixed pathspec tuple -- `promote`'s write is a
        multi-file code-reference rename, not the single-pathspec shape
        `GENERIC_COMMIT_MIRRORED` assumes, so it needs its own mirror
        shape rather than joining that set.
    GENERIC_COMMIT_MIRRORED: the dispatch-wrapper commits whatever ledger
        residue the verb's handler left dirty (T-1615's uniform sweep,
        idempotent if the handler already committed) AND mirrors the
        ticket's ledger pathspecs onto the primary checkout (T-2563) --
        the pure-metadata verbs (`scope`, `block`, `priority`, ...) whose
        entire effect the rest of the fleet must see immediately, because
        `scope` IS the write lease in this repo. `requeue` (T-2840) is
        also a member for the same reason even though it is otherwise a
        state-machine verb: the T-0453 tree-lease is derived live from
        IN_PROGRESS state + scope, so requeue's `IN_PROGRESS -> QUEUED`
        transition IS a lease release -- exactly the kind of edit the
        rest of the fleet must see immediately, not only once some later
        `land` happens to carry it (which, for a requeued ticket, never
        happens at all: see `GENERIC_COMMIT_UNMIRRORED`'s docstring
        above for the measured incident this closes).
    GENERIC_COMMIT_UNMIRRORED: the dispatch-wrapper may attempt the same
        generic commit (usually a no-op: these state-machine verbs --
        `new`/`start`/`close`/`drop`/`fail`/`done-report`/`evidence`/
        `archive`/`milestone`/... -- already call
        `commit_ticket_ledger_change` themselves, T-1130/T-1178) but is
        NEVER mirrored: their ledger write describes progress on work
        that is still worktree-local, and `land` already carries it
        across atomically with the code it describes. Mirroring one
        would advance `main`'s state machine ahead of the work it claims
        to have finished -- a worse failure than the one this module
        exists to fix. `requeue` is deliberately NOT a member of this
        set (T-2840): unlike close/drop/fail/done-report, a requeue's
        whole point is that the ticket's worktree work will NEVER land
        -- there is no future `land` to carry its QUEUED state across to
        main atomically. Classifying it here left the release of a
        held lease invisible to the fleet whenever the requeuing
        worktree was later swept before some OTHER mechanism happened
        to carry the edit across; see `GENERIC_COMMIT_MIRRORED`'s entry
        for `requeue` below.
    NOT_TICKET_SCOPED: `_auto_commit_ledger_after_dispatch`'s `cfg.
        ticket_id is None` early-return always fires for this verb (pure
        read-only verbs -- `list`/`show`/`doable`/`board`/...; `migrate`,
        whose whole-store rewrite is deliberately left for the caller to
        commit as one change, per its own module contract; `waive-audit`,
        whose `complete` subcommand writes a watermark file, never
        `tickets.md`) -- there is no per-ticket ledger write for this
        mechanism to ever act on.
    """

    OWN_TRANSACTION = "own_transaction"
    OWN_TRANSACTION_LEDGER_MIRROR = "own_transaction_ledger_mirror"
    GENERIC_COMMIT_MIRRORED = "generic_commit_mirrored"
    GENERIC_COMMIT_UNMIRRORED = "generic_commit_unmirrored"
    NOT_TICKET_SCOPED = "not_ticket_scoped"


# frob:ticket T-2603
# frob:ticket T-2675
# frob:doc docs/modules/tickets-lifecycle.md#one-verb-table-not-two-sets-t-2603
# frob:tests \
# tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy.test_all_classified
# frob:tests \
# tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy.test_derived_sets_track_the_live_strategy_table  # noqa: E501
# frob:tests \
# tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain.test_requeue_edit_from_worktree_is_visible_on_primary  # noqa: E501
# frob:tests \
# tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorScope.test_requeue_running_in_the_primary_checkout_is_a_no_op  # noqa: E501
#: The single source of truth for every `frob ticket` verb's ledger-write
#: strategy (T-2603). `_MIRRORED_LEDGER_VERBS`/`_OWN_TRANSACTION_VERBS`
#: below are DERIVED from this table, never redeclared, so there is
#: exactly one place a verb's classification can be edited or forgotten.
LEDGER_VERB_STRATEGY: dict[str, LedgerWriteStrategy] = {
    # OWN_TRANSACTION -- owns a complete multi-file transaction; the
    # generic sweep and this module's mirror must never touch it.
    "land": LedgerWriteStrategy.OWN_TRANSACTION,
    "merge-driver": LedgerWriteStrategy.OWN_TRANSACTION,
    "renumber": LedgerWriteStrategy.OWN_TRANSACTION,
    "sweep-async": LedgerWriteStrategy.OWN_TRANSACTION,
    # OWN_TRANSACTION_LEDGER_MIRROR -- owns its own transaction like the
    # verbs above, but also gets a dedicated ledger-only mirror.
    "promote": LedgerWriteStrategy.OWN_TRANSACTION_LEDGER_MIRROR,
    # GENERIC_COMMIT_MIRRORED -- pure ledger metadata the fleet must see
    # immediately; the T-2563 mirror copies its ledger pathspecs onto the
    # primary checkout right after the generic commit.
    "accept": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    "anchor": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    "attach": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    "block": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    "body": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    "component": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    "kind": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    "label": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    "priority": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    "review": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    "runs-last": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    # frob:ticket T-2624
    "runs-last-parallel-safe": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    "scope": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    "scope-ack": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    # frob:ticket T-2770
    # `set-parent` writes the `parent` field, same fleet-visibility
    # reasoning as `tier`'s own hierarchy-field mirror.
    "set-parent": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    "sprint": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    "tier": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    # frob:ticket T-2681
    # `unblock` writes the same `blocked_by` field `block` does (just
    # removing rather than appending an entry) -- same fleet-visibility
    # reasoning, same strategy.
    "unblock": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    # T-2840: reclassified from GENERIC_COMMIT_UNMIRRORED -- a requeue's
    # IN_PROGRESS -> QUEUED transition releases the T-0453 tree-lease,
    # and (unlike close/drop/fail) no future `land` ever carries a
    # requeued ticket's state across, so this write must reach main the
    # same way scope/block do, not wait on a land that will never come.
    "requeue": LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
    # GENERIC_COMMIT_UNMIRRORED -- state-machine progress `land` already
    # carries atomically; never mirrored ahead of the work it describes.
    "new": LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
    "plan": LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
    "start": LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
    "work": LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
    "sweep": LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
    "reconcile": LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
    "close": LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
    "reverify": LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
    "fail": LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
    "drop": LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
    "evidence": LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
    "done-report": LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
    "archive": LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
    # T-2574: added post-T-1615/T-2563 and never classified into either
    # legacy set -- see the follow-up bug this audit filed for whether it
    # belongs in GENERIC_COMMIT_MIRRORED instead (its write primitive,
    # `_set_ticket_field`, is the same one `priority`/`kind`/`tier` use).
    # Kept here, unmirrored, to match TODAY's actual behaviour exactly --
    # this table's job is a faithful unification, not a silent drive-by
    # fix of a bug outside T-2603's own scope.
    "milestone": LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
    # NOT_TICKET_SCOPED -- read-only, or a write this mechanism never
    # engages with (`cfg.ticket_id` is always `None` when these dispatch).
    "list": LedgerWriteStrategy.NOT_TICKET_SCOPED,
    "show": LedgerWriteStrategy.NOT_TICKET_SCOPED,
    "doable": LedgerWriteStrategy.NOT_TICKET_SCOPED,
    "wave": LedgerWriteStrategy.NOT_TICKET_SCOPED,
    "contention": LedgerWriteStrategy.NOT_TICKET_SCOPED,
    "board": LedgerWriteStrategy.NOT_TICKET_SCOPED,
    "epic": LedgerWriteStrategy.NOT_TICKET_SCOPED,
    "brief": LedgerWriteStrategy.NOT_TICKET_SCOPED,
    "flow": LedgerWriteStrategy.NOT_TICKET_SCOPED,
    "debt": LedgerWriteStrategy.NOT_TICKET_SCOPED,
    "deprecated": LedgerWriteStrategy.NOT_TICKET_SCOPED,
    "waive-audit": LedgerWriteStrategy.NOT_TICKET_SCOPED,
    "migrate": LedgerWriteStrategy.NOT_TICKET_SCOPED,
}


# frob:ticket T-2603
# frob:doc docs/modules/tickets-lifecycle.md#one-verb-table-not-two-sets-t-2603
# frob:tests \
# tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy.test_missing_raises
# frob:raises KeyError
# T-2603: deliberate -- an unclassified verb must fail loudly, never
# silently default; the dispatch-table exhaustiveness test and this
# function's own docstring are what catches a caller forgetting to
# handle it, not a broad except.
def ledger_write_strategy_for(command: str) -> LedgerWriteStrategy:
    """`command`'s declared `LedgerWriteStrategy`, or a loud `KeyError`
    naming exactly the gap -- never a silent default.

    This is the mechanical half of T-2603's "fails loudly" requirement: a
    verb added to `_ticket_dispatch_table()` without a matching
    `LEDGER_VERB_STRATEGY` entry raises here instead of quietly falling
    through to whatever the old two-frozenset code happened to do for an
    unlisted key (commit-but-never-mirror, T-2197's exact bug shape) --
    the failure surfaces at the first `frob ticket <verb>` invocation
    that reaches this dispatch wrapper, not just in a test someone has to
    remember to run."""
    try:
        return LEDGER_VERB_STRATEGY[command]
    except KeyError:
        raise KeyError(
            f"ticket runner: {command!r} has no LEDGER_VERB_STRATEGY entry in "
            "frob.app.ticket_runner._ledger_mirror -- every verb in "
            "_ticket_dispatch_table() must declare one (T-2603); add it "
            "before this verb can auto-commit or mirror its ledger write"
        ) from None


# frob:ticket T-2603
#: Derived from `LEDGER_VERB_STRATEGY` -- the verbs whose generic ledger
#: write mirrors onto the primary checkout. Replaces the old, separately
#: hand-maintained `MIRRORED_LEDGER_VERBS` frozenset; kept under this old
#: name too (module-level alias below) since tests and docs still refer
#: to it by that name.
_MIRRORED_LEDGER_VERBS = frozenset(
    verb
    for verb, strategy in LEDGER_VERB_STRATEGY.items()
    if strategy is LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED
)

# frob:doc docs/modules/tickets-lifecycle.md#worktree-ledger-mirror-t-2563
# frob:tests tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorScope.test_state_machine_verbs_are_not_mirrored  # noqa: E501
#: Back-compat alias (T-2563's original name) for `_MIRRORED_LEDGER_VERBS`
#: -- both names refer to the SAME frozenset, derived from
#: `LEDGER_VERB_STRATEGY` above rather than declared twice.
MIRRORED_LEDGER_VERBS = _MIRRORED_LEDGER_VERBS

# frob:ticket T-2603
# frob:doc docs/modules/tickets-lifecycle.md#one-verb-table-not-two-sets-t-2603
#: Derived from `LEDGER_VERB_STRATEGY` -- verbs that own a complete
#: transaction and must never be touched by the generic per-dispatch
#: sweep. Replaces the old, separately hand-maintained
#: `_LEDGER_TRANSACTIONAL_VERBS` frozenset in `ticket_runner/__init__.py`
#: (re-exported there under that name for the same back-compat reason).
OWN_TRANSACTION_VERBS = frozenset(
    verb
    for verb, strategy in LEDGER_VERB_STRATEGY.items()
    if strategy
    in (
        LedgerWriteStrategy.OWN_TRANSACTION,
        LedgerWriteStrategy.OWN_TRANSACTION_LEDGER_MIRROR,
    )
)


# frob:ticket T-2570
# frob:doc docs/modules/tickets-lifecycle.md#worktree-ledger-mirror-t-2563
_UNMIRRORED_TICKET_FILENAMES = frozenset({"done-report.md"})
"""T-2570: filenames the mirror must never copy or commit even when they
sit inside an otherwise-mirrored `tickets/T-####/` directory.

`_ledger_pathspecs` returns the whole ticket DIRECTORY as one pathspec
(needed so `attach`'s new files under `attachments/` reach main), but
`done-report.md` is explicitly `GENERIC_COMMIT_UNMIRRORED` for its own
verb (`LEDGER_VERB_STRATEGY["done-report"]`) and is separately owned by
`land`'s `OWN_TRANSACTION` write. A directory-wide `shutil.copytree(...,
dirs_exist_ok=True)` does not know that -- it silently overwrote main's
own `done-report.md` (e.g. a land's freshly written `error-findings:`
claims) with whatever stale copy happened to sit in the mirroring
worktree, the moment an unrelated verb like `scope` mirrored. This set is
subtracted from both the copy and the git add/commit steps so a mirror
touches only the files its own verb table actually claims."""


# frob:ticket T-2563
# frob:ticket T-2570
def _copy_ledger_paths(
    worktree: Path,
    primary: Path,
    pathspecs: tuple[str, ...],
    *,
    exclude_filenames: frozenset[str] = frozenset(),
) -> bool:
    """Copy `pathspecs` from `worktree` into `primary`, returning whether
    anything was actually copied.

    `exclude_filenames` (T-2570) is skipped even inside an otherwise-
    mirrored directory -- `mirror_ledger_change_to_primary` passes
    `_UNMIRRORED_TICKET_FILENAMES` here so a metadata-verb mirror cannot
    clobber `done-report.md`; `mirror_promote_to_primary` passes nothing,
    because a promote's whole-ticket rename legitimately DOES carry any
    existing done report along with the rest of the directory -- it is
    not a second writer racing anything, it is the one authoritative move
    of the ticket's own content to its new id. Otherwise: only the
    ticket's own ledger paths move, which is what keeps the positive
    control "source changes must NOT leak to main" true by construction
    rather than by care -- nothing outside these pathspecs is ever read,
    so a worktree's in-progress source edits cannot ride along even if
    the tree is filthy.
    """
    ignore = shutil.ignore_patterns(*exclude_filenames) if exclude_filenames else None
    copied = False
    for spec in pathspecs:
        src = worktree / spec
        dst = primary / spec
        if src.is_dir():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore)
            copied = True
        elif src.is_file():
            if src.name in exclude_filenames:
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied = True
    return copied


# frob:ticket T-2570
def _mirror_commit_pathspecs(pathspecs: tuple[str, ...]) -> tuple[str, ...]:
    """`pathspecs` plus a `:(exclude)` magic entry per mirrored directory
    for each name in `_UNMIRRORED_TICKET_FILENAMES` (T-2570).

    Belt-and-suspenders alongside `_copy_ledger_paths`'s own exclusion:
    even if `done-report.md` already sits uncommitted on the primary
    checkout for some other reason, `git add`/`git commit` must never
    pick it up as a passenger of a mirrored metadata commit."""
    excludes = tuple(
        f":(exclude){spec.rstrip('/')}/{name}"
        for spec in pathspecs
        for name in _UNMIRRORED_TICKET_FILENAMES
        if not spec.endswith(name)
    )
    return pathspecs + excludes


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
        if not _copy_ledger_paths(
            root, primary, pathspecs, exclude_filenames=_UNMIRRORED_TICKET_FILENAMES
        ):
            return
        _commit_mirrored_paths(
            primary, _mirror_commit_pathspecs(pathspecs), ticket_id, command
        )


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
    an oversight left for a later ticket -- see this repo's T-2587 ticket
    body for the original reasoning against folding `promote` into
    `MIRRORED_LEDGER_VERBS` outright. T-2603 later gave `promote` its own
    `LedgerWriteStrategy.OWN_TRANSACTION_LEDGER_MIRROR` value in
    `LEDGER_VERB_STRATEGY` precisely so this narrower shape stays a
    DECLARED strategy rather than an undeclared special case -- the
    unification T-2587 declined was doing this by hand-folding `promote`
    into an existing set; T-2603's table adds a distinct value instead,
    which is what let the two original sets merge safely.

    Not reachable via `MIRRORED_LEDGER_VERBS`/`_mirror_target` at all --
    call this directly (from `frob.app.ticket_runner.
    _auto_commit_ledger_after_dispatch`'s `"promote"` branch, since
    `promote` owns its own commit sequence and is excluded from the
    generic per-verb sweep like every other `OWN_TRANSACTION_VERBS`
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
