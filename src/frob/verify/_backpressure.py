# frob:ticket T-1692
"""T-1692: bound the unverified window by depth AND age, and block a land
at the ceiling (docs/modules/tickets.md).

DEFERRAL IS A CREDIT LINE, NOT FREE MONEY. Without this leaf, T-1686's
verify queue (T-1687) plus coalescing worker (T-1688) is a mechanism for
accumulating unbounded unverified debt with a pleasant user experience --
strictly worse than the synchronous sweep it replaces. This module is
what makes the deferral bounded, not merely deferred.

TWO INDEPENDENT CEILINGS, EITHER ONE SUFFICIENT TO TRIP. `BackpressureStatus.
tripped` is `True` the moment EITHER axis is exceeded:

- DEPTH: the number of entries currently in the verify queue (commits
  landed above the last watermark advance) exceeds `max_depth`. Depth
  alone is not enough -- one commit can sit unverified all weekend behind
  a dead worker without depth ever growing past a small number.
- AGE: the OLDEST unverified entry's `enqueued_at` is older than
  `max_age_s`. Age alone is not enough either -- a burst of forty lands
  in quick succession stays inside any reasonable age window while depth
  grows unbounded.

Both axes are read from the SAME durable queue T-1687/T-1688 already
maintain (`frob.verify.queue_status`) -- this module adds no new storage.

BLOCK, NEVER FAIL. `block_until_watermark_advances` is the land-path
entrypoint: at the ceiling it does not refuse the land outright (which
would just make the developer re-run the whole thing) -- it BLOCKS,
logging the trip LOUDLY at WARNING (current depth, age, and the watermark
commit being waited on -- T-1686's own standing rule: "blocking silently
is the one unacceptable outcome"), and ACTIVELY PAYS BACK the deferred
verification cost right there by driving the coalescing worker itself
(`frob.verify.run_coalesced_verification`) rather than passively waiting
on some other process to drain the queue -- "a block simply pays back the
deferred cost at the moment it came due" (T-1686's own framing). This is
what keeps the design correct even in a topology with no daemon watching
the queue at all: the blocked land IS the thing that unblocks itself.

PER-PROFILE CEILINGS ARE THE PROFILE-COLLAPSE DIAL. `ceilings_for_profile`
resolves `fortress` to depth 0 (synchronous -- ANY queued-but-unverified
commit trips it, matching "refuse on red" at the strictest tier),
`standard` to a bounded depth/age pair, and `rapid` to `None`/`None`
(unbounded on both axes -- rapid NEVER blocks, by design, matching T-1684/
T-1686's existing "files, never blocks, never reverts" rapid posture).
`frob.toml [profile]` overrides let an owner tune the `standard` numbers
without a code change, the same `[profile]` table
`frob.tickets._profile.ratchet_override_enabled` already reads.
"""

from __future__ import annotations

import time
import tomllib
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.verify._watermark import load_watermark, queue_status

_log = get_logger(__name__)

#: `standard`'s default depth ceiling (T-1692's own acceptance example
#: uses K=2 for a small synthetic queue; this is the production default
#: for a real repo -- tune here, not scattered inline, mirroring
#: `frob.tickets._profile`'s own "documented calibration, not load-bearing
#: physics" posture for its threshold constants).
_STANDARD_DEFAULT_MAX_DEPTH = 5

#: `standard`'s default age ceiling: one hour. A commit that has waited
#: this long for verification is stale enough that the credit line is due,
#: even if depth alone never crossed the ceiling.
_STANDARD_DEFAULT_MAX_AGE_S = 3600.0

#: How long `block_until_watermark_advances` waits between drain attempts
#: when a single `run_coalesced_verification` call does not clear the
#: ceiling immediately (e.g. it just recorded a first-ever baseline, or
#: filed a red batch and left the watermark untouched -- either way,
#: retrying immediately would just repeat the identical unresolved state).
_DEFAULT_POLL_INTERVAL_S = 5.0

