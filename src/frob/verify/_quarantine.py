# frob:ticket T-1693
"""T-1693: the quarantine circuit breaker -- the T-1686 epic's single most
important rule (this ticket's own text). Landing on top of a known-broken
base is what makes attribution cost explode: every subsequent land widens
the candidate set and adds findings that are consequences rather than
causes, not new problems of their own.

On a RED batch verification, `raise_quarantine` persists a durable flag.
While raised, `is_quarantined` reports `True` and the land path
(`frob.app.ticket_runner._land_cmd`) must fall back to fully synchronous
verification (or block, per profile) -- the deferred-landing credit line
is suspended, not the work itself. Ledger-integrity and LAND-PROOF paths
are untouched, as always (this module never touches either).

CLEARS ONLY ON ATTRIBUTION, NEVER ON GREEN. This is the one property this
whole module exists to enforce, and it is deliberately NOT the obvious
design: a naive circuit breaker clears itself the next time a check comes
back green. That is wrong here -- a green run after more lands means the
tree is clean NOW, it says nothing about whether the ORIGINAL regression
was ever understood. Auto-clearing on green is how a circuit breaker
silently becomes decoration (this ticket's own words). `clear_quarantine`
is the ONLY way out, and it requires the caller to name, for every
finding the raise recorded, either a real ticket id that now tracks it
(`FindingDisposition.filed`) or an explicit human dismissal
(`FindingDisposition.dismissed`, always carrying a `reason`) --
`_all_findings_disposed` refuses to clear otherwise, per finding, by id.

DURABLE ACROSS A WORKER RESTART. `.frob/quarantine.json` (mirroring
`frob.verify._watermark`'s own `.frob/verify-watermark.json` persistence
shape: a single current record, pydantic `frozen=True, extra="forbid"`,
schema-versioned) is the only source of truth `is_quarantined` reads --
never an in-memory flag a daemon restart could lose. A quarantine that
evaporates on restart is worse than none, because it is trusted (this
ticket's own words) -- a `.frob/quarantine.json` that disappears with the
process is exactly that failure mode; disk survives a restart, memory
does not.

LOGGED LOUDLY, BOTH DIRECTIONS. `raise_quarantine` logs at ERROR (naming
the batch and every finding); `clear_quarantine` logs at WARNING (naming
the clearing reason and who/what recorded it) -- silent state transitions
on the single most consequential flag in the land path are exactly the
kind of "worked once, then nobody could tell why the system behaved that
way" bug this repo has been burned by before."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/modules/tickets.md#quarantine-circuit-breaker-t-1693
#: Bumped whenever `QuarantineRecord`'s shape changes in a way an OLDER
#: reader could not safely interpret -- same convention `frob.verify.
#: _watermark.SCHEMA_VERSION` already establishes for this package.
SCHEMA_VERSION = 1

_QUARANTINE_REL = Path(".frob") / "quarantine.json"
_QUARANTINE_LOCK_REL = Path(".frob") / "quarantine.lock"

# frob:ticket T-2132
#: T-2132: gate rules whose finding is a statement about ELAPSED TIME or
#: repo/queue STATE, never about a commit's diff -- structurally
#: impossible for `frob.verify._attribution.attribute_batch` to pin to a
#: commit, no matter how good the reference-graph walk gets. `TICK004`
#: ("T-#### has sat queued for Nd") fires purely off `date.today()` minus
#: a ticket's `created` date (`frob.gates._tickets_gate._tick004_queue_
#: rot`) -- no land can ever be "the commit that caused" a clock ticking
#: forward, so `commit_sha=None` for a TICK004 finding is the TRUTH, not
#: a failed attribution.
#:
#: THE LINE THIS SET DRAWS (read before adding to it): membership here is
#: a claim about the RULE's own inputs, decided once by a human reading
#: the rule's implementation -- never inferred from an `Attribution`'s
#: runtime `status`. `status="unattributed"` (attribution genuinely
#: tried, walked the reference graph, and found zero or >1 reaching
#: commits) is NOT the same fact as "this rule could never have named a
#: commit in the first place", and the two must not be conflated: an
#: unattributed CODE finding (e.g. TEST001 with no reaching commit) still
#: raises quarantine below, because the attribution attempt failing is
#: itself a real, actionable "we don't know what broke this" signal
#: (T-1686's prior-art incident, referenced in this module's own
#: docstring, was a sweep that dropped UNATTRIBUTED findings as if they
#: were non-regressions -- do not repeat that mistake here by widening
#: this set past rules that are unattributable BY NATURE). A candidate
#: for this set must satisfy: "no git commit, however written, could ever
#: be the cause of this finding" -- true for a pure `date.today()`/queue-
#: age computation, false for anything that reads source, config, or
#: generated artifacts a commit could change.
_NATURALLY_UNATTRIBUTABLE_RULES: frozenset[str] = frozenset({"TICK004"})


# frob:doc docs/modules/tickets.md#quarantine-circuit-breaker-t-1693
class QuarantineError(ErrorSet):
    """Fallible outcomes of this module's raise/clear/status operations."""

    StoreCorrupt = "the quarantine file exists but failed to parse/validate"
    NotQuarantined = "clear_quarantine called with no quarantine currently raised"
    FindingsNotDisposed = (
        "one or more recorded findings have no filed ticket or dismissal yet"
    )
    EmptyFindings = "raise_quarantine requires at least one finding"


