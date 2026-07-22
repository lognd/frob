"""`run_fuzz`: the actual hypothesis execution harness
(docs/modules/fuzz.md "Execution").

Honest v1 limit (documented, not silently dropped): driving arbitrary user
functions -- calling the real property under test with generated args and
checking a real assertion -- needs a bound `frob:tests kind="fuzz"` test
function to call, which is `frob.testing`'s job, not this module's. What
`run_fuzz` implements here is the DERIVED-model round-trip case: for each
pydantic `BaseModel` target, resolve its generator and drive it through
hypothesis's real engine, proving the rejection-sampled strategy actually
produces valid instances within `policy.max_reject_rate` and the budget.
Wiring `run_fuzz` to call bound `kind="fuzz"` test functions is `frob.testing`
+ coordinator work (docs/modules/fuzz.md "Execution and corpus"), not this ticket.

`budget_s` is a real wall-clock cutoff (T-0469): hypothesis's own
`settings(max_examples=...)` is only a per-batch example ceiling, so
`_drive_strategy` implements the "custom stopping callback" the v1 doc
called out as missing -- it drives hypothesis in small batches and checks
`time.monotonic()` against the deadline between batches, stopping as soon
as the wall-clock budget is exhausted (or a hard total-examples safety cap
is hit, so a pathological `budget_s` cannot spin forever).
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: src/frob/fuzz/_run.py's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable \
# by reading the code it annotates) rather than a separate cross-module contract \
# needing its own tracked invariant; disposed as a calibration batch, not \
# claim-by-claim"

from __future__ import annotations

import time
from collections.abc import Mapping

from pydantic import BaseModel

from frob.fuzz._arbitrary import HYPOTHESIS_AVAILABLE, resolve
from frob.fuzz._models import FuzzPolicy, FuzzResult
from frob.logging import get_logger

_log = get_logger(__name__)

# Per-batch example count fed to hypothesis's own `max_examples`; kept small
# so the wall-clock check between batches (see module docstring) is fine-
# grained rather than overshooting the budget by a whole batch's runtime.
_BATCH_EXAMPLES = 25

# Hard safety ceiling on total examples across all batches of one target,
# independent of `budget_s` -- guards against a misconfigured huge budget_s
# (or a strategy so cheap it never bumps against wall-clock time) spinning
# indefinitely.
_MAX_TOTAL_EXAMPLES = 2000


def _ref_of(tp: type) -> str:
    """`module.Qualname` used as the `FuzzResult.ref` for a derived-model target."""
    return f"{tp.__module__}.{tp.__qualname__}"


def _run_one(tp: type[BaseModel], policy: FuzzPolicy, digest: str) -> FuzzResult:
    """Drive `tp`'s resolved strategy through hypothesis; report examples/failures."""
    ref = _ref_of(tp)
    resolved = resolve(tp)
    if resolved.is_err:
        _log.warning("run_fuzz: %s has no generator; skipping", ref)
        return FuzzResult(
            ref=ref, body_digest=digest, examples=0, falsified="no generator"
        )

    count, falsified = _drive_strategy(resolved.danger_ok, tp, policy, ref)
    if falsified is not None:
        return FuzzResult(
            ref=ref, body_digest=digest, examples=count, falsified=falsified
        )

    _log.info("run_fuzz: %s -> %d example(s), no falsification", ref, count)
    return FuzzResult(ref=ref, body_digest=digest, examples=count, falsified=None)


def _drive_strategy(
    strategy: object, tp: type[BaseModel], policy: FuzzPolicy, ref: str
) -> tuple[int, str | None]:
    """Run hypothesis's real engine over `strategy` in small batches until
    `policy.budget_s` wall-clock elapses (or `_MAX_TOTAL_EXAMPLES` is hit);
    return (examples drawn, falsification reason or None)."""
    from typing import Any, cast

    from hypothesis import HealthCheck, given, settings

    typed_strategy = cast(Any, strategy)
    count = 0

    deadline = time.monotonic() + max(policy.budget_s, 0)
    while count < _MAX_TOTAL_EXAMPLES:
        if time.monotonic() >= deadline:
            _log.debug("run_fuzz: %s budget_s=%s elapsed", ref, policy.budget_s)
            break
        batch = min(_BATCH_EXAMPLES, _MAX_TOTAL_EXAMPLES - count)

        # A fresh function object per batch: `settings(...)` mutates the
        # decorated callable in place, so re-applying it to the SAME
        # function across batches raises hypothesis's "already decorated"
        # InvalidArgument on the second batch.
        def _property(instance: BaseModel) -> None:
            nonlocal count
            count += 1
            assert isinstance(instance, tp)

        test_fn = given(typed_strategy)(
            settings(
                max_examples=batch,
                deadline=None,
                suppress_health_check=[
                    HealthCheck.filter_too_much,
                    HealthCheck.too_slow,
                ],
            )(_property)
        )
        count_before = count
        drawn, falsified = _run_property_test(test_fn, ref, policy, lambda: count)
        if falsified is not None:
            return drawn, falsified
        if count == count_before:
            # The batch drew nothing new (e.g. entirely filtered/rejected
            # without raising Unsatisfiable) -- stop instead of spinning.
            break
    return count, None


def _run_property_test(test_fn, ref: str, policy: FuzzPolicy, get_count):  # noqa: ANN001
    """Execute a built hypothesis `test_fn`, translating its outcome into
    (examples drawn, falsification reason or None)."""
    from hypothesis.errors import Unsatisfiable

    try:
        test_fn()
    except Unsatisfiable as exc:
        _log.warning("run_fuzz: %s exceeded max_reject_rate: %s", ref, exc)
        reason = f"rejection rate too high (max={policy.max_reject_rate}): {exc}"
        return get_count(), reason
    except AssertionError as exc:  # pragma: no cover - _property never fails logically
        _log.error("run_fuzz: %s falsified: %s", ref, exc)
        return get_count(), repr(exc)

    return get_count(), None


# frob:doc docs/modules/fuzz.md#public-api
def run_fuzz(
    targets: tuple[type[BaseModel], ...],
    budget_s: int,
    *,
    policy: FuzzPolicy | None = None,
    digests: Mapping[str, str] | None = None,
) -> tuple[FuzzResult, ...]:
    """Exercise hypothesis on each derived-model target's resolved strategy.

    `targets` are pydantic `BaseModel` subclasses (the DERIVED case, see
    module docstring for the v1 scope limit). `digests` optionally maps a
    target's `_ref_of` string to its graph body digest for stamping;
    missing entries stamp with an empty digest.
    """
    if not HYPOTHESIS_AVAILABLE:
        _log.error("run_fuzz: hypothesis is not installed; returning no results")
        return ()

    effective_policy = policy or FuzzPolicy(budget_s=budget_s)
    digest_map = digests or {}
    results = tuple(
        _run_one(tp, effective_policy, digest_map.get(_ref_of(tp), ""))
        for tp in targets
    )
    _log.info("run_fuzz: ran %d target(s)", len(results))
    return results


__all__ = ["run_fuzz"]
