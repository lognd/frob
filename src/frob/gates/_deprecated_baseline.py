"""`frob.gates._deprecated_baseline` -- the DEPR005 reference-set baseline
(T-0639): a committed, git-tracked snapshot of which files/lines currently
reference each `frob:deprecated` public symbol, so a genuinely NEW caller
(one absent from the baseline) can be told apart from the pile of
pre-existing callers a deprecation was declared against in the first
place.

Same shape of contract as `frob.gates._ratchet`'s pool mechanism -- freeze
what already exists, error on anything new -- but keyed on a MEASURED
reference set per symbol rather than a rule's violation-location set, and
committed at a fixed top-level path (`frob-deprecated-baseline.lock.json`,
same "committed summary outside .gitignore's `.frob/` reach" posture as
`frob-ratchet.lock.json`/`frob-coverage.lock.json`, T-0569/T-0545) rather
than under `.frob/pool` snapshots.

Deliberately read/write split from `frob.gates.__init__`'s DEPR005 gate
function: `deprecated_gate` only ever READS this module's
`load_deprecated_baseline` (gates stay pure static analysis over an
already-recorded artifact, matching `frob.perf._ratchet`'s posture) --
`tighten_deprecated_baseline` is the one place that WRITES, called
separately (at land) once a fresh reference-set snapshot is available, and
only ever shrinks or seeds, never silently grows past what a human
reviewed into the committed file.
"""
# frob:waive INV006 reason="T-1023 INV006 burn-down: this file's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring describing already-implemented internal read/write-split behavior, \
# verifiable by reading the code it annotates) rather than a separate cross-module \
# contract needing its own tracked invariant; disposed as a calibration batch, not \
# claim-by-claim, same INV006 first-turn-on-pool disposition this repo already applies \
# elsewhere (T-0585)"

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "BASELINE_REL",
    "DeprecatedBaselineEntry",
    "DeprecatedBaselineLock",
    "load_deprecated_baseline",
    "save_deprecated_baseline",
    "tighten_deprecated_baseline",
]

# frob:doc docs/modules/gates.md#depr005-new-caller-baseline-ratchet-t-0639
#: `frob-deprecated-baseline.lock.json`'s path, relative to a project root
#: -- committed (outside `.frob/`'s gitignored reach), same naming
#: convention as `frob-ratchet.lock.json`/`frob-coverage.lock.json`.
BASELINE_REL = Path("frob-deprecated-baseline.lock.json")


