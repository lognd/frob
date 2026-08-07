"""`frob.lock` -- acknowledged digests and drift detection (docs/modules/graph.md).

Locking covers edge endpoints only, not every symbol -- locking everything
would churn `frob.lock` on every commit and drown review signal. `drift` is
a PURE comparison (never fails, never touches disk) so it is cheap to call
from any gate or CLI query; `acknowledge` and `write_lock` are the only
fallible, effectful operations here.
"""

from __future__ import annotations

import getpass
import json
import os
import tempfile
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from typani import Err, ErrorSet, Ok
from typani.result import Result
from typani.unit import Unit

from frob.graph import resolve
from frob.graph._models import (
    AckAuditEntry,
    DanglingEdge,
    DriftReport,
    Edge,
    EdgeKind,
    GraphSnapshot,
    LockEntry,
    LockFile,
    StaleItem,
)
from frob.lang import SymbolKind
from frob.logging import get_logger

_log = get_logger(__name__)

# frob:ticket T-0402
# G5: `digest.py`'s `body` facet is a constant empty-tuple hash for these
# kinds (class/const/type have no body_tokens) -- acking `body` on one of
# them can never observe drift, so `acknowledge` skips it rather than
# recording a lock entry that looks meaningful but never fires.
_BODY_FACET_MEANINGLESS_KINDS = frozenset(
    {SymbolKind.CLASS, SymbolKind.CONST, SymbolKind.TYPE}
)

_DEFAULT_FACET = "sig"

# frob:ticket T-1317
# T-1317: reasons that read as a rubber stamp rather than a genuine vouch
# ("what was re-verified and why the doc is still true") -- mirrors
# WAIVE002's reason discipline. Deliberately small and literal (not an NLP
# heuristic): anything a human would type without thinking, lowercased and
# stripped of trailing punctuation.
_BOILERPLATE_REASONS = frozenset(
    {
        "ok",
        "okay",
        "fine",
        "done",
        "ack",
        "acked",
        "reviewed",
        "looks good",
        "lgtm",
        "still accurate",
        "still true",
        "no change",
        "n/a",
        "na",
        "verified",
        "yes",
        "todo",
        "tbd",
        "fix",
    }
)
_MIN_REASON_LEN = 15


# frob:doc docs/modules/graph.md#error-types
class LockError(ErrorSet):
    """Failure values `frob.lock` read/write paths can return."""

    Malformed = "frob.lock could not be parsed"
    UnknownRef = "Acknowledged ref is not an edge endpoint in the graph"
    WriteFailed = "Atomic write of frob.lock failed"
    AckReasonMissing = (
        "frob ack requires --reason: what was re-verified and why the doc is "
        "still true (T-1317)"
    )
    AckReasonBoilerplate = (
        "frob ack --reason reads as a rubber stamp, not a genuine vouch "
        "(T-1317, mirrors WAIVE002's reason discipline)"
    )


def _current_actor() -> str:
    """Best-effort identity for an `AckAuditEntry.actor` field (T-1317) --
    the OS login name, or `"unknown"` if the platform/sandbox refuses to
    report one (never raises). Duplicated one-liner from `frob.tickets.
    _scope._current_actor`/`_accept._current_actor` rather than imported:
    same load-order-independence tradeoff those two siblings already
    accept relative to each other."""
    try:
        return getpass.getuser()
    except OSError:
        return "unknown"


# frob:ticket T-1317
def _reject_boilerplate_reason(reason: str) -> Result[Unit, LockError]:
    """`Err(AckReasonMissing)` for a blank reason, `Err
    (AckReasonBoilerplate)` for a too-short or literally-boilerplate one,
    else `Ok`. Acceptance criterion [1]: an ack whose reason is empty or
    boilerplate-detected is refused outright -- rubber-stamping is a gate
    failure, not a formality to route around."""
    stripped = reason.strip()
    if not stripped:
        _log.warning("acknowledge: refused, --reason is blank")
        return Err(LockError.AckReasonMissing)
    normalized = stripped.rstrip(".!").lower()
    if len(stripped) < _MIN_REASON_LEN or normalized in _BOILERPLATE_REASONS:
        _log.warning("acknowledge: refused, --reason reads as boilerplate: %r", reason)
        return Err(LockError.AckReasonBoilerplate)
    return Ok(Unit())


