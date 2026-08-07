# frob:ticket T-1575
# frob:waive INV006 reason="module docstring's 'never'/'only' claims (e.g. ledger \
# integrity/LAND-PROOF verification never relaxed, downgrade is the only way back) \
# describe this module's own implemented branching, verifiable by reading the code \
# they annotate -- not a separate cross-module contract needing a tracked invariant, \
# same disposition as _mutation_sweep_queue.py's identical T-0602-era-style waiver"
"""T-1575: development profiles (`frob.toml [profile]`) -- `rapid` /
`standard` (default) / `fortress` (placeholder) -- and the one-way
auto-ratchet from `rapid` to `standard`.

Small/new repos pay the same fixed land ceremony (TEST016, the T-1514
double sweep, the T-1463 baseline snapshot worktree, REL001) as this
950-file repo, and that ceremony does not scale down with repo size --
it is fixed-cost, not proportional (this ticket's own body). `rapid`
trims that ceremony for a repo genuinely small enough not to need it yet;
`standard` is today's unchanged behavior, the default whenever `[profile]`
is absent (existing repos are never silently relaxed by upgrading frob).

**What `rapid` relaxes** (each wired at the T-1518 land-pipeline stage
seam that already exists for it, never an inline `if profile ==` sprinkled
through unrelated logic):

- No TEST016 on the land path AT ALL, not even for `security`-kind
  tickets -- `frob.tickets._land._check_mutation_evidence` checks
  `effective_profile(worktree) == ProfileName.RAPID` before its normal
  `SYNC_BLOCKING_KINDS` branch (T-1518) and skips both the synchronous
  security-kind check and the deferred-sweep enqueue outright when rapid.
- Single post-land sweep with revert-on-red, no pre-commit sweep --
  `frob.app.ticket_runner._land_cmd`'s existing pre-commit-sweep call site
  is the seam; `rapid` skips it.
- No baseline-snapshot worktree (the T-1463 background thread `_land`
  spins up before calling `land()`).
- Evidence/done-report requirements light for `kind in {docs, chore}`.
- REL001 (the version-bump/changelog/debt-and-deprecation gate) off.

**NEVER relaxed in any profile, rapid included** (this ticket's own
text): ledger integrity checks and LAND-PROOF verification -- neither is
gated by `effective_profile` anywhere in this module or its callers.

**`fortress`** is reserved for a stricter tier; this ticket ships only
the enum member and config parsing (`ProfileName.FORTRESS` resolves and
round-trips), with NO behavioral wiring yet -- `effective_profile` never
returns it as an auto-ratchet target, and no land-path seam branches on
it. A follow-up ticket defines its actual semantics.

**One-way auto-ratchet.** `effective_profile(root)` is the single read
path every land-pipeline seam calls (never `frob.toml`'s raw `profile=`
directly) -- it resolves the configured profile, and if that is `rapid`,
checks `_ratchet_thresholds_tripped` against three live counts:

- repo file count (`_THRESHOLD_FILE_COUNT`, 300) -- via
  `frob.excludes.iter_files` scoped to the repo root, matching the count
  every other file-scale gate in this package already uses as its
  cheap proxy for "this is not a tiny repo anymore".
- total ticket count, open + closed (`_THRESHOLD_TICKET_COUNT`, 200) --
  via `frob.tickets.load_queue`'s merged active+archive count.
- concurrent agent/lease count (`_THRESHOLD_LEASE_COUNT`, 5) -- via
  `frob.tickets._leases.read_all_leases`'s length, the same signal
  `frob worktree sweep` already uses to tell a live multi-agent session
  from a solo one.

These three numbers are a starting calibration, not load-bearing physics
-- tune via `_THRESHOLD_FILE_COUNT`/`_THRESHOLD_TICKET_COUNT`/
`_THRESHOLD_LEASE_COUNT` if a real repo's experience says otherwise.
Any ONE threshold tripping is enough (an OR, not an AND): the ceremony
this profile trims exists because a mistake got expensive to unwind at
scale, and each axis (file count, ticket count, concurrent agents) is
an independent way to reach that scale.

The ratchet, once tripped, is PERSISTED to `.frob/profile-ratchet.json`
(`_RatchetState`) and never re-evaluated downward: `effective_profile`
checks the persisted ratchet file BEFORE re-computing live thresholds, so
a repo that later shrinks (tickets archived, files deleted) stays on
`standard` -- exactly the "upgrades automatic, downgrades never
automatic" contract this ticket's body states. `downgrade_profile_ratchet`
is the ONLY way to clear it: an explicit, loudly-logged CLI-level
decision (`frob.app.profile_runner`, not part of this module), never
something a land-pipeline seam can trigger on its own.
"""

