"""`frob.lock` -- acknowledged digests and drift detection (docs/graph.md).

Locking covers edge endpoints only, not every symbol -- locking everything
would churn `frob.lock` on every commit and drown review signal. `drift` is
a PURE comparison (never fails, never touches disk) so it is cheap to call
from any gate or CLI query; `acknowledge` and `write_lock` are the only
fallible, effectful operations here.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Sequence
from pathlib import Path

from typani import Err, ErrorSet, Ok
from typani.result import Result
from typani.unit import Unit

from frob.graph import resolve
from frob.graph._models import (
    DanglingEdge,
    DriftReport,
    Edge,
    GraphSnapshot,
    LockEntry,
    LockFile,
    StaleItem,
)
from frob.logging import get_logger

_log = get_logger(__name__)

_DEFAULT_FACET = "sig"


# frob:doc docs/graph.md#error-types
class LockError(ErrorSet):
    """Failure values `frob.lock` read/write paths can return."""

    Malformed = "frob.lock could not be parsed"
    UnknownRef = "Acknowledged ref is not an edge endpoint in the graph"
    WriteFailed = "Atomic write of frob.lock failed"


# frob:doc docs/graph.md#public-api
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


def _facet_for_ref(ref: str, snapshot: GraphSnapshot) -> str:
    """The facet a DESCRIBES edge targeting `ref` requests, else the default."""
    for edge in snapshot.edges:
        if edge.kind.value == "describes" and edge.target == ref:
            return edge.attrs.get("facet", _DEFAULT_FACET)
    return _DEFAULT_FACET


# frob:doc docs/graph.md#public-api
def acknowledge(
    lock: LockFile, snapshot: GraphSnapshot, refs: Sequence[str]
) -> Result[LockFile, LockError]:
    """Record current digests for `refs`; each ref must be an edge endpoint."""
    endpoints = _edge_endpoints(snapshot)
    entries: dict[tuple[str, str], LockEntry] = {
        (entry.ref, entry.facet): entry for entry in lock.entries
    }
    for ref in refs:
        if ref not in endpoints:
            _log.warning("acknowledge: %r is not an edge endpoint", ref)
            return Err(LockError.UnknownRef)
        record_result = resolve(snapshot, ref)
        if record_result.is_err:
            _log.warning("acknowledge: %r does not resolve to a symbol", ref)
            return Err(LockError.UnknownRef)
        record = record_result.danger_ok
        facet = _facet_for_ref(ref, snapshot)
        digest = getattr(record.digests, facet)
        entries[(ref, facet)] = LockEntry(ref=ref, facet=facet, digest=digest)
        _log.info("acknowledge: %s facet=%s digest=%s", ref, facet, digest[:8])
    ordered = tuple(sorted(entries.values(), key=lambda e: (e.ref, e.facet)))
    return Ok(LockFile(version=lock.version, entries=ordered))


def _dependents(ref: str, snapshot: GraphSnapshot) -> tuple[str, ...]:
    """Origins of every edge touching `ref` (what an acked change breaks)."""
    return tuple(
        edge.origin for edge in snapshot.edges if edge.src == ref or edge.target == ref
    )


def _vanished_endpoint(edge: Edge, snapshot: GraphSnapshot) -> str | None:
    """The edge endpoint (target checked first, then src) that no longer resolves."""
    if "::" in edge.target and edge.target not in snapshot.symbols:
        return edge.target
    if "::" in edge.src and edge.src not in snapshot.symbols:
        return edge.src
    return None


def _rename_candidates(
    vanished_ref: str, lock: LockFile, snapshot: GraphSnapshot
) -> tuple[str, ...]:
    """Body-digest and same-qualname rename candidates for `vanished_ref`."""
    recorded_digests = {
        entry.digest for entry in lock.entries if entry.ref == vanished_ref
    }
    candidates: set[str] = set()
    for record in snapshot.symbols.values():
        if record.digests.body in recorded_digests:
            candidates.add(record.symref)
    if "::" in vanished_ref:
        _path, _sep, qualname = vanished_ref.partition("::")
        for record in snapshot.symbols.values():
            if record.id.qualname == qualname:
                candidates.add(record.symref)
    return tuple(sorted(candidates))


# frob:doc docs/graph.md#public-api
def drift(lock: LockFile, snapshot: GraphSnapshot) -> DriftReport:
    """Pure comparison: stale acks (digest moved) and dangling edges (endpoint gone)."""
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

    _log.info("drift: %d stale, %d dangling", len(stale), len(dangling))
    return DriftReport(stale=tuple(stale), dangling=tuple(dangling))


# frob:invariant INV-001
# frob:doc docs/graph.md#public-api
def write_lock(lock: LockFile, path: Path) -> Result[Unit, LockError]:
    """Atomically write `lock` as deterministic, sorted, diff-friendly JSON."""
    ordered = sorted(lock.entries, key=lambda e: (e.ref, e.facet))
    document = {
        "version": lock.version,
        "entries": [entry.model_dump() for entry in ordered],
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