# frob:doc docs/modules/graph.md#public-api
def load_lock(path: Path) -> Result[LockFile, LockError]:
    """Load `frob.lock`; a missing file is an empty lock, not an error."""
    if not path.exists():
        _log.debug("load_lock: no lock file at %s, treating as empty", path)
        return Ok(LockFile())
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        lock = LockFile.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        _log.error("load_lock: %s is malformed: %s", path, exc)
        return Err(LockError.Malformed)
    _log.info("load_lock: %d entries from %s", len(lock.entries), path)
    return Ok(lock)


def _edge_endpoints(snapshot: GraphSnapshot) -> set[str]:
    """Every string that appears as a `src` or `target` in the snapshot's edges."""
    endpoints: set[str] = set()
    for edge in snapshot.edges:
        endpoints.add(edge.src)
        endpoints.add(edge.target)
    return endpoints


# frob:ticket T-0402
# frob:ticket T-0556
def _facets_for_ref(ref: str, snapshot: GraphSnapshot) -> set[str]:
    """Every distinct facet a DESCRIBES edge targeting `ref` requests, or
    `{_DEFAULT_FACET}` if none does -- always unioned with `"body"`.

    G11 (T-0402): `acknowledge` used to call `_facet_for_ref` (singular),
    which returns only the FIRST describes-facet found; a symbol described
    by two anchors under different facets (one `sig`, one `doc`) only ever
    got the first facet's digest locked -- the second facet's contract
    could drift forever with no `DRIFT001` signal, because it was never
    acked in the first place.

    T-0556 (docs/audits/gates-accounting.md B2): before this, an ack with
    no explicit facet (the common case -- most `frob:doc`/`frob:describes`
    anchors never name one) locked ONLY the `sig` digest, so rewriting a
    documented function's BODY (the actual behavior the doc claims to
    describe) after ack never tripped `DRIFT001` -- the doc could lie
    about behavior forever. Always including `"body"` here, regardless of
    what facet(s) were explicitly requested, closes that gap for every ack
    path without touching `frob.graph.dsl`'s per-directive facet parsing
    or any existing EXPLICIT facet request (an explicit `sig`-only ack
    still also gets a body entry, not a NARROWER one -- this only ever
    adds coverage, never removes it). `acknowledge` already skips the body
    facet for kinds where it is meaningless (`_BODY_FACET_MEANINGLESS_KINDS`
    -- class/const/type have a constant body digest), so this cannot
    produce a body entry that could never observe drift. A compat survey
    against this repo's own `frob.lock` at the time of this change (T-0556's
    Done report has the numbers) found only 43 entries total, all `sig`-only
    with no existing `body` entries -- small enough that landing this as
    the default outright, rather than behind an opt-in flag nobody would
    flip, is the sound choice; the old lock entries are simply left as-is
    until their next `frob ack`, exactly like any other lock format
    evolution.
    """
    facets = {
        edge.attrs.get("facet", _DEFAULT_FACET)
        for edge in snapshot.edges
        if edge.kind == EdgeKind.DESCRIBES and edge.target == ref
    }
    return (facets or {_DEFAULT_FACET}) | {"body"}


def _sorted_entries(entries: Sequence[LockEntry]) -> tuple[LockEntry, ...]:
    """Lock entries in the canonical, diff-stable `(ref, facet)` order."""
    return tuple(sorted(entries, key=lambda e: (e.ref, e.facet)))


