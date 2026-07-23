"""T-0711: `frob.stats._sketch.QuantileSketch` algebra (merge associativity,
bimodal relative-error bound, decay convergence) plus `frob.perf.
_sketch_store`'s sqlite decayed-merge store (round-trip, decayed-merge
convergence, size-cap eviction, stable keying)."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from frob.perf._hotgraph import Section
from frob.perf._sketch_store import (
    SketchStoreConfig,
    _close_all,
    get_sketch,
    load_sketch_config,
    new_run_sketch,
    put_sketch,
    stable_section_key,
    store_size_bytes,
)
from frob.stats._sketch import (
    DEFAULT_ALPHA,
    QuantileSketch,
    add_value,
    decay_sketch,
    merge_sketches,
    new_sketch,
    quantile,
    sketch_size_bytes,
    total_weight,
)


def _sketch_from_values(
    values: list[float], alpha: float = DEFAULT_ALPHA
) -> QuantileSketch:
    sketch = new_sketch(alpha=alpha)
    for value in values:
        sketch = add_value(sketch, value)
    return sketch


def _bimodal_sample(n: int, seed: int = 0) -> list[float]:
    """`n` values split across two well-separated modes (~1ms, ~100ms)
    with jitter -- the ticket's own acceptance-criterion fixture, chosen
    specifically because a moment-based sketch (t-digest, HDR-adjacent
    mean/variance approaches) is misled by bimodal data; DDSketch's
    per-bucket exactness is not."""
    rng = random.Random(seed)
    values = []
    for _ in range(n):
        if rng.random() < 0.5:
            values.append(rng.uniform(0.9, 1.1))
        else:
            values.append(rng.uniform(90.0, 110.0))
    return values


class TestQuantileSketchAlgebra:
    """Pure sketch algebra -- no sqlite, no filesystem."""

    def test_bimodal_quantiles_within_relative_error_and_under_1kb(self) -> None:
        """T-0711's acceptance criterion, verbatim: bimodal latencies (1ms
        and 100ms modes) sketched at alpha=2 percent read back p10/p50/p90
        within relative error, and the serialized sketch is under 1KB."""
        alpha = 0.02
        values = _bimodal_sample(4000, seed=1)
        sketch = _sketch_from_values(values, alpha=alpha)

        values.sort()

        def _true_quantile(q: float) -> float:
            index = min(int(q * len(values)), len(values) - 1)
            return values[index]

        for q in (0.10, 0.50, 0.90):
            true_v = _true_quantile(q)
            estimated = quantile(sketch, q)
            relative_error = abs(estimated - true_v) / true_v
            assert relative_error <= alpha + 1e-9, (
                f"q={q}: estimated={estimated} true={true_v} "
                f"relative_error={relative_error} > alpha={alpha}"
            )

        assert sketch_size_bytes(sketch) < 1024

    def test_merge_is_associative(self) -> None:
        """`merge(merge(a, b), c) == merge(a, merge(b, c))` -- the core
        mergeability property a decayed cross-run store depends on
        (partial per-run sketches must combine correctly regardless of
        grouping/order)."""
        a = _sketch_from_values(_bimodal_sample(50, seed=10))
        b = _sketch_from_values(_bimodal_sample(50, seed=20))
        c = _sketch_from_values(_bimodal_sample(50, seed=30))

        left = merge_sketches(merge_sketches(a, b), c)
        right = merge_sketches(a, merge_sketches(b, c))

        assert left.buckets == right.buckets
        assert left.zero_count == pytest.approx(right.zero_count)

    def test_merge_is_commutative(self) -> None:
        """`merge(a, b) == merge(b, a)` -- plain per-bucket addition, order
        never matters."""
        a = _sketch_from_values(_bimodal_sample(30, seed=1))
        b = _sketch_from_values(_bimodal_sample(30, seed=2))
        assert merge_sketches(a, b).buckets == merge_sketches(b, a).buckets

    def test_merge_rejects_mismatched_alpha(self) -> None:
        """Merging sketches built at different relative-error targets
        would silently blend incompatible bucket boundaries -- refused,
        not guessed."""
        a = new_sketch(alpha=0.02)
        b = new_sketch(alpha=0.05)
        with pytest.raises(ValueError, match="alpha"):
            merge_sketches(a, b)

    def test_decay_shrinks_weight_toward_zero(self) -> None:
        """Repeated decay strictly shrinks total weight, converging to
        zero -- an unwritten-to section's stored prior fades out rather
        than accumulating forever."""
        sketch = _sketch_from_values([1.0, 2.0, 100.0, 100.0])
        weight = total_weight(sketch)
        for _ in range(50):
            sketch = decay_sketch(sketch, 0.5)
            new_weight = total_weight(sketch)
            assert new_weight <= weight
            weight = new_weight
        assert weight < 1e-6

    def test_decay_rejects_out_of_range_factor(self) -> None:
        sketch = new_sketch()
        with pytest.raises(ValueError):
            decay_sketch(sketch, 1.5)
        with pytest.raises(ValueError):
            decay_sketch(sketch, -0.1)

    def test_zero_values_land_in_zero_count_not_a_bucket(self) -> None:
        sketch = add_value(new_sketch(), 0.0, weight=3.0)
        assert sketch.zero_count == 3.0
        assert sketch.buckets == {}
        assert quantile(sketch, 0.5) == 0.0

    def test_negative_value_is_dropped_not_raised(self) -> None:
        """NO-FAIL-SILENT-but-not-a-crash: this sketch models non-negative
        latencies; a negative input is logged and dropped rather than
        corrupting the sketch or raising into a caller's hot path."""
        sketch = new_sketch()
        result = add_value(sketch, -5.0)
        assert result == sketch

    def test_quantile_on_empty_sketch_is_zero(self) -> None:
        assert quantile(new_sketch(), 0.5) == 0.0

    def test_quantile_rejects_out_of_range_q(self) -> None:
        with pytest.raises(ValueError):
            quantile(new_sketch(), 1.5)


