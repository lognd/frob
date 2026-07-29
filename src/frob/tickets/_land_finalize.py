"""`frob ticket land` -- finalize/close/squash-apply/release stage.

See docs/modules/tickets.md#frob-ticket-land.

Split out of `frob.tickets._land` (T-1186, following the verbatim-move
pattern `_evidence.py`/`_reporting.py` set at T-1171): the final stage of
a land -- draft-id finalization and sibling-draft renumbering, closing
the finalized ticket, the squash-apply-onto-main step and its ledger
splice, the completeness assertion, and the release-bump/uv.lock/native-
rebuild machinery `land()` runs once the merge and reverification stages
(`_land_merge`/`_land_verify`) have both succeeded. Zero caller-visible
behavior change -- every moved function keeps its original body,
docstring, and `frob:ticket`/`frob:tests` directives verbatim;
`frob.tickets._land` re-exports the public surface via explicit import.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.gitio import current_branch, run_argv
from frob.logging import get_logger
from frob.tickets._land_merge import (
    _archived_ids,
    _auto_resolve_out_of_scope_conflicts,
    _commit_message,
    _describe_git_failure,
    _land_internal_git_env,
    _porcelain_dirty,
    _read_archive_text_or_empty,
    _read_ledger_text_or_empty,
    _rev_parse,
    _splice_and_stage,
    _splice_and_stage_archive,
    _true_merge_base,
    _verified_reset_root,
)
from frob.tickets._models import (
    LandError,
    LandReport,
    Ticket,
    TicketState,
    scope_matches,
)
from frob.tickets._provisional import is_draft_id
from frob.tickets._store import (
    _parse_ledger,
    archive_path,
    ledger_digest,
    ledger_lock,
    ledger_path,
    load_all,
    load_archive,
    write_all,
    write_archive,
)

_log = get_logger(__name__)


def _land_finalize_and_close(
    root: Path,
    worktree: Path,
    ticket_id: str,
    did_merge: bool,
    main_branch_name: str,
    *,
    covers_scope: Callable[[Ticket], bool | None] | None = None,
) -> Result[str, LandError]:
    """Commit the merge (if any), finalize a draft id, close the ticket,
    and commit those writes too -- returns the ticket's final id. Runs
    under `FROB_LAND_INTERNAL=1` (T-0828) so the merge commit is never
    refused by the T-0731 land-owned-files `pre-commit` hook.

    T-1179: `root` (main) is threaded through to `_finalize_and_close_
    ticket` so the draft-id finalize below reads its id ceiling from
    main's CURRENT ledger, not `worktree`'s possibly-stale copy -- see
    `finalize_draft_for_land`'s doc for the incident this closes."""
    if did_merge:
        commit_argv = [
            "git",
            "-C",
            str(worktree),
            "commit",
            "-m",
            f"merge {main_branch_name} into worktree for landing {ticket_id}",
        ]
        with _land_internal_git_env():
            commit = run_argv(commit_argv)
        if commit.is_err or commit.danger_ok.returncode != 0:
            _log.error(
                "land: %s merge commit failed: %s",
                ticket_id,
                _describe_git_failure(commit_argv, commit),
            )
            return Err(LandError.GitFailed)

    finalized = _finalize_and_close_ticket(
        root, worktree, ticket_id, covers_scope=covers_scope
    )
    if finalized.is_err:
        return Err(finalized.danger_err)
    final_id = finalized.danger_ok

    draft_id_mapping: dict[str, str] = {}
    if is_draft_id(ticket_id) and ticket_id != final_id:
        draft_id_mapping[ticket_id] = final_id

    siblings_finalized = _finalize_sibling_drafts(root, worktree, final_id)
    if siblings_finalized.is_err:
        return Err(siblings_finalized.danger_err)
    draft_id_mapping.update(siblings_finalized.danger_ok)

    rewritten = _rewrite_draft_references_in_bodies(worktree, draft_id_mapping)
    if rewritten.is_err:
        return Err(rewritten.danger_err)

    waive_rewritten = _rewrite_draft_references_in_waive_sites(
        worktree, draft_id_mapping
    )
    if waive_rewritten.is_err:
        return Err(waive_rewritten.danger_err)

    committed = _commit_finalize_writes(worktree, final_id)
    if committed.is_err:
        return Err(committed.danger_err)
    return Ok(final_id)


def _finalize_and_close_ticket(
    root: Path,
    worktree: Path,
    ticket_id: str,
    *,
    covers_scope: Callable[[Ticket], bool | None] | None = None,
) -> Result[str, LandError]:
    """Finalize a draft id (if `ticket_id` is one) and transition it to
    DONE; returns the ticket's final id."""
    final_id_result = _finalize_draft_id(root, worktree, ticket_id)
    if final_id_result.is_err:
        return Err(final_id_result.danger_err)
    final_id = final_id_result.danger_ok

    return _close_finalized_ticket(
        worktree, ticket_id, final_id, covers_scope=covers_scope
    )


def _finalize_draft_id(
    root: Path, worktree: Path, ticket_id: str
) -> Result[str, LandError]:
    """`finalize_draft_for_land` if `ticket_id` is a draft id; else
    `ticket_id` unchanged. T-1179: uses the land-specific finalize (id
    ceiling read fresh from `root`/main) rather than plain `finalize_draft`
    (worktree-only view) -- see `finalize_draft_for_land`'s doc."""
    from frob.tickets import finalize_draft_for_land

    if not is_draft_id(ticket_id):
        return Ok(ticket_id)
    finalized = finalize_draft_for_land(worktree, ticket_id, root)
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
    return Ok(finalized.danger_ok)