# frob:doc docs/modules/graph.md#public-api
# frob:doc docs/modules/gates.md#ack-accountability-t-1317
# frob:tests tests/test_graph_lock.py::TestAckDrift.test_acknowledge_records_every_describes_facet  # noqa: E501
# frob:tests tests/test_graph_lock.py::TestAckDrift.test_acknowledge_skips_meaningless_body_facet_on_class  # noqa: E501
# frob:tests tests/test_graph_lock.py::TestAckDrift.test_acknowledge_endpoint_that_does_not_resolve_is_err  # noqa: E501
# frob:tests tests/test_gates_drift_ack.py::TestAckAccountability.test_ack_requires_reason  # noqa: E501
# frob:tests tests/test_gates_drift_ack.py::TestAckAccountability.test_ack_rejects_boilerplate_reason  # noqa: E501
# frob:tests tests/test_gates_drift_ack.py::TestAckAccountability.test_ack_records_digest_delta  # noqa: E501
# frob:tests tests/test_gates_drift_ack.py::TestAckAccountability.test_first_ack_records_none_old_digest  # noqa: E501
# frob:ticket T-1317
# frob:ticket T-0972
# frob:waive OPAQUE001 reason="T-1038: facet ranges only over _facets_for_ref's own \
# closed 'sig'/'body' vocabulary (a Digests model with exactly those two fields) -- \
# not attacker- or externally-controlled input; a deliberate generic accessor over a \
# fixed two-facet shape"
def acknowledge(
    lock: LockFile,
    snapshot: GraphSnapshot,
    refs: Sequence[str],
    *,
    reason: str,
    actor: str | None = None,
) -> Result[LockFile, LockError]:
    """Record current digests for `refs`; each ref must be an edge endpoint.

    T-1317: `reason` is keyword-only and REQUIRED (`Err(AckReasonMissing)`
    blank, `Err(AckReasonBoilerplate)` for a rubber-stamp reason -- see
    `_reject_boilerplate_reason`) -- the `frob ticket scope --reason`
    precedent (T-0455) applied to `frob ack`: it is the one place the
    obligation graph accepts a human assertion in place of a mechanical
    check, so it costs the same bookkeeping every other mutation that can
    discharge an obligation already costs. Every (ref, facet) actually
    (re-)acked here appends one `AckAuditEntry` to `lock.ack_log`
    recording the digest DELTA (`old_digest` from the entries dict as it
    stood BEFORE this call touched it -- `None` only for a genuine
    first-ever ack, never a stand-in for "could not compute" -- and
    `new_digest`, the value just written) plus `reason`/`actor`/`at`. The
    audit log is append-only: existing entries are always carried forward
    unchanged."""
    reason_check = _reject_boilerplate_reason(reason)
    if reason_check.is_err:
        return Err(reason_check.danger_err)
    resolved_actor = actor if actor is not None else _current_actor()
    today = date.today()

    endpoints = _edge_endpoints(snapshot)
    entries: dict[tuple[str, str], LockEntry] = {
        (entry.ref, entry.facet): entry for entry in lock.entries
    }
    new_audit: list[AckAuditEntry] = []
    for ref in refs:
        if ref not in endpoints:
            _log.warning("acknowledge: %r is not an edge endpoint", ref)
            return Err(LockError.UnknownRef)
        record_result = resolve(snapshot, ref)
        if record_result.is_err:
            _log.warning("acknowledge: %r does not resolve to a symbol", ref)
            return Err(LockError.UnknownRef)
        record = record_result.danger_ok
        new_audit.extend(
            _ack_one_ref(ref, record, snapshot, entries, reason, resolved_actor, today)
        )
    ordered = _sorted_entries(list(entries.values()))
    ack_log = tuple(lock.ack_log) + tuple(new_audit)
    return Ok(LockFile(version=lock.version, entries=ordered, ack_log=ack_log))


