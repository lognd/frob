"""
frob.tickets._new_renumber -- ticket id allocation, `new_ticket`, and the whole-tree
`renumber`/`renumber_one`/`finalize_draft` id-rewrite family
(T-1103 split residue of frob.tickets.__init__: carved out verbatim with its
T-0102/T-0140/T-0162/T-0398/T-0458/T-0577/T-0633/T-0889/T-1090 directives intact).

T-1103: `renumber_one` is externally monkeypatched at the `frob.tickets` package
attribute by tests exercising `frob.app.ticket_runner`'s CLI dispatch, and
`finalize_draft` calls `renumber_one` internally -- `finalize_draft` therefore
re-imports `renumber_one` from the PACKAGE (`from frob.tickets import
renumber_one`) at call time rather than calling the module-local name directly,
so a package-level monkeypatch takes effect there too (same indirection T-1089's
ticket_runner split used for its own cross-module callbacks).
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/tickets/_new_renumber.py's \
# exclusivity-vocabulary hit is source-level design-rationale prose (a \
# docstring or comment describing already-implemented internal behavior, \
# verifiable by reading the code it annotates) rather than a separate \
# cross-module contract needing its own tracked invariant; disposed as a \
# calibration batch, not claim-by-claim -- module prose split from \
# the pre-T-1103 tickets/__init__.py monolith"

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._archive import _load_merged
from frob.tickets._models import (
    RenumberReport,
    Ticket,
    TicketError,
    TicketKind,
    TicketSpec,
    TicketState,
)
from frob.tickets._provisional import is_draft_id, mint_draft_id, on_default_branch
from frob.tickets._store import (
    archive_path,
    atomic_write,
    ledger_digest,
    ledger_lock,
    ledger_path,
    load_all,
    load_archive,
    write_all,
    write_archive,
    write_ticket,
)
from frob.tickets._worktree_guard import enforce_worktree_lease

# T-1103: shared "frob.tickets" logger name kept explicit (not get_logger(__name__),
# which would read "frob.tickets._new_renumber") -- several tests filter caplog
# records by the package's own logger name, the same monkeypatch/logger-name hazard
# T-1089's ticket_runner split report documented for this family of split.
_log = get_logger("frob.tickets")


# frob:ticket T-0162
# frob:doc docs/modules/tickets.md#decision-record-t-0162
# frob:waive COV007 reason="the decision-record anchor documents THIS private \
# function's own allocation algorithm/design rationale (why provisional ids vs \
# branch-tip scanning vs content-nonce were compared, T-0162), not the public API \
# surface -- the private symbol genuinely is the documented contract here, not a \
# caller-side summary"
def _allocate_ticket_id(
    root: Path, existing: dict[str, Ticket], merged: dict[str, Ticket]
) -> str:
    """The id a fresh ticket should get: the next sequential T-#### when
    `root` is on the default branch (the merged view is authoritative there),
    otherwise a provisional T-draft-<hex> id -- final sequential ids are only
    ever minted against the default branch's view, so two checkouts filing
    independently structurally cannot converge on the same final id (T-0162:
    three real collisions were all sequential max+1 races across checkouts).
    """
    if not on_default_branch(root):
        draft_id = mint_draft_id()
        while draft_id in existing or draft_id in merged:
            draft_id = mint_draft_id()
        _log.info("tickets: off-default-branch, minted provisional id %s", draft_id)
        return draft_id
    return _next_ticket_id(merged)


def _next_ticket_id(existing: dict[str, Ticket]) -> str:
    """The next sequential `T-####` id above the highest existing ticket number
    in `existing` -- callers must pass the id space they want ids kept clear
    of (T-0140: `new_ticket` passes active+archive merged, not active alone)."""
    max_num = 0
    for tid in existing:
        try:
            max_num = max(max_num, int(tid.split("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    return f"T-{max_num + 1:04d}"


def _ticket_from_spec(
    ticket_id: str, spec: TicketSpec, evidence: tuple[str, ...]
) -> Ticket:
    """Build a fresh QUEUED ticket from `spec`, applying the incident template."""
    body = spec.body
    if spec.kind == TicketKind.INCIDENT and not body.strip():
        body = _INCIDENT_TEMPLATE
    return Ticket(
        id=ticket_id,
        title=spec.title,
        state=TicketState.QUEUED,
        kind=spec.kind,
        origin=spec.origin,
        created=date.today(),
        priority=spec.priority,
        blocked_by=spec.blocked_by,
        parent=spec.parent,
        tier=spec.tier,
        sprint=spec.sprint,
        scope=spec.scope,
        evidence=evidence,
        attachments=(),
        acceptance=spec.acceptance,
        threat=spec.threat,
        component=spec.component,
        labels=spec.labels,
        body=body,
    )


# frob:ticket T-0102
# frob:ticket T-0140
# frob:ticket T-0398
# frob:doc docs/modules/tickets.md#public-api
def new_ticket(
    root: Path,
    spec: TicketSpec,
    collected: frozenset[str] | None = None,
) -> Result[Ticket, TicketError]:
    """Allocate the next sequential id and upsert the ticket into the store.

    Any `spec.evidence` entries are schema-validated (validate_evidence)
    before the ticket is ever built, so a malformed entry cannot land via
    `frob ticket new` either (T-0102 companion fix). The id is allocated from
    the max across BOTH the active ledger and the archive (T-0140) -- scanning
    only the active store restarts numbering at T-0001 the moment a queue has
    been archived, colliding with archived ids and making the merged queue
    unloadable (DuplicateId) on the very next `load_queue`. A malformed
    archive fails loudly here too, via the same `_load_merged` path
    `load_queue` uses -- never silently ignored.

    D-08: `spec.evidence` is now ALSO resolution-checked via the same
    `_check_evidence_resolution` `add_evidence` uses, whenever a caller
    supplies `collected` -- previously `new_ticket --evidence` only
    schema-validated, so a bogus id (`tests/ghost.py::test_x`) was stored
    unresolved and surfaced only if/when the ticket later reached DONE and
    `frob check` ran COV003. `collected=None` (default, matching every
    caller before D-08) preserves that schema-only behavior for a context
    with no collector available, but now logs the same explicit UNRESOLVED
    warning `add_evidence` does, so the gap is never silent.

    T-1103: `_validate_evidence_list`/`_check_evidence_resolution` stay
    defined in `frob.tickets` proper (the evidence family) -- imported here
    from the PACKAGE rather than a submodule to avoid a load-time circular
    import (this module is imported BY `frob.tickets.__init__` itself).
    """
    from frob.tickets import _check_evidence_resolution, _validate_evidence_list

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    validated = _validate_evidence_list(spec.evidence)
    if validated.is_err:
        return Err(validated.danger_err)
    resolution = _check_evidence_resolution(
        "new_ticket", validated.danger_ok, collected
    )
    if resolution.is_err:
        return Err(resolution.danger_err)
    # frob:ticket T-0458
    # Allocation (read the current max id) and the write that claims it
    # MUST happen under one held lock -- two processes each reading the
    # pre-write max id and then writing, unlocked in between, is exactly
    # the sequential-id race that produced T-0465's duplicate T-0427.
    # `write_ticket` re-acquires the same lock internally (reentrant, see
    # `ledger_lock`), so this outer hold is what actually closes the gap.
    with ledger_lock(root):
        ticket_id_result = _allocate_and_check_ticket_id(root)
        if ticket_id_result.is_err:
            return Err(ticket_id_result.danger_err)
        ticket_id = ticket_id_result.danger_ok
        ticket = _ticket_from_spec(ticket_id, spec, validated.danger_ok)
        write_result = write_ticket(root, ticket)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info("tickets: created %s", ticket_id)
    return Ok(ticket)


def _allocate_and_check_ticket_id(root: Path) -> Result[str, TicketError]:
    """Load the active+archived ticket state and allocate a fresh id,
    erroring on an archive-load failure or an id collision."""
    loaded = load_all(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    existing = loaded.danger_ok
    merged = _load_merged(root)
    if merged.is_err:
        _log.error("tickets: id allocation aborted, archive unreadable")
        return Err(merged.danger_err)
    ticket_id = _allocate_ticket_id(root, existing, merged.danger_ok)
    if ticket_id in existing:
        _log.error("tickets: id collision allocating %s", ticket_id)
        return Err(TicketError.DuplicateId)
    return Ok(ticket_id)


_INCIDENT_TEMPLATE = (
    "## Summary\n\n"
    "## Timeline\n\n"
    "## Root cause (blameless)\n\n"
    "## Action items\n"
    "<!-- each action item MUST become a ticket -- link them here as T-#### -->\n"
)


def _is_contiguous(ordered: list[Ticket], mapping: dict[str, str]) -> bool:
    """Whether every ticket already carries the id `mapping` would assign it."""
    return all(t.id == mapping[t.id] for t in ordered)


def _apply_renumber(
    ordered: list[Ticket], mapping: dict[str, str]
) -> tuple[dict[str, Ticket], int]:
    """Rewrite each ticket's id plus blocked_by/parent refs via `mapping`."""

    def remap(tid: str) -> str:
        return mapping.get(tid, tid)

    new_map: dict[str, Ticket] = {}
    renumbered = 0
    for ticket in ordered:
        new_id = mapping[ticket.id]
        if new_id != ticket.id:
            renumbered += 1
        new_map[new_id] = ticket.model_copy(
            update={
                "id": new_id,
                "blocked_by": tuple(remap(b) for b in ticket.blocked_by),
                "parent": remap(ticket.parent) if ticket.parent else None,
            }
        )
    return new_map, renumbered


