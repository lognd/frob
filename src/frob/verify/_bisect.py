# frob:ticket T-1691
"""T-1691: Tier 3 of the attribution ladder -- the fallback for a finding
the symbolic tier (`frob.verify._attribution`) honestly could not pin to
one commit. Bisects the batch's ordered candidate commits over the SINGLE
failing finding identity: `log2(N)` scoped re-verifications, each re-
checking only that one finding, rather than `N` full gate passes.
Scoping is what keeps the fallback cheaper than the batching it exists
to rescue -- a full check per candidate would make the whole epic a wash
on any batch that ever goes red (see this module's own ticket body).

Each candidate is verified in a throwaway, DETACHED snapshot worktree
(`frob.app.ticket_runner._land_cmd._spawn_baseline_snapshot_worktree`/
`_remove_baseline_snapshot_worktree`, T-1463's own isolation machinery,
reused here rather than reimplemented -- the ticket body's own explicit
instruction) -- `root`, the shared checkout other agents may be actively
landing against, is NEVER moved, checked out, or otherwise mutated by
this module.

BOUNDED, NEVER SILENT. A step budget and a wall-clock budget, both
caller-configurable, both logged when hit. Exhausting either produces an
`UNATTRIBUTED` `BisectOutcome` naming EVERY original candidate commit
(not just the still-unresolved half) -- "cannot verify" is never
"verified", and a search that narrowed some candidates out before
exhausting its budget has not actually PROVEN those candidates clean,
only left them unchecked; only an outcome that names the full original
set is an honest one. Same posture for a candidate whose snapshot
worktree cannot even be spawned, or whose verify callback itself returns
`Err` (an inconclusive step): both degrade to the same bounded,
whole-batch `UNATTRIBUTED` outcome rather than guessing which half of
the search space to trust.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import Err, Ok, Result
from typani.error_set import ErrorSet

from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/tickets-verify-sweep.md#bisect-attribution-t-1691
# frob:tests \
# tests/unit/verify/test_bisect.py::TestBisectUnattributedFinding::test_empty_candidate\
# s_refuses kind="unit"
class BisectError(ErrorSet):
    """Fatal, pre-search refusals `bisect_unattributed_finding` returns --
    never raised for a mid-search inconclusive step, which degrades to an
    `UNATTRIBUTED` `BisectOutcome` instead (see module docstring)."""

    NoCandidates = "the candidate commit list is empty -- nothing to bisect"
    NonPositiveBudget = "step_budget and wall_clock_budget_s must both be positive"


#: Verifies whether `finding_id` reproduces at `commit` inside `snapshot`
#: (a throwaway detached worktree checked out at that commit): `Ok(True)`
#: the finding is present (this commit is "bad" -- the culprit is at or
#: before it), `Ok(False)` the finding is absent ("good" -- the culprit
#: is strictly after it), `Err(...)` the check itself could not produce a
#: verdict (any string reason; logged, then treated as a bounded search
#: exhaustion per the module docstring's "cannot verify is never
#: verified" invariant).
VerifyAtCommit = Callable[[Path, str], Result[bool, str]]


# frob:doc docs/modules/tickets-verify-sweep.md#bisect-attribution-t-1691
# frob:tests \
# tests/unit/verify/test_bisect.py::TestBisectUnattributedFinding::test_converges_to_th\
# e_known_culprit_within_log2_n_steps kind="unit"
class BisectOutcome(BaseModel):
    """Result of one `bisect_unattributed_finding` run over `candidates`
    for `finding_id` (T-1691): exactly one of `culprit_commit` (search
    isolated a single commit) or `unattributed_candidates` (the batch's
    full original candidate list, on a bounded-exhaustion or
    inconclusive-step degrade) is populated -- never both, never
    neither. Frozen/`extra=\"forbid\"` per the attribution epic's
    persisted-record contract (this module's own ticket body)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    finding_id: str
    culprit_commit: str | None = None
    unattributed_candidates: tuple[str, ...] = ()
    steps_used: int = 0

    # frob:doc docs/modules/tickets-verify-sweep.md#bisect-attribution-t-1691
    @property
    def is_attributed(self) -> bool:
        """True when the bisect isolated a single culprit commit rather
        than degrading to a whole-batch `UNATTRIBUTED` outcome."""
        return self.culprit_commit is not None


def _unattributed(
    finding_id: str, candidates: Sequence[str], steps_used: int, reason: str
) -> BisectOutcome:
    """Build the bounded-exhaustion/inconclusive-step `BisectOutcome`
    (T-1691): logs `reason` at WARNING (the module docstring's own "both
    caller-configurable budgets, both logged when hit" contract, plus the
    inconclusive-verify-callback degrade this same helper also covers)
    before returning the outcome, naming EVERY original candidate --
    never just the still-unresolved half, per the module docstring's
    "cannot verify is never verified" reasoning."""
    _log.warning(
        "bisect: %s UNATTRIBUTED after %d step(s) over %d candidate(s): %s",
        finding_id,
        steps_used,
        len(candidates),
        reason,
    )
    return BisectOutcome(
        finding_id=finding_id,
        unattributed_candidates=tuple(candidates),
        steps_used=steps_used,
    )


# frob:ticket T-1691
class _BisectStep:
    """One bisect midpoint check's outcome (T-1691, extracted out of
    `bisect_unattributed_finding` for ARCH001 -- the search loop and the
    single-step git/verify mechanics are two distinct concerns, and this
    is the seam between them): either `narrowed` is set to the new
    `(low, high)` range, or `unattributed_reason` names why the step
    could not produce one -- never both."""

    __slots__ = ("narrowed", "unattributed_reason")

    def __init__(
        self,
        *,
        narrowed: tuple[int, int] | None = None,
        unattributed_reason: str | None = None,
    ) -> None:
        self.narrowed = narrowed
        self.unattributed_reason = unattributed_reason


def _run_one_bisect_step(
    root: Path,
    commit: str,
    low: int,
    high: int,
    mid: int,
    verify_fn: VerifyAtCommit,
) -> _BisectStep:
    """Spawn a detached snapshot worktree at `commit` (T-1463's own
    isolation machinery, reused not reimplemented -- see module
    docstring), call `verify_fn` against it, and always remove the
    snapshot again (`finally`) regardless of the verdict -- `root`
    itself is never touched. A missing snapshot or an `Err` verdict both
    return an `unattributed_reason` rather than raising; only a real
    Boolean verdict narrows the search range."""
    from frob.app.ticket_runner._land_cmd import (
        _remove_baseline_snapshot_worktree,
        _spawn_baseline_snapshot_worktree,
    )

    snapshot = _spawn_baseline_snapshot_worktree(root, commit)
    if snapshot is None:
        reason = f"snapshot worktree unavailable at {commit}"
        return _BisectStep(unattributed_reason=reason)
    try:
        verdict = verify_fn(snapshot, commit)
    finally:
        _remove_baseline_snapshot_worktree(root, snapshot)

    if verdict.is_err:
        reason = f"verify_fn inconclusive at {commit}: {verdict.danger_err}"
        return _BisectStep(unattributed_reason=reason)
    bad = verdict.danger_ok
    return _BisectStep(narrowed=(low, mid) if bad else (mid + 1, high))


# frob:ticket T-1691
def _run_bisect_search(
    root: Path,
    finding_id: str,
    ordered: tuple[str, ...],
    verify_fn: VerifyAtCommit,
    step_budget: int,
    deadline: float,
) -> BisectOutcome:
    """The actual bisect loop, split out of `bisect_unattributed_finding`
    for ARCH001 (T-1691) -- that function's own remaining job is just the
    pre-search `Err` refusals plus this call. Classic index bisect over
    `[0, len(ordered) - 1]`: the midpoint is checked
    (`_run_one_bisect_step`); a "bad" verdict narrows to `[0, mid]`, a
    "good" verdict narrows to `[mid + 1, high]`. Converges to a single
    index in `ceil(log2(len(ordered)))` steps -- the module's own
    acceptance criterion. Either budget tripping, or a step returning no
    `narrowed` range (a snapshot/verify inconclusive), degrades to the
    bounded whole-batch `UNATTRIBUTED` outcome (`_unattributed`) rather
    than continuing on a guess."""
    low, high = 0, len(ordered) - 1
    steps = 0
    _log.info(
        "bisect: %s starting over %d candidate(s) (%s .. %s), step_budget=%d",
        finding_id,
        len(ordered),
        ordered[0],
        ordered[-1],
        step_budget,
    )

    while low < high:
        if steps >= step_budget:
            return _unattributed(
                finding_id, ordered, steps, f"step budget ({step_budget}) exhausted"
            )
        if time.monotonic() >= deadline:
            return _unattributed(
                finding_id, ordered, steps, "wall-clock budget exhausted"
            )

        mid = (low + high) // 2
        commit = ordered[mid]
        steps += 1
        step = _run_one_bisect_step(root, commit, low, high, mid, verify_fn)
        if step.narrowed is None:
            reason = step.unattributed_reason or ""
            return _unattributed(finding_id, ordered, steps, reason)
        low, high = step.narrowed
        _log.debug(
            "bisect: %s step %d/%d at %s -> range now [%d, %d]",
            finding_id,
            steps,
            step_budget,
            commit,
            low,
            high,
        )

    culprit = ordered[low]
    _log.info(
        "bisect: %s converged to %s in %d step(s) over %d candidate(s)",
        finding_id,
        culprit,
        steps,
        len(ordered),
    )
    return BisectOutcome(
        finding_id=finding_id, culprit_commit=culprit, steps_used=steps
    )


# frob:doc docs/modules/tickets-verify-sweep.md#bisect-attribution-t-1691
# frob:tests tests/unit/verify/test_bisect.py::TestBisectUnattributedFinding kind="unit"
def bisect_unattributed_finding(
    root: Path,
    finding_id: str,
    candidates: Sequence[str],
    verify_fn: VerifyAtCommit,
    *,
    step_budget: int = 20,
    wall_clock_budget_s: float = 300.0,
) -> Result[BisectOutcome, BisectError]:
    """Binary-search `candidates` (ordered oldest-first; the LAST entry is
    the batch's own known-bad tip) for the single commit that introduced
    `finding_id`, using `verify_fn` scoped to that one finding at each
    midpoint instead of a full gate pass (T-1691's whole point -- see the
    module docstring). The search itself lives in `_run_bisect_search`
    (ARCH001 split); this function owns only the pre-search refusals.

    `Err(BisectError.NoCandidates)` for an empty `candidates` (nothing to
    search) or a non-positive budget -- both refused before any git or
    verify call, distinct from every OTHER outcome, which is a valid
    `Ok(BisectOutcome)` (attributed OR bounded-unattributed) since an
    exhausted/inconclusive search is a documented result, not a caller
    error."""
    if not candidates:
        return Err(BisectError.NoCandidates)
    if step_budget <= 0 or wall_clock_budget_s <= 0:
        return Err(BisectError.NonPositiveBudget)

    deadline = time.monotonic() + wall_clock_budget_s
    outcome = _run_bisect_search(
        root, finding_id, tuple(candidates), verify_fn, step_budget, deadline
    )
    return Ok(outcome)


__all__ = [
    "BisectError",
    "BisectOutcome",
    "VerifyAtCommit",
    "bisect_unattributed_finding",
]