# frob:ticket T-1317
# frob:waive PERF004 reason="_facets_for_ref(ref, snapshot) is this loop's own per-ref distinct set, not a shared re-sort"  # noqa: E501
# frob:waive COV005 reason="T-1317: the ARCH001 line-count split moved this OPAQUE001 \
# waiver from acknowledge (public) onto _ack_one_ref (private) DELIBERATELY -- the \
# getattr call it covers moved with it verbatim, not a silent extraction-above-a-def \
# displacement COV005 is designed to catch"
# frob:waive OPAQUE001 reason="T-1038/T-1317: facet ranges only over _facets_for_ref's \
# own closed 'sig'/'body' vocabulary (a Digests model with exactly those two fields) \
# -- not attacker- or externally-controlled input; a deliberate generic accessor over \
# a fixed two-facet shape, moved here verbatim from acknowledge's own pre-T-1317 body \
# by the ARCH001 line-count split"
def _ack_one_ref(
    ref: str,
    record,  # noqa: ANN001
    snapshot: GraphSnapshot,
    entries: dict[tuple[str, str], LockEntry],
    reason: str,
    actor: str,
    at: date,
) -> list[AckAuditEntry]:
    """`acknowledge`'s per-ref body, split out to keep the outer loop under
    the ARCH001 line threshold (T-1317): (re-)ack every facet `_facets_for_
    ref` requests for `ref`, mutating `entries` in place and returning the
    `AckAuditEntry` rows to append to the audit log."""
    audit: list[AckAuditEntry] = []
    for facet in sorted(_facets_for_ref(ref, snapshot)):
        if facet == "body" and record.kind in _BODY_FACET_MEANINGLESS_KINDS:
            _log.warning(
                "acknowledge: skipping meaningless body-facet ack for "
                "%s (kind=%s has a constant body digest, G5)",
                ref,
                record.kind,
            )
            continue
        digest = getattr(record.digests, facet)
        old_entry = entries.get((ref, facet))
        old_digest = old_entry.digest if old_entry is not None else None
        entries[(ref, facet)] = LockEntry(ref=ref, facet=facet, digest=digest)
        audit.append(
            AckAuditEntry(
                ref=ref,
                facet=facet,
                old_digest=old_digest,
                new_digest=digest,
                reason=reason,
                actor=actor,
                at=at,
            )
        )
        _log.info("acknowledge: %s facet=%s digest=%s", ref, facet, digest[:8])
    return audit


def _dependents(ref: str, snapshot: GraphSnapshot) -> tuple[str, ...]:
    """Origins of every edge touching `ref` (what an acked change breaks)."""
    return tuple(
        edge.origin for edge in snapshot.edges if edge.src == ref or edge.target == ref
    )


def _vanished_endpoint(edge: Edge, snapshot: GraphSnapshot) -> str | None:
    """The edge endpoint (target checked first, then src) that no longer resolves.

    G3 (T-0402): a DESCRIBES target is special-cased through `resolve()`
    even when it is a bare name (no `::`) -- `markdown_anchors` happily
    accepts `<!-- frob:describes my_func -->` with no path qualifier, so a
    plain `"::" in edge.target` check never flagged a doc anchor pointing
    at a symbol that does not exist. Every other verb's bare targets
    (ticket ids, invariant ids, ...) are a different namespace entirely and
    stay untouched by this check.
    """
    if edge.kind == EdgeKind.DESCRIBES:
        if resolve(snapshot, edge.target).is_err:
            return edge.target
    elif "::" in edge.target and edge.target not in snapshot.symbols:
        return edge.target
    if "::" in edge.src and edge.src not in snapshot.symbols:
        return edge.src
    return None


def _recorded_digests(vanished_ref: str, lock: LockFile) -> set[str]:
    """Every digest the lock recorded for `vanished_ref`."""
    return {entry.digest for entry in lock.entries if entry.ref == vanished_ref}


def _body_digest_matches(
    vanished_ref: str, lock: LockFile, snapshot: GraphSnapshot
) -> set[str]:
    """Symrefs whose body digest matches a recorded ack of `vanished_ref`."""
    recorded = _recorded_digests(vanished_ref, lock)
    return {
        record.symref
        for record in snapshot.symbols.values()
        if record.digests.body in recorded
    }


def _qualname_matches(vanished_ref: str, snapshot: GraphSnapshot) -> set[str]:
    """Symrefs sharing the qualname of `vanished_ref` (a plausible rename)."""
    if "::" not in vanished_ref:
        return set()
    _path, _sep, qualname = vanished_ref.partition("::")
    return {
        record.symref
        for record in snapshot.symbols.values()
        if record.id.qualname == qualname
    }