# frob:ticket T-0637
# frob:tests tests/test_ticket_land.py::TestStandaloneSiblingDraftSurvivesLand.test_sibling_draft_ticket_finalized_and_lands_alongside  # noqa: E501
def _finalize_sibling_drafts(
    root: Path, worktree: Path, landed_final_id: str
) -> Result[dict[str, str], LandError]:
    """Finalize every OTHER draft ticket (T-draft-...) still in `worktree`'s
    active ledger after the ticket actually being landed has already been
    finalized (T-0637).

    A worktree can accumulate STANDALONE sibling draft tickets (features/
    bugs filed mid-session via `frob ticket new` off the default branch,
    T-0162 mints a draft id there since final sequential ids are only ever
    minted against the default branch) that have nothing to do with the
    ticket actually being landed. Left unfinalized, a draft id block would
    either land verbatim onto main (violating the T-0162 invariant that a
    T-draft-<hex> id must never persist on the default branch) or -- before
    T-0637's `_carry_forward_new_worktree_tickets` fix -- get silently
    dropped outright by the ledger splice, the real field incident this
    closes (T-0575's own T-draft-3d5f6965 sibling block, and again two
    drafts filed in T-0576's worktree). Every remaining draft ticket is
    finalized here (via `finalize_draft`, i.e. `renumber_one` against the
    worktree's CURRENT merged view, same primitive `_finalize_draft_id`
    uses for the landing ticket itself) so the later ledger splice onto
    main carries a real sequential id, not a draft one.

    Returns the old-draft-id -> final-id mapping for every sibling
    finalized (T-0811: this is the exact mapping `_rewrite_draft_references_
    in_bodies` needs to fix up stale Done-report prose citing these old
    draft ids elsewhere in the ledger), for logging/observability; the
    caller does not need to thread these through further otherwise --
    once finalized, each sibling's fresh section is picked up by
    `_carry_forward_new_worktree_tickets` at squash-splice time the same
    way any other new-to-main ticket is.

    T-1179: uses `finalize_draft_for_land` (not `finalize_draft`) so each
    sibling's id ceiling is also read fresh from `root` (main), not just
    `worktree`'s copy -- same fix as the landing ticket's own finalize."""
    from frob.tickets import finalize_draft_for_land

    loaded = load_all(worktree)
    if loaded.is_err:
        _log.error(
            "land: could not load %s's active ledger to finalize sibling draft tickets",
            worktree,
        )
        return Err(LandError.GitFailed)
    draft_ids = sorted(
        tid for tid in loaded.danger_ok if is_draft_id(tid) and tid != landed_final_id
    )
    finalized_mapping: dict[str, str] = {}
    for draft_id in draft_ids:
        result = finalize_draft_for_land(worktree, draft_id, root)
        if result.is_err:
            _log.error(
                "land: sibling draft %s finalize failed (%s) after %s "
                "already finalized -- inspect %s and retry",
                draft_id,
                result.danger_err,
                landed_final_id,
                worktree,
            )
            return Err(LandError.GitFailed)
        finalized_mapping[draft_id] = result.danger_ok
        _log.info(
            "land: finalized sibling draft %s -> %s (alongside %s)",
            draft_id,
            result.danger_ok,
            landed_final_id,
        )
    return Ok(finalized_mapping)


# frob:ticket T-0811
# frob:tests tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand.test_land_rewrites_own_draft_id_reference_in_done_report  # noqa: E501
# frob:ticket T-0976
def _rewrite_draft_references_in_one_ledger(
    worktree: Path,
    loader,  # noqa: ANN001
    writer,  # noqa: ANN001
    path_fn,  # noqa: ANN001
    label: str,
    mapping: dict[str, str],
    pattern: re.Pattern,
) -> Result[None, LandError]:
    """One ledger (active or archive)'s draft-id-reference rewrite:
    `_rewrite_draft_references_in_bodies`'s per-ledger half, split from
    its loop over the two ledgers. T-0889: this load and its own
    write are NOT held under one lock span -- the load's `ledger_digest`
    is passed as `expected_digest` so the write refuses instead of
    clobbering if the ledger changed in between."""
    digest = ledger_digest(path_fn(worktree))
    loaded = loader(worktree)
    if loaded.is_err:
        _log.error(
            "land: could not load %s ledger to rewrite stale draft-id "
            "reference(s) %s (%s)",
            label,
            mapping,
            loaded.danger_err,
        )
        return Err(LandError.GitFailed)
    tickets = loaded.danger_ok
    rewritten: dict[str, Ticket] = {}
    changed_ids: list[str] = []
    for tid, ticket in tickets.items():
        new_body = pattern.sub(lambda m: mapping[m.group(0)], ticket.body)
        if new_body == ticket.body:
            rewritten[tid] = ticket
            continue
        rewritten[tid] = ticket.model_copy(update={"body": new_body})
        changed_ids.append(tid)
    if not changed_ids:
        return Ok(None)
    written = writer(worktree, rewritten, expected_digest=digest)
    if written.is_err:
        _log.error(
            "land: failed writing %s ledger after rewriting stale "
            "draft-id reference(s) in %s (%s)",
            label,
            changed_ids,
            written.danger_err,
        )
        return Err(LandError.GitFailed)
    _log.info(
        "land: rewrote stale draft-id reference(s) %s in %s ledger body text for %s",
        mapping,
        label,
        changed_ids,
    )
    return Ok(None)


def _rewrite_draft_references_in_bodies(
    worktree: Path, mapping: dict[str, str]
) -> Result[None, LandError]:
    """Rewrite every prose mention of a just-finalized draft id (the
    `mapping` computed by `_finalize_draft_id`/`_finalize_sibling_drafts`,
    old draft id -> final id) inside ticket BODY text, across both the
    active and archive ledgers, before the finalize writes are committed
    (T-0811).

    `renumber_one` (the rename primitive both callers above use) already
    rewrites every STRUCTURAL id reference -- a ticket's own id, its
    `blocked_by`/`parent` fields, and `frob:ticket`/`frob:tests`/etc.
    directive lines in code -- but a Done report's own free-text "Filed:
    T-draft-<hex8> (...)" claim about a SIBLING draft is prose, not a
    structural field, so it survives untouched. When that cited sibling
    is finalized to a real id in the same land, the claim now points at
    an id no longer present anywhere in the ledger and TICK006's
    phantom-filing-claim gate reds main -- the recurring incident this
    ticket exists to close (T-0778/T-0797, T-0745/T-0764: 3x this drive).

    A draft id (`T-draft-<hex8>`, T-0162) is a fixed-width, unambiguous
    token -- substituting it as plain text carries no partial-match risk,
    so a straight regex alternation over `mapping`'s keys (guarded so a
    match can't be a PREFIX of a longer hex run) is sufficient; no
    ticket-DSL parsing is needed here, unlike `renumber_one`'s structural
    rewrite.

    T-0889: unlike `renumber_one`, this loop's load and its eventual
    `write_all`/`write_archive` are NOT held under one `ledger_lock` span
    (each `loader`/`writer` pair acquires its own lock independently) -- so
    each iteration's load captures a `ledger_digest` snapshot passed
    through as `expected_digest`; the write refuses instead of clobbering
    if the ledger changed between this loop's load and its own write."""
    if not mapping:
        return Ok(None)
    pattern = re.compile(
        "(?:"
        + "|".join(
            re.escape(old_id) for old_id in sorted(mapping, key=len, reverse=True)
        )
        + r")(?![0-9a-fA-F])"
    )

    for loader, writer, path_fn, label in (
        (load_all, write_all, ledger_path, "active"),
        (load_archive, write_archive, archive_path, "archive"),
    ):
        rewritten = _rewrite_draft_references_in_one_ledger(
            worktree, loader, writer, path_fn, label, mapping, pattern
        )
        if rewritten.is_err:
            return rewritten
    return Ok(None)


