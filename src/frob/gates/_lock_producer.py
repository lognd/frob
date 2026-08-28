"""Producer-staleness for the repo's committed baseline `.lock.json`
files (T-2999): distinguishes a DELIBERATELY frozen baseline (correct,
healthy, no action needed) from an ABANDONED one whose stamping producer
has quietly stopped running while the code it baselines kept moving --
two states that, read as raw file age alone, look identical.

THE THREE TRACKED LOCKS (module-level `KNOWN_LOCKS`): `frob-coverage.
lock.json` (`frob.gates._coverage.write_coverage_lock`, T-0545),
`frob-ratchet.lock.json` (`frob.gates._ratchet`, T-0569), and
`frob-deprecated-baseline.lock.json` (`frob.gates._deprecated_baseline`,
T-0639) -- all three share the same "committed summary outside
`.gitignore`'s reach" posture those modules' own docstrings already
document, and all three have exactly the same silent-fossil failure
mode this module targets.

SIGNAL: commits-since-last-stamp is measured two ways -- `commits_since`
(every commit after the lock's own last touch) and `code_commits_since`
(only commits that touched the lock's own `code_glob`, a pathspec
passed to `git log --oneline -- <glob>`). A lock with a HIGH
`code_commits_since` and no pin is the honest signature of abandonment:
the code the baseline claims to summarize kept changing while nothing
re-stamped it. A lock that is old but whose code never moved is
legitimately frozen by construction, pin or no pin.

PIN: a lock file MAY carry a top-level `"pin"` object --
`{"reason": "...", "ticket": "T-####"}` -- a positive declaration that
staleness here is deliberate, the same "a warning nobody can action
trains itself out" doctrine `frob:waive` already applies to inline gate
findings. `producer_status` treats ANY lock carrying a non-empty pin
`reason` as `PINNED`, never `ABANDONED`, regardless of the measured
commit counts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from frob.gitio import run_argv
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "ABANDONED_CODE_COMMIT_THRESHOLD",
    "KNOWN_LOCKS",
    "LockPin",
    "LockProducerStatus",
    "TrackedLock",
    "all_producer_statuses",
    "producer_status",
]

#: Below this many commits touching a lock's own `code_glob` since the
#: lock's last stamp, a stale-but-unpinned lock reads as ordinary lag
#: (a producer that runs occasionally, not one that stopped); at or
#: above it, the code the baseline claims to summarize has moved far
#: enough that "nobody has re-run the producer" is the more honest
#: reading than "nothing needed updating". Chosen well below this
#: repo's OWN measured worst case (T-2999 Done report: 5810-7447
#: commits since each of the three locks' last touch) so the signal
#: fires on real abandonment, not on healthy occasional-refresh lag.
# frob:doc docs/modules/gates.md#public-api
ABANDONED_CODE_COMMIT_THRESHOLD = 200


# frob:doc docs/modules/gates.md#public-api
# frob:tests tests/unit/gates/test_lock_producer.py::TestProducerStatusVerdicts.test_must_stay_quiet_when_pinned kind="unit"  # noqa: E501
class LockPin(BaseModel):
    """A lock's `"pin"` object: a positive, reasoned declaration that its
    staleness is deliberate, never inferred from silence."""

    model_config = {}

    reason: str
    ticket: str | None = None


# frob:doc docs/modules/gates.md#public-api
# frob:tests tests/unit/gates/test_lock_producer.py::TestProducerStatusVerdicts.test_fresh_when_unpinned_and_below_threshold kind="unit"  # noqa: E501
class TrackedLock(BaseModel):
    """One of the three known baseline locks this module watches: its
    committed path and the code glob whose churn measures whether its
    producer has fallen behind."""

    model_config = {}

    name: str
    path_rel: str
    code_glob: str


#: The three baseline locks this repo currently commits, in the same
#: order T-2999's ticket body lists them.
# frob:doc docs/modules/gates.md#public-api
KNOWN_LOCKS: tuple[TrackedLock, ...] = (
    TrackedLock(
        name="coverage",
        path_rel="frob-coverage.lock.json",
        code_glob="src/frob/**/*.py",
    ),
    TrackedLock(
        name="deprecated-baseline",
        path_rel="frob-deprecated-baseline.lock.json",
        code_glob="src/frob/**/*.py",
    ),
    TrackedLock(
        name="ratchet",
        path_rel="frob-ratchet.lock.json",
        code_glob="src/frob/**/*.py",
    ),
)


# frob:doc docs/modules/gates.md#public-api
# frob:tests tests/unit/gates/test_lock_producer.py::TestAgainstThisRepo.test_runs_clean_against_this_repo kind="unit"  # noqa: E501
class LockProducerStatus(BaseModel):
    """One lock's measured producer state (T-2999): age, churn since its
    last stamp, and the verdict `frob status`/a consuming gate should
    show a reader -- `UNMEASURED` (no committed lock, or git history for
    it could not be read; never fabricated), `PINNED` (a positive `pin`
    declaration exists), `ABANDONED` (unpinned and `code_commits_since`
    is at or above `ABANDONED_CODE_COMMIT_THRESHOLD`), or `FRESH`
    (anything else)."""

    model_config = {}

    name: str
    path_rel: str
    exists: bool
    last_stamp_commit: str | None
    last_stamp_date: str | None
    commits_since: int | None
    code_commits_since: int | None
    pin: LockPin | None
    verdict: Literal["UNMEASURED", "PINNED", "ABANDONED", "FRESH"]


def _load_pin(root: Path, path_rel: str) -> LockPin | None:
    """The lock's own `"pin"` object, or `None` if absent/malformed/the
    file does not parse -- a malformed pin is treated as no pin (never a
    crash, never a silently-trusted one), so an accidentally-corrupted
    pin field cannot suppress a genuine abandonment signal."""
    path = root / path_rel
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log.debug("_load_pin: %s unreadable: %s", path, exc)
        return None
    raw = doc.get("pin") if isinstance(doc, dict) else None
    if not isinstance(raw, dict):
        return None
    reason = raw.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        return None
    ticket = raw.get("ticket")
    return LockPin(reason=reason, ticket=ticket if isinstance(ticket, str) else None)


def _last_commit_touching(root: Path, path_rel: str) -> tuple[str | None, str | None]:
    """`(sha, iso_date)` of the most recent commit that touched `path_rel`,
    or `(None, None)` if the file has never been committed or `git log`
    could not be read (deny-by-default: an unreadable history reads as
    "cannot measure", never as "just stamped")."""
    result = run_argv(
        ("git", "-C", str(root), "log", "-1", "--format=%H%x1f%cI", "--", path_rel)
    )
    if result.is_err:
        return None, None
    line = result.danger_ok.stdout.strip()
    if not line:
        return None, None
    parts = line.split("\x1f")
    if len(parts) != 2:
        return None, None
    return parts[0], parts[1]


def _commit_count(
    root: Path, rev_range: str, pathspec: str | None = None
) -> int | None:
    """`git rev-list --count <rev_range> [-- <pathspec>]`, or `None` if the
    command failed or produced non-numeric output."""
    argv = ["git", "-C", str(root), "rev-list", "--count", rev_range]
    if pathspec is not None:
        argv.extend(("--", pathspec))
    result = run_argv(tuple(argv))
    if result.is_err:
        return None
    text = result.danger_ok.stdout.strip()
    if not text.isdigit():
        return None
    return int(text)


# frob:doc docs/modules/gates.md#public-api
# frob:tests tests/unit/gates/test_lock_producer.py::TestProducerStatusVerdicts \
# kind="unit"
# frob:ticket T-2999
def producer_status(root: Path, lock: TrackedLock) -> LockProducerStatus:
    """One `TrackedLock`'s measured `LockProducerStatus` against `root`'s
    real git history -- the single computation `frob status`'s baseline
    section and any consuming gate's loud-failure check both read, so
    the verdict is identical everywhere it is shown."""
    path = root / lock.path_rel
    exists = path.is_file()
    pin = _load_pin(root, lock.path_rel)
    sha, iso_date = _last_commit_touching(root, lock.path_rel)
    if not exists or sha is None:
        return LockProducerStatus(
            name=lock.name,
            path_rel=lock.path_rel,
            exists=exists,
            last_stamp_commit=None,
            last_stamp_date=None,
            commits_since=None,
            code_commits_since=None,
            pin=pin,
            verdict="UNMEASURED",
        )
    commits_since = _commit_count(root, f"{sha}..HEAD")
    code_commits_since = _commit_count(root, f"{sha}..HEAD", lock.code_glob)
    if pin is not None:
        verdict: Literal["UNMEASURED", "PINNED", "ABANDONED", "FRESH"] = "PINNED"
    elif code_commits_since is None or commits_since is None:
        verdict = "UNMEASURED"
    elif code_commits_since >= ABANDONED_CODE_COMMIT_THRESHOLD:
        verdict = "ABANDONED"
    else:
        verdict = "FRESH"
    return LockProducerStatus(
        name=lock.name,
        path_rel=lock.path_rel,
        exists=exists,
        last_stamp_commit=sha,
        last_stamp_date=iso_date,
        commits_since=commits_since,
        code_commits_since=code_commits_since,
        pin=pin,
        verdict=verdict,
    )


# frob:doc docs/modules/gates.md#public-api
# frob:tests \
# tests/unit/gates/test_lock_producer.py::TestAgainstThisRepo.test_runs_clean_against_t\
# his_repo kind="unit"
# frob:ticket T-2999
def all_producer_statuses(root: Path) -> tuple[LockProducerStatus, ...]:
    """`producer_status` for every lock in `KNOWN_LOCKS`, in order -- the
    one call `frob status` and `frob check`'s loud-failure wiring both
    make, so a fourth tracked lock only needs adding to `KNOWN_LOCKS`
    once."""
    return tuple(producer_status(root, lock) for lock in KNOWN_LOCKS)