def _rename_candidates(
    vanished_ref: str, lock: LockFile, snapshot: GraphSnapshot
) -> tuple[str, ...]:
    """Body-digest and same-qualname rename candidates for `vanished_ref`."""
    candidates = _body_digest_matches(vanished_ref, lock, snapshot)
    candidates |= _qualname_matches(vanished_ref, snapshot)
    return tuple(sorted(candidates))


# frob:waive OPAQUE001 reason="T-1038: entry.facet is always one of the closed \
# 'sig'/'body' vocabulary a persisted LockEntry can hold (the same Digests model \
# acknowledge() writes above) -- not attacker- or externally-controlled input"
def _stale_items(lock: LockFile, snapshot: GraphSnapshot) -> tuple[StaleItem, ...]:
    """Acked entries whose current digest has moved off the recorded value."""
    stale: list[StaleItem] = []
    for entry in lock.entries:
        record = snapshot.symbols.get(entry.ref)
        if record is None:
            continue  # no longer a symbol; covered by dangling edges, not stale acks
        current = getattr(record.digests, entry.facet, None)
        if current is None or current == entry.digest:
            continue
        stale.append(
            StaleItem(
                entry=entry,
                current=current,
                dependents=_dependents(entry.ref, snapshot),
            )
        )
    return tuple(stale)


def _dangling_edges(
    lock: LockFile, snapshot: GraphSnapshot
) -> tuple[DanglingEdge, ...]:
    """Edges whose endpoint no longer resolves, with rename candidates attached."""
    dangling: list[DanglingEdge] = []
    for edge in snapshot.edges:
        vanished = _vanished_endpoint(edge, snapshot)
        if vanished is None:
            continue
        dangling.append(
            DanglingEdge(
                edge=edge, candidates=_rename_candidates(vanished, lock, snapshot)
            )
        )
    return tuple(dangling)


# frob:doc docs/modules/graph.md#public-api
# frob:tests tests/test_graph_lock.py::TestAckDrift.test_bare_describes_target_to_nonexistent_symbol_is_dangling  # noqa: E501
def drift(lock: LockFile, snapshot: GraphSnapshot) -> DriftReport:
    """Pure comparison: stale acks (digest moved) and dangling edges (endpoint gone)."""
    stale = _stale_items(lock, snapshot)
    dangling = _dangling_edges(lock, snapshot)
    _log.info("drift: %d stale, %d dangling", len(stale), len(dangling))
    return DriftReport(stale=stale, dangling=dangling)


# frob:invariant INV-001
# frob:doc docs/modules/graph.md#public-api
# frob:tests tests/test_graph_lock.py::TestAckDrift.test_write_lock_deterministic
# frob:tests tests/test_graph_lock.py::TestAckDrift.test_write_lock_is_atomic
# frob:tests tests/test_graph_lock.py::TestAckDrift.test_write_lock_oserror_on_replace_is_write_failed  # noqa: E501
# frob:raises BaseException
def write_lock(lock: LockFile, path: Path) -> Result[Unit, LockError]:
    """Atomically write `lock` as deterministic, sorted, diff-friendly JSON.

    T-1317: `ack_log` is written in its existing append order (never
    resorted -- it is a chronological audit trail, not a lookup table like
    `entries`) so `frob ack --list` can render it oldest-first."""
    ordered = _sorted_entries(lock.entries)
    document = {
        "version": lock.version,
        "entries": [entry.model_dump() for entry in ordered],
        "ack_log": [entry.model_dump(mode="json") for entry in lock.ack_log],
    }
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=".frob-lock-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
            os.replace(tmp_name, path)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
    except OSError as exc:
        _log.error("write_lock: failed writing %s: %s", path, exc)
        return Err(LockError.WriteFailed)
    _log.info("write_lock: %d entries -> %s", len(ordered), path)
    return Ok(Unit())


__all__ = ["LockError", "acknowledge", "drift", "load_lock", "write_lock"]