_WAIVE_REWRITE_EXCLUDED_LEDGERS = frozenset({"tickets.md", "tickets-archive.md"})


# frob:ticket T-0812
# frob:tests tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand.test_land_rewrites_strata_waive_clause_draft_id_reference  # noqa: E501
def _rewrite_draft_references_in_waive_sites(
    worktree: Path, mapping: dict[str, str]
) -> Result[None, LandError]:
    """Rewrite every WAIVE-site reference to a just-finalized draft id (the
    same `mapping` `_rewrite_draft_references_in_bodies` consumes) across
    every TRACKED file, not just ledger prose (T-0812).

    `_rewrite_draft_references_in_bodies` (T-0811) only fixes up Done-
    report prose in `tickets.md`/`tickets-archive.md` -- a `design/*.strata`
    `waive "RULE" ... ticket "T-draft-<hex8>"` clause, or a source
    `frob:waive RULE reason="..." ticket=T-draft-<hex8>` comment, citing
    the SAME renumbered draft id stays dangling forever, because
    `waive007_gate`'s `_waive007_is_exempt_dangling_ref` unconditionally
    exempts every `T-draft-*` id from WAIVE007 (the original T-draft-
    8cd37914 incident this exemption exists for). That exemption is safe
    only as long as the waiver is rewritten to the final id at land time;
    left as-is it silently becomes load-bearing instead -- a waiver
    nobody can ever re-litigate because its ticket ref can never resolve
    again. This closes that gap by extending the identical draft-id ->
    final-id substitution to every tracked file a waive site could live
    in, not just ledger bodies.

    Grep-scoped cheaply via `git grep -l --fixed-strings`, so only files
    that actually contain a literal old draft id are ever opened -- on a
    repo this size that is normally zero or a handful of files, never a
    full-tree walk. The ledger files are excluded here since
    `_rewrite_draft_references_in_bodies` already rewrote them through
    the ticket model (a raw-text rewrite of the same files here would
    race that write); every other tracked file (`.strata`, `.py`, `.rs`,
    `.ts`, ...) is fair game -- a waive site can live in any language's
    comment syntax. Reuses the same fixed-width, unambiguous-token regex
    shape as T-0811 (a draft id can never be a prefix of a longer hex
    run), so no per-language comment parsing is needed."""
    if not mapping:
        return Ok(None)
    pattern = re.compile(
        "(?:"
        + "|".join(
            re.escape(old_id) for old_id in sorted(mapping, key=len, reverse=True)
        )
        + r")(?![0-9a-fA-F])"
    )

    candidates = _grep_waive_site_candidate_files(worktree, mapping)
    if candidates.is_err:
        return Err(candidates.danger_err)
    if candidates.danger_ok is None:
        return Ok(None)

    changed_files: list[str] = []
    for rel in candidates.danger_ok:
        rewritten = _rewrite_one_waive_site_file(worktree, rel, mapping, pattern)
        if rewritten.is_err:
            return Err(rewritten.danger_err)
        if rewritten.danger_ok:
            changed_files.append(rel)

    if changed_files:
        _log.info(
            "land: rewrote stale draft-id waive-site reference(s) %s in %s",
            mapping,
            changed_files,
        )
    return Ok(None)


# frob:ticket T-0976
def _grep_waive_site_candidate_files(
    worktree: Path, mapping: dict[str, str]
) -> Result[list[str] | None, LandError]:
    """`git grep -l --fixed-strings` for every file under `worktree`
    containing a literal old draft id from `mapping`, excluding the ledger
    files (`_rewrite_draft_references_in_bodies` already rewrote those
    through the ticket model) -- `_rewrite_draft_references_in_waive_
    sites`'s candidate-gathering half. `Ok(None)` means "nothing matched,
    caller is done"; a real list means "these files need the per-file
    rewrite pass"."""
    grep_argv = ["git", "-C", str(worktree), "grep", "-l", "--fixed-strings", "-I"]
    for old_id in mapping:
        grep_argv += ["-e", old_id]
    grepped = run_argv(grep_argv)
    if grepped.is_err:
        _log.error(
            "land: could not grep worktree %s for stale draft-id waive-site "
            "reference(s) %s (%s)",
            worktree,
            mapping,
            grepped.danger_err,
        )
        return Err(LandError.GitFailed)
    proc = grepped.danger_ok
    # `git grep -l` returns 1 (not an error) when nothing matches.
    if proc.returncode not in (0, 1):
        _log.error(
            "land: git grep for stale draft-id waive-site reference(s) %s "
            "failed unexpectedly in %s (exit %s): %s",
            mapping,
            worktree,
            proc.returncode,
            proc.stderr,
        )
        return Err(LandError.GitFailed)
    if proc.returncode == 1:
        return Ok(None)
    return Ok(
        [
            rel.strip()
            for rel in proc.stdout.splitlines()
            if rel.strip()
            and Path(rel.strip()).name not in _WAIVE_REWRITE_EXCLUDED_LEDGERS
        ]
    )


# frob:ticket T-0976
def _rewrite_one_waive_site_file(
    worktree: Path, rel: str, mapping: dict[str, str], pattern: re.Pattern
) -> Result[bool, LandError]:
    """One candidate file's draft-id waive-site rewrite:
    `_rewrite_draft_references_in_waive_sites`'s per-file half. Returns
    `Ok(True)` if the file actually changed, `Ok(False)` if the pattern
    matched nothing (a `git grep -l` false-positive on a substring outside
    any live reference), `Err` on a read/write failure."""
    target = worktree / rel
    try:
        text = target.read_text(encoding="utf-8")
    except OSError as exc:
        _log.error(
            "land: could not read %s while rewriting stale draft-id "
            "waive-site reference(s) %s (%s)",
            target,
            mapping,
            exc,
        )
        return Err(LandError.GitFailed)
    new_text = pattern.sub(lambda m: mapping[m.group(0)], text)
    if new_text == text:
        return Ok(False)
    try:
        target.write_text(new_text, encoding="utf-8")
    except OSError as exc:
        _log.error(
            "land: could not write %s while rewriting stale draft-id "
            "waive-site reference(s) %s (%s)",
            target,
            mapping,
            exc,
        )
        return Err(LandError.GitFailed)
    return Ok(True)


