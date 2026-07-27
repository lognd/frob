"""`frob.stats._sketch` -- log-bucket (DDSketch-style) quantile sketch
(T-0711, child of EPIC T-0709's hot-graph line).

A pure, allocation-cheap value type: no I/O, no sqlite, no `frob.perf`
dependency. `frob.perf._sketch_store` (this ticket's other half) is the
sqlite-backed store that persists these keyed by hot-graph section and
layers decayed merge across runs on top; this module only defines the
sketch itself and its algebra (`add_value`/`merge_sketches`/
`decay_sketch`/`quantile`) so it stays reusable by any future consumer
that wants a bounded-error quantile summary over a weighted value stream,
not just the hot-graph.

**The algorithm** is the standard DDSketch fixed-relative-accuracy
histogram (Masson/Rim/Lee, VLDB 2019): values are mapped onto
log-scale buckets sized so that any two values landing in the same
bucket are within a relative factor of `gamma = (1+alpha)/(1-alpha)`
of each other, and a bucket's read-time point estimate (`_bucket_value`,
the bucket's log-midpoint `2*gamma**index/(gamma+1)`) is therefore within
`alpha` relative error of every value that bucket ever received --
independent of the input distribution's shape (unlike t-digest/moment-
based sketches, which degrade on multi-modal inputs; DDSketch is exact
per-bucket by construction, which is why this ticket picked it for a
"bimodal latencies" acceptance criterion). Buckets are a sparse
`dict[int, float]` (bucket index -> accumulated weight), so a sketch over
a small number of distinct magnitude clusters (the bimodal case) stays a
handful of entries regardless of how many samples fed it -- the <1KB
serialized-size acceptance criterion falls out of that sparsity, not a
separate compaction step.

Quantiles are NEVER stored -- `quantile(sketch, q)` computes p10/p50/p90/
anything on demand from the bucket weights at read time, per the ticket's
plan ("deciles/any-quantile computed at read time, never stored").
"""
# frob:waive INV006 reason="T-0711: this module's 'only' usages (e.g. \
# 'Quantiles are NEVER stored', 'buckets are ... never stored') are \
# source-level design-rationale prose describing already-implemented \
# internal behavior (verifiable by reading quantile()/add_value() below), \
# not a separate cross-module contract needing its own tracked invariant; \
# same calibration-batch disposition as the T-0585 INV006 pool"
# frob:waive ARCH102 reason="6 of 10 exports form one connected cluster \
# around the sketch's bucket algebra (_bucket_index/_bucket_value/_gamma/ \
# add_value/quantile/total_weight); the 4 outliers (new_sketch, \
# merge_sketches, decay_sketch, sketch_size_bytes) are lifecycle operations \
# on the exact same QuantileSketch value type this docstring describes -- \
# they read/write its bucket dict by field access rather than calling the \
# algebra helpers directly, so the naming/usage heuristic cannot see the \
# real single-value-type cohesion this module's own docstring names"

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "DEFAULT_ALPHA",
    "QuantileSketch",
    "add_value",
    "decay_sketch",
    "merge_sketches",
    "new_sketch",
    "quantile",
    "sketch_size_bytes",
    "total_weight",
]

#: Default DDSketch relative-error target (T-0711's plan: "tunable relative-
#: error alpha (frob.toml, default ~2 percent)") -- `frob.perf._sketch_store.
#: SketchStoreConfig.alpha` is the frob.toml-configurable knob that feeds
#: this default into `new_sketch` at the store layer; this module's own
#: default exists so `new_sketch()` is usable standalone in tests/tools
#: with no config plumbing required.
# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
DEFAULT_ALPHA = 0.02

#: Below this accumulated bucket weight, `decay_sketch` drops the bucket
#: entirely rather than keeping an ever-shrinking float around forever --
#: keeps a long-decayed sketch's serialized size from creeping back up
#: with numerically-irrelevant near-zero entries.
_MIN_BUCKET_WEIGHT = 1e-9


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
class QuantileSketch(BaseModel):
    """A DDSketch-style log-bucket quantile summary at relative-error
    `alpha`: `buckets` maps a log-scale bucket index to the accumulated
    weight of every value that landed in it; `zero_count` is a dedicated
    bucket for exact `0.0` values (undefined on the log scale otherwise).
    Frozen/value-typed like the rest of this project's data shapes --
    every mutating operation (`add_value`/`merge_sketches`/`decay_sketch`)
    returns a NEW `QuantileSketch` rather than mutating in place, so a
    sketch can be safely shared/cached without defensive copies."""

    model_config = ConfigDict(frozen=True)

    alpha: float = DEFAULT_ALPHA
    buckets: dict[int, float] = {}
    zero_count: float = 0.0


def _gamma(alpha: float) -> float:
    """The DDSketch bucket growth ratio for `alpha`: any two values in the
    same bucket differ by at most this factor, and the bucket's read-time
    point estimate is within `alpha` relative error of both."""
    return (1.0 + alpha) / (1.0 - alpha)


def _bucket_index(value: float, alpha: float) -> int:
    """The log-scale bucket a positive `value` falls into at `alpha`."""
    return math.ceil(math.log(value) / math.log(_gamma(alpha)))