# frob:doc docs/modules/tickets.md#public-api
# frob:ticket T-0633
# frob:ticket T-0889
# frob:tests tests/test_tickets_ledger_concurrency.py::TestLedgerLockSpansWholesaleOperations.test_concurrent_ledger_lock_acquisition_serializes  # noqa: E501
def renumber(root: Path) -> Result[int, TicketError]:
    """Reassign ticket ids to a contiguous T-0001.. sequence (ordered by
    current id), rewriting blocked_by/parent references so the queue stays
    consistent. The remedy for sequential-id collisions after a worktree
    merge (T-0012). Returns the number of tickets renumbered.

    T-0633: `load_all` and the eventual `write_all` are now held under one
    `ledger_lock` span (same fix and rationale as `archive`'s docstring) --
    previously the load ran unlocked, so a concurrent single-ticket write
    landing before this function's own locked `write_all` was silently
    reverted by the stale wholesale rewrite.
    """
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    with ledger_lock(root):
        digest = ledger_digest(ledger_path(root))
        loaded = load_all(root)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ordered = sorted(loaded.danger_ok.values(), key=lambda t: t.id)
        mapping = {t.id: f"T-{i + 1:04d}" for i, t in enumerate(ordered)}
        if _is_contiguous(ordered, mapping):
            _log.info("tickets: renumber -- already contiguous, nothing to do")
            return Ok(0)
        new_map, renumbered = _apply_renumber(ordered, mapping)
        result = write_all(root, new_map, expected_digest=digest)
        if result.is_err:
            return Err(result.danger_err)
    _log.info("tickets: renumbered %d ticket(s)", renumbered)
    return Ok(renumbered)