def _close_finalized_ticket(
    worktree: Path,
    ticket_id: str,
    final_id: str,
    *,
    covers_scope: Callable[[Ticket], bool | None] | None = None,
) -> Result[str, LandError]:
    """Transition `final_id` to DONE. `covers_scope`, if supplied, is a
    callable invoked with the just-finalized `Ticket` (loaded fresh here,
    post-finalize) -- see `land`'s docstring for why this is lazy.

    T-0795: idempotent against a RETRY whose prior attempt already reached
    this transition and committed it (finalize succeeded, close succeeded,
    but a LATER step -- the squash-apply onto `root` -- failed and the
    caller retried the same `land()` call). Before this fix, a retry's
    `transition(..., DONE)` against an already-DONE ticket always errored
    `InvalidTransition` (`done` is a terminal state with no `done -> done`
    edge in `_TRANSITIONS`), even though the land is otherwise perfectly
    resumable -- the real incident this closes (T-0676/T-0774/T-0767: three
    lands that merged+finalized in the worktree, failed before the main
    commit, and required a manual splice-apply onto main because the
    obvious `frob ticket land` retry errored instead of resuming). Loading
    `final_id` FIRST and checking its state lets a retry recognize "already
    done from a prior finalize" and skip straight to returning `final_id`
    for the caller (`_land_finalize_and_close`) to proceed to squash-apply,
    instead of re-running (and failing) the transition.

    T-0821: also auto-advances a ticket still in PLANNED (never run
    through `frob ticket start`, or reverted there by a section-10b ledger
    restore) to IN_PROGRESS before attempting the DONE transition -- see
    the inline comment at that check for the recurring incident this
    closes."""
    from frob.tickets import _load_one, transition

    loaded = _load_one(worktree, final_id)
    if loaded.is_err:
        _log.error(
            "land: %s not found post-finalize in %s -- cannot close",
            final_id,
            worktree,
        )
        return Err(LandError.NotFound)
    current = loaded.danger_ok

    if current.state == TicketState.DONE:
        _log.info(
            "land: %s already done in %s (retry after a prior finalize "
            "that did not reach the main commit, T-0795) -- skipping the "
            "done transition, proceeding straight to squash-apply",
            final_id,
            worktree,
        )
        return Ok(final_id)

    # T-0821: a ticket landed with full evidence and a Done report but
    # never actually run through `frob ticket start` (or reverted to
    # PLANNED by a section-10b ledger restore, T-0752) cannot legally
    # jump PLANNED -> DONE (`_TRANSITIONS` only allows PLANNED ->
    # IN_PROGRESS/DROPPED) -- every prior incident (T-0799, T-0752,
    # T-0815) hit this AFTER the merge already landed in the worktree,
    # forcing a manual start-then-retry recipe with main untouched but
    # the coordinator now needing a second pass. Advance PLANNED ->
    # IN_PROGRESS transparently here, right before the real close
    # transition, whenever finalize's own preconditions (evidence + a
    # substantive Done report, the same gate `transition(..., DONE)`
    # checks a moment later) are otherwise about to be satisfied -- so
    # the close below always sees a from-state the state machine
    # actually allows, and a legitimately-done PLANNED ticket never
    # surfaces `InvalidTransition` post-merge at all.
    if current.state == TicketState.PLANNED:
        advanced = transition(worktree, final_id, TicketState.IN_PROGRESS)
        if advanced.is_err:
            _log.error(
                "land: %s could not auto-advance planned -> in-progress in "
                "%s ahead of close (%s) -- fix evidence/Done report in %s "
                "and retry `frob ticket land %s --worktree %s`",
                final_id,
                worktree,
                advanced.danger_err,
                worktree,
                ticket_id,
                worktree,
            )
            return Err(LandError.CloseFailed)
        current = advanced.danger_ok

    resolved_covers_scope: bool | None = None
    if covers_scope is not None:
        resolved_covers_scope = covers_scope(current)

    closed = transition(
        worktree, final_id, TicketState.DONE, covers_scope=resolved_covers_scope
    )
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
    return Ok(final_id)


# finalize_draft (renumber_one) and transition/close both write directly to
# the worktree's working tree, UNCOMMITTED -- the squash-apply below reads
# from the branch's last COMMIT, which predates these writes. Left
# uncommitted, the finalize rewrite of every frob:ticket <draft-id>
# reference in code (not just the ledger) would never reach main, and the
# worktree would be left dirty after a successful land (reviewer repro,
# T-0176). Commit them now so the squash-apply below sees everything, and
# the worktree ends up clean.
def _commit_finalize_writes(worktree: Path, final_id: str) -> Result[None, LandError]:
    """Commit any working-tree changes finalize/close made, if any -- under
    `FROB_LAND_INTERNAL=1` (T-0828) so this land-internal commit is never
    refused by the T-0731 land-owned-files `pre-commit` hook."""
    finalize_dirty = _porcelain_dirty(worktree)
    if finalize_dirty.is_err:
        return Err(finalize_dirty.danger_err)
    if not finalize_dirty.danger_ok:
        return Ok(None)
    add_argv = ["git", "-C", str(worktree), "add", "-A"]
    with _land_internal_git_env():
        add = run_argv(add_argv)
        if add.is_err or add.danger_ok.returncode != 0:
            _log.error(
                "land: %s finalize add failed: %s",
                final_id,
                _describe_git_failure(add_argv, add),
            )
            return Err(LandError.GitFailed)
        finalize_commit_argv = [
            "git",
            "-C",
            str(worktree),
            "commit",
            "-m",
            f"finalize and close {final_id} for landing",
        ]
        finalize_commit = run_argv(finalize_commit_argv)
    if finalize_commit.is_err or finalize_commit.danger_ok.returncode != 0:
        _log.error(
            "land: %s finalize commit failed: %s",
            final_id,
            _describe_git_failure(finalize_commit_argv, finalize_commit),
        )
        return Err(LandError.GitFailed)
    return Ok(None)


