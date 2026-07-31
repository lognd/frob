"""`frob ticket land` -- draft-finalization/sibling-renumbering and close
stage.

See docs/modules/tickets.md#frob-ticket-land.

Split out of `frob.tickets._land` (T-1186, following the verbatim-move
pattern `_evidence.py`/`_reporting.py` set at T-1171): originally the
whole final stage of a land (draft-id finalization and sibling-draft
renumbering, closing the finalized ticket, the squash-apply-onto-main
step and its ledger splice, the completeness assertion, and the release-
bump/uv.lock/native-rebuild machinery). T-1251 split the git-plumbing/
wip-commit family out into `_land_git_ops.py`; T-1334 (this change)
finishes that residue by splitting the remaining two families out too --
the squash-apply/close family into `frob.tickets._land_squash`, and the
release-bump/uv.lock/native-rebuild family into
`frob.tickets._land_release` -- leaving this module with just the
draft-finalization/sibling-renumbering/close family named in T-1189's own
plan: `_land_finalize_and_close` (the entry point), draft-id finalization
(`_finalize_and_close_ticket`/`_finalize_draft_id`/
`_finalize_sibling_drafts`), the T-0811/T-0812 stale-draft-id-reference
rewrite trio (`_rewrite_draft_references_in_bodies`/`_rewrite_draft_
references_in_one_ledger`/`_rewrite_draft_references_in_waive_sites`/
`_grep_waive_site_candidate_files`/`_rewrite_one_waive_site_file`), ticket
closing (`_close_finalized_ticket`), and the finalize-writes commit
(`_commit_finalize_writes`). Zero caller-visible behavior change -- every
moved function keeps its original body, docstring, and `frob:ticket`/
`frob:tests` directives verbatim; `frob.tickets._land` now imports
`_v2_effective_scope`/`_land_squash_apply` from `frob.tickets._land_squash`
directly instead of from here (this module no longer defines them).
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.tickets._land_git_ops import (
    _describe_git_failure,
    _land_internal_git_env,
    _porcelain_dirty,
)
from frob.tickets._models import LandError, Ticket, TicketState
from frob.tickets._provisional import is_draft_id
from frob.tickets._store import (
    archive_path,
    ledger_digest,
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
