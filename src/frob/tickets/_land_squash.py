"""`frob ticket land` -- squash-apply/close stage.

See docs/modules/tickets-landing.md#frob-ticket-land.

Split out of `frob.tickets._land_finalize` (T-1334, continuing the
verbatim-move discipline T-1186/T-1189/T-1192/T-1194/T-1251 established):
the squash-apply-onto-main family -- the v1/v2 squash-and-splice pair
(`_squash_and_splice_ledger`/`_squash_and_splice_ledger_v2`) and their
conflict-check counterparts (`_check_squash_conflicted`/
`_check_squash_conflicted_v2`, plus the v2 scope-widening helper
`_v2_effective_scope`), the squash unwind/regression-sweep pair
(`_unwind_squash_apply`/`_refuse_if_land_regresses_terminal_state`/
`_tick005_land_regressions`), the pre-commit completeness assertion
(`_worktree_full_changeset`/`_staged_files`/`_assert_land_complete`), the
stacked-sibling absorption check (`_absorption_scoped_content_matches`/
`_absorption_verified`/`_report_stacked_sibling_absorption`/
`_absorbed_land_report`), the final commit helpers
(`_commit_squash_apply`/`_land_commit_details`), and the top-level
orchestrator `_land_squash_apply` itself. `_land_squash_apply` is further
split here into itself plus `_land_squash_apply_finish` (T-1334, clearing
its own ARCH001 finding -- 87 lines against the 60-line threshold): the
seam is the squash call itself, the one point every path below it already
unwinds back through `_verified_reset_root` on failure, so no control-flow
or unwind semantics change. Zero other caller-visible behavior change --
every moved function keeps its original body, docstring, and
`frob:ticket`/`frob:tests` directives verbatim; `frob.tickets._land` now
imports `_land_squash_apply`/`_v2_effective_scope` from here directly
instead of via `_land_finalize`. Release-bump/uv.lock/native-rebuild
helpers this family calls (`_apply_release_bump`/`_apply_gate_rule_sync`/
`_maybe_rebuild_natives`/`_warn_if_native_stale`) live in the sibling
`frob.tickets._land_release` module and are imported back from there.
"""

# frob:waive LARGE001 reason="T-1651-grade: this module is itself the T-1334 split's \
# squash-apply/close output, and its own docstring shows the internal seam \
# (_land_squash_apply/_land_squash_apply_finish) was ALREADY cut at the one safe point \
# (the squash call, the sole unwind point every path shares). What remains -- the \
# v1/v2 splice pair, their conflict checks, the unwind/regression-sweep pair, the \
# completeness assertion, and the stacked-sibling absorption check -- are five guards \
# that all run in the same _land_squash_apply/_land_squash_apply_finish sequence \
# against the same worktree-vs-main diff; splitting them apart would scatter one \
# atomic commit-or-unwind transaction's checks across files with no independent \
# consumer, the same outcome T-1651 ruled worse than the warning."

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.gitio import current_branch, run_argv
from frob.logging import get_logger
from frob.tickets._land_compose import (
    fold_worktree_into_commit,
    publish_ref_cas,
    resync_root_to_published_tip,
)
from frob.tickets._land_git_ops import (
    _archived_ids,
    _auto_resolve_out_of_scope_conflicts,
    _describe_git_failure,
    _land_internal_git_env,
    _pathspec_targets,
    _porcelain_dirty_paths,
    _read_archive_text_or_empty,
    _read_ledger_text_or_empty,
    _read_text_at_ref,
    _rev_parse,
    _splice_and_stage,
    _splice_and_stage_archive,
    _true_merge_base,
    _unstage_index_only,
    _verified_reset_root,
)
from frob.tickets._land_merge import _commit_message
from frob.tickets._land_release import (
    _apply_gate_rule_sync,
    _apply_release_bump,
    _maybe_rebuild_natives,
    _warn_if_native_stale,
)
from frob.tickets._models import (
    LandError,
    LandReport,
    Ticket,
    TicketState,
    scope_matches,
)
from frob.tickets._store import _parse_ledger, _store_mode, ledger_lock, ledger_path

_log = get_logger(__name__)


# frob:ticket T-0907
# frob:waive DUP002 reason="T-1186 split-induced false positive: this is the \
# pre-existing, deliberate mirror-image counterpart to \
# frob.tickets._land_git_ops._check_only_tickets_conflicted -- one checks conflicts \
# after squash-merging main INTO root (root=ours), the other after merging main INTO \
# the worktree (worktree=theirs); the two already coexisted, unwaived, side by side in \
# frob.tickets._land before T-1186's split moved them into separate modules, which is \
# what triggers DUP002's both-new-in-this-diff pairing -- neither function's body \
# changed"
# frob:waive DUP001 reason="T-1334 split-induced false positive, same root cause as \
# the DUP002 waiver just above: moving this verbatim function into its own new file \
# (_land_squash.py) makes the dup detector compare it against pre-existing \
# frob.tickets._land_git_ops._check_only_tickets_conflicted as though it were new code \
# near a pre-existing sibling, rather than the T-1186-established, deliberate \
# mirror-image pair it already was -- neither function's body changed"
def _check_squash_conflicted(
    stage: Path, worktree: Path, ticket: Ticket, branch_name: str, pre_land_tip: str
) -> Result[None, LandError]:
    """`Err(SquashConflict)` (unwinding the squash) if any IN-SCOPE file
    besides tickets.md/tickets-archive.md is still conflicted after the
    squash merge; any OUT-OF-SCOPE conflict is auto-resolved by taking
    main's side first
    (T-0479) -- main is `ours` here (stage's checked-out branch, with the
    worktree's finalized branch squash-merged in as `theirs`). `pre_land_tip`
    (T-0907) is this run's verified pre-mutation stage tip, threaded through
    to `_verified_reset_root` so every unwind here resets to an explicit sha
    rather than a bare (HEAD-at-reset-time) `git reset --hard`."""
    resolved = _auto_resolve_out_of_scope_conflicts(stage, ticket, keep="ours")
    if resolved.is_err:
        unwound = _verified_reset_root(stage, pre_land_tip, ticket.id)
        return Err(unwound.danger_err if unwound.is_err else resolved.danger_err)
    remaining = resolved.danger_ok
    if remaining:
        unwound = _verified_reset_root(stage, pre_land_tip, ticket.id)
        _log.error(
            "land: %s squash-apply onto %s conflicts in scoped file(s): %s "
            "-- resolve manually (cd %s && git merge --squash %s), commit, "
            "then retry `frob ticket land %s --worktree %s`",
            ticket.id,
            stage,
            sorted(remaining),
            stage,
            branch_name,
            ticket.id,
            worktree,
        )
        return Err(unwound.danger_err if unwound.is_err else LandError.SquashConflict)
    return Ok(None)


# frob:ticket T-1258
# frob:doc docs/design/ledger-v2.md#5-merge-story-the-frob-ledger-driver-retired
# frob:tests tests/test_ticket_land.py::TestLedgerV2LandMergeStory.test_disjoint_v2_tickets_land_with_no_custom_merge  # noqa: E501
# frob:waive COV007 reason="T-1636: docs/design/ledger-v2.md's Merge story section \
# (T-1136/T-1258) is a deliberate design doc walking through this exact private \
# v2-mode scope-widening helper's own contract -- same T-0524/T-0529 per-function \
# architecture-doc precedent every other COV007 waiver in this repo already carries, \
# not accidental drift onto a private helper"
def _v2_effective_scope(ticket: Ticket) -> Ticket:
    """v2-mode land treats a ticket's own `tickets/<id>/` directory as
    always in scope (design section 1's file-per-ticket layout), mirroring
    the v1 "tickets.md is always in scope" convention (agent-playbook.md
    section 4) -- returns a scope-widened COPY of `ticket` (never mutates
    the original) so the existing v1 out-of-scope conflict auto-resolver
    (`_auto_resolve_out_of_scope_conflicts`) can be reused VERBATIM for
    v2-mode merges/squash-applies instead of a parallel scope-matching
    implementation. Idempotent: a second call on an already-widened ticket
    is a no-op (the glob is only appended once)."""
    own_glob = f"tickets/{ticket.id}/*"
    if own_glob in ticket.scope:
        return ticket
    return ticket.model_copy(update={"scope": (*ticket.scope, own_glob)})