# frob:ticket T-0907
# frob:waive DUP002 reason="T-1186 split-induced false positive: this is the \
# pre-existing, deliberate mirror-image counterpart to \
# frob.tickets._land_merge._check_only_tickets_conflicted -- one checks conflicts \
# after squash-merging main INTO root (root=ours), the other after merging main INTO \
# the worktree (worktree=theirs); the two already coexisted, unwaived, side by side in \
# frob.tickets._land before T-1186's split moved them into separate modules, which is \
# what triggers DUP002's both-new-in-this-diff pairing -- neither function's body \
# changed"
def _check_squash_conflicted(
    root: Path, worktree: Path, ticket: Ticket, branch_name: str, pre_land_tip: str
) -> Result[None, LandError]:
    """`Err(SquashConflict)` (unwinding the squash) if any IN-SCOPE file
    besides tickets.md/tickets-archive.md is still conflicted after the
    squash merge; any OUT-OF-SCOPE conflict is auto-resolved by taking
    main's side first
    (T-0479) -- main is `ours` here (root's checked-out branch, with the
    worktree's finalized branch squash-merged in as `theirs`). `pre_land_tip`
    (T-0907) is this run's verified pre-mutation root tip, threaded through
    to `_verified_reset_root` so every unwind here resets to an explicit sha
    rather than a bare (HEAD-at-reset-time) `git reset --hard`."""
    resolved = _auto_resolve_out_of_scope_conflicts(root, ticket, keep="ours")
    if resolved.is_err:
        unwound = _verified_reset_root(root, pre_land_tip, ticket.id)
        return Err(unwound.danger_err if unwound.is_err else resolved.danger_err)
    remaining = resolved.danger_ok
    if remaining:
        unwound = _verified_reset_root(root, pre_land_tip, ticket.id)
        _log.error(
            "land: %s squash-apply onto %s conflicts in scoped file(s): %s "
            "-- resolve manually (cd %s && git merge --squash %s), commit, "
            "then retry `frob ticket land %s --worktree %s`",
            ticket.id,
            root,
            sorted(remaining),
            root,
            branch_name,
            ticket.id,
            worktree,
        )
        return Err(unwound.danger_err if unwound.is_err else LandError.SquashConflict)
    return Ok(None)


# frob:ticket T-0907
# frob:ticket T-1036
# frob:tests tests/test_ticket_land.py::TestSquashSpliceLedgerChurn.test_concurrent_write_between_squash_and_splice_survives_land  # noqa: E501
def _squash_and_splice_ledger(
    root: Path,
    worktree: Path,
    ticket: Ticket,
    final_id: str,
    branch_name: str,
    pre_land_tip: str,
) -> Result[None, LandError]:
    """`git merge --squash --no-commit` the worktree's finalized `branch_name`
    onto `root`, then splice tickets.md and tickets-archive.md (T-0959);
    unwinds the squash on any conflict outside `ticket.scope` (or a true
    in-scope conflict), or a splice failure. `pre_land_tip` (T-0907) is this
    run's verified pre-mutation root tip, threaded through to
    `_check_squash_conflicted` and this function's own unwind.

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
    read-splice-write critical section needs the lock, not the merge."""
    squash = run_argv(
        ["git", "-C", str(root), "merge", "--squash", "--no-commit", branch_name]
    )
    if squash.is_err:
        return Err(LandError.GitFailed)

    conflict_check = _check_squash_conflicted(
        root, worktree, ticket, branch_name, pre_land_tip
    )
    # (ticket-scoped; final_id is used only for the ledger splice below)
    if conflict_check.is_err:
        return Err(conflict_check.danger_err)

    worktree_final_text = ledger_path(worktree).read_text(encoding="utf-8")
    worktree_final_archive_text = _read_archive_text_or_empty(worktree)

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
        # upstream missed it.
        archived_ids = _archived_ids(root)
        spliced = _splice_and_stage(
            root,
            root_pre_text,
            worktree_final_text,
            archived_ids=archived_ids,
            ticket_id=final_id,
        )
        if spliced.is_err:
            return _unwind_squash_apply(
                root, pre_land_tip, final_id, spliced.danger_err
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
            root, root_pre_archive_text, worktree_final_archive_text
        )
        if archive_spliced.is_err:
            return _unwind_squash_apply(
                root, pre_land_tip, final_id, archive_spliced.danger_err
            )

        return _refuse_if_land_regresses_terminal_state(
            root, pre_land_tip, final_id, root_pre_text, spliced.danger_ok, archived_ids
        )


# frob:ticket T-0976
def _unwind_squash_apply(
    root: Path, pre_land_tip: str, final_id: str, err: LandError
) -> Result[None, LandError]:
    """Reset `root`'s squash-apply back to `pre_land_tip` and propagate
    `err` -- `_squash_and_splice_ledger`'s shared unwind-on-failure step,
    used by every one of its own failure paths. `_verified_reset_root`'s
    own error (if the reset itself fails) takes priority over `err` since
    a failed unwind leaves `root` in a worse, unresolved state that must
    be surfaced first."""
    unwound = _verified_reset_root(root, pre_land_tip, final_id)
    return Err(unwound.danger_err if unwound.is_err else err)


# frob:ticket T-0976
def _refuse_if_land_regresses_terminal_state(
    root: Path,
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
        root,
    )
    unwound = _verified_reset_root(root, pre_land_tip, final_id)
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
def _staged_files(root: Path) -> Result[frozenset[str], LandError]:
    """The paths currently staged in `root`'s index relative to `HEAD`
    (`git diff --cached --name-only`) -- used to assert the squash-apply
    actually staged everything the worktree changed BEFORE the landing
    commit is made, so an incomplete land aborts loudly instead of
    committing a silently-partial changeset."""
    diff = run_argv(["git", "-C", str(root), "diff", "--cached", "--name-only"])
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
    root: Path,
    worktree: Path,
    ticket_id: str,
    main_branch_name: str,
    pre_land_tip: str,
) -> Result[frozenset[str], LandError]:
    """Post-squash, pre-commit completeness assertion (T-0463): the set of
    paths staged in `root`'s index must be a SUPERSET of everything the
    worktree changed relative to `main_branch_name` (tracked edits,
    untracked new files, deletions). If any worktree-changed file is
    missing from staging, the squash is unwound (`_verified_reset_root`,
    T-0907 -- resets to the explicit `pre_land_tip`, not a bare `HEAD`) and
    this returns `Err(IncompleteLand)` with the exact missing paths logged
    -- the land never commits a silently-partial changeset. Returns the
    worktree's full changeset on success (for the report)."""
    expected = _worktree_full_changeset(worktree, main_branch_name)
    if expected.is_err:
        unwound = _verified_reset_root(root, pre_land_tip, ticket_id)
        return Err(unwound.danger_err if unwound.is_err else expected.danger_err)

    staged = _staged_files(root)
    if staged.is_err:
        unwound = _verified_reset_root(root, pre_land_tip, ticket_id)
        return Err(unwound.danger_err if unwound.is_err else staged.danger_err)

    missing = expected.danger_ok - staged.danger_ok
    if missing:
        unwound = _verified_reset_root(root, pre_land_tip, ticket_id)
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
            root,
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


