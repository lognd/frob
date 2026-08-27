# frob:ticket T-1693
# frob:ticket T-3025
# frob:waive LARGE001 reason="T-3025's severity-proportional raise filter (_RUFF_DETERMINISTIC_AUTOFIX_RULES/_trivial_autofixable_rules/_is_trivial_unattributed plus their frob:tests directives) pushed this file ~90 lines past the 800 threshold; the addition is a single small, cohesive filter co-located with the raise/clear logic it modifies (T-1693's own module), not a candidate for an arbitrary split -- a real file-split ticket is a separate, larger architecture decision out of this bugfix's scope"  # noqa: E501
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

PROPORTIONAL TO THE TRIGGER (T-3025). `raise_quarantine` drops a finding
that is BOTH a proven-deterministic-autofix rule (ruff's own `I001`/
`F401`, deliberately narrow) AND genuinely unattributed (no commit, no
ticket) before persisting -- see `_is_trivial_unattributed`. A real
regression that IS attributed still raises even if trivial; an
unattributed finding without a proven mechanical fix still raises. Only
the intersection is exempted (still filed as an ordinary regression
ticket, recorded as debt, not dropped) -- the shape of all four measured
2026-08-26 incidents (I001 x2, F401 x1), each pinning quarantine for
hours across several failed land attempts.

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

# frob:doc docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693
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

# frob:ticket T-3025
#: T-3025: ruff rule ids whose ENTIRE fix is a blind, deterministic,
#: no-judgment-required mechanical rewrite (`I001` reorders an import
#: block, `F401` deletes a name nothing references) -- deliberately
#: narrow, never "any ruff code": a rule whose fix could change runtime
#: behavior has no business here. Each of T-3025's four measured
#: incidents was exactly one of these two codes.
_RUFF_DETERMINISTIC_AUTOFIX_RULES: frozenset[str] = frozenset({"I001", "F401"})


def _trivial_autofixable_rules() -> frozenset[str]:
    """T-3025: the rule ids treated as TRIVIAL for `raise_quarantine`'s
    unattributed-exemption -- exactly `_RUFF_DETERMINISTIC_AUTOFIX_
    RULES` above. Deliberately NOT widened to frob's own Tier-A-handled
    gate rules (e.g. `E501`, `frob.gates.__init__._KNOWN_RULE_
    FIXABILITY`'s "auto" tier): `frob.verify` has no existing
    architectural dependency on `frob.gates` (SYS003 would need a new
    declared Flow), and every measured incident was a ruff code. Widen
    this only against a real measured frob-gate-rule incident, via a
    follow-up ticket that declares the Flow."""
    return _RUFF_DETERMINISTIC_AUTOFIX_RULES


def _is_trivial_unattributed(finding: QuarantinedFinding) -> bool:
    """T-3025: `True` iff `finding` is BOTH (a) a rule with a proven
    deterministic auto-fix (`_trivial_autofixable_rules`) AND (b)
    genuinely unattributed (`commit_sha is None and ticket_id is None`).

    Both halves matter: a trivial rule ATTRIBUTED to a real commit/
    ticket already has a home and still raises (the fix being easy does
    not change that a regression was pinned); a non-trivial rule that is
    unattributed is real "we don't know what broke this" signal
    (`_NATURALLY_UNATTRIBUTABLE_RULES`'s own docstring) and still
    raises. Only the intersection -- cosmetic AND undisposable by the
    normal `--file-ticket`/`--dismiss` route, since there is no commit to
    attribute a filed ticket's evidence against -- is exempted here
    (the exact shape of all four measured T-3025 incidents). Still
    filed as an ordinary regression ticket by the sweep's own unaffected
    filing path (`frob.app.ticket_runner._rapid_sweep._file_regression_
    ticket`, which reads the pre-filter `pairs`, never this function's
    output) -- recorded as debt, not silently dropped."""
    return (
        finding.rule_id in _trivial_autofixable_rules()
        and finding.commit_sha is None
        and finding.ticket_id is None
    )