_DIRECTIVE_LINE_RE = re.compile(r"frob:(ticket|waive|todo|tests|invariant|doc)\b")

# T-0577: registry disposition targets (docs/design/registry/*.yaml's
# `disposition: "deferred:<ticket>"` / `"duplicate_of:<ticket>"` values, per
# `frob.registry._models.parse_disposition`'s grammar) are ticket-id
# REFERENCES exactly like a `frob:ticket` directive line, but they live in
# YAML data files, not source comments -- `_DIRECTIVE_LINE_RE` never matched
# them. A draft id finalized at land time used to leave every registry
# yaml's `deferred:T-draft-...` pointing at a now-dead id, silently
# breaking REG003 (deferred-to-missing-ticket) until a human hand-swapped it
# (the real T-0388/compliance.yaml incident this pattern closes). Matched
# independent of `_DIRECTIVE_LINE_RE` so a bare `disposition:
# "deferred:T-draft-xxxx"` line (no `frob:` prefix at all) still rewrites.
_REGISTRY_REF_RE = re.compile(r"(?:deferred|duplicate[_-]of):\S+")


def _rewrite_registry_references(
    text: str, old_id: str, new_id: str
) -> tuple[str, int]:
    """Replace whole-word `old_id` with `new_id` wherever it appears as the
    target of a `deferred:`/`duplicate_of:` registry disposition (T-0577,
    see `_REGISTRY_REF_RE`'s doc) -- never elsewhere, so a ticket id
    mentioned only in registry prose/free text is left alone."""
    id_re = re.compile(rf"\b{re.escape(old_id)}\b")
    hits = 0

    def _sub_ref(match: re.Match[str]) -> str:
        nonlocal hits
        rewritten, n = id_re.subn(new_id, match.group(0))
        hits += n
        return rewritten

    return _REGISTRY_REF_RE.sub(_sub_ref, text), hits


