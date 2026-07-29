"""
frob.tickets._new_renumber -- ticket id allocation, `new_ticket`, and the whole-tree
`renumber`/`renumber_one` id-rewrite family
(T-1103 split residue of frob.tickets.__init__: carved out verbatim with its
T-0102/T-0140/T-0162/T-0398/T-0458/T-0577/T-0633/T-0889/T-1090 directives intact).

T-1103: `renumber_one` is externally monkeypatched at the `frob.tickets` package
attribute by tests exercising `frob.app.ticket_runner`'s CLI dispatch.

T-1192: the `finalize_draft`/`finalize_draft_for_land` provisional-draft-id
finalization pair (LARGE001 residue: this module alone was 847 lines) moved
to `frob.tickets._draft_finalize`, which imports `_next_ticket_id` back from
here -- `finalize_draft`/`finalize_draft_for_land` still re-import
`renumber_one` from the PACKAGE at call time (rather than this module's own
name), preserving the same package-level-monkeypatch indirection T-1103
established, now just from a different caller module.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/tickets/_new_renumber.py's exclusivity-vocabulary hit is source-level \
# design-rationale prose (a docstring or comment describing already-implemented \
# internal behavior, verifiable by reading the code it annotates) rather than a \
# separate cross-module contract needing its own tracked invariant; disposed as a \
# calibration batch, not claim-by-claim -- module prose split from the pre-T-1103 \
# tickets/__init__.py monolith"

from __future__ import annotations

import re
from contextlib import ExitStack
from datetime import date
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.tickets._archive import _load_merged
from frob.tickets._leases import rename_lease
from frob.tickets._models import (
    RenumberReport,
    Ticket,
    TicketError,
    TicketKind,
    TicketSpec,
    TicketState,
)
from frob.tickets._provisional import mint_draft_id, on_default_branch
from frob.tickets._store import (
    _store_mode,
    archive_path,
    atomic_write,
    ledger_digest,
    ledger_lock,
    ledger_path,
    load_all,
    load_archive,
    ticket_lock,
    tickets_dir,
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


# frob:ticket T-1125
def _rewrite_body_prose_references(
    body: str, mapping: dict[str, str]
) -> tuple[str, int]:
    """Rewrite every whole-word PROSE occurrence of a renumbered id in
    `body` to its new id, for every `old != new` pair in `mapping` -- the
    Done-report/description-prose analog of `_apply_renumber`'s structural
    `blocked_by`/`parent` rewrite.

    T-1125: `_apply_renumber` used to rewrite only the structured id/
    blocked_by/parent fields, leaving free-text prose (a Done report citing
    a draft id like "T-1109", or a description referencing a now-renumbered
    ticket) permanently stale after `renumber_one`/`finalize_draft` --
    either a dead-id TICK006 phantom once the draft id no longer resolves,
    or worse (invisible to any gate) a citation of the WRONG real ticket if
    a hand-guessed final id happened to already exist. Four wave-17
    incidents (T-1077/T-1084/T-1095's phantom citations, T-0668's 8-site
    wrong-id citation) motivated this. Skips any pair where `old_id ==
    new_id` (nothing moved) or `old_id` is not even present in `body`
    (the common case -- most tickets' bodies reference nothing that moved),
    so a ticket whose prose mentions no renumbered id is left byte-for-byte
    unchanged."""
    hits = 0
    for old_id, new_id in mapping.items():
        if old_id == new_id or old_id not in body:
            continue
        id_re = re.compile(rf"\b{re.escape(old_id)}\b")
        body, n = id_re.subn(new_id, body)
        hits += n
    return body, hits


def _apply_renumber(
    ordered: list[Ticket], mapping: dict[str, str]
) -> tuple[dict[str, Ticket], int, int]:
    """Rewrite each ticket's id, blocked_by/parent refs, AND body prose
    citations of any renumbered id, via `mapping` (T-1125: body prose used
    to be left stale -- see `_rewrite_body_prose_references`).

    Returns `(new_map, touched, prose_hits)`: `touched` is "tickets touched"
    (id changed OR body prose rewritten), not "ids changed" alone -- a
    ticket whose own id is stable but whose Done-report prose cited a
    SIBLING id that moved must still be persisted, so `_persist_renumber`'s
    write-trigger (built from this count) has to see it as a change too.
    `prose_hits` is the total count of individual prose substitutions made
    across every ticket's body, folded into `RenumberReport.occurrences`
    alongside code-reference hits."""

    def remap(tid: str) -> str:
        return mapping.get(tid, tid)

    new_map: dict[str, Ticket] = {}
    touched = 0
    prose_hits_total = 0
    for ticket in ordered:
        new_id = mapping[ticket.id]
        id_changed = new_id != ticket.id
        new_body, prose_hits = _rewrite_body_prose_references(ticket.body, mapping)
        prose_hits_total += prose_hits
        if id_changed or prose_hits:
            touched += 1
        new_map[new_id] = ticket.model_copy(
            update={
                "id": new_id,
                "blocked_by": tuple(remap(b) for b in ticket.blocked_by),
                "parent": remap(ticket.parent) if ticket.parent else None,
                "body": new_body,
            }
        )
    return new_map, touched, prose_hits_total


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
        new_map, renumbered, _prose_hits = _apply_renumber(ordered, mapping)
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
) -> tuple[dict[str, Ticket], int, dict[str, Ticket], int, int]:
    """Build the id-rename mapping (`old_id -> new_id`, every other id
    fixed) and apply it to both the active and archive ticket maps.

    Returns `(new_active_map, active_changed, new_archive_map,
    archive_changed, prose_hits)` -- `prose_hits` (T-1125) is the combined
    count of Done-report/description-prose substitutions across BOTH maps,
    folded into the eventual `RenumberReport.occurrences`."""
    all_ids = set(active_map) | set(archive_map)
    full_mapping = {tid: tid for tid in all_ids}
    full_mapping[old_id] = new_id

    new_active_map, active_changed, active_prose_hits = _apply_renumber(
        list(active_map.values()), full_mapping
    )
    new_archive_map, archive_changed, archive_prose_hits = _apply_renumber(
        list(archive_map.values()), full_mapping
    )
    return (
        new_active_map,
        active_changed,
        new_archive_map,
        archive_changed,
        active_prose_hits + archive_prose_hits,
    )


def _build_renumber_report(
    root: Path,
    old_id: str,
    new_id: str,
    active_changed: int,
    archive_changed: int,
    code_changes: dict[Path, tuple[str, int]],
    dry_run: bool,
    ledger_prose_hits: int = 0,
) -> RenumberReport:
    """Assemble the `RenumberReport` for a rename, from the computed
    ledger-changed flags and code-reference scan results.

    `ledger_prose_hits` (T-1125) folds Done-report/description-prose
    substitutions made directly in tickets.md/tickets-archive.md into
    `occurrences` alongside code-reference hits, so a caller inspecting the
    report sees the full picture of what got rewritten, not just the code
    side."""
    return RenumberReport(
        old_id=old_id,
        new_id=new_id,
        ledger_changed=bool(active_changed or archive_changed),
        files_changed=tuple(sorted(str(p.relative_to(root)) for p in code_changes)),
        occurrences=sum(hits for _text, hits in code_changes.values())
        + ledger_prose_hits,
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
# ---------------------------------------------------------------------------
# v2 backend: git-mv renumber (ledger v2 design section 4.1, T-1255)
# ---------------------------------------------------------------------------


_V2_ID_FRONTMATTER_RE = re.compile(r"(?m)^id:\s*\S+")


def _v2_id_dir(root: Path, ticket_id: str) -> Path | None:
    """The v2 ticket directory (active `tickets/<id>/` or archived
    `tickets/archive/<id>/`) currently holding `ticket_id`'s `ticket.md`, or
    `None` if neither exists -- the v2-mode analog of
    `_load_and_validate_renumber_ids`'s active/archive membership check."""
    from frob.tickets._store import v2_ticket_dir

    active = v2_ticket_dir(root, ticket_id)
    if (active / "ticket.md").is_file():
        return active
    archived = tickets_dir(root) / "archive" / ticket_id
    if (archived / "ticket.md").is_file():
        return archived
    return None


def _rewrite_v2_id_field(text: str, new_id: str) -> str:
    """Rewrite a v2 `ticket.md`'s frontmatter `id:` line to `new_id` (design
    section 4.1 step 3) -- the one field a `git mv` does not fix up on its
    own, since the directory name and the frontmatter `id:` are two
    independent pieces of data that must both move together."""
    return _V2_ID_FRONTMATTER_RE.sub(f"id: {new_id}", text, count=1)


def _v2_reference_files(root: Path) -> list[Path]:
    """Every `ticket.md`/`done-report.md` under `tickets/` (active or
    archived), sorted -- the multi-file glob design section 4.1 step 4 scans
    for whole-word prose citations of a renumbered id, generalizing
    `_rewrite_body_prose_references`'s single-ledger-body scan to a glob over
    disjoint per-ticket files."""
    d = tickets_dir(root)
    if not d.exists():
        return []
    return sorted(p for p in d.rglob("*.md") if p.is_file())


def _scan_v2_reference_files(
    root: Path, old_id: str, new_id: str, *, exclude: Path
) -> dict[Path, tuple[str, int]]:
    """Every `tickets/**/*.md` file (other than `exclude`, the renamed
    ticket's own `ticket.md`) whose text whole-word-cites `old_id`, mapped to
    its rewritten text and hit count -- reuses
    `_rewrite_body_prose_references`'s single-pair matching core (a
    `{old_id: new_id}` mapping of one entry) so both call sites share the
    exact same whole-word regex semantics."""
    id_mapping = {old_id: new_id}
    changed: dict[Path, tuple[str, int]] = {}
    for path in _v2_reference_files(root):
        if path == exclude:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if old_id not in text:
            continue
        rewritten, hits = _rewrite_body_prose_references(text, id_mapping)
        if hits:
            changed[path] = (rewritten, hits)
    return changed


def _git_mv_ticket_dir(
    root: Path, old_dir: Path, new_dir: Path
) -> Result[None, TicketError]:
    """`git mv old_dir new_dir` (design section 4.1 step 2) -- falls back to
    a plain filesystem rename if `old_dir` is not yet tracked by git (e.g. a
    just-filed draft that has not been `git add`ed), since a git-mv over an
    untracked path always fails even though the rename itself is perfectly
    safe.

    Chain-review fix (mirrors `frob.tickets._store.git_mv_dir`'s identical
    fix, found alongside T-1258): `git mv` on a directory refuses with "No
    such file or directory" whenever `new_dir`'s PARENT does not exist yet,
    which used to silently take the os.rename fallback below -- losing the
    real git rename record for what is actually the common case (a fresh
    id range's first renumber into it), not just the rare untracked-draft
    case. Pre-creating the parent here makes `git mv` itself succeed (and
    record a real rename) for every case except a genuinely untracked
    source."""
    new_dir.parent.mkdir(parents=True, exist_ok=True)
    argv = ("git", "-C", str(root), "mv", str(old_dir), str(new_dir))
    spawned = run_argv(argv)
    if spawned.is_ok and spawned.danger_ok.returncode == 0:
        return Ok(None)
    _log.debug(
        "tickets: git mv %s -> %s failed or untracked, falling back to os.rename",
        old_dir,
        new_dir,
    )
    try:
        new_dir.parent.mkdir(parents=True, exist_ok=True)
        old_dir.rename(new_dir)
    except OSError as exc:
        _log.error(
            "tickets: renumber_one_v2: rename %s -> %s failed: %s",
            old_dir,
            new_dir,
            exc,
        )
        return Err(TicketError.WriteFailed)
    return Ok(None)


# frob:ticket T-1255
def _validate_v2_renumber_ids(
    root: Path, old_id: str, new_id: str
) -> Result[Path, TicketError]:
    """Validate `old_id`/`new_id` are v2-renumber-able (not equal, `old_id`
    resolves to a real v2 ticket dir, `new_id` free), returning `old_id`'s
    directory on success -- the v2 analog of
    `_load_and_validate_renumber_ids`."""
    if old_id == new_id:
        _log.warning("tickets: renumber_one_v2 %s -> %s is a no-op id", old_id, new_id)
        return Err(TicketError.InvalidTransition)
    old_dir = _v2_id_dir(root, old_id)
    if old_dir is None:
        _log.error("tickets: renumber_one_v2: %s not found", old_id)
        return Err(TicketError.NotFound)
    if _v2_id_dir(root, new_id) is not None:
        _log.error("tickets: renumber_one_v2: target id %s already exists", new_id)
        return Err(TicketError.DuplicateId)
    return Ok(old_dir)


# frob:ticket T-1255
def _build_v2_renumber_report(
    root: Path,
    old_id: str,
    new_id: str,
    old_dir: Path,
    ref_changes: dict[Path, tuple[str, int]],
    code_changes: dict[Path, tuple[str, int]],
    dry_run: bool,
) -> RenumberReport:
    """Assemble the `RenumberReport` for a v2-mode rename, from the computed
    reference-file/code-reference scan results plus the renamed ticket's own
    `id:` field rewrite."""
    occurrences = (
        sum(hits for _text, hits in ref_changes.values())
        + sum(hits for _text, hits in code_changes.values())
        + 1  # the renamed ticket's own id: field
    )
    files_changed = sorted(
        {str(p.relative_to(root)) for p in (*ref_changes, *code_changes)}
        | {str((old_dir.parent / new_id).relative_to(root) / "ticket.md")}
    )
    return RenumberReport(
        old_id=old_id,
        new_id=new_id,
        ledger_changed=True,
        files_changed=tuple(files_changed),
        occurrences=occurrences,
        dry_run=dry_run,
    )


# frob:ticket T-1255
def _persist_v2_renumber(
    root: Path,
    old_dir: Path,
    new_id: str,
    new_text: str,
    ref_changes: dict[Path, tuple[str, int]],
    code_changes: dict[Path, tuple[str, int]],
) -> Result[Path, TicketError]:
    """`git mv` `old_dir` to its new id, write back the moved `ticket.md`
    plus every rewritten reference/code file, returning the new directory on
    success. A reference file that lived INSIDE `old_dir` (e.g. the moved
    ticket's own `done-report.md`) is written under the NEW directory
    instead -- every other reference file's path is untouched by the mv."""
    new_dir = old_dir.parent / new_id
    moved = _git_mv_ticket_dir(root, old_dir, new_dir)
    if moved.is_err:
        return Err(moved.danger_err)
    written = atomic_write(new_dir / "ticket.md", new_text)
    if written.is_err:
        return Err(written.danger_err)
    for path, (rewritten, _hits) in {**ref_changes, **code_changes}.items():
        target = (
            new_dir / path.relative_to(old_dir)
            if path in ref_changes and path.is_relative_to(old_dir)
            else path
        )
        write_result = atomic_write(target, rewritten)
        if write_result.is_err:
            return Err(write_result.danger_err)
    return Ok(new_dir)


# frob:doc docs/design/ledger-v2.md#41-renumber-with-reference-rewrite
# frob:ticket T-1255
# frob:tests tests/test_tickets_collision.py::TestRenumberOneV2.test_git_mv_renames_directory_and_rewrites_id_field  # noqa: E501
# frob:tests tests/test_tickets_collision.py::TestRenumberOneV2.test_sibling_ticket_prose_citation_rewritten  # noqa: E501
# frob:tests tests/test_tickets_collision.py::TestRenumberOneV2.test_locks_acquired_in_sorted_id_order_no_deadlock  # noqa: E501
def renumber_one_v2(
    root: Path, old_id: str, new_id: str, *, dry_run: bool = False
) -> Result[RenumberReport, TicketError]:
    """v2-mode `renumber_one` (design section 4.1): `git mv tickets/<old>
    tickets/<new>` (or `tickets/archive/<old>` if archived), rewrite the
    moved `ticket.md`'s own `id:` frontmatter field, then rewrite every OTHER
    `tickets/**/*.md` file's whole-word prose citation of `old_id` -- reusing
    `_rewrite_body_prose_references`'s matching core verbatim, just re-
    pointed at a multi-file glob instead of one ledger's rendered text.

    Locks are acquired for BOTH `old_id` and `new_id` in sorted order (design
    section 3's fixed-order discipline, mirroring the T-1090 lesson this
    generalizes) so a renumber can never lock-order-deadlock against a
    concurrent renumber/write touching the same two ids in the opposite
    order. A `dry_run` call takes no locks and mutates nothing -- it only
    computes and reports what WOULD change."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    validated = _validate_v2_renumber_ids(root, old_id, new_id)
    if validated.is_err:
        return Err(validated.danger_err)
    old_dir = validated.danger_ok

    lock_ids = sorted({old_id, new_id})
    with ExitStack() as stack:
        for lock_id in lock_ids:
            stack.enter_context(ticket_lock(root, lock_id))

        ticket_path = old_dir / "ticket.md"
        old_text = ticket_path.read_text(encoding="utf-8")
        new_text = _rewrite_v2_id_field(old_text, new_id)
        ref_changes = _scan_v2_reference_files(
            root, old_id, new_id, exclude=ticket_path
        )
        code_changes = _scan_code_references(root, old_id, new_id)
        report = _build_v2_renumber_report(
            root, old_id, new_id, old_dir, ref_changes, code_changes, dry_run
        )
        if dry_run:
            _log_renumber_dry_run(old_id, new_id, report)
            return Ok(report)

        persisted = _persist_v2_renumber(
            root, old_dir, new_id, new_text, ref_changes, code_changes
        )
        if persisted.is_err:
            return Err(persisted.danger_err)

    rename_lease(root, old_id, new_id)
    _log_renumber_done(old_id, new_id, {**ref_changes, **code_changes}, report)
    return Ok(report)


# frob:doc docs/modules/tickets.md#public-api
# frob:ticket T-0162
# frob:ticket T-0633
# frob:ticket T-0889
# frob:ticket T-1255
# frob:tests tests/test_tickets_ledger_concurrency.py::TestRenumberOneRaceWithConcurrentNew.test_concurrent_new_ticket_survives_a_racing_renumber_one  # noqa: E501
def renumber_one(
    root: Path, old_id: str, new_id: str, *, dry_run: bool = False
) -> Result[RenumberReport, TicketError]:
    """Atomically rewrite ONE ticket's id everywhere: its ledger section
    (active or archive, id + every blocked_by/parent reference across BOTH
    stores), every OTHER ticket's Done-report/description PROSE citation of
    it in tickets.md/tickets-archive.md (T-1125, see
    `_rewrite_body_prose_references`), and every `frob:ticket`/`frob:waive`/
    `frob:todo`/`frob:tests`/`frob:invariant`/`frob:doc` directive line
    across the tracked tree that names it.

    T-0633: the load (`_load_and_validate_renumber_ids`) and the eventual
    persist (`_persist_renumber`, which calls `write_all`/`write_archive`)
    are held under one `ledger_lock` span for a non-dry-run call -- this is
    `finalize_draft`'s rename primitive (T-0162), so the same TOCTOU that
    `archive`/`renumber` had (an unlocked load, then a locked wholesale
    write built from that stale snapshot silently reverting a concurrent
    single-ticket write in between) applied here too, and matters more:
    `finalize_draft` runs at `frob ticket land` time, exactly when a
    concurrent worktree's ledger write is most likely to be in flight.

    T-1255: a v2-mode repo (`_store_mode(root) == "v2"`) dispatches to
    `renumber_one_v2` instead -- design section 4.1's `git mv` + per-ticket-
    file reference rewrite, in place of this function's whole-ledger
    read-modify-write. Checked FIRST, before `enforce_worktree_lease` even
    runs, since `renumber_one_v2` does its own lease check."""
    if _store_mode(root) == "v2":
        return renumber_one_v2(root, old_id, new_id, dry_run=dry_run)
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    with ledger_lock(root):
        loaded = _load_and_validate_renumber_ids(root, old_id, new_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        active_map, archive_map, active_digest, archive_digest = loaded.danger_ok
        (
            new_active_map,
            active_changed,
            new_archive_map,
            archive_changed,
            ledger_prose_hits,
        ) = _apply_renumber_mapping(active_map, archive_map, old_id, new_id)
        code_changes = _scan_code_references(root, old_id, new_id)
        report = _build_renumber_report(
            root,
            old_id,
            new_id,
            active_changed,
            archive_changed,
            code_changes,
            dry_run,
            ledger_prose_hits=ledger_prose_hits,
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
        return _finish_renumber(persisted, old_id, new_id, code_changes, report, root)


def _finish_renumber(
    persisted: Result[None, TicketError],
    old_id: str,
    new_id: str,
    code_changes: dict[Path, tuple[str, int]],
    report: RenumberReport,
    root: Path,
) -> Result[RenumberReport, TicketError]:
    """Propagate a persist failure, else migrate `old_id`'s cross-worktree
    lease (if any) to `new_id` (T-1173), log completion, and return the
    report. The lease rename runs AFTER the ledger persist succeeds --
    never before -- so a persist failure never leaves a lease renamed to
    an id the ledger itself never actually claimed."""
    if persisted.is_err:
        return Err(persisted.danger_err)
    rename_lease(root, old_id, new_id)
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
