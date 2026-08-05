"""Cache observational-transparency sweeps (T-1519, INV-050) for caches
`test_gate_cache.py` does not already cover: `.frob/cache.db` (the graph
cache) and `.frob/pytest-collect.json` (the collection cache). Each sweep
uses `tests/_cache_transparency.py::run_cold_warm_sweep` to drive arbitrary
edit sequences and assert a stale-but-present cache never disagrees with a
from-scratch (empty-cache) evaluation."""

from __future__ import annotations

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
# tests -- WIRE001's reachability scan skips test paths by design, same precedent as \
# tests/test_cache_gate.py::_git_init_tracked" follow_up="T-1490"
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