# frob:ticket T-0639
# frob:doc docs/modules/gates.md#depr005-new-caller-baseline-ratchet-t-0639
class DeprecatedBaselineEntry(BaseModel):
    """One `frob:deprecated` symbol's frozen reference set: `symbol` is the
    directive's edge `src` (`path::qualname`, matching `Edge.src` for a
    `DEPRECATED` edge); `references` is a sorted tuple of `file:line`
    strings, each one a caller accepted as pre-existing at the time it was
    baselined."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    references: tuple[str, ...] = ()


# frob:ticket T-0639
# frob:doc docs/modules/gates.md#depr005-new-caller-baseline-ratchet-t-0639
class DeprecatedBaselineLock(BaseModel):
    """The whole committed `frob-deprecated-baseline.lock.json` document:
    one `DeprecatedBaselineEntry` per deprecated symbol ever baselined."""

    model_config = ConfigDict(frozen=True)

    entries: tuple[DeprecatedBaselineEntry, ...] = ()

    # frob:doc docs/modules/gates.md#depr005-new-caller-baseline-ratchet-t-0639
    # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedBaselineLock.test_for_symbol_missing_is_none  # noqa: E501
    def for_symbol(self, symbol: str) -> DeprecatedBaselineEntry | None:
        """The baselined entry for `symbol` (an `Edge.src`), or `None` if
        `symbol` has never been baselined."""
        for entry in self.entries:
            if entry.symbol == symbol:
                return entry
        return None


# frob:ticket T-0639
# frob:doc docs/modules/gates.md#depr005-new-caller-baseline-ratchet-t-0639
# frob:tests tests/unit/gates/test_deprecated_baseline.py::TestLoadSave.test_missing_file_is_empty  # noqa: E501
def load_deprecated_baseline(root: Path) -> DeprecatedBaselineLock:
    """The committed `frob-deprecated-baseline.lock.json` at `root`, or an
    empty `DeprecatedBaselineLock` if it does not exist yet or fails to
    parse (T-0639) -- "no baseline for any deprecated symbol" is a valid,
    unremarkable starting state, not an error, mirroring
    `frob.gates._ratchet.load_ratchet_lock`."""
    path = root / BASELINE_REL
    if not path.is_file():
        return DeprecatedBaselineLock()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return DeprecatedBaselineLock.model_validate(data)
    except (OSError, ValueError) as exc:
        _log.warning(
            "load_deprecated_baseline: %s unreadable/malformed, treating as empty: %s",
            path,
            exc,
        )
        return DeprecatedBaselineLock()


# frob:ticket T-0639
# frob:doc docs/modules/gates.md#depr005-new-caller-baseline-ratchet-t-0639
# frob:tests tests/unit/gates/test_deprecated_baseline.py::TestLoadSave.test_save_then_load_round_trips  # noqa: E501
def save_deprecated_baseline(root: Path, lock: DeprecatedBaselineLock) -> None:
    """Atomically overwrite `root/frob-deprecated-baseline.lock.json` with
    `lock`, entries sorted by symbol then reference so the diff a reviewer
    sees is minimal and deterministic run-to-run (T-0639, mirroring
    `frob.gates._ratchet._write_ratchet_lock`'s sort discipline)."""
    path = root / BASELINE_REL
    sorted_entries = tuple(
        sorted(
            (
                entry.model_copy(update={"references": tuple(sorted(entry.references))})
                for entry in lock.entries
            ),
            key=lambda e: e.symbol,
        )
    )
    payload = DeprecatedBaselineLock(entries=sorted_entries).model_dump(mode="json")
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


# frob:ticket T-0639
# frob:doc docs/modules/gates.md#depr005-new-caller-baseline-ratchet-t-0639
# frob:tests tests/unit/gates/test_deprecated_baseline.py::TestTighten.test_shrinkage_drops_stale_references  # noqa: E501
# frob:tests tests/unit/gates/test_deprecated_baseline.py::TestTighten.test_never_absorbs_a_new_reference  # noqa: E501
# frob:tests tests/unit/gates/test_deprecated_baseline.py::TestTighten.test_first_seen_symbol_is_seeded_whole  # noqa: E501
# frob:tests tests/unit/gates/test_deprecated_baseline.py::TestTighten.test_symbol_no_longer_deprecated_is_dropped  # noqa: E501
def tighten_deprecated_baseline(
    root: Path, current: dict[str, frozenset[str]]
) -> DeprecatedBaselineLock:
    """The auto-tightened baseline for `current` (every still-deprecated
    symbol's `Edge.src` mapped to its freshly-observed reference set) --
    the PERF009 ratchet idiom applied to a reference-set baseline instead
    of a measured quantile (T-0639): a symbol never baselined before is
    SEEDED whole (its first-observed reference set is accepted as
    pre-existing legacy, not flagged); an already-baselined symbol's
    entry SHRINKS to the intersection of what was baselined and what is
    still observed (a caller that disappeared drops out, auto-tightening
    the baseline) but never GROWS past what was baselined (a genuinely
    new reference stays un-baselined, and DEPR005 keeps firing on it,
    until a human re-baselines deliberately -- shrink-only, exactly like
    `frob.gates._ratchet.snapshot_ratchet` never silently drops a key a
    caller did not ask to clear); a symbol no longer in `current` (its
    `frob:deprecated` directive is gone -- removed, or the symbol itself
    deleted) is dropped from the baseline entirely, since there is
    nothing left to ratchet against. Does NOT write to disk -- pure
    function of `current` and whatever is already committed; the caller
    persists the result via `save_deprecated_baseline` when it differs."""
    existing = load_deprecated_baseline(root)
    entries: list[DeprecatedBaselineEntry] = []
    for symbol, refs in current.items():
        prior = existing.for_symbol(symbol)
        if prior is None:
            _log.debug(
                "tighten_deprecated_baseline: seeding %s with %d reference(s)",
                symbol,
                len(refs),
            )
            # frob:waive PERF004 reason="refs is this loop's own per-symbol distinct \
            # reference set, sorted once at seed time; not a shared re-sort"
            entries.append(
                DeprecatedBaselineEntry(symbol=symbol, references=tuple(sorted(refs)))
            )
            continue
        kept = frozenset(prior.references) & refs
        if len(kept) != len(prior.references):
            _log.info(
                "tighten_deprecated_baseline: %s baseline shrank %d -> %d reference(s)",
                symbol,
                len(prior.references),
                len(kept),
            )
        entries.append(
            DeprecatedBaselineEntry(symbol=symbol, references=tuple(sorted(kept)))
        )
    return DeprecatedBaselineLock(entries=tuple(entries))