# frob:ticket T-3065
# frob:tests tests/unit/verify/test_quarantine.py::TestNormalizeFindingPath.test_absolute_and_relative_resolve_identical kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestNormalizeFindingPath.test_empty_file_passes_through kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestNormalizeFindingPath.test_unresolvable_path_falls_back_verbatim kind="unit"  # noqa: E501
def _normalize_finding_path(root: Path, file: str) -> str:
    """The single normalization every quarantine finding identity WRITE
    (`raise_quarantine`) and LOOKUP (`frob.app.verify_runner`'s
    `--file-ticket`/`--dismiss` key parsing) must pass through, so two
    callers naming the SAME filesystem path in different shapes
    (absolute vs. relative) land on the identical stored/matched
    identity (T-3065) -- comparison becomes symbolic (a resolved
    filesystem path), never a literal string match on whatever shape the
    caller happened to use. Previously only diagnosed after the fact by
    `_path_shape_hint` (T-2312); this is the write/lookup-time fix that
    makes the mismatch never occur in the first place, for any NEW
    finding going through either path.

    Returns `file` unchanged when it is empty (the `_is_unidentifiable`
    shape must stay exactly `""`, never a resolved cwd-relative string)
    or when it cannot be resolved against `root` (e.g. a malformed path)
    -- normalization must never turn an input it cannot handle into a
    crash or a silently different string. Otherwise returns the POSIX
    form of `file` resolved relative to `root` (absolute inputs are
    resolved as-is; relative inputs are resolved against `root` first),
    made relative to `root` itself -- i.e. the canonical repo-relative
    form regardless of the shape given.

    NOTE: this does not retroactively renormalize a finding already
    persisted to `.frob/quarantine.json` before this fix landed --
    `_path_shape_hint` stays in place as a diagnostic for exactly that
    legacy-record case."""
    if not file:
        return file
    try:
        candidate = Path(file)
        resolved = (
            candidate if candidate.is_absolute() else root / candidate
        ).resolve()
        resolved_root = root.resolve()
        return resolved.relative_to(resolved_root).as_posix()
    except (OSError, ValueError):
        return file


def _is_unidentifiable(finding: QuarantinedFinding) -> bool:
    """`True` iff `finding` carries an identity-less shape (`rule_id` AND
    `file` both empty) -- T-2207's live incident shape: a finding naming
    no rule and no file is not actionable by construction, so it is
    filtered out of `raise_quarantine` before it ever reaches disk, and
    it is the exact shape `retire_unidentifiable_findings` exists to
    repair for a store that already holds one from before that filter
    existed."""
    return finding.rule_id == "" and finding.file == ""


# frob:doc docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693
# frob:ticket T-2744
class QuarantineError(ErrorSet):
    """Fallible outcomes of this module's raise/clear/status operations."""

    StoreCorrupt = "the quarantine file exists but failed to parse/validate"
    NotQuarantined = "clear_quarantine called with no quarantine currently raised"
    FindingsNotDisposed = (
        "one or more recorded findings have no filed ticket or dismissal yet"
    )
    EmptyFindings = "raise_quarantine requires at least one finding"
    #: T-2207: `retire_unidentifiable_findings` called against a raised
    #: record none of whose findings are identity-less -- nothing for
    #: this specific verb to do (the normal `clear_quarantine`/CLI
    #: dispose path is the right tool for a well-formed finding).
    NoUnidentifiableFindings = (
        "no identity-less (empty rule_id and file) finding is present to retire"
    )
    #: T-2744: a `dispositions` entry disposes a finding as `"filed"`
    #: against a ticket id that does not resolve on `root` -- the clear
    #: must refuse rather than release the finding against a phantom
    #: home (the T-2736 incident: quarantine was cleared citing an
    #: auto-filed ticket that was never durably written, so nothing
    #: tracked the released findings afterward).
    UnresolvableFiledTicket = (
        "a 'filed' disposition names a ticket id that does not exist on root"
    )


# frob:doc docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693
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


# frob:doc docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693
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


# frob:doc docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693
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


# frob:doc docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693
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