# frob:ticket T-1258
# frob:doc docs/design/ledger-v2.md#5-merge-story-the-frob-ledger-driver-retired
# frob:tests tests/test_ticket_land.py::TestLedgerV2LandMergeStory.test_same_ticket_conflict_surfaces_loudly_no_splice  # noqa: E501
# frob:waive COV007 reason="T-1636: docs/design/ledger-v2.md's Merge story section \
# (T-1136/T-1258, AC3's 'no splice_ledger-class resolution needed' contract) is a \
# deliberate design doc walking through this exact private v2-mode conflict-check \
# counterpart -- same T-0524/T-0529 per-function architecture-doc precedent every \
# other COV007 waiver in this repo already carries, not accidental drift onto a \
# private helper"
def _check_squash_conflicted_v2(
    stage: Path, worktree: Path, ticket: Ticket, branch_name: str, pre_land_tip: str
) -> Result[None, LandError]:
    """v2-mode counterpart to `_check_squash_conflicted`: no tickets.md/
    tickets-archive.md carve-out is needed here (those files do not exist
    in v2 mode) -- any conflict OUTSIDE the ticket's own `tickets/<id>/`
    directory is auto-resolved by taking stage's side (`keep="ours"`, same
    convention `_check_squash_conflicted` uses); anything left conflicted
    is a genuine same-ticket-file conflict and is surfaced loudly as an
    ORDINARY git conflict, per design section 5's explicit "no
    `splice_ledger`-class resolution needed" contract (AC3) -- never
    silently resolved by picking a side."""
    widened = _v2_effective_scope(ticket)
    resolved = _auto_resolve_out_of_scope_conflicts(stage, widened, keep="ours")
    if resolved.is_err:
        unwound = _verified_reset_root(stage, pre_land_tip, ticket.id)
        return Err(unwound.danger_err if unwound.is_err else resolved.danger_err)
    remaining = resolved.danger_ok
    if remaining:
        unwound = _verified_reset_root(stage, pre_land_tip, ticket.id)
        _log.error(
            "land: %s squash-apply onto %s conflicts in scoped file(s) "
            "(v2 mode, no ledger splice applies): %s -- resolve manually "
            "(cd %s && git merge --squash %s), commit, then retry "
            "`frob ticket land %s --worktree %s`",
            ticket.id,
            stage,
            sorted(remaining),
            stage,
            branch_name,
            ticket.id,
            worktree,
        )
        return Err(unwound.danger_err if unwound.is_err else LandError.SquashConflict)
    return Ok(None)


# frob:ticket T-1258
# frob:doc docs/design/ledger-v2.md#5-merge-story-the-frob-ledger-driver-retired
# frob:tests tests/test_ticket_land.py::TestLedgerV2LandMergeStory.test_disjoint_v2_tickets_land_with_no_custom_merge  # noqa: E501
# frob:waive COV007 reason="T-1636: docs/design/ledger-v2.md's Merge story section \
# (T-1136/T-1258) is a deliberate design doc walking through this exact private \
# v2-mode squash-and-splice entry point's own contract -- same T-0524/T-0529 \
# per-function architecture-doc precedent every other COV007 waiver in this repo \
# already carries, not accidental drift onto a private helper"
def _squash_and_splice_ledger_v2(
    stage: Path,
    worktree: Path,
    ticket: Ticket,
    final_id: str,
    branch_name: str,
    pre_land_tip: str,
    *,
    merge_already_composed: bool = False,
) -> Result[None, LandError]:
    """v2-mode counterpart to `_squash_and_splice_ledger` (design section
    5): `git merge --squash --no-commit` the worktree's finalized branch
    onto `stage`, exactly like v1, but performs NO ledger splice at all --
    disjoint `tickets/T-####/` directories are ordinary git objects the
    squash-merge already stages correctly on its own, so there is nothing
    left to splice, no `ledger_lock` critical section is needed, and the
    monofile-specific TICK005 terminal-state regression sweep does not
    apply (a v2-mode analog of that sweep is out of THIS ticket's scope --
    see its Done report for the follow-up filed). `final_id` is accepted
    only for call-shape parity with `_squash_and_splice_ledger` (a v2-mode
    draft finalization renumbers the directory itself, upstream of this
    call, so there is no id-scoped splice left to perform here).

    T-3089: `stage` is the checkout the squash-merge is performed IN and
    the one every downstream index-consuming stage reads -- `root` itself
    today, a disposable worktree detached at `pre_land_tip` once the
    compose moves out of tree."""
    del final_id
    if not merge_already_composed:
        squash = run_argv(
            ["git", "-C", str(stage), "merge", "--squash", "--no-commit", branch_name]
        )
        if squash.is_err:
            return Err(LandError.GitFailed)
    return _check_squash_conflicted_v2(
        stage, worktree, ticket, branch_name, pre_land_tip
    )


# frob:ticket T-0907
# frob:ticket T-1036
# frob:tests tests/test_ticket_land.py::TestSquashSpliceLedgerChurn.test_concurrent_write_between_squash_and_splice_survives_land  # noqa: E501
def _squash_and_splice_ledger(
    root: Path,
    stage: Path,
    worktree: Path,
    ticket: Ticket,
    final_id: str,
    branch_name: str,
    pre_land_tip: str,
    main_branch_name: str | None = None,
    *,
    merge_already_composed: bool = False,
) -> Result[None, LandError]:
    """`git merge --squash --no-commit` the worktree's finalized `branch_name`
    onto `root`, then splice tickets.md and tickets-archive.md (T-0959);
    unwinds the squash on any conflict outside `ticket.scope` (or a true
    in-scope conflict), or a splice failure. `pre_land_tip` (T-0907) is this
    run's verified pre-mutation root tip, threaded through to
    `_check_squash_conflicted` and this function's own unwind.

    T-1721: `main_branch_name`, when given, resolves the true merge-base
    (`_true_merge_base(worktree, main_branch_name)`) and reads tickets.md
    at that commit, threading it into the ledger splice as `base_text` --
    this is the FINAL splice that actually lands on main, so it is the
    real fix site for the T-1637 field incident (a legitimate sibling-
    ticket ledger edit, made in the same worktree while landing a
    different ticket, silently dropped by T-0479's blanket main-wins
    sibling default -- see `_splice_only_ticket`'s own docstring).
    `None` (the default, and the degrade path on any git failure resolving
    the base) falls back to the pre-T-1721 behavior unchanged.

    T-1036: the ledger read that this splice is BASED ON is deliberately
    deferred until immediately before the write, and taken under `root`'s
    own `ledger_lock` -- the same lock every ordinary single-ticket verb
    (`write_ticket`/`write_all`/`write_archive`) already serializes
    through. Before this fix, `root_pre_text`/`root_pre_archive_text` were
    captured once, BEFORE the `git merge --squash` step, then used to
    build the spliced write several git operations (and, on a busy
    checkout, several seconds) later with no lock held in between: any
    concurrent `frob ticket new`/`evidence`/`done-report`/... writing
    `root`'s tickets.md in that window had its bytes silently overwritten
    the moment this splice wrote its own stale-based text back out --
    a real lost update (a tail-filed coordinator block clobbered twice by
    concurrent lands' squash-splices, and stale-snapshot draft-id
    collisions from the same root cause). Re-reading fresh, under the
    lock, right before the single write that actually lands means any
    writer that got in first is captured in this splice's base text
    instead of being silently discarded; a writer that loses the lock
    race simply writes to the working tree after this land's commit,
    same as any other sequential edit -- never a lost update. The
    squash-merge itself (a `git` operation against `root`'s working tree,
    run once per land, well before this point) is deliberately NOT run
    under `ledger_lock` -- see `_land_lock`'s own module comment for why
    a worktree's committed lock-file artifact once made reusing that
    exact path across a squash-merge unsafe; only the narrow
    read-splice-write critical section needs the lock, not the merge.

    T-3089: `root` and `stage` are two DIFFERENT roles that happen to be
    the same directory today. `stage` is the checkout the squash-merge
    runs in, the conflicts are resolved in, and the spliced ledger is
    written and staged into -- a disposable worktree detached at
    `pre_land_tip` once the compose moves out of tree. `root` stays the
    repository whose LIVE ledger is authoritative: `ledger_lock(root)`
    and the base texts re-read under it are deliberately still root's,
    because T-1036's lost-update fix is about capturing whichever
    concurrent `frob ticket new`/`evidence` writer got to root's
    working-tree tickets.md first, and that writer never touches a
    disposable stage.

    T-3121: `merge_already_composed` says the caller
    (`compose_squash_in_disposable_worktree`) has ALREADY run the real
    `git merge --squash --no-commit` inside `stage`, so running it again
    here would either be a no-op-with-an-error or, worse, re-merge an
    already-resolved tree. Everything downstream of the merge -- the
    per-path conflict resolution, the splice, the unwind -- is unchanged
    and still reads `stage`'s index exactly as it did when this function
    performed the merge itself."""
    if not merge_already_composed:
        squash = run_argv(
            ["git", "-C", str(stage), "merge", "--squash", "--no-commit", branch_name]
        )
        if squash.is_err:
            return Err(LandError.GitFailed)

    conflict_check = _check_squash_conflicted(
        stage, worktree, ticket, branch_name, pre_land_tip
    )
    # (ticket-scoped; final_id is used only for the ledger splice below)
    if conflict_check.is_err:
        return Err(conflict_check.danger_err)

    worktree_final_text = ledger_path(worktree).read_text(encoding="utf-8")
    worktree_final_archive_text = _read_archive_text_or_empty(worktree)
    # frob:ticket T-1721
    base_ledger_text = None
    if main_branch_name is not None:
        base_sha = _true_merge_base(worktree, main_branch_name)
        if base_sha.is_ok:
            base_ledger_text = _read_text_at_ref(
                worktree, base_sha.danger_ok, "tickets.md"
            )

    with ledger_lock(root):
        # T-1036: re-read root's CURRENT ledger/archive/archived-ids HERE,
        # under the lock, not from a stale pre-squash snapshot -- see this
        # function's own docstring for the incident this closes.
        root_pre_text = _read_ledger_text_or_empty(root)
        # frob:ticket T-0959
        root_pre_archive_text = _read_archive_text_or_empty(root)

        # T-0479: base on root's CURRENT tickets.md, overlay only
        # `final_id`'s own block from the worktree's finalized copy -- see
        # the analogous comment in `_merge_main_into_worktree`. This is the
        # final splice that actually lands on main, so it is the last line
        # of defense against sibling-ticket resurrection even if something
        # upstream missed it -- and (T-1721) also the last chance to carry
        # a genuine sibling edit forward via `base_ledger_text` before it
        # is silently and permanently lost.
        archived_ids = _archived_ids(root)
        spliced = _splice_and_stage(
            stage,
            root_pre_text,
            worktree_final_text,
            archived_ids=archived_ids,
            ticket_id=final_id,
            base_text=base_ledger_text,
        )
        if spliced.is_err:
            return _unwind_squash_apply(
                stage, pre_land_tip, final_id, spliced.danger_err
            )

        # frob:ticket T-0959
        # T-0959: tickets-archive.md's final splice, mirroring the
        # tickets.md splice just above -- this is the LAST line of defense
        # against the T-0703 incident (a stale worktree archive
        # wholesale-overwriting main's newer one), since this is the
        # squash-apply commit that actually lands on main.
        # `root_pre_archive_text` (re-read fresh under the lock, i.e.
        # root's CURRENT tip) is authoritative; the worktree's finalized
        # archive copy is the other side.
        archive_spliced = _splice_and_stage_archive(
            stage, root_pre_archive_text, worktree_final_archive_text
        )
        if archive_spliced.is_err:
            return _unwind_squash_apply(
                stage, pre_land_tip, final_id, archive_spliced.danger_err
            )

        return _refuse_if_land_regresses_terminal_state(
            stage,
            pre_land_tip,
            final_id,
            root_pre_text,
            spliced.danger_ok,
            archived_ids,
        )