# frob:doc docs/modules/tickets.md#quarantine-circuit-breaker-t-1693
class QuarantinedFinding(BaseModel):
    """One finding the raising batch recorded (T-1690's own `Attribution`
    shape, narrowed to what this module persists/acts on) -- `rule_id`
    plus `file`/`line` identify the finding itself; `commit_sha`/
    `ticket_id` carry the T-1690 attribution when one exists (both `None`
    for an unattributed finding -- "cannot verify" is never "verified",
    an unattributed finding is recorded as exactly that, not silently
    dropped or guessed at). `disposition`/`disposition_ref`/
    `disposition_reason` start empty and are filled in only by
    `clear_quarantine`'s own dispose step."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str
    file: str
    line: int | None = None
    commit_sha: str | None = None
    ticket_id: str | None = None
    #: `""` (undisposed), `"filed"`, or `"dismissed"` -- see
    #: `FindingDisposition` for the two non-empty values' own contracts.
    disposition: str = ""
    #: The real ticket id tracking this finding, set only when
    #: `disposition == "filed"`.
    disposition_ref: str | None = None
    #: The human-recorded reason, set only when `disposition == "dismissed"`.
    disposition_reason: str | None = None


# frob:doc docs/modules/tickets.md#quarantine-circuit-breaker-t-1693
class QuarantineRecord(BaseModel):
    """`.frob/quarantine.json`'s single current record: whether quarantine
    is raised right now, the batch/findings that raised it, and (once
    cleared) when/why/by-whom it was cleared. A cleared record is kept
    (not deleted) as the audit trail of the last quarantine event --
    `is_quarantined` only ever looks at `cleared_at is None`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = SCHEMA_VERSION
    raised_at: str
    #: The `VerifyQueueEntry.commit_sha` values the raising batch covered
    #: (`frob.verify.queue_status`'s own shape) -- named plainly rather
    #: than re-importing `VerifyQueueEntry` here, avoiding a dependency
    #: this module does not otherwise need.
    batch_commit_shas: tuple[str, ...]
    findings: tuple[QuarantinedFinding, ...]
    cleared_at: str | None = None
    cleared_reason: str | None = None
    cleared_by: str | None = None


def _quarantine_path(root: Path) -> Path:
    """The `.frob/quarantine.json` path for a checkout rooted at `root`."""
    return root / _QUARANTINE_REL