def _bucket_value(index: int, alpha: float) -> float:
    """The point estimate DDSketch reads back for any value stored in
    bucket `index` -- the bucket's log-midpoint, guaranteed within `alpha`
    relative error of every value that actually landed there."""
    gamma = _gamma(alpha)
    return 2.0 * (gamma**index) / (gamma + 1.0)


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
# frob:tests tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra.test_quantile_on_empty_sketch_is_zero  # noqa: E501
def new_sketch(alpha: float = DEFAULT_ALPHA) -> QuantileSketch:
    """An empty sketch at relative-error `alpha`."""
    return QuantileSketch(alpha=alpha)


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
# frob:tests tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra.test_negative_value_is_dropped_not_raised  # noqa: E501
# frob:tests tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra.test_zero_values_land_in_zero_count_not_a_bucket  # noqa: E501
def add_value(
    sketch: QuantileSketch, value: float, weight: float = 1.0
) -> QuantileSketch:
    """`sketch` with one observation of `value` (weight `weight`) folded
    in. `value` must be non-negative (this sketch models latencies/
    durations, never signed quantities); `0.0` goes to the dedicated
    `zero_count` bucket since it has no position on the log scale."""
    if value < 0:
        _log.warning(
            "sketch: dropped negative value %r (this sketch is non-negative-only)",
            value,
        )
        return sketch
    if value == 0.0:
        return sketch.model_copy(update={"zero_count": sketch.zero_count + weight})
    index = _bucket_index(value, sketch.alpha)
    buckets = dict(sketch.buckets)
    buckets[index] = buckets.get(index, 0.0) + weight
    return sketch.model_copy(update={"buckets": buckets})


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
# frob:tests tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra.test_merge_is_associative  # noqa: E501
# frob:tests tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra.test_merge_is_commutative  # noqa: E501
# frob:tests tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra.test_merge_rejects_mismatched_alpha  # noqa: E501
def merge_sketches(a: QuantileSketch, b: QuantileSketch) -> QuantileSketch:
    """Bucket-wise sum of `a` and `b` -- ASSOCIATIVE and COMMUTATIVE by
    construction (plain per-bucket float addition), which is the whole
    point of a mergeable sketch: `merge(merge(a, b), c) ==
    merge(a, merge(b, c))` regardless of grouping, so partial per-run
    sketches can be combined in any order/parallelism without changing
    the result. `a`/`b` must share the same `alpha` (merging sketches
    built at different relative-error targets would silently blend
    incompatible bucket boundaries) -- raises `ValueError` otherwise,
    never a silent wrong-answer merge."""
    if a.alpha != b.alpha:
        raise ValueError(
            f"cannot merge sketches at different alpha: {a.alpha} != {b.alpha}"
        )
    merged = dict(a.buckets)
    for index, weight in b.buckets.items():
        merged[index] = merged.get(index, 0.0) + weight
    return QuantileSketch(
        alpha=a.alpha, buckets=merged, zero_count=a.zero_count + b.zero_count
    )


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
# frob:tests tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra.test_decay_shrinks_weight_toward_zero  # noqa: E501
# frob:tests tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra.test_decay_rejects_out_of_range_factor  # noqa: E501
def decay_sketch(sketch: QuantileSketch, factor: float) -> QuantileSketch:
    """`sketch` with every bucket's (and `zero_count`'s) weight scaled by
    `factor` (`0.0 <= factor <= 1.0`) -- the exponential-decay half of
    `frob.perf._sketch_store`'s `prior' = merge(run_sketch,
    decay(stored_prior, half_life_runs))` update rule. Buckets that decay
    below `_MIN_BUCKET_WEIGHT` are dropped rather than kept as
    numerically-irrelevant near-zero entries, so repeated decay of an
    unwritten-to section shrinks its serialized size toward zero instead
    of holding it steady forever."""
    if not 0.0 <= factor <= 1.0:
        raise ValueError(f"decay factor must be in [0, 1], got {factor}")
    buckets = {
        index: weight * factor
        for index, weight in sketch.buckets.items()
        if weight * factor > _MIN_BUCKET_WEIGHT
    }
    return sketch.model_copy(
        update={"buckets": buckets, "zero_count": sketch.zero_count * factor}
    )


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
# frob:tests tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra.test_decay_shrinks_weight_toward_zero  # noqa: E501
def total_weight(sketch: QuantileSketch) -> float:
    """Total accumulated weight across every bucket plus `zero_count`."""
    return sketch.zero_count + sum(sketch.buckets.values())


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
def quantile(sketch: QuantileSketch, q: float) -> float:
    """The `q`-quantile (`0.0 <= q <= 1.0`) read back from `sketch`,
    computed at read time by walking buckets in ascending order until the
    cumulative weight reaches `q * total_weight(sketch)` -- NEVER stored
    (see module docstring). `0.0` on an empty sketch (no observations
    yet) rather than raising, since "no data" is a legitimate read-time
    state, not a caller error."""
    if not 0.0 <= q <= 1.0:
        raise ValueError(f"quantile must be in [0, 1], got {q}")
    total = total_weight(sketch)
    if total <= 0.0:
        return 0.0
    rank = q * total
    cumulative = 0.0
    if sketch.zero_count > 0.0:
        cumulative += sketch.zero_count
        if cumulative >= rank:
            return 0.0
    last_index: int | None = None
    for index in sorted(sketch.buckets):
        cumulative += sketch.buckets[index]
        last_index = index
        if cumulative >= rank:
            return _bucket_value(index, sketch.alpha)
    # Floating-point edge case: rounding left `cumulative` a hair under
    # `rank` on the final bucket -- return that bucket's estimate rather
    # than falling through to a wrong default.
    if last_index is not None:
        return _bucket_value(last_index, sketch.alpha)
    return 0.0


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
# frob:tests tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra.test_bimodal_quantiles_within_relative_error_and_under_1kb  # noqa: E501
def sketch_size_bytes(sketch: QuantileSketch) -> int:
    """Serialized (JSON) byte size of `sketch` -- what `frob.perf.
    _sketch_store` actually persists per section, and what the ticket's
    <1KB acceptance criterion measures against."""
    return len(sketch.model_dump_json().encode("utf-8"))