# frob:ticket T-0976
def _unwind_squash_apply(
    stage: Path, pre_land_tip: str, final_id: str, err: LandError
) -> Result[None, LandError]:
    """Reset `stage`'s squash-apply back to `pre_land_tip` and propagate
    `err` -- `_squash_and_splice_ledger`'s shared unwind-on-failure step,
    used by every one of its own failure paths. `_verified_reset_root`'s
    own error (if the reset itself fails) takes priority over `err` since
    a failed unwind leaves `stage` in a worse, unresolved state that must
    be surfaced first."""
    unwound = _verified_reset_root(stage, pre_land_tip, final_id)
    return Err(unwound.danger_err if unwound.is_err else err)


# frob:ticket T-0976
def _refuse_if_land_regresses_terminal_state(
    stage: Path,
    pre_land_tip: str,
    final_id: str,
    root_pre_text: str,
    spliced_text: str,
    archived_ids,  # noqa: ANN001
) -> Result[None, LandError]:
    """T-0631's TICK005-backed regression sweep: refuse (and unwind) THIS
    land if its own ledger splice would regress any terminal (DONE/
    DROPPED) ticket back to a non-terminal state, before the squash-apply
    is ever committed -- `_squash_and_splice_ledger`'s final check."""
    regressions = _tick005_land_regressions(root_pre_text, spliced_text, archived_ids)
    if not regressions:
        return Ok(None)
    _log.error(
        "land: %s refused -- ticket(s) %s would regress from a "
        "terminal state to non-terminal via this land's ledger splice "
        "(TICK005 regression sweep, T-0631); resolve the splice by "
        "hand (`git -C %s show HEAD:tickets.md` for the pre-land "
        "state) before retrying",
        final_id,
        ", ".join(regressions),
        stage,
    )
    unwound = _verified_reset_root(stage, pre_land_tip, final_id)
    if unwound.is_err:
        return Err(unwound.danger_err)
    return Err(LandError.TerminalStateRegression)


# frob:ticket T-0631
#: Terminal ticket states -- mirrors `frob.gates._TERMINAL_STATES` (T-0537).
#: Duplicated rather than imported: `frob.gates` depends on `frob.tickets`,
#: never the reverse (docs/rework.md cycle-avoidance), so this land-time
#: sweep cannot reach into `frob.gates` for the constant it mirrors.
_LAND_TERMINAL_STATES = (TicketState.DONE, TicketState.DROPPED)


# frob:ticket T-0631
def _tick005_land_regressions(
    pre_text: str, post_text: str, archived_ids: frozenset[str]
) -> tuple[str, ...]:
    """TICK005-backed regression sweep (T-0631): ticket ids that were
    terminal (DONE/DROPPED) in `pre_text` (root's ledger before this
    land's splice) but are neither terminal nor archived in `post_text`
    (root's ledger staged after the splice) -- the same regression class
    `frob.gates._tick005_merge_state_regression` (T-0537) detects after a
    genuine two-parent merge commit, run here instead directly around
    THIS land's own squash-splice: `_squash_and_splice_ledger` always
    produces a single-parent squash-apply commit, so the gate's own
    `HEAD^2` precondition can never fire for a `frob ticket land` run at
    all (T-0631's motivating gap -- a hand-resolved-conflict-style
    regression introduced by a land would otherwise only surface on some
    LATER unrelated merge commit, or never). A parse failure on either
    side degrades to "no regressions found" (fail-open on this specific
    detector only) rather than blocking every land on a ledger the rest
    of `land()` already tolerates parsing failures around elsewhere."""
    pre_parsed = _parse_ledger(pre_text)
    if pre_parsed.is_err:
        return ()
    post_parsed = _parse_ledger(post_text)
    if post_parsed.is_err:
        return ()
    pre_map = pre_parsed.danger_ok
    post_map = post_parsed.danger_ok
    regressed: list[str] = []
    for ticket_id, pre_ticket in sorted(pre_map.items()):
        if pre_ticket.state not in _LAND_TERMINAL_STATES:
            continue
        if ticket_id in archived_ids:
            continue
        post_ticket = post_map.get(ticket_id)
        if post_ticket is None:
            continue
        if post_ticket.state in _LAND_TERMINAL_STATES:
            continue
        regressed.append(ticket_id)
    return tuple(regressed)


# frob:ticket T-0761


# frob:ticket T-0463
# frob:ticket T-0761
# frob:tests tests/test_ticket_land.py::TestLandCompleteness.test_worktree_pointed_at_same_branch_as_main_is_refused_not_silently_empty  # noqa: E501
def _worktree_full_changeset(
    worktree: Path, main_branch_name: str
) -> Result[frozenset[str], LandError]:
    """The COMPLETE set of paths `worktree`'s finalized branch changes
    relative to `main_branch_name`: tracked edits, untracked new files, AND
    deletions, all in one git-native call.

    `land()`'s wip-commit step (`git add -A`) has already turned every
    untracked new file and every deletion into a tracked change on the
    branch by the time this runs, so a plain `git diff --name-only
    <base>..HEAD` (against the TRUE merge-base, resolved explicitly via
    `_true_merge_base`) reports the true full changeset -- unlike a hand
    `git diff HEAD` / patch-based land, which only ever sees tracked deltas
    against the CURRENT commit and silently omits anything that was
    untracked (T-0463: the root cause of the T-0448
    `docs/modules/render.md` loss, where a surgical git-diff-patch land
    dropped an untracked file with no error).

    T-0761: before diffing, this now ALSO refuses (`Err(IncompleteLand)`)
    if the resolved merge-base commit is identical to `worktree`'s `HEAD`
    commit -- meaning the worktree branch carries not one commit beyond
    `main_branch_name` (the T-0640 false-green condition: `worktree` was
    pointed at the same checkout/branch as `root`, so every git operation
    `land()` performs against "the worktree's own branch" silently
    degenerated to a self-merge/self-diff no-op). A genuine landing always
    has at least the finalize-and-close commit (`_commit_finalize_writes`)
    uniquely on the worktree branch by the time this runs; a merge-base
    equal to HEAD here is never a legitimate "nothing to land" case, only
    this misconfiguration."""
    base = _true_merge_base(worktree, main_branch_name)
    if base.is_err:
        return Err(base.danger_err)
    head = _rev_parse(worktree, "HEAD")
    if head.is_err:
        return Err(head.danger_err)
    if base.danger_ok == head.danger_ok:
        _log.error(
            "land: %s's HEAD (%s) has NO commits beyond the true merge-base "
            "with %s (%s) -- the worktree branch is identical to (or an "
            "ancestor of) %s, so there is nothing to squash-apply. This is "
            "the T-0640 false-green condition: `--worktree` almost "
            "certainly points at the SAME checkout/branch %s has checked "
            "out, rather than a distinct feature branch. Create a real "
            "feature branch (`git -C %s worktree add -b <branch> <path>`) "
            "and retry",
            worktree,
            head.danger_ok,
            main_branch_name,
            base.danger_ok,
            main_branch_name,
            worktree,
            worktree,
        )
        return Err(LandError.IncompleteLand)
    diff = run_argv(
        [
            "git",
            "-C",
            str(worktree),
            "diff",
            "--name-only",
            f"{base.danger_ok}..HEAD",
        ]
    )
    if diff.is_err or diff.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(
        frozenset(
            line.strip() for line in diff.danger_ok.stdout.splitlines() if line.strip()
        )
    )