def _commit_squash_apply(
    root: Path, ticket: Ticket, final_id: str
) -> Result[None, LandError]:
    """Commit the staged squash-apply with a conventional-commit message,
    under `FROB_LAND_INTERNAL=1` (T-0828) -- this commit legitimately
    carries the REL001 version bump and generated CHANGELOG.md entry
    (`_apply_release_bump`), so it MUST set the flag or the T-0731
    land-owned-files `pre-commit` hook refuses land's own commit."""
    commit_argv = [
        "git",
        "-C",
        str(root),
        "commit",
        "-m",
        _commit_message(ticket, final_id),
    ]
    with _land_internal_git_env():
        commit = run_argv(commit_argv)
    if commit.is_err or commit.danger_ok.returncode != 0:
        _log.error(
            "land: %s squash-apply staged onto %s but the final commit "
            "failed (%s) -- inspect `git -C %s status`, commit manually "
            "with a conventional-commit message, or `git -C %s reset "
            "--hard` to unwind the staged squash",
            final_id,
            root,
            _describe_git_failure(commit_argv, commit),
            root,
            root,
        )
        return Err(LandError.CommitFailed)
    return Ok(None)


# frob:ticket T-0248
def _warn_if_native_stale(root: Path, final_id: str) -> None:
    """LOUD, non-blocking log warning if `root`'s just-squashed source tree
    now outpaces its own built native extension(s) (T-0248): the incident
    class from T-0166's review, where a landed `strata-core/**` grammar
    change left main's built `strata_core` behind and `frob check` silently
    ran the OLD grammar until a human noticed a confusing SYS004. Fires
    regardless of whether a `rebuild_natives` callback is also supplied --
    a rebuild that runs but is not this warning's business to suppress, and
    a `rebuild_natives=None` caller still gets the loud heads-up either way."""
    from frob.strata._native_staleness import stale_native_warning

    warning = stale_native_warning(root)
    if warning is not None:
        _log.warning("land: %s -- %s", final_id, warning)


# frob:ticket T-0338
_NATIVE_SOURCE_PREFIXES = ("frob-core/", "strata-core/")


def _touches_native_source(changeset: frozenset[str]) -> bool:
    """Whether any path in `changeset` falls under a native-extension source
    tree (T-0338) -- the trigger condition for `rebuild_natives`: a landed
    change that never touched frob-core/strata-core has nothing stale to
    rebuild, so the (potentially slow, minutes-long cargo) rebuild is only
    ever invoked when it can actually matter."""
    return any(path.startswith(_NATIVE_SOURCE_PREFIXES) for path in changeset)


# frob:ticket T-0338
# frob:ticket T-0992
_LAND_PYPROJECT_VERSION_RE = re.compile(r'(?m)^version\s*=\s*"([^"]*)"')


# frob:ticket T-0992
def _read_root_pyproject_version(root: Path, pre_land_tip: str) -> str | None:
    """Read `pyproject.toml`'s `version = "..."` value as it stood at
    `pre_land_tip` -- MAIN's own last-committed state BEFORE this land's
    squash-apply touched the working tree -- via `git show`, or `None` if
    the file did not exist there / is unparsable. This is the T-0992
    monotonicity check's ground truth for "what MAIN already has".

    Deliberately reads the git OBJECT at `pre_land_tip`, never the
    working-tree file on disk: `pyproject.toml` is not protected from a
    ticket's own scope, so `git merge --squash` can (and, per the T-0976
    incident, did) carry a worktree's stale `pyproject.toml` straight into
    `root`'s working tree as part of the squash-apply itself, before
    `bump_version` ever runs -- reading the on-disk file at that point
    would just re-read the very corruption this check exists to catch.
    `pre_land_tip` (captured once, before any mutation, by `land`'s own
    `_rev_parse(root, "HEAD")`) is the one value in this whole flow that is
    guaranteed to still name MAIN's true pre-land commit."""
    shown = run_argv(["git", "-C", str(root), "show", f"{pre_land_tip}:pyproject.toml"])
    if shown.is_err or shown.danger_ok.returncode != 0:
        return None
    match = _LAND_PYPROJECT_VERSION_RE.search(shown.danger_ok.stdout)
    return match.group(1) if match else None


# frob:ticket T-1078
def _read_root_manifest_version(root: Path, pre_land_tip: str) -> str | None:
    """Read `.frob-release.json`'s `version` field as it stood at
    `pre_land_tip` (T-1078) -- the same git-object-read technique
    `_read_root_pyproject_version` uses for `pyproject.toml`, applied to
    the release manifest so an incoherent quartet (manifest lagging
    pyproject, the T-1078 incident class) can be DETECTED from ground
    truth rather than the worktree-carried on-disk copy the squash-apply
    may have already overwritten. `None` if the manifest did not exist at
    `pre_land_tip`, is unparsable JSON, or has no string `version` field --
    all treated as "nothing to compare", never raised."""
    shown = run_argv(
        ["git", "-C", str(root), "show", f"{pre_land_tip}:.frob-release.json"]
    )
    if shown.is_err or shown.danger_ok.returncode != 0:
        return None
    try:
        data = json.loads(shown.danger_ok.stdout)
    except ValueError:
        return None
    version = data.get("version") if isinstance(data, dict) else None
    return version if isinstance(version, str) else None


# frob:ticket T-0992
def _release_bump_is_monotonic(pre_bump_version: str | None, new_version: str) -> bool:
    """Whether `new_version` is strictly greater than `pre_bump_version`
    (T-0992's hard monotonicity refusal, sibling of T-0959's archive
    assertion and T-0740's ledger integrity check). No prior version on
    disk (`pre_bump_version=None`, e.g. a `pyproject.toml`-less test root)
    is vacuously monotonic -- there is nothing to regress against. Falls
    back to a plain string inequality if either side fails PEP 440 parsing
    (e.g. a synthetic non-numeric version in a unit-test fixture) rather
    than raising -- this is a refusal gate, not a place to crash the whole
    land on a malformed version string."""
    if pre_bump_version is None:
        return True
    try:
        from packaging.version import Version

        return Version(new_version) > Version(pre_bump_version)
    except Exception:
        return new_version != pre_bump_version and new_version > pre_bump_version


