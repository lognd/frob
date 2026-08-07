"""Cache observational-transparency sweeps (T-1519, INV-050) for caches
`test_gate_cache.py` does not already cover: `.frob/cache.db` (the graph
cache) and `.frob/pytest-collect.json` (the collection cache). Each sweep
uses `tests/_cache_transparency.py::run_cold_warm_sweep` to drive arbitrary
edit sequences and assert a stale-but-present cache never disagrees with a
from-scratch (empty-cache) evaluation.

T-1529 extends the same harness to three caches INV-050's own inventory
table deliberately left out of the original sweep because they are not
correctness-critical (never change a gate's PASS/FAIL result or violation
fingerprint, only advisory precision or scheduling) -- but each still has
a real observable-transparency property worth locking in:

- `.frob/coverage-stamp` / `frob-coverage.lock.json`
  (`TestCoverageLockCacheTransparency`): the public accessor
  (`load_coverage_lock`) must never disagree with a direct, uncached read
  of the same file -- there is no in-process cache layer here today, so
  this sweep is a regression lock against one being added later without
  this property in mind.
- `.frob/hotgraph_sketches.db` (`TestHotgraphSketchCacheTransparency`):
  `_sketch_store._connect` DOES cache a live sqlite connection per
  resolved db path for the life of the process -- this sweep is the one
  that actually exercises a real staleness risk, forcing a cold
  reconnect (`_close_all()`) after every mutation and asserting it reads
  back exactly what the still-open warm connection just wrote.
- `.frob/check-budget-timing.json` (`TestBudgetTimingCacheTransparency`):
  `_load_budget_timing` is also an uncached read-through, including its
  "corrupt file degrades to `{}`, never a crash" contract -- swept the
  same way as the coverage lock, corrupt-content rounds included."""

from __future__ import annotations

import json
import random
from pathlib import Path

from frob.graph import build_graph
from frob.testing._collect import _content_key
from frob.testing._collect_shared import _load_cache, _store_cache
from tests._cache_transparency import git_commit_all, git_init, run_cold_warm_sweep


# frob:ticket T-1520
def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# frob:ticket T-1520
# frob:waive WIRE001 reason="private test-fixture helper used only by this file's own \
# tests -- no production caller to wire it to by design" permanent="true"
def _graph_fingerprint(root: Path, cache: Path) -> frozenset[tuple[str, str]]:
    """`(ref, sig-digest)` pairs for every symbol -- the observable surface a
    cache-consuming caller (a gate, `frob ticket evidence`, ...) actually
    reads out of a `GraphSnapshot`."""
    snap = build_graph(root, cache).danger_ok
    return frozenset((ref, rec.digests.sig) for ref, rec in snap.symbols.items())


# frob:ticket T-1520
class TestGraphCacheTransparency:
    """`.frob/cache.db`: cold (fresh empty cache path each round) must agree
    with warm (one cache path reused, and staying present, across every
    round) after arbitrary file add/edit/remove/rename rounds."""

    # frob:ticket T-1520
    # frob:tests tests/test_cache_transparency.py::TestGraphCacheTransparency.test_cold_warm_agree_across_random_edits  # noqa: E501
    def test_cold_warm_agree_across_random_edits(self, tmp_path: Path) -> None:
        """frob:tests src/frob/graph/__init__.py::build_graph"""
        rng = random.Random(4242)
        git_init(tmp_path)
        warm_cache = tmp_path / ".frob" / "warm-cache.db"
        files = [f"pkg/mod{i}.py" for i in range(4)]

        def mutate(rng: random.Random, round_: int) -> None:
            action = rng.choice(["edit", "add", "remove", "rename", "noop"])
            if action == "edit" and files:
                target = rng.choice(files)
                _write(
                    tmp_path, target, f"def f_{round_}(x):\n    return x + {round_}\n"
                )
            elif action == "add":
                new_file = f"pkg/extra{round_}.py"
                _write(tmp_path, new_file, f"def g_{round_}():\n    pass\n")
                files.append(new_file)
            elif action == "remove" and files:
                target = rng.choice(files)
                path = tmp_path / target
                if path.exists():
                    path.unlink()
                files.remove(target)
            elif action == "rename" and files:
                target = rng.choice(files)
                path = tmp_path / target
                if path.exists():
                    new_rel = f"pkg/renamed{round_}.py"
                    path.rename(tmp_path / new_rel)
                    files.remove(target)
                    files.append(new_rel)
            git_commit_all(tmp_path, message=f"round {round_} ({action})")

        def cold_fp() -> frozenset[tuple[str, str]]:
            fresh_cache = tmp_path / ".frob" / "cold-cache.db"
            if fresh_cache.exists():
                fresh_cache.unlink()
            return _graph_fingerprint(tmp_path, fresh_cache)

        def warm_fp() -> frozenset[tuple[str, str]]:
            return _graph_fingerprint(tmp_path, warm_cache)

        run_cold_warm_sweep(
            rng,
            rounds=8,
            mutate=mutate,
            cold_fingerprint=cold_fp,
            warm_fingerprint=warm_fp,
        )