# frob:ticket T-0463
def _staged_files(stage: Path) -> Result[frozenset[str], LandError]:
    """The paths currently staged in `stage`'s index relative to `HEAD`
    (`git diff --cached --name-only`) -- used to assert the squash-apply
    actually staged everything the worktree changed BEFORE the landing
    commit is made, so an incomplete land aborts loudly instead of
    committing a silently-partial changeset."""
    diff = run_argv(["git", "-C", str(stage), "diff", "--cached", "--name-only"])
    if diff.is_err or diff.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(
        frozenset(
            line.strip() for line in diff.danger_ok.stdout.splitlines() if line.strip()
        )
    )


# frob:ticket T-0463
# frob:ticket T-0907
def _assert_land_complete(
    stage: Path,
    worktree: Path,
    ticket_id: str,
    main_branch_name: str,
    pre_land_tip: str,
) -> Result[frozenset[str], LandError]:
    """Post-squash, pre-commit completeness assertion (T-0463): the set of
    paths staged in `stage`'s index must be a SUPERSET of everything the
    worktree changed relative to `main_branch_name` (tracked edits,
    untracked new files, deletions). If any worktree-changed file is
    missing from staging, the squash is unwound (`_verified_reset_root`,
    T-0907 -- resets to the explicit `pre_land_tip`, not a bare `HEAD`) and
    this returns `Err(IncompleteLand)` with the exact missing paths logged
    -- the land never commits a silently-partial changeset. Returns the
    worktree's full changeset on success (for the report)."""
    expected = _worktree_full_changeset(worktree, main_branch_name)
    if expected.is_err:
        unwound = _verified_reset_root(stage, pre_land_tip, ticket_id)
        return Err(unwound.danger_err if unwound.is_err else expected.danger_err)

    staged = _staged_files(stage)
    if staged.is_err:
        unwound = _verified_reset_root(stage, pre_land_tip, ticket_id)
        return Err(unwound.danger_err if unwound.is_err else staged.danger_err)

    # frob:ticket T-1769
    # T-1769: the land-owned release artifacts are DELIBERATELY absent
    # from the staged apply. T-1760's `_reset_release_artifacts_to_pre_land`
    # discards whatever the squash carried for them (recompute, do not
    # carry), so a worktree that merged main after a sibling's version bump
    # legitimately "changed" all three and legitimately has none of them
    # staged. Counting that as an incomplete land made every such worktree
    # permanently unlandable -- the two guards contradicted each other.
    # `_apply_release_bump` writes the correct values afterwards.
    from frob.tickets._land_release import _LAND_OWNED_RELEASE_FILES

    missing = (expected.danger_ok - staged.danger_ok) - set(_LAND_OWNED_RELEASE_FILES)
    if missing:
        unwound = _verified_reset_root(stage, pre_land_tip, ticket_id)
        if unwound.is_err:
            return Err(unwound.danger_err)
        _log.error(
            "land: %s refused -- the staged squash-apply onto %s is missing "
            "file(s) the worktree changed: %s. This is the T-0463 "
            "completeness gap (a stale git-diff/patch land silently drops "
            "untracked or deleted files) -- inspect `git -C %s status` and "
            "`git -C %s diff --name-only %s...HEAD`, then retry "
            "`frob ticket land %s --worktree %s`",
            ticket_id,
            stage,
            sorted(missing),
            worktree,
            worktree,
            main_branch_name,
            ticket_id,
            worktree,
        )
        return Err(LandError.IncompleteLand)

    return Ok(expected.danger_ok)


def _land_commit_details(root: Path) -> tuple[str | None, tuple[str, ...]]:
    """The just-made HEAD commit's sha and changed-file list, best-effort
    (`None`/`()` if the git calls fail)."""
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
    return sha_str, files


# frob:ticket T-2220
# frob:ticket T-2274
# frob:tests tests/test_ticket_land.py::TestRecordLandCommit.test_records_land_commit_field_in_a_follow_up_commit  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestRecordLandCommit.test_plan_land_finalized_ticket_is_resolvable_by_ticket_id  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestRecordLandCommit.test_record_land_commit_never_absorbs_a_bystanders_dirty_file  # noqa: E501
def _record_land_commit(root: Path, final_id: str, land_sha: str) -> str | None:
    """Persist `land_sha` (the squash-apply commit that just landed
    `final_id`'s code) onto that ticket's own `land_commit` field, in a
    small follow-up commit made right here, still inside this same `frob
    ticket land` invocation (T-2220 -- see `Ticket.land_commit`'s own
    docstring for why this cannot be baked into `land_sha`'s own commit: a
    commit's tree/hash is fixed before the commit exists, so nothing can
    embed its own future hash in its own content; the earliest a commit
    can truthfully name a sha is the very next commit after it).

    Best-effort throughout, mirroring `_record_verify_intent_for_landed_
    commit`'s posture in `frob.tickets._land`: `land_sha` is already
    durably on `root` by the time this runs, so a failure here (ticket
    not found post-squash, a write/add/commit git failure) is logged
    loudly and swallowed, never turned into a `LandError` -- an already-
    sealed land must never be reported as failed over a missing
    convenience field. Returns the new HEAD sha (this record commit) on
    success, or `None` if no new commit was made (the field could not be
    written, or nothing to commit)."""
    from frob.tickets import _load_one
    from frob.tickets._store import write_ticket

    loaded = _load_one(root, final_id)
    if loaded.is_err:
        _log.error(
            "land: %s not found post-squash in %s -- cannot record its "
            "own land_commit (%s); %s already landed, this is a best-"
            "effort T-2220 augmentation only",
            final_id,
            root,
            land_sha,
            final_id,
        )
        return None
    # T-2274: snapshot the dirty-path set BEFORE this write, so the
    # `add` below can stage exactly (and only) the paths THIS write_ticket
    # call itself produced -- never a bystander's unrelated dirty file
    # already sitting in `root` at this moment (the T-2256 incident: a
    # concurrent land's own uncommitted mid-edit to `_land.py` was ambient
    # in the shared root when this exact step ran and got scooped into
    # this commit by a blanket `git add -A`). Comparing the before/after
    # porcelain sets is mode-agnostic -- it works whether `write_ticket`
    # touches `tickets.md` (single mode), `tickets/<id>/ticket.md` (dir/v2
    # mode), or some future storage shape, without this function needing
    # to know or guess which.
    before_dirty = frozenset(_porcelain_dirty_paths(root))
    updated = loaded.danger_ok.model_copy(update={"land_commit": land_sha})
    written = write_ticket(root, updated)
    if written.is_err:
        _log.error(
            "land: %s land_commit write failed (%s) -- %s already landed "
            "at %s, only the T-2220 record field is missing",
            final_id,
            written.danger_err,
            final_id,
            land_sha,
        )
        return None
    return _stage_and_commit_land_commit_record(root, final_id, land_sha, before_dirty)