def _quarantine_lock_path(root: Path) -> Path:
    """The advisory lock file guarding every `.frob/quarantine.json`
    mutation against `root` -- mirrors `frob.verify._watermark`'s own
    per-store lock-file convention, one lock per persisted store rather
    than one repo-wide lock, so a quarantine mutation never contends with
    an unrelated verify-queue/watermark write."""
    return root / _QUARANTINE_LOCK_REL


def _now_iso() -> str:
    """The current UTC time, ISO-8601 -- the single clock read every
    write in this module uses, matching `frob.verify._watermark`'s own
    `enqueued_at`/`verified_at` convention."""
    return datetime.now(UTC).isoformat()


# frob:doc docs/modules/tickets.md#quarantine-circuit-breaker-t-1693
# frob:tests \
# tests/unit/verify/test_quarantine.py::TestLoadQuarantine.test_missing_file_is_none \
# kind="unit"
# frob:tests \
# tests/unit/verify/test_quarantine.py::TestLoadQuarantine.test_corrupt_file_errors \
# kind="unit"
def load_quarantine(root: Path) -> Result[QuarantineRecord | None, QuarantineError]:
    """The current `.frob/quarantine.json` record for `root`, or `Ok(None)`
    if no quarantine has ever been raised (a fresh/absent file). A
    CORRUPT file is `Err(QuarantineError.StoreCorrupt)`, never silently
    treated as "no quarantine" -- the same "cannot verify is never
    verified" posture `frob.verify._watermark.queue_status` applies to a
    corrupt queue: an unreadable quarantine record must never be
    misread as a green light."""
    path = _quarantine_path(root)
    if not path.exists():
        return Ok(None)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _log.error("quarantine: %s failed to parse: %s", path, exc)
        return Err(QuarantineError.StoreCorrupt)
    try:
        return Ok(QuarantineRecord.model_validate(raw))
    except Exception as exc:  # noqa: BLE001 -- pydantic ValidationError, any shape
        _log.error("quarantine: %s failed to validate: %s", path, exc)
        return Err(QuarantineError.StoreCorrupt)


def _save_quarantine(root: Path, record: QuarantineRecord) -> None:
    """Write `record` back to `.frob/quarantine.json` -- caller must hold
    `_quarantine_lock_path`."""
    path = _quarantine_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")