#: The hard stop on `block_until_watermark_advances`'s own wait -- without
#: this, a permanently red batch (T-1686's own quarantine posture: red
#: stays red until a human fixes it, never auto-reverted) would hang a
#: land forever. Generous on purpose: this is a LAST-RESORT ceiling on the
#: block itself, not the depth/age ceiling being enforced.
_DEFAULT_BLOCK_TIMEOUT_S = 1800.0


# frob:doc docs/modules/tickets-verify-sweep.md#backpressure-t-1692
# frob:ticket T-1756
class BackpressureError(ErrorSet):
    """Fallible outcomes of this module's status/block operations."""

    QueueUnreadable = (
        "the verify queue could not be read to compute backpressure status"
    )
    BlockTimedOut = (
        "the ceiling did not clear before block_until_watermark_advances's own timeout"
    )


# frob:doc docs/modules/tickets-verify-sweep.md#backpressure-t-1692
class BackpressureCeilings(BaseModel):
    """The two independent ceilings a profile enforces. `None` on either
    field means that axis is UNBOUNDED (never trips) -- `rapid`'s own
    ceilings, both `None`, is what makes rapid never block by
    construction rather than by a separate `if profile == rapid: skip`
    branch at every call site."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_depth: int | None
    max_age_s: float | None


# frob:doc docs/modules/tickets-verify-sweep.md#backpressure-t-1692
class BackpressureStatus(BaseModel):
    """One `current_status` reading: the queue's current depth and the
    age of its oldest entry, the watermark commit (if any) being waited
    on, and whether either ceiling is currently tripped."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    depth: int
    #: Age, in seconds, of the oldest queued entry -- `None` when the
    #: queue is empty (there is no "oldest entry" to measure).
    age_s: float | None
    watermark_commit: str | None
    tripped: bool
    #: Human-readable "which axis tripped and by how much" -- always
    #: empty when `tripped` is `False`.
    reason: str