# frob:ticket T-2274
def _stage_and_commit_land_commit_record(
    root: Path, final_id: str, land_sha: str, before_dirty: frozenset[str]
) -> str | None:
    """`_record_land_commit`'s own ARCH001 split (T-2274): stage exactly
    the paths `write_ticket` itself made dirty (`before_dirty`'s
    complement, see the caller's own T-2274 comment) and commit them --
    never `git add -A`. Same best-effort, log-and-swallow posture as the
    caller."""
    new_paths = sorted(
        _pathspec_targets(frozenset(_porcelain_dirty_paths(root)) - before_dirty)
    )
    if not new_paths:
        _log.error(
            "land: %s land_commit write produced no new dirty path in %s "
            "-- %s already landed at %s, only the T-2220 record field is "
            "missing (nothing to stage, so nothing committed)",
            final_id,
            root,
            final_id,
            land_sha,
        )
        return None

    add_argv = ["git", "-C", str(root), "add", "--", *new_paths]
    with _land_internal_git_env():
        add = run_argv(add_argv)
        if add.is_err or add.danger_ok.returncode != 0:
            _log.error(
                "land: %s land_commit add failed: %s -- %s already landed "
                "at %s, only the T-2220 record field is missing",
                final_id,
                _describe_git_failure(add_argv, add),
                final_id,
                land_sha,
            )
            return None
        commit_argv = [
            "git",
            "-C",
            str(root),
            "commit",
            "-m",
            f"chore(tickets): record land commit for {final_id}",
        ]
        commit = run_argv(commit_argv)
    if commit.is_err or commit.danger_ok.returncode != 0:
        _log.error(
            "land: %s land_commit commit failed: %s -- %s already landed "
            "at %s, only the T-2220 record field is missing",
            final_id,
            _describe_git_failure(commit_argv, commit),
            final_id,
            land_sha,
        )
        return None

    new_sha = _rev_parse(root, "HEAD")
    if new_sha.is_err:
        return None
    _log.info(
        "land: %s land_commit recorded as %s (own record commit %s)",
        final_id,
        land_sha,
        new_sha.danger_ok,
    )
    return new_sha.danger_ok


# frob:ticket T-1001
def _absorption_scoped_content_matches(
    root: Path, worktree: Path, ticket: Ticket
) -> bool:
    """Whether every file in `ticket.scope` that a diff between the
    worktree's finalized HEAD and `root`'s current HEAD touches is empty
    (T-1001, churn item 2's content-verification half): the two commit
    tips live in the SAME object store (`worktree` is a git worktree of
    `root`'s own clone), so a direct cross-checkout `git diff` between
    them is a real content comparison, not a heuristic. Best-effort:
    a git failure on either side conservatively returns `False` (never
    treat an unverifiable comparison as a confirmed match)."""
    worktree_head = _rev_parse(worktree, "HEAD")
    if worktree_head.is_err:
        return False
    diff = run_argv(
        ["git", "-C", str(root), "diff", "--name-only", worktree_head.danger_ok, "HEAD"]
    )
    if diff.is_err or diff.danger_ok.returncode != 0:
        return False
    diverged = [
        line.strip() for line in diff.danger_ok.stdout.splitlines() if line.strip()
    ]
    scoped_diverged = [p for p in diverged if scope_matches(p, ticket.scope)]
    return not scoped_diverged


# frob:ticket T-1001
# frob:tests tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail.test_retry_after_full_success_reports_absorption_not_commit_failed kind="integration"  # noqa: E501
def _absorption_verified(
    root: Path, worktree: Path, ticket: Ticket, final_id: str
) -> bool:
    """Whether an empty-stage squash-apply (T-1001, churn item 2) can
    safely be reported as `absorbed by prior land` rather than the
    misleading `CommitFailed` an empty `git commit` would otherwise raise:
    BOTH `final_id` must already be `done` in `root`'s CURRENT ledger
    (loaded fresh, post-splice -- proving a prior land really did close
    this exact ticket on main, not merely that this squash happened to
    stage nothing for some unrelated reason) AND every one of `ticket`'s
    own scoped files must already match between the worktree and `root`
    (`_absorption_scoped_content_matches`). Either check failing means
    this is NOT a genuine absorption -- the caller falls through to the
    original `_commit_squash_apply` attempt (and its honest error) rather
    than silently reporting a false success."""
    from frob.tickets import _load_one

    loaded = _load_one(root, final_id)
    if loaded.is_err or loaded.danger_ok.state != TicketState.DONE:
        return False
    return _absorption_scoped_content_matches(root, worktree, ticket)


# frob:ticket T-1001
# frob:tests tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail.test_retry_after_full_success_reports_absorption_not_commit_failed kind="integration"  # noqa: E501
def _report_stacked_sibling_absorption(
    root: Path,
    ticket_id: str,
    final_id: str,
    wip_committed: bool,
    did_merge: bool,
) -> LandReport:
    """Build the clean-success `LandReport` for an absorbed land (T-1001):
    `ledger_spliced=False` (nothing NEW was spliced -- the prior land's
    splice already carries this ticket's ledger state) is the honest,
    reusable signal distinguishing this from a normal land's report
    without needing a new field on the frozen `LandReport` model;
    `commit_sha` names the ALREADY-EXISTING commit that absorbed this
    ticket (root's current `HEAD`, since this call made no new commit),
    and `files_changed`/`worktree_changeset` are empty since nothing new
    landed with this call."""
    sha = _rev_parse(root, "HEAD")
    sha_str = sha.danger_ok if sha.is_ok else None
    _log.info(
        "land: %s (%s) absorbed by prior land -- already done on %s at %s, "
        "no new commit needed",
        ticket_id,
        final_id,
        root,
        sha_str,
    )
    return LandReport(
        ticket_id=ticket_id,
        final_id=final_id,
        dry_run=False,
        wip_committed=wip_committed,
        merged_main_into_worktree=did_merge,
        ledger_spliced=False,
        commit_sha=sha_str,
        files_changed=(),
        worktree_changeset=(),
        release_bumped_to=None,
        natives_rebuilt=False,
    )


# frob:ticket T-3121
# frob:doc docs/modules/tickets-landing.md#the-disposable-stage-flip-t-3121
# frob:tests tests/unit/test_land_stage_flip.py::TestPublishSquashApply.test_racing_publish_surfaces_dirtymain  # noqa: E501
# frob:tests tests/unit/test_land_stage_flip.py::TestPublishSquashApply.test_blocked_resync_is_not_a_land_failure  # noqa: E501
# frob:tests tests/unit/test_land_stage_flip.py::TestPublishSquashApply.test_clean_publish_advances_root_and_resyncs  # noqa: E501
def _publish_squash_apply(
    root: Path,
    stage: Path,
    ticket: Ticket,
    final_id: str,
    *,
    pre_land_tip: str,
    main_branch_name: str,
) -> Result[bool, LandError]:
    """`_commit_squash_apply`'s disposable-stage replacement (T-3121):
    fold everything the transaction built in `stage` into a commit object
    parented on `pre_land_tip`, publish it onto `refs/heads/
    <main_branch_name>` by compare-and-swap, then bring `root`'s index and
    working tree up to the published tip. Returns `Ok(root_resync_failed)`
    -- `True` meaning the commit IS public and correct but `root` still
    describes the old tip and needs an operator.

    WHY this replaces the in-tree `git commit` wholesale rather than
    wrapping it: a `git commit` writes the ref of whatever checkout it
    runs in. Running it in `stage` would advance the disposable worktree's
    detached HEAD and publish nothing; running it in `root` would put the
    whole transaction back in the shared tree, which is the window this
    ticket exists to close. Fold + CAS is the only shape that keeps the
    build off `root` AND makes `main` move in one atomic ref update.
    `fold_worktree_into_commit` refuses while any path is unmerged, which
    is what keeps conflict markers out of a landing commit, and
    `commit-tree` runs no hooks, so the `FROB_LAND_INTERNAL` env
    `_commit_squash_apply` needed for the T-0731 pre-commit hook has no
    counterpart here.

    A lost CAS means `main` moved since `pre_land_tip` -- a concurrently
    landed sibling -- which is the SAME condition `land()` already refuses
    with `DirtyMain`, so it is reported as `DirtyMain` and not as a new
    error class for an old condition.

    The resync's failure semantics are settled (T-3114): post-publish
    there is nothing to unwind, so an `Err` is logged loudly (the log line
    carries the published sha and the `git read-tree -m -u` recovery
    command) and returned as `True` rather than propagated as a land
    failure, and it is attempted EXACTLY once -- a retry only races the
    same sibling that blocked it."""
    folded = fold_worktree_into_commit(
        root, stage, pre_land_tip, _commit_message(ticket, final_id)
    )
    if folded.is_err:
        _log.error(
            "land: %s could not fold the composed stage %s into a commit "
            "(unresolved conflict, or a git-plumbing failure) -- nothing "
            "was published, %s is untouched",
            final_id,
            stage,
            root,
        )
        _verified_reset_root(stage, pre_land_tip, final_id)
        return Err(LandError.CommitFailed)
    new_sha = folded.danger_ok

    published = publish_ref_cas(
        root, f"refs/heads/{main_branch_name}", pre_land_tip, new_sha
    )
    if published.is_err:
        _log.error(
            "land: %s refused -- %s moved away from %s while this land was "
            "composing (a sibling land published first), so the "
            "compare-and-swap publish of %s was rejected. Nothing was "
            "overwritten and %s is untouched; re-run `frob ticket land %s "
            "--worktree ...` against the new tip",
            final_id,
            main_branch_name,
            pre_land_tip,
            new_sha,
            root,
            final_id,
        )
        _verified_reset_root(stage, pre_land_tip, final_id)
        return Err(LandError.DirtyMain)

    resynced = resync_root_to_published_tip(root, pre_land_tip, new_sha)
    if resynced.is_err:
        _log.error(
            "land: %s IS LANDED as %s on %s -- the commit is public and "
            "correct -- but %s's index/working tree could not be advanced "
            "off %s (%s). This is NOT a land failure and must not be "
            "reverted. `git -C %s status` will report the whole landed "
            "changeset as local modifications until an operator commits or "
            "stashes the concurrent uncommitted edit that blocked it and "
            "runs: git -C %s read-tree -m -u %s %s",
            final_id,
            new_sha,
            main_branch_name,
            root,
            pre_land_tip,
            resynced.danger_err,
            root,
            root,
            pre_land_tip,
            new_sha,
        )
        return Ok(True)
    return Ok(False)