# frob:doc docs/modules/tickets.md#quarantine-circuit-breaker-t-1693
# frob:tests \
# tests/unit/verify/test_quarantine.py::TestIsQuarantined.test_false_when_never_raised \
# kind="unit"
# frob:tests \
# tests/unit/verify/test_quarantine.py::TestIsQuarantined.test_true_while_raised \
# kind="unit"
# frob:tests \
# tests/unit/verify/test_quarantine.py::TestIsQuarantined.test_false_after_clear \
# kind="unit"
def is_quarantined(root: Path) -> Result[bool, QuarantineError]:
    """`True` iff `root` currently has an UNCLEARED quarantine raised
    (`cleared_at is None` on the current record). Propagates
    `QuarantineError.StoreCorrupt` rather than degrading to `False` on a
    corrupt file -- a caller that cannot tell whether quarantine is
    raised must never proceed as though it is not (this module's own
    "cannot verify is never verified" standing constraint)."""
    loaded = load_quarantine(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    record = loaded.danger_ok
    return Ok(record is not None and record.cleared_at is None)


# frob:doc docs/modules/tickets.md#quarantine-circuit-breaker-t-1693
# frob:tests \
# tests/unit/verify/test_quarantine.py::TestRaiseQuarantine.test_raises_and_persists \
# kind="unit"
# frob:tests tests/unit/verify/test_quarantine.py::TestRaiseQuarantine.test_empty_findings_refused kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestRaiseQuarantine.test_survives_a_fresh_load_reflecting_a_restart kind="unit"  # noqa: E501
def raise_quarantine(
    root: Path,
    *,
    batch_commit_shas: tuple[str, ...],
    findings: tuple[QuarantinedFinding, ...],
) -> Result[QuarantineRecord, QuarantineError]:
    """Raise quarantine for `root`, persisting `findings` (T-1690
    attribution results, narrowed to `QuarantinedFinding`) against the
    `batch_commit_shas` that produced them, and logging the raise at
    ERROR (naming the batch and every finding, T-1686's own "blocking/
    state-changing silently is the one unacceptable outcome" standing
    rule). Idempotent in the sense that raising again while ALREADY
    raised simply overwrites with the new, presumably larger, finding
    set -- the caller (the batch-verification driver) is expected to call
    this once per red batch, not per finding.

    `Err(QuarantineError.EmptyFindings)` for a call with no findings (or
    whose findings are ALL naturally-unattributable, T-2132 -- see
    `_NATURALLY_UNATTRIBUTABLE_RULES`) -- quarantine exists to name WHAT
    is wrong; a flag with nothing to attribute is a caller bug, not a
    legitimate empty raise, and a clock-driven finding that no commit
    could ever fix is exactly as unnameable as no finding at all.

    T-2132: every `_NATURALLY_UNATTRIBUTABLE_RULES` finding is dropped
    from `findings` FIRST, before the emptiness check and before
    persisting -- this is the single choke point both real callers
    (`frob.app.ticket_runner._land_cmd`'s backpressure-timeout raise and
    `_rapid_sweep`'s red-batch raise) already go through, so filtering
    here covers both without either needing its own copy of this rule.
    A finding that legitimately failed attribution (a real code rule,
    `commit_sha=None` because the reachability walk found zero or >1
    candidates) is NEVER in this set and always passes through unchanged
    -- see `_NATURALLY_UNATTRIBUTABLE_RULES`'s own docstring for exactly
    where that line is drawn."""
    exempted = tuple(
        f for f in findings if f.rule_id in _NATURALLY_UNATTRIBUTABLE_RULES
    )
    if exempted:
        _log.info(
            "quarantine: %d naturally-unattributable finding(s) dropped from "
            "this raise (rules=%s) -- a clock/repo-state rule can never be "
            "fixed by a commit, so it cannot gate landing (T-2132)",
            len(exempted),
            sorted({f.rule_id for f in exempted}),
        )
        findings = tuple(
            f for f in findings if f.rule_id not in _NATURALLY_UNATTRIBUTABLE_RULES
        )

    if not findings:
        _log.error(
            "quarantine: raise_quarantine called with zero findings for batch %s "
            "-- refusing (a raise must name what is wrong)",
            batch_commit_shas,
        )
        return Err(QuarantineError.EmptyFindings)

    from frob.tickets._land_queue import file_lock  # late import, mirrors _watermark.py

    with file_lock(_quarantine_lock_path(root), label="quarantine"):
        record = QuarantineRecord(
            raised_at=_now_iso(),
            batch_commit_shas=batch_commit_shas,
            findings=findings,
        )
        _save_quarantine(root, record)

    _log.error(
        "quarantine: RAISED for batch %s -- %d finding(s): %s -- deferred landing "
        "is OFF until every finding is filed or dismissed (frob.verify._quarantine."
        "clear_quarantine)",
        batch_commit_shas,
        len(findings),
        [(f.rule_id, f.file, f.line) for f in findings],
    )
    return Ok(record)


def _all_findings_disposed(findings: tuple[QuarantinedFinding, ...]) -> bool:
    """`True` iff every finding in `findings` carries a non-empty
    `disposition` (`"filed"` or `"dismissed"`) -- `clear_quarantine`'s own
    precondition, split out so the check itself is a single, obviously-
    correct expression rather than inlined into the mutation body."""
    return all(f.disposition in ("filed", "dismissed") for f in findings)


# frob:doc docs/modules/tickets.md#quarantine-circuit-breaker-t-1693
# frob:tests tests/unit/verify/test_quarantine.py::TestClearQuarantine.test_refuses_when_not_raised kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestClearQuarantine.test_refuses_when_a_finding_is_undisposed kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestClearQuarantine.test_clears_when_every_finding_disposed kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestClearQuarantine.test_green_verification_alone_never_clears kind="unit"  # noqa: E501
def clear_quarantine(
    root: Path,
    *,
    dispositions: dict[tuple[str, str, int | None], tuple[str, str]],
    reason: str,
    actor: str,
) -> Result[QuarantineRecord, QuarantineError]:
    """Clear the currently-raised quarantine for `root` -- THE ONLY path
    that ever clears it (this module's own docstring: never on a green
    verification alone). `dispositions` maps each raised finding's
    `(rule_id, file, line)` key to `(disposition, ref_or_reason)`, where
    `disposition` is `"filed"` (`ref_or_reason` is the real ticket id
    tracking it) or `"dismissed"` (`ref_or_reason` is the human's
    dismissal reason) -- every finding the current record carries MUST
    appear here, or `Err(QuarantineError.FindingsNotDisposed)` refuses
    the whole clear (never a partial clear: quarantine is raised or it is
    not, there is no "half-cleared" state to reason about).

    `Err(QuarantineError.NotQuarantined)` if nothing is currently raised
    -- clearing an already-clear quarantine is a caller bug, not a no-op,
    since it would otherwise silently accept a `reason`/`actor` for an
    event that never happened."""
    # late import, mirrors raise_quarantine
    from frob.tickets._land_queue import file_lock

    with file_lock(_quarantine_lock_path(root), label="quarantine"):
        loaded = load_quarantine(root)
        if loaded.is_err:
            return Err(loaded.danger_err)
        record = loaded.danger_ok
        if record is None or record.cleared_at is not None:
            _log.error(
                "quarantine: clear_quarantine called but no quarantine is "
                "currently raised for %s",
                root,
            )
            return Err(QuarantineError.NotQuarantined)

        disposed_findings = tuple(
            _dispose_one(f, dispositions) for f in record.findings
        )
        if not _all_findings_disposed(disposed_findings):
            undisposed = [
                (f.rule_id, f.file, f.line)
                for f in disposed_findings
                if not f.disposition
            ]
            _log.error(
                "quarantine: clear_quarantine refused -- %d finding(s) still "
                "undisposed: %s",
                len(undisposed),
                undisposed,
            )
            return Err(QuarantineError.FindingsNotDisposed)

        cleared = record.model_copy(
            update={
                "findings": disposed_findings,
                "cleared_at": _now_iso(),
                "cleared_reason": reason,
                "cleared_by": actor,
            }
        )
        _save_quarantine(root, cleared)

    _log.warning(
        "quarantine: CLEARED for batch %s by %s -- reason: %s -- deferred "
        "landing resumes",
        cleared.batch_commit_shas,
        actor,
        reason,
    )
    return Ok(cleared)


def _dispose_one(
    finding: QuarantinedFinding,
    dispositions: dict[tuple[str, str, int | None], tuple[str, str]],
) -> QuarantinedFinding:
    """Apply `dispositions`' entry for `finding` (keyed by `(rule_id,
    file, line)`), if any -- `clear_quarantine`'s own per-finding
    dispose step, split out to keep that function's body a single
    linear sequence."""
    key = (finding.rule_id, finding.file, finding.line)
    if key not in dispositions:
        return finding
    kind, ref_or_reason = dispositions[key]
    if kind == "filed":
        return finding.model_copy(
            update={"disposition": "filed", "disposition_ref": ref_or_reason}
        )
    if kind == "dismissed":
        return finding.model_copy(
            update={"disposition": "dismissed", "disposition_reason": ref_or_reason}
        )
    return finding