def _tracked_files(root: Path) -> list[Path]:
    """Every git-tracked file under `root`, or (no git repo) every file not
    under a build/vendor/cache directory -- the search space `renumber_one`
    scans for code directive references. Falling back to a filesystem walk
    keeps renumber usable in a non-git fixture/test tree."""
    from frob.excludes import iter_files

    return list(iter_files(root))


def _rewrite_directive_references(
    text: str, old_id: str, new_id: str
) -> tuple[str, int]:
    """Replace whole-word `old_id` with `new_id` on every line that carries a
    `frob:` directive -- never elsewhere in the file (a ticket id mentioned
    in prose/a docstring/an unrelated string is left alone; only directive
    lines are code REFERENCES this command owns rewriting)."""
    id_re = re.compile(rf"\b{re.escape(old_id)}\b")
    lines = text.splitlines(keepends=True)
    hits = 0
    for i, line in enumerate(lines):
        if _DIRECTIVE_LINE_RE.search(line) and id_re.search(line):
            lines[i], n = id_re.subn(new_id, line)
            hits += n
    return "".join(lines), hits


def _scan_code_references(
    root: Path, old_id: str, new_id: str
) -> dict[Path, tuple[str, int]]:
    """Every tracked non-ledger file whose directive lines OR registry
    disposition targets (`_rewrite_registry_references`, T-0577) mention
    `old_id`, mapped to its rewritten text and the number of references
    replaced (both classes combined)."""
    skip_names = {ledger_path(root).name, archive_path(root).name}
    changed: dict[Path, tuple[str, int]] = {}
    for path in _tracked_files(root):
        if path.name in skip_names:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if old_id not in text:
            continue
        directive_text, directive_hits = _rewrite_directive_references(
            text, old_id, new_id
        )
        rewritten, registry_hits = _rewrite_registry_references(
            directive_text, old_id, new_id
        )
        hits = directive_hits + registry_hits
        if hits:
            changed[path] = (rewritten, hits)
    return changed