# frob:ticket T-1740
def _commit_squash_apply(
    stage: Path, ticket: Ticket, final_id: str, *, pre_land_tip: str
) -> Result[None, LandError]:
    """Commit the staged squash-apply with a conventional-commit message,
    under `FROB_LAND_INTERNAL=1` (T-0828) -- this commit legitimately
    carries the REL001 version bump and generated CHANGELOG.md entry
    (`_apply_release_bump`), so it MUST set the flag or the T-0731
    land-owned-files `pre-commit` hook refuses land's own commit.

    T-1740: THE gap this ticket's audit found -- every OTHER failure path
    in the squash-apply pipeline already unwinds via `_verified_reset_
    root`, but this, the LAST step, used to just tell the operator to
    clean up by hand, leaving the fully-staged squash sitting in `stage`'s
    index on any commit failure (a hook rejection, an identity/config
    issue, disk pressure). Now attempts `_verified_reset_root` first (the
    normal, safe full unwind back to `pre_land_tip` -- nothing else can
    have moved `stage`'s tip between the successful stage and this commit
    attempt in the ordinary case) and falls back to `_unstage_index_only`
    if THAT itself reports drift, so the index is never left holding
    land's own staged content for an unrelated `git commit` to sweep up,
    even in this doubly-unlikely case."""
    commit_argv = [
        "git",
        "-C",
        str(stage),
        "commit",
        "-m",
        _commit_message(ticket, final_id),
    ]
    with _land_internal_git_env():
        commit = run_argv(commit_argv)
    if commit.is_err or commit.danger_ok.returncode != 0:
        unwound = _verified_reset_root(stage, pre_land_tip, final_id)
        if unwound.is_err:
            _unstage_index_only(stage)
        _log.error(
            "land: %s squash-apply staged onto %s but the final commit "
            "failed (%s) -- %s. Fix the underlying commit failure (a "
            "pre-commit hook, git identity/config, disk pressure) and "
            "retry `frob ticket land %s --worktree ...`",
            final_id,
            stage,
            _describe_git_failure(commit_argv, commit),
            "the staged squash was unwound"
            if unwound.is_ok
            else (
                "the squash could not be safely unwound (tip drift); the "
                f"index was unstaged instead (T-1740): {stage} is unchanged "
                "except for whatever a concurrent write already committed"
            ),
            final_id,
        )
        return Err(LandError.CommitFailed)
    return Ok(None)


# frob:ticket T-1001
def _absorbed_land_report(
    root: Path,
    stage: Path,
    worktree: Path,
    ticket: Ticket,
    ticket_id: str,
    final_id: str,
    wip_committed: bool,
    did_merge: bool,
) -> LandReport | None:
    """`_land_squash_apply`'s T-1001 (churn item 2) pre-commit check: when
    a worktree carries several tickets, the first land's squash absorbs
    every sibling's files and ledger state -- each subsequent land then
    stages an EMPTY squash, and an unconditional `git commit` would exit 1
    with no stderr, surfaced as a scary, unexplained `CommitFailed`.
    Returns a ready-to-return `LandReport` (`Ok`, never committing
    anything new) when nothing is staged AND that emptiness is VERIFIED
    genuine absorption (`_absorption_verified`) -- `None` otherwise, telling
    the caller to fall through to the ordinary `_commit_squash_apply`
    attempt and its honest error. An empty stage for some OTHER,
    unexplained reason is never silently reported as success.

    T-3089: emptiness is read from `stage`'s index (the checkout the
    squash was applied into), while the absorption EVIDENCE -- `final_id`
    already `done`, scoped content already matching -- is read from
    `root`, the repository whose landed history is what "a prior land
    already did this" is a claim about."""
    staged_now = _staged_files(stage)
    if staged_now.is_err or staged_now.danger_ok:
        return None
    if not _absorption_verified(root, worktree, ticket, final_id):
        return None
    return _report_stacked_sibling_absorption(
        root, ticket_id, final_id, wip_committed, did_merge
    )


# frob:ticket T-0907
# frob:ticket T-1721
# frob:ticket T-3089
# frob:tests tests/unit/test_land_squash_stage.py::TestSquashApplyStageTarget.test_default_stage_runs_the_whole_transaction_in_root  # noqa: E501
# frob:tests tests/unit/test_land_squash_stage.py::TestSquashApplyStageTarget.test_explicit_stage_leaves_root_completely_untouched  # noqa: E501
# frob:doc \
# docs/modules/tickets-landing.md#frobtickets_land_squash----the-squash-apply-stage-tar\
# get-t-3089
def _land_squash_apply(
    root: Path,
    worktree: Path,
    ticket: Ticket,
    ticket_id: str,
    final_id: str,
    wip_committed: bool,
    did_merge: bool,
    main_branch_name: str,
    *,
    pre_land_tip: str,
    bump_version: Callable[[Path, Ticket, str], Result[str | None, LandError]]
    | None = None,
    rebuild_natives: Callable[[Path], bool] | None = None,
    sync_gate_rules: Callable[[Path, str], Result[tuple[str, ...] | None, LandError]]
    | None = None,
    pre_commit_sweep: Callable[[Path, str], bool | None] | None = None,
    stage: Path | None = None,
    squash_precomposed: bool = False,
) -> Result[LandReport, LandError]:
    """Squash-apply the worktree's finalized branch onto `root`, splice
    tickets.md, apply an optional REL001 version bump (T-0338), assert
    completeness (T-0463) BEFORE committing, commit, trigger an optional
    native rebuild, and build the final `LandReport`.

    `pre_land_tip` (T-0907) is `root`'s verified `HEAD` sha captured by the
    caller (`_land_locked`) BEFORE this function started mutating `root` --
    every unwind path below (`_squash_and_splice_ledger`,
    `_apply_release_bump`, `_assert_land_complete`) resets to this EXACT
    value via `_verified_reset_root` rather than a bare `git reset --hard`,
    the fix for the T-0907 stale-tip incident (see that ticket's module-
    level comment above `_verified_reset_root`).

    T-1334: split into this squash-and-splice half plus
    `_land_squash_apply_finish` (everything once the squash itself has
    succeeded) to clear ARCH001 -- the seam is the one point every failure
    path on both sides already unwinds through `_verified_reset_root`, so
    no control-flow or unwind semantics change.

    T-1514: `pre_commit_sweep(root, final_id)` (opt-in), if supplied, is
    invoked by `_land_squash_apply_finish` at the LAST point before the
    final commit -- `root`'s working tree already holds the full squashed
    merge-preview changeset, staged but not yet committed, so a refusal
    here is unwound via the same `_verified_reset_root` every other
    pre-commit failure path already uses, costing nothing and touching no
    foreign commit (unlike the T-1456 post-land sweep, which must
    `git reset --hard` a REAL commit that may already have foreign work
    stacked on top of it). Returns `True` (sweep passed, possibly after a
    Tier-A auto-fix), `False` (refuse and unwind), or `None` (skip,
    matching every other opt-in land callable's default posture).

    T-3089: `stage` is the checkout every index- and working-tree-consuming
    step of this transaction runs against -- the squash-merge itself, the
    conflict resolution, the ledger splice, the REL001 bump, the gate-rule
    sync, the completeness assertion, the Tier-A pre-commit sweep and the
    landing commit. It defaults to `root`, which is the historical
    behavior byte for byte: the whole transaction happens in the shared
    checkout and is visible to every sibling agent's `git status` while it
    runs. Passing a DISPOSABLE worktree detached at `pre_land_tip`
    (`compose_squash_in_disposable_worktree`) moves that entire window off
    the shared tree instead. All six stages must move TOGETHER: composing
    only some of them leaves the rest reading an index nothing populated,
    which commits nothing while still writing `state: done`.

    `root` keeps the roles that are genuinely about the repository rather
    than about the tree being built: `ledger_lock` and the live ledger
    base texts (T-1036), the absorption evidence, and the branch-drift
    guard.

    T-3121: `squash_precomposed` says `stage` is a disposable worktree the
    caller already ran the real `git merge --squash --no-commit` inside
    (`compose_squash_in_disposable_worktree`). It changes exactly two
    things and nothing else: the splice helpers skip their own merge so it
    cannot run twice, and the transaction is sealed by fold + CAS publish
    (`_publish_squash_apply`) instead of an in-tree `git commit`. It is an
    error to pass it without also passing `stage`; the two always travel
    together."""
    stage = root if stage is None else stage
    branch = current_branch(worktree)
    if branch.is_err:
        return Err(LandError.GitFailed)
    branch_name = branch.danger_ok

    # frob:ticket T-1258
    # Ledger v2 design section 5: a v2-mode `root` (any `tickets/T-####/
    # ticket.md` present) needs no ledger splice at all -- the squash-merge
    # already stages disjoint ticket directories correctly on its own.
    v2_mode = _store_mode(root) == "v2"
    squashed = (
        _squash_and_splice_ledger_v2(
            stage,
            worktree,
            ticket,
            final_id,
            branch_name,
            pre_land_tip,
            merge_already_composed=squash_precomposed,
        )
        if v2_mode
        else _squash_and_splice_ledger(
            root,
            stage,
            worktree,
            ticket,
            final_id,
            branch_name,
            pre_land_tip,
            main_branch_name=main_branch_name,
            merge_already_composed=squash_precomposed,
        )
    )
    if squashed.is_err:
        return Err(squashed.danger_err)

    return _land_squash_apply_finish(
        root,
        worktree,
        ticket,
        ticket_id,
        final_id,
        wip_committed,
        did_merge,
        main_branch_name,
        v2_mode,
        stage,
        pre_land_tip=pre_land_tip,
        bump_version=bump_version,
        rebuild_natives=rebuild_natives,
        sync_gate_rules=sync_gate_rules,
        pre_commit_sweep=pre_commit_sweep,
        squash_precomposed=squash_precomposed,
    )