# frob:doc docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693
# frob:tests \
# tests/unit/verify/test_quarantine.py::TestRaiseQuarantine.test_raises_and_persists \
# kind="unit"
# frob:tests tests/unit/verify/test_quarantine.py::TestRaiseQuarantine.test_empty_findings_refused kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestRaiseQuarantine.test_survives_a_fresh_load_reflecting_a_restart kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestIdentityLessFindingRecovery.test_raise_quarantine_drops_identity_less_findings_at_write_time kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestIdentityLessFindingRecovery.test_raise_quarantine_refuses_when_only_identity_less_findings_given kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestRaiseQuarantine.test_a_trivial_unattributed_ruff_finding_alone_does_not_raise kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestRaiseQuarantine.test_a_trivial_unattributed_unused_import_finding_does_not_raise kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestRaiseQuarantine.test_an_unattributed_frob_gate_autofix_rule_is_deliberately_not_exempt kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestRaiseQuarantine.test_an_attributed_trivial_finding_still_raises kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestRaiseQuarantine.test_an_unattributed_non_trivial_finding_still_raises kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestRaiseQuarantine.test_a_mixed_batch_drops_only_the_trivial_unattributed_finding kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestRaiseQuarantine.test_normalizes_an_absolute_file_to_root_relative_at_write_time kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestRaiseQuarantine.test_an_already_relative_file_is_left_as_is kind="unit"  # noqa: E501
# frob:waive DUP001 reason="T-2207: the new identity-less filter block mirrors this function's OWN pre-existing _NATURALLY_UNATTRIBUTABLE_RULES filter shape on purpose (deliberate consistency, see this function's docstring) -- the resulting structural match against unrelated filter/log/drop bodies across the tree (native-stub pairs, compliance-catalog tests, etc) is the generic shape, not shared logic worth extracting"  # noqa: E501
# frob:waive AFFECT001 reason="T-3065 adds a write-time path-normalization step (_normalize_finding_path) inside this function's existing filter pipeline -- an implementation-level bugfix to the identity-matching mechanism, not a change to the raise/persist/logging behavior docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693 describes; re-verified accurate via frob ack rather than an edit to that shared, many-symbol doc section"  # noqa: E501
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
    where that line is drawn.

    T-3025: a SECOND, independent filter runs right after this one -- a
    finding matching `_is_trivial_unattributed` (both a proven-
    deterministic-autofix rule AND genuinely unattributed) is also
    dropped before persisting. This is a SEVERITY cut, not an
    attribution one -- see that function's own docstring for why both
    halves are required and how narrow the resulting intersection is."""
    # T-3065: normalize every finding's `file` to its canonical
    # root-relative form BEFORE any filter runs or the record is
    # persisted -- the single write-time choke point that makes the
    # stored identity independent of whatever path shape the caller
    # (land-time backpressure raise vs. rapid-sweep red-batch raise)
    # happened to pass in.
    findings = tuple(
        f.model_copy(update={"file": _normalize_finding_path(root, f.file)})
        for f in findings
    )

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

    # T-3025: drop a finding that is BOTH a proven-deterministic-autofix
    # rule AND genuinely unattributed -- see `_is_trivial_unattributed`'s
    # own docstring for exactly why both halves are required and what
    # stays OUT of this set. Still filed as an ordinary regression ticket
    # by the caller's own unaffected filing path (this only changes what
    # reaches the quarantine dispose queue, matching `_NATURALLY_
    # UNATTRIBUTABLE_RULES`'s own precedent immediately above).
    trivial_unattributed = tuple(f for f in findings if _is_trivial_unattributed(f))
    if trivial_unattributed:
        _log.info(
            "quarantine: %d trivial-and-unattributed finding(s) dropped from "
            "this raise (rule=file: %s) -- a proven deterministic auto-fix "
            "with no commit/ticket to attribute it to does not warrant "
            "disabling fleet-wide deferred landing; still filed as an "
            "ordinary regression ticket (T-3025)",
            len(trivial_unattributed),
            [(f.rule_id, f.file) for f in trivial_unattributed],
        )
        findings = tuple(f for f in findings if not _is_trivial_unattributed(f))

    # T-2207: reject an identity-less finding (rule_id AND file both
    # empty) at write time -- something upstream persisting one is the
    # PRODUCER half of the live incident this ticket fixes. A finding
    # naming no rule and no file is not actionable by construction, so
    # it is dropped here, before it ever reaches `.frob/quarantine.json`,
    # rather than being written and discovered unrecoverable later.
    unidentifiable = tuple(f for f in findings if _is_unidentifiable(f))
    if unidentifiable:
        _log.error(
            "quarantine: %d identity-less finding(s) (empty rule_id AND file) "
            "dropped from this raise -- not actionable by construction (T-2207)",
            len(unidentifiable),
        )
        findings = tuple(f for f in findings if not _is_unidentifiable(f))

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


# frob:ticket T-2312
def _path_shape_hint(
    root: Path,
    undisposed: list[tuple[str, str, int | None]],
    dispositions: dict[tuple[str, str, int | None], tuple[str, str]],
) -> list[str]:
    """T-2312: diagnose the specific case where a `clear_quarantine` call
    refuses with `FindingsNotDisposed` because the caller's `--file-ticket`/
    `--dismiss` key resolves to the SAME file as an undisposed finding but
    written with a different path shape (absolute vs. relative) -- the
    quarantine store holds whatever shape the finding was originally
    recorded with, and a disposition key is matched by literal string
    equality (`_dispose_one`), so a shape mismatch fails identically to a
    genuinely wrong key: a bare `FindingsNotDisposed` naming the stored
    tuple, with nothing pointing at WHY the caller's own key -- which may
    look correct at a glance -- did not match.

    Returns one human-readable hint string per undisposed finding whose
    `(rule_id, line)` matches some given disposition key and whose `file`
    resolves (via `Path.resolve()`, relative to `root` when not already
    absolute) to the identical filesystem path as that key's `file` --
    i.e. the two keys name the same finding, differing only in path
    shape. Empty when no such pairing exists (an ordinary undisposed
    finding, or a malformed path this cannot resolve, is not this
    diagnosis and must not be reported as if it were)."""
    hints: list[str] = []
    for rule_id, file, line in undisposed:
        try:
            stored_path = Path(file)
            resolved_stored = (
                stored_path if stored_path.is_absolute() else root / stored_path
            ).resolve()
        except OSError:
            continue
        for d_rule, d_file, d_line in dispositions:
            if d_rule != rule_id or d_line != line or d_file == file:
                continue
            try:
                given_path = Path(d_file)
                resolved_given = (
                    given_path if given_path.is_absolute() else root / given_path
                ).resolve()
            except OSError:
                continue
            if resolved_given == resolved_stored:
                hints.append(
                    f"quarantine: {rule_id}:{file}: undisposed finding is "
                    f"stored with a different PATH SHAPE than the "
                    f"--file-ticket/--dismiss key given ({d_file!r}) -- "
                    f"same file, but the stored identity uses {file!r} "
                    "verbatim (string-matched, not resolved); re-address it "
                    f"using that exact stored form"
                )
                break
    return hints


def _all_findings_disposed(findings: tuple[QuarantinedFinding, ...]) -> bool:
    """`True` iff every finding in `findings` carries a non-empty
    `disposition` (`"filed"` or `"dismissed"`) -- `clear_quarantine`'s own
    precondition, split out so the check itself is a single, obviously-
    correct expression rather than inlined into the mutation body."""
    return all(f.disposition in ("filed", "dismissed") for f in findings)


# frob:doc docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693
# frob:tests tests/unit/verify/test_quarantine.py::TestClearQuarantine.test_refuses_when_not_raised kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestClearQuarantine.test_refuses_when_a_finding_is_undisposed kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestClearQuarantine.test_clears_when_every_finding_disposed kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestClearQuarantine.test_green_verification_alone_never_clears kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestIdentityLessFindingRecovery.test_cli_addressing_can_never_key_an_identity_less_finding kind="unit"  # noqa: E501
# frob:ticket T-2312
# frob:waive COV007 reason="docs/modules/tickets-verify-sweep.md's Quarantine circuit \
# breaker (T-1693) section documents several symbols under one section, not just a \
# public entry point -- the many-symbols- one-section convention this repo already \
# accepted for vet.md (T-2810 declined to touch it), not a T-2810-shaped duplicate"
def _refuse_if_undisposed(
    root: Path,
    disposed_findings: tuple[QuarantinedFinding, ...],
    dispositions: dict[tuple[str, str, int | None], tuple[str, str]],
) -> QuarantineError | None:
    """T-2312 (ARCH001 split of `clear_quarantine`): its own "still
    undisposed" refusal branch. `None` (proceed) when every finding in
    `disposed_findings` already carries a disposition; otherwise logs
    the undisposed set at ERROR -- plus a `_path_shape_hint` for any of
    them whose stored identity differs from a given disposition key only
    by absolute/relative path shape (T-2312's own diagnosability
    requirement: a bare `FindingsNotDisposed` leaves an operator with no
    clue WHY a key that looks right at a glance did not match) -- and
    returns `QuarantineError.FindingsNotDisposed` for the caller to wrap
    in its own `Err(...)` (plain error value, not a `Result`, so this
    helper's return type never has to fake a `T` it does not know)."""
    if _all_findings_disposed(disposed_findings):
        return None
    undisposed = [
        (f.rule_id, f.file, f.line) for f in disposed_findings if not f.disposition
    ]
    _log.error(
        "quarantine: clear_quarantine refused -- %d finding(s) still undisposed: %s",
        len(undisposed),
        undisposed,
    )
    for hint in _path_shape_hint(root, undisposed, dispositions):
        _log.error("%s", hint)
    return QuarantineError.FindingsNotDisposed


# frob:ticket T-2744
# frob:tests tests/unit/verify/test_quarantine.py::TestClearQuarantine.test_refuses_when_filed_ticket_does_not_resolve  # noqa: E501
def _refuse_if_filed_ticket_unresolvable(
    root: Path,
    dispositions: dict[tuple[str, str, int | None], tuple[str, str]],
) -> QuarantineError | None:
    """T-2744: `clear_quarantine`'s own gate on every `"filed"`
    disposition's `ref_or_reason` -- it must name a ticket id that
    actually resolves on `root`, or the clear is refused loudly rather
    than releasing the finding against a home nothing tracks.

    This is deliberately mechanism-agnostic: whether the citing id was
    never durably written (a failed ledger commit that a caller
    proceeded past anyway), lives only on a worktree branch that never
    landed, or was allocated and reported before its write completed,
    the observable defect is identical -- `root` cannot resolve the id
    -- so one check here closes all three at the single point every
    clear (CLI, rapid sweep, or otherwise) must pass through, rather
    than each caller re-deriving its own success check.

    A `"dismissed"` disposition's `ref_or_reason` is a free-text human
    reason, not a ticket id, and is never checked here."""
    from frob.tickets import _load_one

    for (rule_id, file, line), (kind, ref_or_reason) in dispositions.items():
        if kind != "filed":
            continue
        loaded = _load_one(root, ref_or_reason)
        if loaded.is_err:
            _log.error(
                "quarantine: clear_quarantine refused -- disposition for "
                "(%s, %s, %s) cites ticket %s as 'filed', but it does not "
                "resolve on %s (%s); the clear would release this finding "
                "against a phantom home",
                rule_id,
                file,
                line,
                ref_or_reason,
                root,
                loaded.danger_err,
            )
            return QuarantineError.UnresolvableFiledTicket
    return None


# frob:doc docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693
# frob:ticket T-2744
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
    event that never happened.

    T-2744: `Err(QuarantineError.UnresolvableFiledTicket)` if any
    `"filed"` disposition names a ticket id that does not resolve on
    `root` -- checked BEFORE any finding is disposed, so a bogus id
    refuses the whole clear rather than releasing that finding against a
    home nothing tracks (see `_refuse_if_filed_ticket_unresolvable`)."""
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

        ticket_refusal = _refuse_if_filed_ticket_unresolvable(root, dispositions)
        if ticket_refusal is not None:
            return Err(ticket_refusal)

        disposed_findings = tuple(
            _dispose_one(f, dispositions) for f in record.findings
        )
        refusal = _refuse_if_undisposed(root, disposed_findings, dispositions)
        if refusal is not None:
            return Err(refusal)

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


# frob:ticket T-2207
# frob:doc docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693
# frob:tests tests/unit/verify/test_quarantine.py::TestIdentityLessFindingRecovery.test_retire_unidentifiable_findings_recovers_a_stuck_store kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestIdentityLessFindingRecovery.test_retire_unidentifiable_findings_still_blocks_on_a_well_formed_sibling kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestIdentityLessFindingRecovery.test_retire_unidentifiable_findings_refuses_when_none_present kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_quarantine.py::TestIdentityLessFindingRecovery.test_retire_unidentifiable_findings_refuses_when_not_raised kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_verify_runner.py::TestDispose.test_retire_unidentifiable_flag_retires_and_clears kind="unit"  # noqa: E501
def retire_unidentifiable_findings(
    root: Path,
    *,
    reason: str,
    actor: str,
) -> Result[QuarantineRecord, QuarantineError]:
    """T-2207's CONSUMER-side recovery verb: explicitly, logged-ly retire
    every currently-raised finding whose identity is empty (`rule_id`
    AND `file` both `""` -- `_is_unidentifiable`), dismissing each with
    `reason`/`actor`, then applying the SAME "clear only if every
    finding -- identity-less or not -- ends up disposed" rule
    `clear_quarantine` itself enforces. A well-formed undisposed sibling
    still blocks the actual clear afterward, exactly as before: this
    retires ONLY the identity-less records, it is never a bulk-dismiss,
    and it never widens `clear_quarantine`'s own "no partial clear"
    contract.

    This exists because the live incident this ticket fixes could not be
    recovered any other way: the CLI's own `RULE:FILE:LINE` addressing
    (`frob.app.verify_runner._parse_finding_arg`) can never key to
    `("", "", None)` -- an empty `file` component is always rejected as
    malformed, by construction of that syntax, so no `--dismiss`/
    `--file-ticket` argument can ever name an identity-less finding.
    `raise_quarantine`'s own producer-side filter (this module, same
    ticket) stops NEW identity-less findings from ever reaching disk,
    but a store that already reached this state before that filter
    existed needs an explicit, non-CLI-syntax-dependent way out -- this
    is that way out: target the identity-less SHAPE directly rather than
    a caller-supplied key, since no caller-supplied key can ever exist
    for it.

    `Err(QuarantineError.NotQuarantined)` if nothing is currently raised
    (same posture as `clear_quarantine`). `Err(QuarantineError.
    NoUnidentifiableFindings)` if the current record is raised but
    carries no identity-less finding -- use `clear_quarantine` directly
    for a well-formed finding, this verb is not a general-purpose
    dispose path."""
    from frob.tickets._land_queue import (  # late import, mirrors raise_quarantine
        file_lock,
    )

    with file_lock(_quarantine_lock_path(root), label="quarantine"):
        loaded = load_quarantine(root)
        if loaded.is_err:
            return Err(loaded.danger_err)
        record = loaded.danger_ok
        if record is None or record.cleared_at is not None:
            _log.error(
                "quarantine: retire_unidentifiable_findings called but no "
                "quarantine is currently raised for %s",
                root,
            )
            return Err(QuarantineError.NotQuarantined)

        targets = [f for f in record.findings if _is_unidentifiable(f)]
        if not targets:
            _log.error(
                "quarantine: retire_unidentifiable_findings called but no "
                "identity-less finding is present in the current record for %s",
                root,
            )
            return Err(QuarantineError.NoUnidentifiableFindings)

        _log.warning(
            "quarantine: retiring %d identity-less finding(s) for %s by %s -- "
            "reason: %s (T-2207 recovery path)",
            len(targets),
            root,
            actor,
            reason,
        )
        disposed_findings = tuple(
            f.model_copy(
                update={"disposition": "dismissed", "disposition_reason": reason}
            )
            if _is_unidentifiable(f)
            else f
            for f in record.findings
        )

        if not _all_findings_disposed(disposed_findings):
            undisposed = [
                (f.rule_id, f.file, f.line)
                for f in disposed_findings
                if not f.disposition
            ]
            partially_retired = record.model_copy(
                update={"findings": disposed_findings}
            )
            _save_quarantine(root, partially_retired)
            _log.error(
                "quarantine: %d identity-less finding(s) retired but %d "
                "well-formed finding(s) still undisposed -- quarantine NOT "
                "cleared: %s",
                len(targets),
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
        "quarantine: CLEARED for batch %s by %s -- reason: %s (retired %d "
        "identity-less finding(s)) -- deferred landing resumes",
        cleared.batch_commit_shas,
        actor,
        reason,
        len(targets),
    )
    return Ok(cleared)