# frob:ticket T-0338
# frob:ticket T-0907
# frob:ticket T-0992
# frob:ticket T-1078
def _log_monotonicity_refusal(
    final_id: str,
    new_version: str,
    pre_bump_version: str | None,
    pre_manifest_version: str | None,
) -> None:
    """Log the T-0992 monotonicity refusal (T-1078: split out of
    `_apply_release_bump` for ARCH001) -- names an incoherent quartet
    (`.frob-release.json` lagging `pyproject.toml` at `pre_land_tip`)
    explicitly and prescribes `frob release sync` when that desync is the
    actual cause, instead of the bare "not strictly greater" message that
    reads like a genuine version regression."""
    quartet_desynced = (
        pre_manifest_version is not None
        and pre_bump_version is not None
        and pre_manifest_version != pre_bump_version
    )
    if quartet_desynced:
        _log.error(
            "land: %s REL001 version-bump callback computed %s from "
            "a release manifest still at %s, but pyproject.toml is "
            "already at %s -- the release quartet (pyproject.toml/"
            "CHANGELOG.md/.frob-release.json) is INCOHERENT on main "
            "(manifest lagging pyproject); refusing (T-0992 "
            "monotonicity assertion) and unwinding the staged "
            "squash -- run `frob release sync` to reconcile the "
            "manifest to pyproject's actual version, then retry "
            "the land",
            final_id,
            new_version,
            pre_manifest_version,
            pre_bump_version,
        )
    else:
        _log.error(
            "land: %s REL001 version-bump callback computed %s, "
            "which is not strictly greater than main's pre-land "
            "version %s -- refusing (T-0992 monotonicity assertion) "
            "and unwinding the staged squash; the bump input must "
            "be derived from root's current state, never a stale "
            "worktree-carried value",
            final_id,
            new_version,
            pre_bump_version,
        )


# frob:ticket T-1078
def _resync_release_manifest(
    root: Path, final_id: str, new_version: str
) -> Result[None, LandError]:
    """Force `.frob-release.json`'s version to `new_version` and stage it
    (T-1078: split out of `_apply_release_bump` for ARCH001) -- the
    atomic-write fix for the incident where a REL001 bump updated
    `pyproject.toml`/`CHANGELOG.md` but left the manifest on its old
    version, regardless of whether the `bump_version` callback itself
    wrote (or correctly wrote) the manifest. `Ok(None)` when there was
    nothing to resync (`ReleaseError.NoManifest` -- a repo that never
    adopted `frob release stamp`) as well as on a successful resync;
    `Err(LandError.ReleaseBumpFailed)` if the write or the `git add`
    fails."""
    from frob.release import ReleaseError, set_manifest_version

    resynced = set_manifest_version(root, new_version)
    if resynced.is_err and resynced.danger_err != ReleaseError.NoManifest:
        _log.error(
            "land: %s could not resync .frob-release.json to %s (%s) -- "
            "unwinding the staged squash",
            final_id,
            new_version,
            resynced.danger_err,
        )
        return Err(LandError.ReleaseBumpFailed)
    if resynced.is_ok:
        staged = run_argv(["git", "-C", str(root), "add", ".frob-release.json"])
        if staged.is_err or staged.danger_ok.returncode != 0:
            _log.error("land: %s failed to stage resynced .frob-release.json", final_id)
            return Err(LandError.ReleaseBumpFailed)
    return Ok(None)


def _apply_release_bump(
    root: Path,
    ticket: Ticket,
    final_id: str,
    bump_version: Callable[[Path, Ticket, str], Result[str | None, LandError]] | None,
    pre_land_tip: str,
) -> Result[str | None, LandError]:
    """Invoke `bump_version(root, ticket, final_id)` if supplied, unwinding
    the staged squash via `_verified_reset_root` (T-0907) on failure
    (T-0338). `bump_version=None` is a no-op returning `Ok(None)` -- see
    `land`'s docstring for why this is a caller-supplied callback.

    T-0992: captures main's own pre-`pre_land_tip` `pyproject.toml`
    version and hard-refuses (via `_log_monotonicity_refusal`, T-1078)
    unless a reported bump is strictly greater than it -- guards against a
    `bump_version` implementation computing its "next version" from a
    stale, worktree-carried input (T-0976, T-0989).

    T-1078: after a successful, monotonic bump, `_resync_release_manifest`
    force-resyncs `.frob-release.json`'s version to `new_version` in this
    SAME step, regardless of whether `bump_version` itself wrote the
    manifest correctly -- the fix for a REL001 bump that updated
    pyproject.toml/CHANGELOG.md but left the manifest stale, desyncing the
    quartet and blocking every subsequent land on the T-0992 guard."""
    if bump_version is None:
        return Ok(None)
    pre_bump_version = _read_root_pyproject_version(root, pre_land_tip)
    pre_manifest_version = _read_root_manifest_version(root, pre_land_tip)
    bumped = bump_version(root, ticket, final_id)
    if bumped.is_err:
        _log.error(
            "land: %s REL001 version-bump callback failed (%s) -- unwinding "
            "the staged squash; bump pyproject.toml/CHANGELOG.md by hand "
            "(`frob release stamp` once fixed) and retry",
            final_id,
            bumped.danger_err,
        )
        unwound = _verified_reset_root(root, pre_land_tip, final_id)
        return Err(unwound.danger_err if unwound.is_err else bumped.danger_err)
    if bumped.danger_ok is not None:
        new_version = bumped.danger_ok
        if not _release_bump_is_monotonic(pre_bump_version, new_version):
            _log_monotonicity_refusal(
                final_id, new_version, pre_bump_version, pre_manifest_version
            )
            unwound = _verified_reset_root(root, pre_land_tip, final_id)
            return Err(
                unwound.danger_err if unwound.is_err else LandError.ReleaseBumpFailed
            )
        resynced = _resync_release_manifest(root, final_id, new_version)
        if resynced.is_err:
            unwound = _verified_reset_root(root, pre_land_tip, final_id)
            return Err(unwound.danger_err if unwound.is_err else resynced.danger_err)
        _log.info(
            "land: %s REL001 version bump applied and staged: -> %s",
            final_id,
            bumped.danger_ok,
        )
        synced = _sync_uv_lock_for_land(root, final_id)
        if synced.is_err:
            unwound = _verified_reset_root(root, pre_land_tip, final_id)
            return Err(unwound.danger_err if unwound.is_err else synced.danger_err)
    return bumped