from __future__ import annotations

import json
import tomllib
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger

_log = get_logger(__name__)

_RATCHET_REL = Path(".frob") / "profile-ratchet.json"

#: See this module's own docstring, "One-way auto-ratchet" -- an initial,
#: documented calibration, not load-bearing physics.
_THRESHOLD_FILE_COUNT = 300
_THRESHOLD_TICKET_COUNT = 200
_THRESHOLD_LEASE_COUNT = 5


# frob:doc docs/modules/tickets.md#development-profiles-frobtoml-profile-t-1575
class ProfileName(StrEnum):
    """`frob.toml`'s `[profile] profile = "..."` value -- `standard` is
    the default (today's unchanged behavior) whenever `[profile]` is
    absent, so an existing repo is never silently relaxed by upgrading
    `frob` itself."""

    RAPID = "rapid"
    STANDARD = "standard"
    #: Reserved, no behavioral wiring yet -- see module docstring.
    FORTRESS = "fortress"


# frob:doc docs/modules/tickets.md#development-profiles-frobtoml-profile-t-1575
class ProfileError(ErrorSet):
    """Fallible outcomes of this module's config/ratchet operations."""

    BadConfig = "frob.toml [profile] table failed to parse"
    RatchetStoreCorrupt = "the profile-ratchet file exists but failed to parse"


class _RatchetState(BaseModel):
    """`.frob/profile-ratchet.json`'s persisted shape -- written once, the
    moment `rapid` first auto-upgrades, never rewritten downward except by
    `downgrade_profile_ratchet`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ratcheted_to: str
    reason: str
    at: str


# frob:doc docs/modules/tickets.md#development-profiles-frobtoml-profile-t-1575
# frob:tests tests/unit/test_profile.py::TestConfiguredProfile.test_absent_frob_toml_is_standard  # noqa: E501
# frob:tests tests/unit/test_profile.py::TestConfiguredProfile.test_explicit_rapid_parses  # noqa: E501
# frob:tests tests/unit/test_profile.py::TestConfiguredProfile.test_unknown_value_errors  # noqa: E501
def configured_profile(root: Path) -> Result[ProfileName, ProfileError]:
    """The RAW `[profile] profile = "..."` value from `root`'s
    `frob.toml`, with no ratchet applied -- `standard` (`Ok`) whenever the
    file, the `[profile]` table, or the `profile` key is absent (matching
    `frob.testing._runners.load_natives`'s own fail-to-default-not-fail-
    closed posture for an optional TOML table). `Err(BadConfig)` only for
    a genuinely malformed file or an unrecognized profile name -- never a
    silent fallback to `standard` for a TYPO'd value, since that would
    silently drop the user's intent to relax the ceremony rather than
    honor or reject it."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return Ok(ProfileName.STANDARD)
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.error("profile: configured_profile: %s unreadable: %s", toml_path, exc)
        return Err(ProfileError.BadConfig)
    table = doc.get("profile")
    if not table:
        return Ok(ProfileName.STANDARD)
    raw = table.get("profile", "standard")
    try:
        return Ok(ProfileName(raw))
    except ValueError:
        _log.error(
            "profile: configured_profile: %s has unrecognized [profile] "
            "profile=%r (expected rapid/standard/fortress)",
            toml_path,
            raw,
        )
        return Err(ProfileError.BadConfig)