# frob:ticket T-1514
def _apply_pre_commit_sweep_or_unwind(
    stage: Path,
    ticket_id: str,
    final_id: str,
    pre_land_tip: str,
    pre_commit_sweep: Callable[[Path, str], bool | None] | None,
) -> Result[None, LandError]:
    """`_land_squash_apply_finish`'s LAST pre-commit checkpoint (T-1514,
    split out to keep that function under ARCH001's line threshold):
    `stage`'s working tree already holds the complete, staged merge-preview
    changeset with nothing committed yet, so a `pre_commit_sweep` refusal
    here is unwound cheaply via `_verified_reset_root` and touches no
    foreign commit, unlike the T-1456 post-land sweep's `git reset --hard`
    of an already-real commit. A `None` `pre_commit_sweep` (not supplied)
    or a `None`/`True` verdict is a no-op `Ok(None)`."""
    if pre_commit_sweep is None:
        return Ok(None)
    swept = pre_commit_sweep(stage, final_id)
    if swept is not False:
        return Ok(None)
    unwound = _verified_reset_root(stage, pre_land_tip, ticket_id)
    if unwound.is_err:
        return Err(unwound.danger_err)
    _log.error(
        "land: %s refused -- the T-1514 pre-commit unscoped error sweep "
        "found new error(s) no Tier-A auto-fix could resolve; the staged "
        "squash was unwound, %s is unchanged, nothing was committed",
        ticket_id,
        stage,
    )
    return Err(LandError.PreLandUnscopedSweepFailed)


# frob:ticket T-1920
# frob:tests tests/test_ticket_work_and_land_finish.py::TestBranchDriftGuard.test_branch_drift_before_final_commit_refuses_by_construction  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestBranchDriftGuard.test_no_drift_is_a_noop  # noqa: E501
def _assert_still_on_expected_branch(
    root: Path, expected_branch: str, ticket_id: str, *, unstage_on_drift: bool = True
) -> Result[None, LandError]:
    """T-1920 (T-1910 residue, REQUIRED FIXES 2-4): re-derive `root`'s
    CURRENT checked-out branch fresh, right here, immediately before the
    one git operation (`_commit_squash_apply`) that durably writes the
    ticket's terminal state and any REL001 bump -- and refuse, unstaging
    everything staged so far, if it no longer matches `expected_branch`
    (the branch `main_branch_name` resolved to back at precheck time,
    threaded through this entire land unchanged).

    This is the by-construction fix T-1910 left as residue rather than a
    race-catcher: the prior architecture computed `main_branch_name`
    once, early, then trusted it all the way through the squash, the
    REL001 bump, and the final commit -- so if `root`'s HEAD ever moved
    to a DIFFERENT branch in that window (the T-1895 incident's own
    shape: a fully-formed, complete commit that carried the whole diff
    and sat only on branch `t-1906-fix` while the ledger read `done` on
    `main`), `_commit_squash_apply` would commit onto whatever branch
    HEAD NOW points at -- durably writing `state: done` plus the version
    bump into a commit reachable from `expected_branch` only by
    accident, discoverable only afterward via `LAND-PROOF
    verified=False` (playbook's `[[verify-after-the-mutation]]` failure
    shape: a guard that runs after the mutation it is meant to gate can
    only report the problem, never prevent it).

    Called as the LAST check before `_commit_squash_apply` -- nothing
    below this point can move `root`'s HEAD before the commit runs, so a
    clean result here means the immediately-following commit is
    reachable from `expected_branch` BY CONSTRUCTION, not by hope: git's
    own `commit` unconditionally advances whatever branch ref HEAD
    currently names, so verifying HEAD's branch identity right before
    the commit is equivalent to verifying the commit's own future
    reachability.

    On drift, only `_unstage_index_only(root)` is used to unwind -- never
    `_verified_reset_root`'s `git reset --hard`, which would hard-reset
    whatever branch is NOW checked out (not necessarily
    `expected_branch`) back to `pre_land_tip`; that would be actively
    destructive to a foreign branch a concurrent process may be using,
    the same T-1740 lesson `_commit_squash_apply`'s own fallback already
    applies. `expected_branch` itself was never re-derived here from a
    hardcoded `"main"` literal -- it is the exact value this land has
    used consistently since `_land_precheck` resolved it, so a caller
    whose repository's default branch is not literally named `main`
    (uncommon in this repo, but not assumed away) is still verified
    correctly against its OWN branch, not a hardcoded string.

    T-1920's own investigation (mirroring T-1913's for the sibling
    ancestor-retry mitigation) could not reproduce the underlying T-1895
    race in a synchronous test fixture either -- no code path in this
    repo's own land pipeline moves `root`'s HEAD mid-land under normal
    operation, and a real concurrent `git checkout` racing a held
    `land_lock` was not observed. This guard closes the class BY
    CONSTRUCTION regardless: if a branch move can happen (any cause,
    reproduced or not), the terminal-state/bump write it would otherwise
    poison now cannot occur without first passing this check.

    T-3121: `unstage_on_drift=False` suppresses the root-side unwind for a
    land whose transaction is staged in a DISPOSABLE worktree instead of
    `root`. The check itself still runs -- the CAS publish moves
    `refs/heads/<expected_branch>`, so verifying `root`'s HEAD still names
    that branch is exactly as load-bearing as before -- but root's index
    then holds nothing of this land's, so `_unstage_index_only(root)`
    could only discard a SIBLING's staged work. Refusing without touching
    root is strictly the safer unwind in that mode."""
    current = current_branch(root)
    if current.is_err:
        _log.error(
            "land: %s refused -- could not determine %s's current branch "
            "immediately before the final squash commit; refusing rather "
            "than risk committing a terminal-state/REL001-bump write onto "
            "an unverified branch (T-1920)",
            ticket_id,
            root,
        )
        if unstage_on_drift:
            _unstage_index_only(root)
        return Err(LandError.BranchDrift)
    if current.danger_ok != expected_branch:
        _log.error(
            "land: %s refused -- %s's checked-out branch drifted from "
            "%s (the branch this land began operating on) to %s between "
            "precheck and the final squash commit; committing now would "
            "produce a commit reachable only from %s, not %s -- exactly "
            "the T-1895 incident shape. The staged squash's index was "
            "unstaged; nothing was committed, no terminal ticket state "
            "and no REL001 bump were written (T-1920)",
            ticket_id,
            root,
            expected_branch,
            current.danger_ok,
            current.danger_ok,
            expected_branch,
        )
        if unstage_on_drift:
            _unstage_index_only(root)
        return Err(LandError.BranchDrift)
    return Ok(None)