# frob:ticket T-1011
# frob:tests tests/test_ticket_land.py::TestSyncGateRulesCallback.test_sync_gate_rules_none_is_noop  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestSyncGateRulesCallback.test_sync_gate_rules_applies_and_stages  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestSyncGateRulesCallback.test_sync_gate_rules_failure_unwinds  # noqa: E501
def _apply_gate_rule_sync(
    root: Path,
    final_id: str,
    sync_gate_rules: Callable[[Path, str], Result[tuple[str, ...] | None, LandError]]
    | None,
    pre_land_tip: str,
) -> Result[tuple[str, ...] | None, LandError]:
    """Invoke `sync_gate_rules(root, pre_land_tip)` if supplied, unwinding
    the staged squash via `_verified_reset_root` (same T-0907 pattern as
    `_apply_release_bump`) on failure (T-1011). `sync_gate_rules=None` (the
    library default) is a no-op returning `Ok(None)` -- see `land`'s
    docstring for why this is a caller-supplied callback rather than
    computed here (cycle-avoidance, docs/rework.md). A failure here is
    treated with the same fail-closed posture as a `bump_version` failure:
    a silently-skipped sync would let a landed gate-rule change slip past
    REG010 registry staleness undetected."""
    if sync_gate_rules is None:
        return Ok(None)
    synced = sync_gate_rules(root, pre_land_tip)
    if synced.is_err:
        _log.error(
            "land: %s gate-rule registry sync callback failed (%s) -- "
            "unwinding the staged squash; run `frob registry audit "
            "--sync-gate-rules` by hand and retry",
            final_id,
            synced.danger_err,
        )
        unwound = _verified_reset_root(root, pre_land_tip, final_id)
        return Err(unwound.danger_err if unwound.is_err else synced.danger_err)
    if synced.danger_ok:
        _log.info(
            "land: %s gate-rule registry auto-synced: filed %d rule id(s): %s",
            final_id,
            len(synced.danger_ok),
            ", ".join(synced.danger_ok),
        )
    return synced


# frob:ticket T-0793
def _sync_uv_lock_for_land(root: Path, final_id: str) -> Result[None, LandError]:
    """Re-sync `root`'s `uv.lock` and stage it in the SAME land commit as
    a just-applied REL001 version bump (T-0793): `uv run`/`uv lock` re-
    derives the `frob` package's `version = "..."` line from `pyproject.
    toml` on every invocation, so a bumped pyproject with a stale lock
    flaps that one line dirty on every subsequent invocation anywhere in
    the repo, tripping DirtyMain/SCOPE001 for whichever worktree notices
    next. Runs `uv lock` through `run_argv` (the guarded T-0778 seam --
    never a bare `subprocess` call, so `FROB_DISABLE_EXEC=1` still
    refuses it like every other spawn in this module) and `git add`s the
    result. This is only invoked right after `bump_version` reports a real
    version change, never on every land.

    Skipped entirely (returns `Ok(None)` without spawning anything) when
    `root` has no `pyproject.toml` -- not every `land()` caller's tree is
    a real uv project (test fixtures, other callers of this library), and
    there is nothing to lock in that case."""
    if not (root / "pyproject.toml").exists():
        _log.debug(
            "land: %s no pyproject.toml at %s, skipping uv.lock re-sync",
            final_id,
            root,
        )
        return Ok(None)
    synced = run_argv(["uv", "lock"], cwd=root, timeout_s=120.0)
    if synced.is_err or synced.danger_ok.returncode != 0:
        _log.error(
            "land: %s uv.lock re-sync failed after version bump -- %s",
            final_id,
            synced.danger_err if synced.is_err else synced.danger_ok.stderr,
        )
        return Err(LandError.ReleaseBumpFailed)
    staged = run_argv(["git", "-C", str(root), "add", "uv.lock"])
    if staged.is_err or staged.danger_ok.returncode != 0:
        _log.error("land: %s failed to stage re-synced uv.lock", final_id)
        return Err(LandError.GitFailed)
    _log.info("land: %s re-synced and staged uv.lock after version bump", final_id)
    return Ok(None)


# frob:ticket T-0338
def _maybe_rebuild_natives(
    root: Path,
    final_id: str,
    changeset: frozenset[str],
    rebuild_natives: Callable[[Path], bool] | None,
) -> bool:
    """Invoke `rebuild_natives(root)` when `changeset` touches a native
    source tree (T-0338); best-effort -- a `False`/exception-free failure
    is logged but never unwinds or blocks the land (the T-0248 stale-native
    warning already covers the "you must rebuild before trusting checks"
    heads-up; this is the "land tried to do it for you" upgrade, not a new
    hard gate). `rebuild_natives=None` (the library default) or a changeset
    that never touches frob-core/strata-core is a no-op returning `False`."""
    if rebuild_natives is None or not _touches_native_source(changeset):
        return False
    rebuilt = rebuild_natives(root)
    if rebuilt:
        _log.info("land: %s native extension(s) rebuilt after landing", final_id)
    else:
        _log.warning(
            "land: %s native source changed but the rebuild callback "
            "reported failure -- run `make core` manually before trusting "
            "`frob check`/`frob test` against %s",
            final_id,
            root,
        )
    return rebuilt


# frob:ticket T-1001
def _absorbed_land_report(
    root: Path,
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
    unexplained reason is never silently reported as success."""
    staged_now = _staged_files(root)
    if staged_now.is_err or staged_now.danger_ok:
        return None
    if not _absorption_verified(root, worktree, ticket, final_id):
        return None
    return _report_stacked_sibling_absorption(
        root, ticket_id, final_id, wip_committed, did_merge
    )


# frob:ticket T-0907
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
    level comment above `_verified_reset_root`)."""
    branch = current_branch(worktree)
    if branch.is_err:
        return Err(LandError.GitFailed)
    branch_name = branch.danger_ok

    squashed = _squash_and_splice_ledger(
        root, worktree, ticket, final_id, branch_name, pre_land_tip
    )
    if squashed.is_err:
        return Err(squashed.danger_err)

    bumped = _apply_release_bump(root, ticket, final_id, bump_version, pre_land_tip)
    if bumped.is_err:
        return Err(bumped.danger_err)
    release_bumped_to = bumped.danger_ok

    gate_rules_synced = _apply_gate_rule_sync(
        root, final_id, sync_gate_rules, pre_land_tip
    )
    if gate_rules_synced.is_err:
        return Err(gate_rules_synced.danger_err)

    completeness = _assert_land_complete(
        root, worktree, ticket_id, main_branch_name, pre_land_tip
    )
    if completeness.is_err:
        return Err(completeness.danger_err)
    worktree_changeset = completeness.danger_ok

    _warn_if_native_stale(root, final_id)
    natives_rebuilt = _maybe_rebuild_natives(
        root, final_id, worktree_changeset, rebuild_natives
    )

    # T-1001 (churn item 2): stacked-sibling absorption -- see
    # `_absorbed_land_report`'s own docstring.
    absorbed = _absorbed_land_report(
        root, worktree, ticket, ticket_id, final_id, wip_committed, did_merge
    )
    if absorbed is not None:
        return Ok(absorbed)

    committed = _commit_squash_apply(root, ticket, final_id)
    if committed.is_err:
        return Err(committed.danger_err)

    sha_str, files = _land_commit_details(root)
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
            worktree_changeset=tuple(sorted(worktree_changeset)),
            release_bumped_to=release_bumped_to,
            natives_rebuilt=natives_rebuilt,
        )
    )