class TestSketchStore:
    """`frob.perf._sketch_store`'s sqlite decayed-merge store, over a
    `tmp_path` repo root."""

    @pytest.fixture(autouse=True)
    def _teardown(self):
        yield
        _close_all()

    def _section(self, qualname: str = "pkg.mod.hot_loop") -> Section:
        return Section(
            id="unused-run-scoped-id",
            kind="loop",
            qualname=qualname,
            file="pkg/mod.py",
            start_line=2,
            end_line=5,
        )

    def test_get_on_never_seen_key_is_none(self, tmp_path: Path) -> None:
        assert get_sketch(tmp_path, "no-such-key") is None

    def test_put_then_get_round_trips(self, tmp_path: Path) -> None:
        key = stable_section_key(self._section())
        run_sketch = _sketch_from_values([1.0, 1.0, 100.0])
        config = SketchStoreConfig()

        result = put_sketch(tmp_path, key, "loop", run_sketch, config)
        assert result.is_ok
        stored = get_sketch(tmp_path, key)
        assert stored is not None
        assert stored.buckets == result.danger_ok.buckets

    def test_decayed_merge_converges_toward_recent_run_distribution(
        self, tmp_path: Path
    ) -> None:
        """Repeated `put_sketch` calls feeding the SAME stable distribution
        converge (the ticket's "repeated runs THEN decayed merge
        converges" criterion): after enough runs, p50 reads back close to
        the true value, and the store never exceeds its configured cap."""
        key = stable_section_key(self._section())
        config = SketchStoreConfig(half_life_runs=3.0, store_cap_bytes=100_000)

        for seed in range(20):
            run_values = _bimodal_sample(200, seed=seed)
            run_sketch = _sketch_from_values(run_values)
            result = put_sketch(tmp_path, key, "loop", run_sketch, config)
            assert result.is_ok

        stored = get_sketch(tmp_path, key)
        assert stored is not None
        p50 = quantile(stored, 0.5)
        # bimodal median lands at either the ~1ms or ~100ms mode; either is
        # a valid converged read -- what matters is it is NOT some
        # unrelated garbage value.
        assert p50 == pytest.approx(1.0, rel=0.2) or p50 == pytest.approx(
            100.0, rel=0.2
        )
        assert store_size_bytes(tmp_path) <= config.store_cap_bytes

    def test_store_cap_evicts_coldest_section_first(self, tmp_path: Path) -> None:
        """A store cap smaller than the total of many sections' sketches
        evicts the LEAST-RECENTLY-USED section first, keeping the store
        under cap -- structurally cannot grow unbounded."""
        config = SketchStoreConfig(store_cap_bytes=600)
        keys = []
        for i in range(20):
            section = self._section(qualname=f"pkg.mod.fn_{i}")
            key = stable_section_key(section)
            keys.append(key)
            run_sketch = _sketch_from_values(_bimodal_sample(20, seed=i))
            result = put_sketch(tmp_path, key, "function", run_sketch, config)
            assert result.is_ok

        assert store_size_bytes(tmp_path) <= config.store_cap_bytes
        # the earliest-written (coldest, since nothing re-touched it) key
        # was evicted; the most recently written key survives.
        assert get_sketch(tmp_path, keys[0]) is None
        assert get_sketch(tmp_path, keys[-1]) is not None

    def test_stable_section_key_ignores_line_drift(self) -> None:
        """The whole point of `stable_section_key` over `Section.id`: two
        `Section`s differing only in `start_line`/`end_line` (a pure
        line-drift edit elsewhere in the file) hash to the SAME key, so
        history keeps accumulating onto the same store row."""
        drifted = self._section().model_copy(update={"start_line": 40, "end_line": 45})
        assert stable_section_key(self._section()) == stable_section_key(drifted)

    def test_stable_section_key_distinguishes_qualname(self) -> None:
        a = stable_section_key(self._section(qualname="pkg.mod.fn_a"))
        b = stable_section_key(self._section(qualname="pkg.mod.fn_b"))
        assert a != b

    def test_stable_section_key_uses_symbol_digest_when_given(self) -> None:
        """A caller supplying a real (future-wired) symbol digest changes
        the key basis from `section.file` to that digest -- proving the
        digest actually participates in the hash, not just documented
        intent."""
        section = self._section()
        without_digest = stable_section_key(section)
        with_digest = stable_section_key(section, symbol_digest="deadbeef")
        assert without_digest != with_digest

    def test_first_write_has_no_prior_to_decay(self, tmp_path: Path) -> None:
        """A never-seen key's first `put_sketch` stores `run_sketch`
        UNCHANGED (no prior exists to merge/decay against)."""
        key = stable_section_key(self._section())
        run_sketch = _sketch_from_values([5.0, 5.0, 5.0])
        config = SketchStoreConfig()
        result = put_sketch(tmp_path, key, "loop", run_sketch, config)
        assert result.danger_ok.buckets == run_sketch.buckets

    def test_new_run_sketch_is_an_empty_sketch_at_alpha(self) -> None:
        """`new_run_sketch` is the thin `frob.perf`-local wrapper over
        `frob.stats._sketch.new_sketch` -- an empty sketch at the given
        alpha, ready for a caller to `add_value` samples into before
        handing it to `put_sketch`."""
        sketch = new_run_sketch(0.03)
        assert sketch.alpha == 0.03
        assert sketch.buckets == {}
        assert sketch.zero_count == 0.0


