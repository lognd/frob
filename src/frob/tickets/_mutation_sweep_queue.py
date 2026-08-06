# frob:ticket T-1518
# frob:waive INV006 reason="module docstring's 'only' claims (e.g. security-kind still \
# runs synchronously) describe this module's own implemented \
# SYNC_BLOCKING_KINDS/enqueue-vs-run-inline branching, verifiable by reading the code \
# they annotate -- not a separate cross-module contract needing a tracked invariant, \
# same disposition as _land_queue.py's identical T-0602-era waiver"
"""T-1518: TEST016 mutation-evidence off the per-land critical path.

`frob.tickets._land._check_mutation_evidence` used to run the real
mutation subprocess (`frob.gates.mutation_evidence_violations`) for EVERY
landing ticket, synchronously, inside `_land_precheck` -- the single most
expensive, least incremental land stage (2026-08-04 dev-cycle review, the
ticket body this module implements). Its marginal per-ticket value is
test-strength validation, not main-correctness, so the exec-heavy half no
longer runs at land time for anything except `security`-kind tickets: a
`security`-kind ticket still runs `mutation_evidence_violations` inline
and still refuses the land on an ERROR-severity finding, exactly as
before (see `SYNC_BLOCKING_KINDS` below). Every other kind's obligation
is instead ENQUEUED here (`enqueue_pending_sweep`) and evaluated later, in
batch, by `run_pending_sweep` -- the natural cadence point is a merge-
queue drain (`frob.app.ticket_runner._land_cmd._land_drain`, T-1444) or a
standalone nightly `frob ticket land --run-mutation-sweep` invocation.

Design, mirroring `frob.tickets._land_queue`'s own precedent as closely as
this concern allows (same lock discipline, same "never silently drop an
entry" posture):

- **Storage.** `.frob/mutation-sweep-queue.json`, a flat JSON array of
  `SweepEntry` records, guarded by an `fcntl` advisory lock
  (`_sweep_lock`) exactly like `_land_queue._queue_lock` -- same
  degrade-to-logged-no-op posture on a platform without `fcntl`.
- **What gets queued.** One entry per deferred land: `ticket_id`, the
  `base_ref` the mutation check should diff against (the ticket's
  pre-land parent, so the batch run reproduces exactly what `_check_
  mutation_evidence` would have diffed inline), and `kind` (recorded so a
  batch finding can decide error-vs-warn severity without re-loading the
  ticket, which may have moved on to a different state by sweep time).
- **What the batch sweep does with a finding.** Per the ticket body: "a
  batch finding files a ticket against the offending land instead of
  refusing it retroactively" -- `run_pending_sweep` never mutates the
  original ticket's state and never blocks anything; a `bug`-kind entry
  (the one kind besides `security` that used to promote TEST016 to ERROR,
  `frob.gates._mutation_evidence._ERROR_KINDS`) whose batch run still
  surfaces a confirmatory-only finding files a NEW ticket
  (`_file_confirmatory_only_ticket`) referencing the offending land,
  origin=agent, kind=bug, so the finding re-enters the normal doable-
  ticket queue instead of vanishing into a log line. Every other kind's
  finding is logged at WARNING only, matching `mutation_evidence_
  violations`' own WARN severity for those kinds.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from types import ModuleType

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._models import Origin, TicketKind, TicketSpec

_log = get_logger(__name__)

fcntl: ModuleType | None
try:
    fcntl = import_module("fcntl")
except ImportError:  # pragma: no cover -- posix-only in this repo's CI
    fcntl = None

#: distinct from `_land_queue`'s `.frob/land-queue.json` and `.frob/
#: land.lock` -- a separate concern, a separate file, per this package's
#: "never reuse a lock/state file across a different concern" convention.
_SWEEP_REL = Path(".frob") / "mutation-sweep-queue.json"
_SWEEP_LOCK_REL = Path(".frob") / "mutation-sweep-queue.lock"

#: kinds whose TEST016 obligation still runs synchronously and blocks at
#: land time -- everything else is deferred to `run_pending_sweep`. Kept
#: here (not re-derived from `frob.gates._mutation_evidence._ERROR_KINDS`,
#: which also includes `bug`) because T-1518's own text narrows blocking
#: to `security` specifically: "keep it synchronous+blocking only for
#: kind=security tickets".
# frob:doc docs/modules/tickets.md#batch-mutation-evidence-sweep-test016-t-1518
SYNC_BLOCKING_KINDS = frozenset({TicketKind.SECURITY})


# frob:doc docs/modules/tickets.md#batch-mutation-evidence-sweep-test016-t-1518
class SweepQueueError(ErrorSet):
    """Fallible outcomes of this module's queue operations."""

    StoreCorrupt = "the mutation-sweep queue file exists but failed to parse"