# frob:ticket T-1520
class TestPytestCollectCacheTransparency:
    """`.frob/pytest-collect.json`: the cache stores `(key, node_ids)`
    keyed by test-file content hash (`_content_key`, T-0333). Observational
    transparency here reduces to: a warm cache entry written under key K1,
    then read back under a DIFFERENT key K2 (any edit to a test file's
    content changes `_content_key`), must be treated as a miss (`None`) --
    never silently served stale node ids -- and a hit for the SAME key must
    return exactly what was stored, byte for byte."""

    # frob:ticket T-1520
    # frob:tests tests/test_cache_transparency.py::TestPytestCollectCacheTransparency.test_cold_warm_agree_across_random_edits  # noqa: E501
    def test_cold_warm_agree_across_random_edits(self, tmp_path: Path) -> None:
        """frob:tests src/frob/testing/_collect_shared.py::_load_cache"""
        rng = random.Random(99)
        git_init(tmp_path)
        cache_path = tmp_path / ".frob" / "pytest-collect.json"
        node_id_pool = [f"tests/test_x.py::test_{i}" for i in range(6)]

        def mutate(rng: random.Random, round_: int) -> None:
            _write(
                tmp_path,
                "tests/test_x.py",
                f"def test_{round_ % len(node_id_pool)}():\n    assert True\n",
            )
            git_commit_all(tmp_path, message=f"round {round_}")

        def cold_fp() -> frozenset[str] | None:
            # "cold" = never consult the cache at all: the real node-id set
            # is whatever the current key's simulated collection produces.
            key = _content_key(tmp_path)
            simulated = frozenset({f"tests/test_x.py::test_{key[:1]}"})
            return simulated

        def warm_fp() -> frozenset[str] | None:
            key = _content_key(tmp_path)
            cached = _load_cache(cache_path, key)
            if cached is not None:
                # A hit MUST match what a fresh computation for this exact
                # key would produce -- since the key changed every round
                # (content-hash-keyed), a stale entry from a prior round's
                # key must never be returned here.
                simulated = frozenset({f"tests/test_x.py::test_{key[:1]}"})
                assert cached == simulated, "stale cache entry served under new key"
                return cached
            simulated = frozenset({f"tests/test_x.py::test_{key[:1]}"})
            _store_cache(cache_path, key, simulated)
            return simulated

        run_cold_warm_sweep(
            rng,
            rounds=6,
            mutate=mutate,
            cold_fingerprint=cold_fp,
            warm_fingerprint=warm_fp,
        )