# frob:ticket T-3111
# frob:tests tests/test_ticket_land.py::TestRebuildNatives.test_rebuild_runs_after_the_landing_commit_is_durable  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestRebuildNatives.test_invoked_when_native_source_touched  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestRebuildNatives.test_skipped_when_no_native_source_touched  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestRebuildNatives.test_rebuild_failure_does_not_block_land  # noqa: E501
def _post_publish_native_rebuild(
    root: Path,
    final_id: str,
    worktree_changeset: frozenset[str],
    rebuild_natives: Callable[[Path], bool] | None,
) -> bool:
    """The stale-native warning plus the optional native rebuild, run only
    AFTER the landing commit is durable (T-3111).

    WHY the position matters: `_maybe_rebuild_natives` shells out to a
    cargo/maturin build that takes minutes. It used to run between
    `_assert_land_complete` and `_commit_squash_apply`, i.e. while `root`
    held the entire squashed changeset staged with nothing committed --
    every second of that build was a second a sibling `frob ticket land`
    saw `DirtyMain`, `frob ticket new` refused with `LandInProgress`, and
    an unrelated agent could not start work at all. One land serialized the
    whole fleet for the length of a native build. Nothing the rebuild
    produces is commit content (it writes gitignored build artifacts), so
    the landing commit is byte-identical either way; only the contention
    window changes.

    A failure here deliberately does NOT unwind, and must not be
    "hardened" into one later: the commit is already public and a sibling
    may already have stacked on it, so hard-resetting it is the T-1456/
    T-1740 "reset --hard a real commit" hazard, traded for a strictly
    smaller problem -- a stale local `.so`, which `_warn_if_native_stale`
    and NATIVE001 already surface and a local `frob natives build` already
    fixes. `_maybe_rebuild_natives` already logs the failure loudly and
    returns `False`, which flows into `LandReport.natives_rebuilt`; this
    function only relocates that behavior, it does not change it."""
    _warn_if_native_stale(root, final_id)
    return _maybe_rebuild_natives(root, final_id, worktree_changeset, rebuild_natives)


# frob:ticket T-3121
# frob:tests tests/unit/test_land_stage_flip.py::TestPublishSquashApply.test_clean_publish_advances_root_and_resyncs  # noqa: E501
# frob:tests tests/unit/test_land_squash_stage.py::TestSquashApplyStageTarget.test_default_stage_runs_the_whole_transaction_in_root  # noqa: E501
def _seal_squash_apply(
    root: Path,
    stage: Path,
    ticket: Ticket,
    final_id: str,
    *,
    pre_land_tip: str,
    main_branch_name: str,
    squash_precomposed: bool,
) -> Result[bool, LandError]:
    """The one step that makes the built transaction durable, in whichever
    of its two forms applies -- split out of `_land_squash_apply_finish`
    to keep that function under ARCH001's threshold (T-2214).

    A pre-composed disposable `stage` is sealed by fold + CAS publish
    (`_publish_squash_apply`); an in-root stage is sealed by the
    historical in-tree `git commit` (`_commit_squash_apply`). Returns
    `Ok(root_resync_failed)` -- always `False` on the in-root path, which
    has no resync step because root IS the tree that was built."""
    if squash_precomposed:
        return _publish_squash_apply(
            root,
            stage,
            ticket,
            final_id,
            pre_land_tip=pre_land_tip,
            main_branch_name=main_branch_name,
        )
    committed = _commit_squash_apply(
        stage, ticket, final_id, pre_land_tip=pre_land_tip
    )
    if committed.is_err:
        return Err(committed.danger_err)
    return Ok(False)


# frob:ticket T-0907
def _land_squash_apply_finish(
    root: Path,
    worktree: Path,
    ticket: Ticket,
    ticket_id: str,
    final_id: str,
    wip_committed: bool,
    did_merge: bool,
    main_branch_name: str,
    v2_mode: bool,
    stage: Path,
    *,
    pre_land_tip: str,
    bump_version: Callable[[Path, Ticket, str], Result[str | None, LandError]] | None,
    rebuild_natives: Callable[[Path], bool] | None,
    sync_gate_rules: Callable[[Path, str], Result[tuple[str, ...] | None, LandError]]
    | None,
    pre_commit_sweep: Callable[[Path, str], bool | None] | None = None,
    squash_precomposed: bool = False,
) -> Result[LandReport, LandError]:
    """`_land_squash_apply`'s post-squash half (T-1334, split to clear that
    function's ARCH001 finding): the release bump, gate-rule sync,
    completeness assertion, native-staleness warning/rebuild, stacked-
    sibling absorption check, final commit, and `LandReport` construction
    -- everything that runs once the squash-and-splice step has already
    succeeded. Same unwind-on-failure behavior as before the split: every
    failure path here still resets `root` back to `pre_land_tip` via the
    helpers it calls, exactly as when this was still inline in
    `_land_squash_apply`.

    T-3089: every index- and working-tree-consuming stage below runs
    against `stage` (see `_land_squash_apply`'s own docstring for the two
    roles and why they must move together); `root` is kept only for the
    branch-drift guard, the absorption evidence and the post-commit
    report, none of which read the staged tree.

    T-3121: under `squash_precomposed` the transaction lives entirely in
    the disposable `stage` until `_publish_squash_apply` folds and
    CAS-publishes it, so every pre-publish failure path here unwinds the
    STAGE (or simply drops it -- the caller's context manager removes the
    worktree either way) and `root` has nothing of this land's in it to
    unwind. That is why the branch-drift guard's root-side unstage is
    suppressed in this mode: root's index holds only whatever a sibling
    put there, and unstaging it would destroy that sibling's staged
    work."""
    bumped = _apply_release_bump(stage, ticket, final_id, bump_version, pre_land_tip)
    if bumped.is_err:
        return Err(bumped.danger_err)
    release_bumped_to = bumped.danger_ok

    gate_rules_synced = _apply_gate_rule_sync(
        stage, final_id, sync_gate_rules, pre_land_tip
    )
    if gate_rules_synced.is_err:
        return Err(gate_rules_synced.danger_err)

    completeness = _assert_land_complete(
        stage, worktree, ticket_id, main_branch_name, pre_land_tip
    )
    if completeness.is_err:
        return Err(completeness.danger_err)
    worktree_changeset = completeness.danger_ok

    # T-1001 (churn item 2): stacked-sibling absorption -- see
    # `_absorbed_land_report`'s own docstring.
    absorbed = _absorbed_land_report(
        root, stage, worktree, ticket, ticket_id, final_id, wip_committed, did_merge
    )
    if absorbed is not None:
        _post_publish_native_rebuild(
            root, final_id, worktree_changeset, rebuild_natives
        )
        return Ok(absorbed)

    swept = _apply_pre_commit_sweep_or_unwind(
        stage, ticket_id, final_id, pre_land_tip, pre_commit_sweep
    )
    if swept.is_err:
        return Err(swept.danger_err)

    still_on_branch = _assert_still_on_expected_branch(
        root, main_branch_name, ticket_id, unstage_on_drift=not squash_precomposed
    )
    if still_on_branch.is_err:
        return Err(still_on_branch.danger_err)

    sealed = _seal_squash_apply(
        root,
        stage,
        ticket,
        final_id,
        pre_land_tip=pre_land_tip,
        main_branch_name=main_branch_name,
        squash_precomposed=squash_precomposed,
    )
    if sealed.is_err:
        return Err(sealed.danger_err)
    root_resync_failed = sealed.danger_ok

    # frob:ticket T-3111
    natives_rebuilt = _post_publish_native_rebuild(
        root, final_id, worktree_changeset, rebuild_natives
    )

    return _finish_real_land_report(
        root,
        ticket_id,
        final_id,
        wip_committed,
        did_merge,
        v2_mode,
        worktree_changeset=worktree_changeset,
        release_bumped_to=release_bumped_to,
        natives_rebuilt=natives_rebuilt,
        root_resync_failed=root_resync_failed,
    )


# frob:ticket T-2220
def _finish_real_land_report(
    root: Path,
    ticket_id: str,
    final_id: str,
    wip_committed: bool,
    did_merge: bool,
    v2_mode: bool,
    *,
    worktree_changeset: frozenset[str],
    release_bumped_to: str | None,
    natives_rebuilt: bool,
    root_resync_failed: bool = False,
) -> Result[LandReport, LandError]:
    """`_land_squash_apply_finish`'s own tail (T-2220, split out to keep
    that function under ARCH001's 60-line threshold): the just-made
    commit's sha/files, `_record_land_commit`'s best-effort follow-up
    write (see that function's own docstring for why it cannot be baked
    into the commit it names), and the final `LandReport`."""
    sha_str, files = _land_commit_details(root)
    _log.info("land: %s landed as %s onto %s at %s", ticket_id, final_id, root, sha_str)
    if sha_str is not None:
        _record_land_commit(root, final_id, sha_str)
    return Ok(
        LandReport(
            ticket_id=ticket_id,
            final_id=final_id,
            dry_run=False,
            wip_committed=wip_committed,
            merged_main_into_worktree=did_merge,
            ledger_spliced=not v2_mode,
            unowned_deletions=(),
            commit_sha=sha_str,
            files_changed=files,
            worktree_changeset=tuple(sorted(worktree_changeset)),
            release_bumped_to=release_bumped_to,
            natives_rebuilt=natives_rebuilt,
            root_resync_failed=root_resync_failed,
        )
    )