class TestSketchStoreConfig:
    """`load_sketch_config`'s `[perf.sketch]` frob.toml parsing."""

    def test_missing_frob_toml_returns_defaults(self, tmp_path: Path) -> None:
        config = load_sketch_config(tmp_path)
        assert config == SketchStoreConfig()

    def test_parses_perf_sketch_table(self, tmp_path: Path) -> None:
        (tmp_path / "frob.toml").write_text(
            "[perf.sketch]\nalpha = 0.05\nhalf_life_runs = 10.0\nstore_cap_bytes = 50000\n"
        )
        config = load_sketch_config(tmp_path)
        assert config.alpha == 0.05
        assert config.half_life_runs == 10.0
        assert config.store_cap_bytes == 50000

    def test_malformed_toml_falls_back_to_defaults(self, tmp_path: Path) -> None:
        (tmp_path / "frob.toml").write_text("not valid toml [[[")
        config = load_sketch_config(tmp_path)
        assert config == SketchStoreConfig()

    def test_wrong_typed_perf_sketch_falls_back_to_defaults(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "frob.toml").write_text("[perf]\nsketch = 5\n")
        config = load_sketch_config(tmp_path)
        assert config == SketchStoreConfig()


class TestConnectionReuse:
    """Mirrors `frob.dup._cache`'s connection-reuse test: `_close_all`
    actually drops the process-cached connection."""

    def test_close_all_drops_cached_connections(self, tmp_path: Path) -> None:
        from frob.perf import _sketch_store

        key = stable_section_key(
            Section(
                id="x",
                kind="function",
                qualname="a.b",
                file="a.py",
                start_line=1,
                end_line=2,
            )
        )
        put_sketch(tmp_path, key, "function", new_sketch(), SketchStoreConfig())
        assert len(_sketch_store._conn_cache) >= 1
        _close_all()
        assert _sketch_store._conn_cache == {}