# frob:ticket T-0889
def _load_and_validate_renumber_ids(
    root: Path, old_id: str, new_id: str
) -> Result[
    tuple[dict[str, Ticket], dict[str, Ticket], str | None, str | None], TicketError
]:
    """Load the active+archive ledgers and validate `old_id`/`new_id` are
    renumber-able: not equal, `old_id` present, `new_id` free.

    Also returns each ledger's `ledger_digest` snapshot at load time
    (T-0889), so `_persist_renumber`'s eventual wholesale `write_all`/
    `write_archive` can refuse instead of clobbering if either file changed
    on disk since this load."""
    if old_id == new_id:
        _log.warning("tickets: renumber_one %s -> %s is a no-op id", old_id, new_id)
        return Err(TicketError.InvalidTransition)

    active_digest = ledger_digest(ledger_path(root))
    active_loaded = load_all(root)
    if active_loaded.is_err:
        return Err(active_loaded.danger_err)
    archive_digest = ledger_digest(archive_path(root))
    archived_loaded = load_archive(root)
    if archived_loaded.is_err:
        return Err(archived_loaded.danger_err)
    active_map, archive_map = active_loaded.danger_ok, archived_loaded.danger_ok

    if old_id not in active_map and old_id not in archive_map:
        _log.error("tickets: renumber_one: %s not found", old_id)
        return Err(TicketError.NotFound)
    if new_id in active_map or new_id in archive_map:
        _log.error("tickets: renumber_one: target id %s already exists", new_id)
        return Err(TicketError.DuplicateId)
    return Ok((active_map, archive_map, active_digest, archive_digest))


# frob:ticket T-0889
def _persist_renumber(
    root: Path,
    *,
    new_active_map: dict[str, Ticket],
    active_changed: int,
    new_archive_map: dict[str, Ticket],
    archive_changed: int,
    code_changes: dict[Path, tuple[str, int]],
    active_digest: str | None = None,
    archive_digest: str | None = None,
) -> Result[None, TicketError]:
    """Write back the renumbered active/archive ledgers (if changed) and
    every rewritten code-reference file.

    `active_digest`/`archive_digest` (T-0889) are the `ledger_digest`
    snapshots `_load_and_validate_renumber_ids` took at load time, threaded
    through to `write_all`/`write_archive` as `expected_digest` so a
    wholesale rewrite refuses rather than clobbers if either ledger changed
    on disk since that load."""
    if active_changed:
        write_result = write_all(root, new_active_map, expected_digest=active_digest)
        if write_result.is_err:
            return Err(write_result.danger_err)
    if archive_changed:
        archive_write = write_archive(
            root, new_archive_map, expected_digest=archive_digest
        )
        if archive_write.is_err:
            return Err(archive_write.danger_err)
    for path, (rewritten, _hits) in code_changes.items():
        written = atomic_write(path, rewritten)
        if written.is_err:
            return Err(written.danger_err)
    return Ok(None)


def _apply_renumber_mapping(
    active_map: dict[str, Ticket],
    archive_map: dict[str, Ticket],
    old_id: str,
    new_id: str,
) -> tuple[dict[str, Ticket], int, dict[str, Ticket], int]:
    """Build the id-rename mapping (`old_id -> new_id`, every other id
    fixed) and apply it to both the active and archive ticket maps."""
    all_ids = set(active_map) | set(archive_map)
    full_mapping = {tid: tid for tid in all_ids}
    full_mapping[old_id] = new_id

    new_active_map, active_changed = _apply_renumber(
        list(active_map.values()), full_mapping
    )
    new_archive_map, archive_changed = _apply_renumber(
        list(archive_map.values()), full_mapping
    )
    return new_active_map, active_changed, new_archive_map, archive_changed


def _build_renumber_report(
    root: Path,
    old_id: str,
    new_id: str,
    active_changed: int,
    archive_changed: int,
    code_changes: dict[Path, tuple[str, int]],
    dry_run: bool,
) -> RenumberReport:
    """Assemble the `RenumberReport` for a rename, from the computed
    ledger-changed flags and code-reference scan results."""
    return RenumberReport(
        old_id=old_id,
        new_id=new_id,
        ledger_changed=bool(active_changed or archive_changed),
        files_changed=tuple(sorted(str(p.relative_to(root)) for p in code_changes)),
        occurrences=sum(hits for _text, hits in code_changes.values()),
        dry_run=dry_run,
    )