# frob:doc docs/modules/tickets.md#batch-mutation-evidence-sweep-test016-t-1518
class SweepEntry(BaseModel):
    """One `.frob/mutation-sweep-queue.json` record: a landed (or landing)
    ticket whose TEST016 obligation was deferred off the land critical
    path, waiting for a batch `run_pending_sweep` pass."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticket_id: str
    base_ref: str
    kind: TicketKind
    #: ISO-8601 UTC timestamp, `enqueue_pending_sweep`'s own clock read --
    #: recorded for observability only, never re-parsed to decide order.
    queued_at: str
    #: "pending" (not yet swept) | "swept" (processed; kept in the file as
    #: history, mirroring `_land_queue.QueueEntry`'s own never-drop rule).
    status: str = "pending"
    #: Set once `status == "swept"`: whether the batch run found a
    #: surviving-mutant (confirmatory-only) result, and the id of the
    #: ticket filed against it (bug-kind findings only; None otherwise).
    finding: bool | None = None
    filed_ticket_id: str | None = None


def _sweep_path(root: Path) -> Path:
    """The `.frob/mutation-sweep-queue.json` path for a checkout rooted at
    `root`."""
    return root / _SWEEP_REL


def _sweep_lock_path(root: Path) -> Path:
    """The advisory lock file `_sweep_lock` holds, serializing every
    sweep-queue mutation against `root`."""
    return root / _SWEEP_LOCK_REL


@contextmanager
def _sweep_lock(root: Path) -> Iterator[None]:
    """Exclusive, blocking, cross-process lock serializing every sweep-
    queue-file mutation against `root` -- same posture as `frob.tickets.
    _land_queue._queue_lock`, degrading to a logged no-op on a platform
    without `fcntl`."""
    if fcntl is None:  # pragma: no cover -- posix-only in this repo's CI
        _log.warning(
            "mutation_sweep_queue: _sweep_lock: fcntl unavailable on this "
            "platform, lock is a NO-OP -- concurrent queue mutations "
            "against %s are NOT serialized here",
            root,
        )
        yield
        return
    path = _sweep_lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _load_sweep_queue(root: Path) -> Result[tuple[SweepEntry, ...], SweepQueueError]:
    """Read `.frob/mutation-sweep-queue.json`, or `Ok(())` on a fresh/
    absent file."""
    path = _sweep_path(root)
    if not path.exists():
        return Ok(())
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _log.error(
            "mutation_sweep_queue: _load_sweep_queue: %s failed to parse: %s",
            path,
            exc,
        )
        return Err(SweepQueueError.StoreCorrupt)
    try:
        return Ok(tuple(SweepEntry.model_validate(e) for e in raw))
    except Exception as exc:  # noqa: BLE001 -- pydantic ValidationError, any shape
        _log.error(
            "mutation_sweep_queue: _load_sweep_queue: %s failed to validate: %s",
            path,
            exc,
        )
        return Err(SweepQueueError.StoreCorrupt)


def _save_sweep_queue(root: Path, entries: tuple[SweepEntry, ...]) -> None:
    """Write `entries` back to `.frob/mutation-sweep-queue.json` -- caller
    must hold `_sweep_lock`."""
    path = _sweep_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps([e.model_dump(mode="json") for e in entries], indent=2)
    path.write_text(payload, encoding="utf-8")


# frob:doc docs/modules/tickets.md#mutation-evidence-obligation-test016-t-0755
# frob:tests tests/unit/test_mutation_sweep_queue.py::TestEnqueuePendingSweep.test_enqueue_persists_entry  # noqa: E501
def enqueue_pending_sweep(
    root: Path, ticket_id: str, base_ref: str, kind: TicketKind
) -> Result[SweepEntry, SweepQueueError]:
    """Append a `pending` sweep entry for `ticket_id` -- called from
    `frob.tickets._land._check_mutation_evidence` in place of running the
    mutation subprocess inline, for every kind outside `SYNC_BLOCKING_
    KINDS`."""
    with _sweep_lock(root):
        loaded = _load_sweep_queue(root)
        if loaded.is_err:
            return Err(loaded.danger_err)
        entries = loaded.danger_ok
        entry = SweepEntry(
            ticket_id=ticket_id,
            base_ref=base_ref,
            kind=kind,
            queued_at=datetime.now(timezone.utc).isoformat(),
        )
        _save_sweep_queue(root, (*entries, entry))
        _log.info(
            "mutation_sweep_queue: enqueue_pending_sweep: %s queued "
            "(kind=%s, base_ref=%s), TEST016 deferred off the land "
            "critical path",
            ticket_id,
            kind.value,
            base_ref,
        )
        return Ok(entry)


# frob:doc docs/modules/tickets.md#mutation-evidence-obligation-test016-t-0755
# frob:tests tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep.test_empty_queue_is_noop  # noqa: E501
# frob:tests tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep.test_clean_finding_marks_swept_no_ticket_filed  # noqa: E501
# frob:tests tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep.test_bug_kind_confirmatory_finding_files_ticket  # noqa: E501
# frob:tests tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep.test_non_bug_confirmatory_finding_only_warns  # noqa: E501
def run_pending_sweep(root: Path) -> Result[int, SweepQueueError]:
    """Process every `pending` entry: re-run `frob.tickets._mutation_
    evidence.check_ticket_mutation_evidence` against `root`'s CURRENT tree
    (by sweep time `root` is expected to already contain the landed diff
    on `main` -- this function does not check out historical commits) and
    the entry's recorded `base_ref`, then mark the entry `swept`.

    A `bug`-kind entry with a surviving-mutant finding files a new
    `bug`-kind ticket (`_file_confirmatory_only_ticket`) against the
    offending land rather than blocking anything retroactively, per the
    ticket body's own text. Every other kind's finding is logged at
    WARNING only -- unchanged from `mutation_evidence_violations`' own
    WARN severity for those kinds. A ticket that no longer loads (closed
    and archived, or otherwise gone) is marked `swept` with `finding=None`
    and skipped -- there is nothing left to check.

    Returns the number of entries processed (0 for an empty queue).

    T-1593: split into `_load_pending_sweep_entries` (queue draining),
    `_process_pending_sweep_entries` (per-entry execution), and
    `_save_pending_sweep_results` (merge + persist) -- this function is
    now just the glue between them, in the same order with the same
    short-circuit semantics as before the split."""
    loaded = _load_pending_sweep_entries(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    pending = loaded.danger_ok
    if not pending:
        _log.debug("mutation_sweep_queue: run_pending_sweep: nothing pending")
        return Ok(0)

    updated_by_id = _process_pending_sweep_entries(root, pending)

    saved = _save_pending_sweep_results(root, updated_by_id)
    if saved.is_err:
        return Err(saved.danger_err)

    _log.info(
        "mutation_sweep_queue: run_pending_sweep: processed %d entr%s",
        len(pending),
        "y" if len(pending) == 1 else "ies",
    )
    return Ok(len(pending))


# frob:ticket T-1593
def _load_pending_sweep_entries(
    root: Path,
) -> Result[list[SweepEntry], SweepQueueError]:
    """Queue-draining half of `run_pending_sweep` (T-1593 split): load the
    sweep queue under `_sweep_lock` and filter to `pending`-status
    entries. Pure extraction of the original leading `with _sweep_lock`
    block plus the `pending = [...]` filter, unchanged."""
    with _sweep_lock(root):
        loaded = _load_sweep_queue(root)
        if loaded.is_err:
            return Err(loaded.danger_err)
        entries = loaded.danger_ok
    return Ok([e for e in entries if e.status == "pending"])


# frob:ticket T-1593
def _process_pending_sweep_entries(
    root: Path, pending: list[SweepEntry]
) -> dict[str, SweepEntry]:
    """Per-entry execution half of `run_pending_sweep` (T-1593 split):
    re-run mutation evidence for each `pending` entry via
    `_process_one_pending_sweep_entry`, returning the by-id map of
    updated entries. Pure extraction of the original `for entry in
    pending:` loop, unchanged (the loop BODY is further split out below
    to stay under ARCH001's threshold)."""
    updated_by_id: dict[str, SweepEntry] = {}
    for entry in pending:
        updated_by_id[entry.ticket_id] = _process_one_pending_sweep_entry(root, entry)
    return updated_by_id


# frob:ticket T-1593
def _process_one_pending_sweep_entry(root: Path, entry: SweepEntry) -> SweepEntry:
    """Single-entry body of `_process_pending_sweep_entries` (T-1593
    split): re-run mutation evidence for one `entry` and classify/log the
    result into an updated `SweepEntry`. Pure extraction of the original
    per-entry loop body, unchanged."""
    from frob.tickets import _load_one
    from frob.tickets._mutation_evidence import (
        MutationEvidenceError,
        check_ticket_mutation_evidence,
    )

    loaded_ticket = _load_one(root, entry.ticket_id)
    if loaded_ticket.is_err:
        _log.warning(
            "mutation_sweep_queue: run_pending_sweep: %s no longer "
            "loadable (%s) -- marking swept, nothing to check",
            entry.ticket_id,
            loaded_ticket.danger_err,
        )
        return entry.model_copy(update={"status": "swept", "finding": None})
    ticket = loaded_ticket.danger_ok
    result = check_ticket_mutation_evidence(root, ticket, entry.base_ref)
    if result.is_err:
        if result.danger_err is not MutationEvidenceError.ExecDisabled:
            _log.warning(
                "mutation_sweep_queue: run_pending_sweep: %s check "
                "failed (%s) -- marking swept, no finding recorded",
                entry.ticket_id,
                result.danger_err,
            )
        return entry.model_copy(update={"status": "swept", "finding": None})
    findings = result.danger_ok
    if not findings:
        return entry.model_copy(update={"status": "swept", "finding": False})
    filed_id: str | None = None
    if entry.kind is TicketKind.BUG:
        filed = _file_confirmatory_only_ticket(root, entry.ticket_id, findings)
        filed_id = filed.ok
    else:
        _log.warning(
            "mutation_sweep_queue: run_pending_sweep: %s (kind=%s) "
            "batch TEST016 finding, %d file(s) confirmatory-only -- "
            "WARN only, not blocking",
            entry.ticket_id,
            entry.kind.value,
            len(findings),
        )
    return entry.model_copy(
        update={"status": "swept", "finding": True, "filed_ticket_id": filed_id}
    )


# frob:ticket T-1593
def _save_pending_sweep_results(
    root: Path, updated_by_id: dict[str, SweepEntry]
) -> Result[None, SweepQueueError]:
    """Merge-and-persist half of `run_pending_sweep` (T-1593 split):
    re-load the queue under `_sweep_lock`, overlay `updated_by_id` on the
    current state, and save. Pure extraction of the original trailing
    `with _sweep_lock` block, unchanged."""
    with _sweep_lock(root):
        loaded = _load_sweep_queue(root)
        if loaded.is_err:
            return Err(loaded.danger_err)
        current = loaded.danger_ok
        merged = tuple(updated_by_id.get(e.ticket_id, e) for e in current)
        _save_sweep_queue(root, merged)
    return Ok(None)


def _file_confirmatory_only_ticket(
    root: Path, offending_ticket_id: str, findings: tuple[object, ...]
) -> Result[str, str]:
    """File a new `bug`-kind, `agent`-origin ticket against `offending_
    ticket_id`'s land, naming the batch TEST016 finding -- the "files a
    ticket against the offending land instead of refusing it retroactively"
    half of T-1518's text. Returns the new ticket's id on success."""
    from frob.tickets._new_renumber import new_ticket

    body = (
        f"Batch TEST016 mutation-evidence sweep (T-1518) found {offending_ticket_id}'s "
        f"bound evidence confirmatory-only (killed zero mutants) across "
        f"{len(findings)} file(s), evaluated after landing rather than at "
        f"land time. Strengthen {offending_ticket_id}'s bound evidence so at "
        f"least one mutant of its changed lines fails, or waive TEST016 "
        f"with a documented reason."
    )
    spec = TicketSpec(
        title=(
            f"TEST016 batch sweep: confirmatory-only evidence in {offending_ticket_id}"
        ),
        kind=TicketKind.BUG,
        origin=Origin.AGENT,
        body=body,
    )
    result = new_ticket(root, spec)
    if result.is_err:
        _log.error(
            "mutation_sweep_queue: _file_confirmatory_only_ticket: failed to "
            "file a ticket against %s: %s",
            offending_ticket_id,
            result.danger_err,
        )
        return Err(str(result.danger_err))
    new_id = result.danger_ok.id
    _log.warning(
        "mutation_sweep_queue: _file_confirmatory_only_ticket: filed %s "
        "against %s's confirmatory-only batch finding",
        new_id,
        offending_ticket_id,
    )
    return Ok(new_id)


# frob:doc docs/modules/tickets.md#batch-mutation-evidence-sweep-test016-t-1518
# frob:tests tests/unit/test_mutation_sweep_queue.py::TestPendingSweepCount.test_counts_only_pending_entries  # noqa: E501
def pending_sweep_count(root: Path) -> Result[int, SweepQueueError]:
    """How many entries are currently `pending` in `root`'s mutation-sweep
    queue -- a read-only count for a caller (e.g. `frob ticket land
    --queue-status`) that wants visibility without mutating anything."""
    loaded = _load_sweep_queue(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    return Ok(sum(1 for e in loaded.danger_ok if e.status == "pending"))


__all__ = [
    "SYNC_BLOCKING_KINDS",
    "SweepEntry",
    "SweepQueueError",
    "enqueue_pending_sweep",
    "pending_sweep_count",
    "run_pending_sweep",
]