# frob:doc docs/modules/tickets.md#rapid-debt-and-the-ratchet-override-t-1681
# frob:tests tests/unit/test_profile.py::TestRatchetOverride.test_absent_frob_toml_is_not_overridden  # noqa: E501
# frob:tests tests/unit/test_profile.py::TestRatchetOverride.test_absent_key_is_not_overridden  # noqa: E501
# frob:tests tests/unit/test_profile.py::TestRatchetOverride.test_explicit_true_overrides  # noqa: E501
# frob:tests tests/unit/test_profile.py::TestRatchetOverride.test_malformed_toml_fails_strict_not_relaxed  # noqa: E501
# frob:ticket T-1681
def ratchet_override_enabled(root: Path) -> bool:
    """Whether `root`'s `frob.toml` sets `[profile] override_ratchet = true`
    (T-1681) -- an EXPLICIT, recorded owner decision to keep `rapid` in a
    repo whose size would otherwise auto-ratchet it to `standard`.

    The auto-ratchet exists because relaxed ceremony gets riskier as a repo
    grows, which is true. But it made `rapid` unreachable for exactly the
    repos where the ceremony costs the most: frob's own tree trips the file
    and ticket thresholds many times over, so configuring `rapid` here was
    a silent no-op. A per-land ceremony measured in tens of minutes is its
    own correctness risk -- work does not get done, and the queue grows
    faster than it drains.

    This is deliberately a config key and not an env var: it lives in a
    tracked file, so `git log frob.toml` states exactly which commits were
    produced under relaxed rules. That is the static record that makes the
    relaxation recoverable rather than merely convenient -- see T-1681 for
    the re-verification obligation it creates."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return False
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return False
    table = doc.get("profile")
    return bool(table.get("override_ratchet", False)) if table else False


def _ratchet_path(root: Path) -> Path:
    """The `.frob/profile-ratchet.json` path for a checkout rooted at
    `root`."""
    return root / _RATCHET_REL


def _load_ratchet(root: Path) -> Result[_RatchetState | None, ProfileError]:
    """Read `.frob/profile-ratchet.json`, or `Ok(None)` if it does not
    exist yet (never ratcheted)."""
    path = _ratchet_path(root)
    if not path.exists():
        return Ok(None)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return Ok(_RatchetState.model_validate(raw))
    except Exception as exc:  # noqa: BLE001 -- json/pydantic, any shape
        _log.error("profile: _load_ratchet: %s failed to parse: %s", path, exc)
        return Err(ProfileError.RatchetStoreCorrupt)


def _write_ratchet(root: Path, state: _RatchetState) -> None:
    """Persist `state` to `.frob/profile-ratchet.json`."""
    path = _ratchet_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def _repo_file_count(root: Path) -> int:
    """A cheap proxy for repo scale: every non-excluded file under
    `root`, via `frob.excludes.iter_files` -- the same pruned-walk
    primitive every other file-scale-aware gate in this package uses, so
    this count matches what a developer would see from e.g. `git ls-files`
    minus vendored/build noise, not a raw unpruned walk."""
    from frob.excludes import iter_files

    return len(iter_files(root))


def _total_ticket_count(root: Path) -> int:
    """Open + closed/archived ticket count, via `frob.tickets.load_queue`'s
    merged store -- `0` on a load failure (a corrupt ledger degrading the
    ratchet check to "not tripped by this axis" is safer than crashing a
    land-path seam over a ratchet threshold read)."""
    from frob.tickets import load_queue

    loaded = load_queue(root)
    if loaded.is_err:
        _log.warning(
            "profile: _total_ticket_count: load_queue failed (%s), "
            "treating as 0 for the ratchet check",
            loaded.danger_err,
        )
        return 0
    return len(loaded.danger_ok.tickets)


def _concurrent_lease_count(root: Path) -> int:
    """Currently-recorded cross-worktree leases, via
    `frob.tickets._leases.read_all_leases` -- the same signal `frob
    worktree sweep` already uses to distinguish a live multi-agent
    session from a solo one."""
    from frob.tickets._leases import read_all_leases

    return len(read_all_leases(root))


def _ratchet_thresholds_tripped(root: Path) -> str | None:
    """`None` if no threshold is tripped; otherwise a human-readable
    reason string naming which axis tripped and its measured value, for
    `effective_profile`'s loud upgrade log line and the persisted
    `_RatchetState.reason`. Any ONE axis tripping is enough (see module
    docstring's "any ONE threshold" note)."""
    files = _repo_file_count(root)
    if files > _THRESHOLD_FILE_COUNT:
        return f"repo file count {files} > {_THRESHOLD_FILE_COUNT}"
    tickets = _total_ticket_count(root)
    if tickets > _THRESHOLD_TICKET_COUNT:
        return f"total ticket count {tickets} > {_THRESHOLD_TICKET_COUNT}"
    leases = _concurrent_lease_count(root)
    if leases > _THRESHOLD_LEASE_COUNT:
        return f"concurrent lease count {leases} > {_THRESHOLD_LEASE_COUNT}"
    return None


# frob:doc docs/modules/tickets.md#development-profiles-frobtoml-profile-t-1575
# frob:tests tests/unit/test_profile.py::TestEffectiveProfile.test_standard_is_unaffected_by_ratchet  # noqa: E501
# frob:tests tests/unit/test_profile.py::TestEffectiveProfile.test_rapid_below_threshold_stays_rapid  # noqa: E501
# frob:tests tests/unit/test_profile.py::TestEffectiveProfile.test_rapid_above_threshold_ratchets_to_standard  # noqa: E501
# frob:tests tests/unit/test_profile.py::TestEffectiveProfile.test_persisted_ratchet_wins_even_if_thresholds_no_longer_trip  # noqa: E501
def effective_profile(root: Path) -> Result[ProfileName, ProfileError]:
    """The profile every land-pipeline seam should actually branch on --
    NEVER `configured_profile` directly. `standard`/`fortress` pass
    through unchanged (the ratchet only ever pushes `rapid` UP, never
    touches an already-stricter configured profile). For `rapid`: a
    previously persisted ratchet (`.frob/profile-ratchet.json`) wins
    immediately, with no threshold re-evaluation -- the one-way contract.
    Otherwise, live thresholds are checked (`_ratchet_thresholds_tripped`);
    a trip persists the ratchet and logs a loud WARNING naming the exact
    axis and value, then returns `standard` for this call and every call
    after. No trip: returns `rapid` and touches nothing on disk."""
    configured = configured_profile(root)
    if configured.is_err:
        return configured
    profile = configured.danger_ok
    if profile is not ProfileName.RAPID:
        return Ok(profile)

    if ratchet_override_enabled(root):
        _log.warning(
            "profile: %s is running RAPID with the size auto-ratchet "
            "OVERRIDDEN ([profile] override_ratchet=true, T-1681) -- "
            "TEST016, the pre-commit sweep, the baseline worktree and "
            "REL001 are OFF on the land path, and docs/chore evidence "
            "requirements are light. Ledger integrity and LAND-PROOF "
            "verification are NOT relaxed. Every commit made in this "
            "state needs the T-1681 re-verification pass before the "
            "relaxation is considered discharged",
            root,
        )
        return Ok(ProfileName.RAPID)

    ratchet = _load_ratchet(root)
    if ratchet.is_err:
        return Err(ratchet.danger_err)
    if ratchet.danger_ok is not None:
        return Ok(ProfileName.STANDARD)

    tripped_reason = _ratchet_thresholds_tripped(root)
    if tripped_reason is None:
        return Ok(ProfileName.RAPID)

    state = _RatchetState(
        ratcheted_to=ProfileName.STANDARD.value,
        reason=tripped_reason,
        at=datetime.now(timezone.utc).isoformat(),
    )
    _write_ratchet(root, state)
    _log.warning(
        "profile: effective_profile: AUTO-RATCHET rapid -> standard (%s) -- "
        "this is ONE-WAY; `frob profile downgrade` is the only way back, "
        "an explicit CLI decision that logs just as loudly",
        tripped_reason,
    )
    return Ok(ProfileName.STANDARD)


# frob:doc docs/modules/tickets.md#development-profiles-frobtoml-profile-t-1575
# frob:tests tests/unit/test_profile.py::TestDowngrade.test_downgrade_clears_persisted_ratchet  # noqa: E501
# frob:tests tests/unit/test_profile.py::TestDowngrade.test_downgrade_is_noop_when_nothing_ratcheted  # noqa: E501
# frob:waive WIRE001 reason="T-1575's own scope excludes a new CLI subcommand surface \
# -- this is the public API a follow-up 'frob profile downgrade' CLI verb will call; \
# no production caller exists yet by design of this increment" follow_up="T-1584"
def downgrade_profile_ratchet(root: Path, *, reason: str) -> Result[bool, ProfileError]:
    """Clear a persisted auto-ratchet -- the ONLY way `effective_profile`
    can go back to reading `rapid` off `frob.toml` after an auto-upgrade.
    Deliberately requires a `reason` (logged, not merely accepted) and is
    ALWAYS an explicit call, never invoked from any land-pipeline seam in
    this module -- see module docstring, "downgrades never automatic".
    Returns `Ok(True)` if a ratchet was actually cleared, `Ok(False)` if
    there was nothing to clear (not an error -- a caller re-running this
    idempotently should not see a failure)."""
    ratchet = _load_ratchet(root)
    if ratchet.is_err:
        return Err(ratchet.danger_err)
    if ratchet.danger_ok is None:
        _log.info(
            "profile: downgrade_profile_ratchet: nothing ratcheted at %s, no-op",
            root,
        )
        return Ok(False)
    path = _ratchet_path(root)
    path.unlink(missing_ok=True)
    _log.warning(
        "profile: downgrade_profile_ratchet: EXPLICIT DOWNGRADE -- cleared "
        "the standing rapid->standard ratchet (was: %s), reason=%r -- "
        "effective_profile will read rapid off frob.toml again until the "
        "next auto-ratchet trip",
        ratchet.danger_ok.reason,
        reason,
    )
    return Ok(True)


__all__ = [
    "ProfileError",
    "ProfileName",
    "configured_profile",
    "downgrade_profile_ratchet",
    "effective_profile",
]