# frob:ticket T-1529
class TestCoverageLockCacheTransparency:
    """`frob-coverage.lock.json`: `load_coverage_lock` (the public
    accessor every gate/CLI caller uses -- "warm") must agree with a
    direct, uncached parse of the same file ("cold") after arbitrary
    write/corrupt/delete rounds. No in-process cache exists for this file
    today; this sweep exists to lock the property in before one is ever
    added."""

    # frob:tests tests/test_cache_transparency.py::TestCoverageLockCacheTransparency.test_cold_warm_agree_across_random_edits  # noqa: E501
    def test_cold_warm_agree_across_random_edits(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_coverage.py::load_coverage_lock"""
        from frob.gates._coverage import _LOCK_REL, load_coverage_lock

        rng = random.Random(1529)
        git_init(tmp_path)
        lock_path = tmp_path / _LOCK_REL

        def mutate(rng: random.Random, round_: int) -> None:
            action = rng.choice(["write", "delete", "corrupt"])
            if action == "write":
                lock_path.parent.mkdir(parents=True, exist_ok=True)
                payload = {
                    "source_sha": f"sha-{round_}",
                    "module_line": {f"pkg/mod{i}.py": round_ % 100 for i in range(3)},
                }
                lock_path.write_text(json.dumps(payload))
            elif action == "delete" and lock_path.exists():
                lock_path.unlink()
            elif action == "corrupt":
                lock_path.parent.mkdir(parents=True, exist_ok=True)
                lock_path.write_text("{not valid json")
            git_commit_all(tmp_path, message=f"round {round_} ({action})")

        def cold_fp() -> dict | None:
            # Bypass the accessor entirely: whatever a caller with no
            # cache at all would see reading the raw file directly.
            if not lock_path.exists():
                return None
            try:
                return json.loads(lock_path.read_text(encoding="utf-8"))
            except Exception:
                return None

        def warm_fp() -> dict | None:
            return load_coverage_lock(tmp_path)

        run_cold_warm_sweep(
            rng,
            rounds=8,
            mutate=mutate,
            cold_fingerprint=cold_fp,
            warm_fingerprint=warm_fp,
        )


# frob:ticket T-1529
class TestHotgraphSketchCacheTransparency:
    """`.frob/hotgraph_sketches.db`: `_sketch_store._connect` caches a
    live sqlite connection per resolved db path for the life of the
    process (`_conn_cache`) -- the one cache among this ticket's three
    that has a REAL staleness risk. This sweep forces a cold reconnect
    (`_close_all()`, mirroring a fresh process opening the store for the
    first time) after every `put_sketch` round and asserts `get_sketch`
    reads back exactly what the still-open warm connection just wrote."""

    # frob:tests tests/test_cache_transparency.py::TestHotgraphSketchCacheTransparency.test_cold_warm_agree_across_random_edits  # noqa: E501
    def test_cold_warm_agree_across_random_edits(self, tmp_path: Path) -> None:
        """frob:tests src/frob/perf/_sketch_store.py::get_sketch"""
        from frob.perf._sketch_store import (
            SketchStoreConfig,
            _close_all,
            get_sketch,
            new_run_sketch,
            put_sketch,
        )
        from frob.stats._sketch import add_value

        rng = random.Random(9271)
        git_init(tmp_path)
        config = SketchStoreConfig()
        section_keys = [f"section-{i:02x}" for i in range(4)]

        def mutate(rng: random.Random, round_: int) -> None:
            key = rng.choice(section_keys)
            sketch = new_run_sketch(alpha=0.01)
            for _ in range(5):
                sketch = add_value(sketch, rng.uniform(0.0, 1000.0))
            result = put_sketch(tmp_path, key, "test", sketch, config)
            assert result.is_ok, result.err
            git_commit_all(tmp_path, message=f"round {round_} put {key}")

        def cold_fp() -> dict[str, object | None]:
            # Force every cached connection closed first -- the next
            # get_sketch call below must reconnect from scratch, mirroring
            # a brand-new process that has never opened this db before.
            _close_all()
            result: dict[str, object | None] = {}
            for key in section_keys:
                sk = get_sketch(tmp_path, key)
                result[key] = sk.model_dump() if sk is not None else None
            return result

        def warm_fp() -> dict[str, object | None]:
            result: dict[str, object | None] = {}
            for key in section_keys:
                sk = get_sketch(tmp_path, key)
                result[key] = sk.model_dump() if sk is not None else None
            return result

        run_cold_warm_sweep(
            rng,
            rounds=8,
            mutate=mutate,
            cold_fingerprint=cold_fp,
            warm_fingerprint=warm_fp,
        )
        _close_all()


# frob:ticket T-1529
class TestBudgetTimingCacheTransparency:
    """`.frob/check-budget-timing.json`: `_load_budget_timing` is an
    uncached read-through, including its "corrupt file degrades to `{}`,
    never a crash" contract -- swept the same way as the coverage lock,
    corrupt-content rounds included, to lock the property in before any
    in-process cache is ever added on top of it."""

    # frob:tests tests/test_cache_transparency.py::TestBudgetTimingCacheTransparency.test_cold_warm_agree_across_random_edits  # noqa: E501
    def test_cold_warm_agree_across_random_edits(self, tmp_path: Path) -> None:
        """frob:tests src/frob/app/_check_chunking.py::_load_budget_timing"""
        from frob.app._check_chunking import _budget_timing_path, _load_budget_timing

        rng = random.Random(4004)
        git_init(tmp_path)
        timing_path = _budget_timing_path(tmp_path)

        def mutate(rng: random.Random, round_: int) -> None:
            action = rng.choice(["write", "delete", "corrupt"])
            if action == "write":
                timing_path.parent.mkdir(parents=True, exist_ok=True)
                payload = {f"group-{i}": float(round_ * 10 + i) for i in range(3)}
                timing_path.write_text(json.dumps(payload))
            elif action == "delete" and timing_path.exists():
                timing_path.unlink()
            elif action == "corrupt":
                timing_path.parent.mkdir(parents=True, exist_ok=True)
                timing_path.write_text("[1, 2, not json")
            git_commit_all(tmp_path, message=f"round {round_} ({action})")

        def cold_fp() -> dict[str, float]:
            # The same "missing/corrupt degrades to {}" contract
            # _load_budget_timing itself implements, computed independently
            # here so the accessor's own behavior is what's under test.
            if not timing_path.exists():
                return {}
            try:
                data = json.loads(timing_path.read_text())
            except Exception:
                return {}
            if not isinstance(data, dict):
                return {}
            return {
                str(k): float(v) for k, v in data.items() if isinstance(v, (int, float))
            }

        def warm_fp() -> dict[str, float]:
            return _load_budget_timing(tmp_path)

        run_cold_warm_sweep(
            rng,
            rounds=8,
            mutate=mutate,
            cold_fingerprint=cold_fp,
            warm_fingerprint=warm_fp,
        )