def _read_frob_toml_profile_table(root: Path) -> dict:
    """`root`/`frob.toml`'s `[profile]` table, or `{}` on any absence/
    parse failure -- the same permissive-degrade-to-empty posture
    `frob.tickets._profile.ratchet_override_enabled` already establishes
    for reading this exact table; a malformed/missing `frob.toml` must
    never make ceiling resolution itself fail."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return {}
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    table = doc.get("profile")
    return table if isinstance(table, dict) else {}


# frob:doc docs/modules/tickets-verify-sweep.md#backpressure-t-1692
# frob:tests tests/unit/verify/test_backpressure.py::TestCeilingsForProfile.test_fortress_is_zero_depth_zero_age  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestCeilingsForProfile.test_rapid_is_unbounded  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestCeilingsForProfile.test_standard_default  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestCeilingsForProfile.test_standard_toml_override  # noqa: E501
def ceilings_for_profile(profile, root: Path) -> BackpressureCeilings:  # noqa: ANN001
    """The `BackpressureCeilings` a given `frob.tickets._profile.
    ProfileName` enforces at `root`: `fortress` is depth 0 (synchronous --
    T-1686's own "refuse on red" framing for the strictest tier, though
    this module blocks rather than refuses even here -- see this module's
    own docstring, "BLOCK, NEVER FAIL"), `standard` is a bounded
    depth/age pair (`_STANDARD_DEFAULT_MAX_DEPTH`/`_STANDARD_DEFAULT_MAX_
    AGE_S`, overridable via `frob.toml`'s `[profile]
    backpressure_max_depth`/`backpressure_max_age_s`), `rapid` is
    unbounded on both axes (`None`/`None` -- never blocks, by
    construction). Accepts `profile` untyped (`ProfileName` -- imported
    lazily by callers, never at this module's own top level, to avoid a
    load-order coupling to `frob.tickets._profile`) rather than importing
    the enum here just to type-hint it."""
    from frob.tickets._profile import ProfileName

    if profile is ProfileName.FORTRESS:
        return BackpressureCeilings(max_depth=0, max_age_s=0.0)
    if profile is ProfileName.RAPID:
        return BackpressureCeilings(max_depth=None, max_age_s=None)
    table = _read_frob_toml_profile_table(root)
    max_depth = table.get("backpressure_max_depth", _STANDARD_DEFAULT_MAX_DEPTH)
    max_age_s = table.get("backpressure_max_age_s", _STANDARD_DEFAULT_MAX_AGE_S)
    if not isinstance(max_depth, int):
        max_depth = _STANDARD_DEFAULT_MAX_DEPTH
    if not isinstance(max_age_s, (int, float)):
        max_age_s = _STANDARD_DEFAULT_MAX_AGE_S
    return BackpressureCeilings(max_depth=max_depth, max_age_s=float(max_age_s))


# frob:doc docs/modules/tickets-verify-sweep.md#land-profile-settings-t-2360
# frob:tests tests/unit/verify/test_backpressure.py::TestSettingsForProfile.test_fortress_matches_current_branch_logic  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestSettingsForProfile.test_rapid_matches_current_branch_logic  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestSettingsForProfile.test_settings_are_frozen  # noqa: E501
class LandProfileSettings(BaseModel):
    """The land-pipeline toggles a profile decides, generalizing
    `ceilings_for_profile`'s "resolve the name to a settings record in
    one place, never branch on the name at the call site" pattern
    (T-1692/T-2290) to the 5 remaining if-rapid seams T-2360 measured via
    `frob explore xref ProfileName` (`_land.py:2878`/`:3103`,
    `_land_cmd.py:4324`/`:4519`, `_evidence.py:323`, `_close_cmd.py:463`).
    `fortress` and `standard` resolve identically on every field today --
    none of these 5 branches currently distinguishes them, only `rapid`
    relaxes anything -- but the fields exist as named settings, not a
    single `is_rapid` bit, so a future profile (or a future decision to
    split fortress/standard on one of these axes) is a new resolver
    branch, never a new call-site `if`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: `_land_cmd.py:4324`'s pre-commit sweep (T-1514/T-1575: "single
    #: post-land sweep with revert-on-red, no pre-commit sweep" under
    #: rapid). `True` for fortress/standard, `False` for rapid.
    pre_commit_sweep_enabled: bool
    #: `_land.py:3103`'s TEST016 mutation evidence -- BOTH the synchronous
    #: subprocess and the deferred batch-sweep enqueue are skipped
    #: entirely when this is `False` (T-1575's own "TEST016 skipped
    #: entirely" framing; BUG002 is unaffected in every profile).
    mutation_evidence_required: bool
    #: `_close_cmd.py:463`'s REL001 close-time preflight (T-1705). `True`
    #: for fortress/standard, `False` for rapid.
    rel001_preflight_enabled: bool
    #: `_land.py:2878`/`_evidence.py:323`'s land-evidence-scope-unbound
    #: finding: recorded as DEBT (via `record_rapid_debt`) when `True`,
    #: left as whatever the caller's normal (stricter) path does when
    #: `False`. `True` only for rapid -- fortress/standard never divert
    #: this finding to debt.
    evidence_scope_unbound_is_debt: bool
    #: `_land_cmd.py:4607`'s `_apply_backpressure` soft-warning gate
    #: (T-2290): whether `rapid_soft_warning` is even consulted. `True`
    #: only for rapid -- fortress/standard already BLOCK at their own
    #: bounded ceilings (`ceilings_for_profile`), so the soft warning,
    #: which exists specifically to make rapid's unbounded "never blocks"
    #: debt visible, has nothing to add for them. T-1696 (this field is
    #: new, added alongside the other 4 T-2360 fields to close the 6th
    #: ProfileName branch T-2360's own measurement did not enumerate).
    rapid_soft_warning_enabled: bool


#: `LandProfileSettings` for fortress/standard: every rapid-only
#: relaxation stays OFF, no evidence-scope-unbound is ever silently
#: filed as debt. Fortress and standard are indistinguishable on all 4
#: of these fields today (see `LandProfileSettings`'s own docstring) --
#: named once here so a future split is a second constant, not a
#: duplicated literal.
_NON_RAPID_LAND_PROFILE_SETTINGS = LandProfileSettings(
    pre_commit_sweep_enabled=True,
    mutation_evidence_required=True,
    rel001_preflight_enabled=True,
    evidence_scope_unbound_is_debt=False,
    rapid_soft_warning_enabled=False,
)

#: `LandProfileSettings` for rapid: every relaxation this profile grants
#: today, in one place (T-1575/T-1681/T-1705's combined effect).
_RAPID_LAND_PROFILE_SETTINGS = LandProfileSettings(
    pre_commit_sweep_enabled=False,
    mutation_evidence_required=False,
    rel001_preflight_enabled=False,
    evidence_scope_unbound_is_debt=True,
    rapid_soft_warning_enabled=True,
)


# frob:doc docs/modules/tickets-verify-sweep.md#land-profile-settings-t-2360
# frob:tests tests/unit/verify/test_backpressure.py::TestSettingsForProfile.test_fortress_matches_current_branch_logic  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestSettingsForProfile.test_standard_matches_current_branch_logic  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestSettingsForProfile.test_rapid_matches_current_branch_logic  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestSettingsForProfile.test_unknown_profile_value_raises  # noqa: E501
def settings_for_profile(profile) -> LandProfileSettings:  # noqa: ANN001
    """The `LandProfileSettings` `profile` resolves to -- T-2360's
    generalization of `ceilings_for_profile`'s pattern to the 5
    if-rapid seams outside the depth/age axis. Accepts `profile`
    untyped (`ProfileName`, imported lazily below) for the same
    load-order reason `ceilings_for_profile` does. Unlike `ceilings_
    for_profile`, this resolver reads no `frob.toml` overrides -- none
    of the 5 branches it generalizes has ever been override-able, so
    adding override plumbing here would be new behavior, not a
    behavior-preserving migration.

    Deliberately loud on an unrecognized value: an `is`-comparison
    chain that quietly fell through to a default for a profile it does
    not recognize is exactly the kind of silent-default this settings
    record exists to prevent (T-1696's own "adding a fourth profile
    requires only a new settings row" acceptance -- a resolver that
    defaults silently would let a new profile fall through unnoticed
    instead of forcing this function to be taught about it). Raises
    `ValueError` rather than returning a typani `Result`: an unresolvable
    `ProfileName` is a programmer error (an enum member this resolver was
    never taught about), not a caller-recoverable outcome -- matching
    this module's own `ANN001`-untyped-argument posture of trusting the
    caller to pass a real `ProfileName`."""
    from frob.tickets._profile import ProfileName

    if profile is ProfileName.RAPID:
        return _RAPID_LAND_PROFILE_SETTINGS
    if profile in (ProfileName.FORTRESS, ProfileName.STANDARD):
        return _NON_RAPID_LAND_PROFILE_SETTINGS
    raise ValueError(
        f"settings_for_profile: unrecognized ProfileName {profile!r} -- "
        "no LandProfileSettings resolution exists for it; teach this "
        "resolver about the new profile rather than falling through to "
        "a default"
    )


# frob:doc docs/modules/tickets-verify-sweep.md#land-profile-settings-t-2360
# frob:ticket T-2361
# frob:tests tests/unit/verify/test_backpressure.py::TestEffectiveProfileOrStandard.test_ok_passes_through  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestEffectiveProfileOrStandard.test_err_falls_back_to_standard  # noqa: E501
def effective_profile_or_standard(root: Path):
    """`frob.tickets._profile.effective_profile(root)`'s resolved
    `ProfileName`, or `ProfileName.STANDARD` on any `Err` (T-2361: an
    unreadable profile config can only ever make a caller's downstream
    `ceilings_for_profile`/`settings_for_profile` resolution STRICTER,
    never silently relax it -- same fail-closed posture every other
    if-rapid-seam migration in this epic already uses, just centralized
    here instead of re-inlined at each call site).

    Exists so a caller that needs an actual resolved `ProfileName` value
    to hand to `ceilings_for_profile`/`settings_for_profile` (not just a
    derived boolean) never has to import `ProfileName` itself just to
    spell its own `Err` fallback -- the last such import outside this
    module and `frob.tickets._profile` was `_land_cmd.py`'s `_apply_
    backpressure` call site, closing T-2361's own "zero ProfileName xref
    outside the settings layer" acceptance check."""
    from frob.tickets._profile import ProfileName, effective_profile

    resolved = effective_profile(root)
    return resolved.danger_ok if resolved.is_ok else ProfileName.STANDARD


def _parse_enqueued_at(raw: str) -> float | None:
    """`VerifyQueueEntry.enqueued_at`'s ISO-8601 UTC string as a UNIX
    timestamp, or `None` on a genuinely unparsable value -- a corrupt
    timestamp must degrade to "age unknown", never to a fabricated
    number that could silently mask a real age-ceiling trip."""
    try:
        return datetime.fromisoformat(raw).timestamp()
    except (ValueError, TypeError):
        return None


# frob:doc docs/modules/tickets-verify-sweep.md#backpressure-t-1692
# frob:tests tests/unit/verify/test_backpressure.py::TestCurrentStatus.test_empty_queue_is_never_tripped  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestCurrentStatus.test_depth_ceiling_trips  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestCurrentStatus.test_age_ceiling_trips  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestCurrentStatus.test_unbounded_ceilings_never_trip  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestCurrentStatus.test_queue_unreadable_is_an_error  # noqa: E501
# frob:ticket T-1756
def current_status(
    root: Path,
    ceilings: BackpressureCeilings,
    *,
    now_fn: Callable[[], float] = time.time,
) -> Result[BackpressureStatus, BackpressureError]:
    """Read the CURRENT verify queue and watermark at `root` and decide
    whether `ceilings` is tripped. `Err(BackpressureError.QueueUnreadable)`
    on a corrupt queue file -- never a false "not tripped" read against
    data this module could not actually see (T-1686's own "cannot verify
    is never verified" invariant, extended to backpressure: an unreadable
    queue must never be silently treated as an empty, safe one)."""
    loaded = queue_status(root)
    if loaded.is_err:
        _log.error(
            "backpressure: current_status: verify queue unreadable (%s)",
            loaded.danger_err,
        )
        return Err(BackpressureError.QueueUnreadable)
    entries = loaded.danger_ok
    depth = len(entries)

    age_s: float | None = None
    if entries:
        oldest_ts = _parse_enqueued_at(entries[0].enqueued_at)
        if oldest_ts is not None:
            age_s = max(0.0, now_fn() - oldest_ts)

    watermark = load_watermark(root)
    watermark_commit = (
        watermark.danger_ok.commit_sha
        if watermark.is_ok and watermark.danger_ok
        else None
    )

    depth_tripped = ceilings.max_depth is not None and depth > ceilings.max_depth
    age_tripped = (
        ceilings.max_age_s is not None
        and age_s is not None
        and age_s > ceilings.max_age_s
    )
    reasons = []
    if depth_tripped:
        reasons.append(f"depth {depth} > max_depth {ceilings.max_depth}")
    if age_tripped:
        reasons.append(f"age {age_s:.0f}s > max_age_s {ceilings.max_age_s:.0f}s")
    tripped = bool(reasons)
    status = BackpressureStatus(
        depth=depth,
        age_s=age_s,
        watermark_commit=watermark_commit,
        tripped=tripped,
        reason="; ".join(reasons),
    )
    _log.debug(
        "backpressure: current_status: depth=%d age_s=%s watermark=%s tripped=%s",
        depth,
        age_s,
        watermark_commit,
        tripped,
    )
    return Ok(status)


# frob:doc docs/modules/tickets-verify-sweep.md#backpressure-t-1692
# frob:tests tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances.test_not_tripped_returns_immediately_without_draining  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances.test_tripped_drains_and_unblocks  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances.test_persistently_red_batch_times_out  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances.test_unbounded_ceiling_never_blocks  # noqa: E501
def block_until_watermark_advances(
    root: Path,
    ceilings: BackpressureCeilings,
    ticket_id: str,
    *,
    drain_fn: Callable[[Path], object] | None = None,
    poll_interval_s: float = _DEFAULT_POLL_INTERVAL_S,
    timeout_s: float = _DEFAULT_BLOCK_TIMEOUT_S,
    now_fn: Callable[[], float] = time.time,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Result[BackpressureStatus, BackpressureError]:
    """The land-path entrypoint (T-1692's own "at the ceiling the land
    BLOCKS" rule): if `ceilings` is not currently tripped, return
    immediately (`Ok`, no logging, no drain attempt -- the common case
    must cost nothing). If it IS tripped, log the trip LOUDLY at WARNING
    (depth, age, and the watermark commit being waited on -- never
    silently), then loop: call `drain_fn` (default `frob.verify.
    run_coalesced_verification`, deferred-imported to avoid a
    `frob.verify` internal import cycle) to actively pay back the
    deferred verification cost, re-check status, and either return `Ok`
    once the ceiling clears or sleep `poll_interval_s` and retry.
    `Err(BackpressureError.BlockTimedOut)` after `timeout_s` total wait
    -- a permanently red batch (quarantined, not auto-reverted, per
    T-1686's own recorded decision) must not hang a land forever; the
    ticket is still named in every log line so the wait is never
    mysterious even when it eventually times out."""
    if drain_fn is None:
        from frob.verify._worker import (
            run_coalesced_verification as drain_fn,  # type: ignore[assignment]  # noqa: E501
        )

    status_result = current_status(root, ceilings, now_fn=now_fn)
    if status_result.is_err:
        return status_result
    status = status_result.danger_ok
    if not status.tripped:
        return Ok(status)

    deadline = now_fn() + timeout_s
    attempt = 0
    while True:
        attempt += 1
        _log.warning(
            "backpressure: %s BLOCKED at the verify ceiling (%s) -- depth=%d "
            "age_s=%s watermark=%s; draining the queue to pay back the "
            "deferred cost before landing (attempt %d)",
            ticket_id,
            status.reason,
            status.depth,
            status.age_s,
            status.watermark_commit,
            attempt,
        )
        drain_fn(root)
        status_result = current_status(root, ceilings, now_fn=now_fn)
        if status_result.is_err:
            return status_result
        status = status_result.danger_ok
        if not status.tripped:
            _log.info(
                "backpressure: %s UNBLOCKED -- watermark now %s, depth=%d",
                ticket_id,
                status.watermark_commit,
                status.depth,
            )
            return Ok(status)
        if now_fn() >= deadline:
            _log.error(
                "backpressure: %s block timed out after %ds still at %s -- "
                "depth=%d age_s=%s watermark=%s; the batch is likely "
                "quarantined red and needs a human fix, not another wait",
                ticket_id,
                timeout_s,
                status.reason,
                status.depth,
                status.age_s,
                status.watermark_commit,
            )
            return Err(BackpressureError.BlockTimedOut)
        sleep_fn(poll_interval_s)


#: `rapid`'s own soft-warning defaults (T-2290) -- deliberately the SAME
#: numbers `_STANDARD_DEFAULT_MAX_DEPTH`/`_STANDARD_DEFAULT_MAX_AGE_S`
#: use, not a second pair to keep in sync by hand, but read from separate
#: `frob.toml` keys (`rapid_soft_warn_depth`/`rapid_soft_warn_age_s`) so
#: an owner can tune the warning threshold independently of `standard`'s
#: real (blocking) ceiling without the two accidentally diverging by
#: default.
_RAPID_SOFT_WARN_DEPTH = _STANDARD_DEFAULT_MAX_DEPTH
_RAPID_SOFT_WARN_AGE_S = _STANDARD_DEFAULT_MAX_AGE_S


# frob:doc docs/modules/tickets-verify-sweep.md#backpressure-t-1692
# frob:ticket T-2290
# frob:waive COV007 reason="docs/modules/tickets-verify-sweep.md's Backpressure \
# (T-1692) section documents several symbols under one section, not just a public \
# entry point -- the many-symbols- one-section convention this repo already accepted \
# for vet.md (T-2810 declined to touch it), not a T-2810-shaped duplicate"
def _rapid_soft_warn_thresholds(root: Path) -> tuple[int, float]:
    """T-2290: `(warn_depth, warn_age_s)` for `rapid_soft_warning` --
    `frob.toml`'s `[profile] rapid_soft_warn_depth`/`rapid_soft_warn_
    age_s` overrides if present and well-typed, else `_RAPID_SOFT_WARN_
    DEPTH`/`_RAPID_SOFT_WARN_AGE_S`. Split out of `rapid_soft_warning`
    (ARCH001) so that function's own body stays the read-and-compare
    sequence."""
    table = _read_frob_toml_profile_table(root)
    warn_depth = table.get("rapid_soft_warn_depth", _RAPID_SOFT_WARN_DEPTH)
    warn_age_s = table.get("rapid_soft_warn_age_s", _RAPID_SOFT_WARN_AGE_S)
    if not isinstance(warn_depth, int):
        warn_depth = _RAPID_SOFT_WARN_DEPTH
    if not isinstance(warn_age_s, (int, float)):
        warn_age_s = _RAPID_SOFT_WARN_AGE_S
    return warn_depth, float(warn_age_s)


# frob:doc docs/modules/tickets-verify-sweep.md#backpressure-t-1692
# frob:ticket T-2290
# frob:tests tests/unit/verify/test_backpressure.py::TestRapidSoftWarning.test_no_watermark_yet_is_none  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestRapidSoftWarning.test_below_threshold_is_none  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestRapidSoftWarning.test_stale_watermark_trips_the_soft_warning  # noqa: E501
# frob:tests tests/unit/verify/test_backpressure.py::TestRapidSoftWarning.test_toml_override  # noqa: E501
def rapid_soft_warning(
    root: Path,
    *,
    now_fn: Callable[[], float] = time.time,
) -> str | None:
    """T-2290: the `rapid` profile's own soft ceiling -- NEVER blocks a
    land (rapid's "never blocks, by construction" contract, T-1692's own
    docstring, is preserved unconditionally: this function only ever
    returns a message or `None`, it has no BLOCK/refuse code path at
    all), but names a message once real verification debt crosses a
    threshold, so the deferred-forever failure mode T-2290 was filed from
    (a watermark stuck 6 days / 403 commits behind, `ceilings_for_profile`
    returning `None`/`None` for rapid meaning nothing ever forces a
    drain) is at least LOUD at every surface an operator already reads
    (`frob verify status`, and the land log via `_apply_backpressure`)
    instead of silent.

    Measures against `frob.verify._watermark.commits_since_watermark` (the
    real git commit gap T-2290 found `queue_status`'s own queue-entry
    depth undercounting by roughly 5x at real staleness), falling back to
    the queue's own depth only when the git count is unavailable (a
    non-git root, or an unresolvable watermark commit) -- never silently
    treating "commit count unavailable" as "zero debt". Returns `None`
    when there is no watermark yet (a fresh repo has nothing to warn
    about) or when both axes stay under threshold."""
    watermark = load_watermark(root)
    if watermark.is_err or watermark.danger_ok is None:
        return None
    wm = watermark.danger_ok

    from frob.verify._watermark import commits_since_watermark

    commit_gap = commits_since_watermark(root, wm.commit_sha)

    queue = queue_status(root)
    queue_depth = len(queue.danger_ok) if queue.is_ok else 0
    depth = commit_gap if commit_gap is not None else queue_depth

    age_s: float | None = None
    parsed_verified_at = _parse_enqueued_at(wm.verified_at)
    if parsed_verified_at is not None:
        age_s = max(0.0, now_fn() - parsed_verified_at)

    warn_depth, warn_age_s = _rapid_soft_warn_thresholds(root)

    reasons = []
    if depth > warn_depth:
        gap_label = "commits" if commit_gap is not None else "queued land-intents"
        reasons.append(
            f"{depth} {gap_label} since watermark (warn threshold {warn_depth})"
        )
    if age_s is not None and age_s > warn_age_s:
        reasons.append(f"watermark age {age_s:.0f}s (warn threshold {warn_age_s:.0f}s)")
    if not reasons:
        return None
    return (
        "rapid profile verification debt is stale: "
        + "; ".join(reasons)
        + " -- rapid never blocks a land on this, but the deferred work "
        "still needs draining (`frob verify now`)"
    )


__all__ = [
    "BackpressureCeilings",
    "BackpressureError",
    "BackpressureStatus",
    "block_until_watermark_advances",
    "ceilings_for_profile",
    "current_status",
    "rapid_soft_warning",
]