def _log_renumber_dry_run(old_id: str, new_id: str, report: RenumberReport) -> None:
    """Log the DRY RUN summary line for `renumber_one`."""
    _log.info(
        "tickets: renumber_one DRY RUN %s -> %s: ledger_changed=%s "
        "code_files=%d occurrences=%d",
        old_id,
        new_id,
        report.ledger_changed,
        len(report.files_changed),
        report.occurrences,
    )


# First-class replacement for the hand-run sed that fixed the T-0157
# incident's ~100 stray waiver references -- a single command,
# `--dry-run`-able, that can never miss a reference class the old sed
# invocation didn't happen to cover. Also the rename primitive
# `finalize_draft` (T-0162's provisional-id mechanism) and, later,
# T-0176's `frob ticket land` reuse.
# frob:doc docs/modules/tickets.md#public-api
# frob:ticket T-0162
# frob:ticket T-0633
# frob:ticket T-0889
# frob:tests tests/test_tickets_ledger_concurrency.py::TestRenumberOneRaceWithConcurrentNew.test_concurrent_new_ticket_survives_a_racing_renumber_one  # noqa: E501
def renumber_one(
    root: Path, old_id: str, new_id: str, *, dry_run: bool = False
) -> Result[RenumberReport, TicketError]:
    """Atomically rewrite ONE ticket's id everywhere: its ledger section
    (active or archive, id + every blocked_by/parent reference across BOTH
    stores) and every `frob:ticket`/`frob:waive`/`frob:todo`/`frob:tests`/
    `frob:invariant`/`frob:doc` directive line across the tracked tree that
    names it.

    T-0633: the load (`_load_and_validate_renumber_ids`) and the eventual
    persist (`_persist_renumber`, which calls `write_all`/`write_archive`)
    are held under one `ledger_lock` span for a non-dry-run call -- this is
    `finalize_draft`'s rename primitive (T-0162), so the same TOCTOU that
    `archive`/`renumber` had (an unlocked load, then a locked wholesale
    write built from that stale snapshot silently reverting a concurrent
    single-ticket write in between) applied here too, and matters more:
    `finalize_draft` runs at `frob ticket land` time, exactly when a
    concurrent worktree's ledger write is most likely to be in flight."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    with ledger_lock(root):
        loaded = _load_and_validate_renumber_ids(root, old_id, new_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        active_map, archive_map, active_digest, archive_digest = loaded.danger_ok
        new_active_map, active_changed, new_archive_map, archive_changed = (
            _apply_renumber_mapping(active_map, archive_map, old_id, new_id)
        )
        code_changes = _scan_code_references(root, old_id, new_id)
        report = _build_renumber_report(
            root, old_id, new_id, active_changed, archive_changed, code_changes, dry_run
        )
        if dry_run:
            _log_renumber_dry_run(old_id, new_id, report)
            return Ok(report)

        persisted = _persist_renumber(
            root,
            new_active_map=new_active_map,
            active_changed=active_changed,
            new_archive_map=new_archive_map,
            archive_changed=archive_changed,
            code_changes=code_changes,
            active_digest=active_digest,
            archive_digest=archive_digest,
        )
        return _finish_renumber(persisted, old_id, new_id, code_changes, report)


def _finish_renumber(
    persisted: Result[None, TicketError],
    old_id: str,
    new_id: str,
    code_changes: dict[Path, tuple[str, int]],
    report: RenumberReport,
) -> Result[RenumberReport, TicketError]:
    """Propagate a persist failure, else log completion and return the report."""
    if persisted.is_err:
        return Err(persisted.danger_err)
    _log_renumber_done(old_id, new_id, code_changes, report)
    return Ok(report)


def _log_renumber_done(
    old_id: str,
    new_id: str,
    code_changes: dict[Path, tuple[str, int]],
    report: RenumberReport,
) -> None:
    """Log the completed-rename summary line for `renumber_one`."""
    _log.info(
        "tickets: renumbered %s -> %s (%d code file(s), %d reference(s) updated)",
        old_id,
        new_id,
        len(code_changes),
        report.occurrences,
    )


# frob:ticket T-0162
# frob:ticket T-1090
# frob:doc docs/modules/tickets.md#provisional-ids
# frob:tests tests/test_tickets_ledger_concurrency.py::TestFinalizeDraftAllocationRace.test_two_concurrent_finalize_draft_calls_get_distinct_ids  # noqa: E501
def finalize_draft(root: Path, draft_id: str) -> Result[str, TicketError]:
    """Assign `draft_id` its final sequential `T-####` id against the CURRENT
    merged (active+archive) view and rewrite the ledger plus every code
    reference via `renumber_one`. This is the callable finalize step the
    T-0162 provisional-id mechanism promises T-0176 (`frob ticket land`):
    a land/merge command finalizes a draft id by calling this function once
    the draft has actually landed on the default branch -- never before,
    since finalizing against a stale (pre-merge) view can reintroduce the
    exact collision this mechanism exists to prevent. A no-op (`Ok(draft_id)`
    unchanged) if `draft_id` is already a final id, so callers can call it
    unconditionally without checking `is_draft_id` themselves first.

    T-1090: the next-id COMPUTATION (`_next_ticket_id` against `_load_merged`'s
    snapshot) used to run entirely OUTSIDE any lock, with `renumber_one`
    acquiring `ledger_lock` only afterward, once `final_id` was already
    fixed. Two concurrent `finalize_draft` calls against the same `root`
    (two sibling lands each renumbering their own residue draft, the T-1086
    vs T-0684 field incident) could both load the same pre-write snapshot,
    both compute the SAME `final_id`, and then serialize only at the
    `renumber_one` write -- the second writer's `_load_and_validate_
    renumber_ids` reload happens under the lock, but if the first writer's
    id happened to land via a DIFFERENT path in between (e.g. a concurrent
    `new_ticket` claiming that exact number first), the second `renumber_one`
    call would silently rename onto a slot a third write had just vacated,
    or a caller retrying after a transient `DuplicateId` could recompute
    from another stale snapshot -- there was no single atomic span covering
    both the read that decides the id and the write that claims it. Now the
    whole read-compute-write sequence is held under ONE `ledger_lock(root)`
    span (reentrant, so `renumber_one`'s own internal lock acquisition below
    is a no-op re-entry in the same thread/process rather than a deadlock),
    mirroring the `new_ticket`/T-0458 pattern and the T-1036 splice-guard
    lineage: allocation and commit are now a single atomic unit under the
    lock, so a concurrent finalizer blocked on the same lock always
    recomputes its own `final_id` against the FRESH post-write ledger once
    it acquires the lock, never a stale pre-write snapshot.

    T-1103: `renumber_one` is re-imported from the PACKAGE at call time
    (rather than called as the module-local name), so a test that
    monkeypatches `frob.tickets.renumber_one` observes `finalize_draft`
    routing through the patched callable too.
    """
    if not is_draft_id(draft_id):
        _log.debug("tickets: finalize_draft(%s): already final, no-op", draft_id)
        return Ok(draft_id)
    with ledger_lock(root):
        merged = _load_merged(root)
        if merged.is_err:
            return Err(merged.danger_err)
        tickets = merged.danger_ok
        if draft_id not in tickets:
            _log.error("tickets: finalize_draft: %s not found", draft_id)
            return Err(TicketError.NotFound)
        final_id = _next_ticket_id(
            {tid: t for tid, t in tickets.items() if tid != draft_id}
        )
        from frob.tickets import renumber_one as _renumber_one

        result = _renumber_one(root, draft_id, final_id)
        if result.is_err:
            return Err(result.danger_err)
        _log.info("tickets: finalized draft %s -> %s", draft_id, final_id)
        return Ok(final_id)
