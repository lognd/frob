"""Tests for `frob.gates._gate_cache` (T-0602): per-obligation
dependency-tracked partial re-evaluation. `TestColdDiffOracle` is the
correctness oracle the ticket asks for -- a full (cold) evaluation and a
partial (cache-aware) evaluation from any prior cached state must agree,
across random content edits, file adds, file removes, and scalar-extra
changes."""

from __future__ import annotations

import random
import subprocess
from pathlib import Path

from frob.gates import GateConfig, run_gates
from frob.gates._gate_cache import (
    TrackedSnapshot,
    evaluate_cacheable_gate,
    extra_key,
    invalidate,
    model_side_channel_key,
)
from frob.graph import build_graph
from frob.graph._models import GraphSnapshot, LockEntry, LockFile
from frob.graph.lock import write_lock


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# frob:ticket T-1520
# T-1520 dedup: the shared cache-transparency harness (tests/
# _cache_transparency.py) is the one home for this fixture now.
from tests._cache_transparency import git_init as _git_init  # noqa: E402


def _snapshot(root: Path) -> GraphSnapshot:
    """A freshly built (uncached) `GraphSnapshot` for `root`."""
    return build_graph(root, root / ".frob" / "cache.db").danger_ok


class TestTrackedSnapshot:
    def test_symbol_iteration_records_file(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::TrackedSnapshot.symbols"""
        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _write(tmp_path, "b.py", "def g():\n    pass\n")
        _git_init(tmp_path)
        snap = _snapshot(tmp_path)
        touched: set[str] = set()
        tracked = TrackedSnapshot(snap, touched)
        for ref in tracked.symbols:
            assert ref  # force iteration
        assert "a.py" in touched
        assert "b.py" in touched

    def test_getitem_records_only_accessed_key(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::TrackedSnapshot.symbols"""
        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _write(tmp_path, "b.py", "def g():\n    pass\n")
        _git_init(tmp_path)
        snap = _snapshot(tmp_path)
        [key_a] = [k for k in snap.symbols if k.startswith("a.py")]
        touched: set[str] = set()
        tracked = TrackedSnapshot(snap, touched)
        _ = tracked.symbols[key_a]
        assert touched == {"a.py"}

    def test_file_hashes(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::TrackedSnapshot.file_hashes"""
        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _write(tmp_path, "b.py", "def g():\n    pass\n")
        _git_init(tmp_path)
        snap = _snapshot(tmp_path)
        touched: set[str] = set()
        tracked = TrackedSnapshot(snap, touched)
        _ = tracked.file_hashes["a.py"]
        assert touched == {"a.py"}


class TestExtraKey:
    def test_extra_key(self) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::extra_key"""
        assert extra_key(["T-0001", "2026-01-01"]) == extra_key(
            ["T-0001", "2026-01-01"]
        )
        assert extra_key(["T-0001"]) != extra_key(["T-0002"])
        assert extra_key([]) != extra_key(["T-0001"])


class TestSideChannelKey:
    """T-1454: `model_side_channel_key` must distinguish side-channel
    inputs (e.g. `frob.lock`'s content) that `TrackedSnapshot` cannot
    observe, since those never register as a touched FILE."""

    def test_model_side_channel_key_changes_on_field_edit(self) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::model_side_channel_key"""
        lock_a = LockFile(entries=(LockEntry(ref="a.py::f", facet="sig", digest="x"),))
        lock_b = LockFile(entries=(LockEntry(ref="a.py::f", facet="sig", digest="y"),))
        assert model_side_channel_key(lock_a) != model_side_channel_key(lock_b)

    def test_model_side_channel_key_stable_for_equal_content(self) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::model_side_channel_key"""
        entry = LockEntry(ref="a.py::f", facet="sig", digest="x")
        lock_a = LockFile(entries=(entry,))
        lock_b = LockFile(entries=(LockEntry(ref="a.py::f", facet="sig", digest="x"),))
        assert model_side_channel_key(lock_a) == model_side_channel_key(lock_b)


class TestEvaluateCacheableGate:
    def test_miss_then_hit_skips_second_call(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::evaluate_cacheable_gate"""
        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        snap = _snapshot(tmp_path)
        calls = []

        def run(tracked) -> tuple:  # noqa: ANN001
            calls.append(1)
            list(tracked.symbols)
            return ()

        r1 = evaluate_cacheable_gate(tmp_path, "fake_gate", snap, run)
        r2 = evaluate_cacheable_gate(tmp_path, "fake_gate", snap, run)
        assert r1 == r2 == ()
        assert len(calls) == 1, (
            "second call with an unchanged snapshot must be a cache HIT"
        )

    def test_edit_to_untouched_file_stays_a_hit(self, tmp_path: Path) -> None:
        """A file the gate never reads changing content must not invalidate
        its cache entry -- the actual partial-re-evaluation win this ticket
        is for."""
        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _write(tmp_path, "b.py", "def g():\n    pass\n")
        _git_init(tmp_path)
        snap1 = _snapshot(tmp_path)
        calls = []

        [key_a] = [k for k in snap1.symbols if k.startswith("a.py")]

        def run(tracked) -> tuple:  # noqa: ANN001
            calls.append(1)
            # Only ever reads a.py's symbol (a direct __getitem__, never a
            # full-mapping iteration -- iterating would itself record every
            # key it walks past, which is by design; see TestTrackedSnapshot).
            _ = tracked.symbols[key_a]
            return ()

        evaluate_cacheable_gate(tmp_path, "fake_gate", snap1, run)
        assert len(calls) == 1

        _write(tmp_path, "b.py", "def g():\n    return 1\n")
        snap2 = _snapshot(tmp_path)
        evaluate_cacheable_gate(tmp_path, "fake_gate", snap2, run)
        assert len(calls) == 1, "editing an untouched file must stay a cache HIT"

    def test_edit_to_touched_file_forces_miss(self, tmp_path: Path) -> None:
        """A file the gate DID read changing content must force re-evaluation."""
        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        snap1 = _snapshot(tmp_path)
        calls = []

        def run(tracked) -> tuple:  # noqa: ANN001
            calls.append(1)
            list(tracked.symbols)
            return ()

        evaluate_cacheable_gate(tmp_path, "fake_gate", snap1, run)
        _write(tmp_path, "a.py", "def f():\n    return 1\n")
        snap2 = _snapshot(tmp_path)
        evaluate_cacheable_gate(tmp_path, "fake_gate", snap2, run)
        assert len(calls) == 2, "editing a touched file must force a cache MISS"

    def test_new_untouched_file_forces_miss_membership_guard(
        self, tmp_path: Path
    ) -> None:
        """T-0602's membership guard: a NEW file appearing anywhere in the
        tree must invalidate every cacheable entry, even one that only ever
        touched an unrelated file -- otherwise a gate that would now also
        touch the new file could serve a stale answer."""
        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        snap1 = _snapshot(tmp_path)
        [key_a] = [k for k in snap1.symbols if k.startswith("a.py")]
        calls = []

        def run(tracked) -> tuple:  # noqa: ANN001
            calls.append(1)
            _ = tracked.symbols[key_a]
            return ()

        evaluate_cacheable_gate(tmp_path, "fake_gate", snap1, run)
        _write(tmp_path, "c.py", "def h():\n    pass\n")
        snap2 = _snapshot(tmp_path)
        evaluate_cacheable_gate(tmp_path, "fake_gate", snap2, run)
        assert len(calls) == 2, "a new file anywhere must force a cache MISS"

    def test_extra_change_forces_miss(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::evaluate_cacheable_gate"""
        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        snap = _snapshot(tmp_path)
        calls = []

        def run(tracked) -> tuple:  # noqa: ANN001
            calls.append(1)
            return ()

        evaluate_cacheable_gate(tmp_path, "fake_gate", snap, run, extra=("2026-01-01",))
        evaluate_cacheable_gate(tmp_path, "fake_gate", snap, run, extra=("2026-01-02",))
        assert len(calls) == 2, "a changed extra scalar must force a cache MISS"

    def test_invalidate_forces_next_call_to_miss(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::invalidate"""
        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        snap = _snapshot(tmp_path)
        calls = []

        def run(tracked) -> tuple:  # noqa: ANN001
            calls.append(1)
            return ()

        evaluate_cacheable_gate(tmp_path, "fake_gate", snap, run)
        invalidate(tmp_path)
        evaluate_cacheable_gate(tmp_path, "fake_gate", snap, run)
        assert len(calls) == 2


class TestRunGatesUseCache:
    def test_use_cache_false_is_default_and_unaffected(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/__init__.py::run_gates"""
        _write(tmp_path, "src/pkg/a.py", "def helper(x):\n    return x\n")
        _git_init(tmp_path)
        cfg = GateConfig(root=str(tmp_path), base="main", gates=frozenset({"drift"}))
        assert run_gates(cfg).is_ok
        assert not (tmp_path / ".frob" / "gate-cache.db").exists()

    def test_use_cache_true_produces_identical_report_to_cold(
        self, tmp_path: Path
    ) -> None:
        """frob:tests src/frob/gates/__init__.py::run_gates"""
        _write(tmp_path, "src/pkg/a.py", "def helper(x):\n    return x\n")
        _git_init(tmp_path)
        selected = frozenset({"drift", "test", "policy", "parse_failures", "debt"})
        cfg = GateConfig(root=str(tmp_path), base="main", gates=selected)
        cold = run_gates(cfg, use_cache=False).danger_ok
        warm_first = run_gates(cfg, use_cache=True).danger_ok
        warm_second = run_gates(cfg, use_cache=True).danger_ok
        cold_fp = sorted((v.rule, v.file, v.line, v.message) for v in cold.violations)
        warm1_fp = sorted(
            (v.rule, v.file, v.line, v.message) for v in warm_first.violations
        )
        warm2_fp = sorted(
            (v.rule, v.file, v.line, v.message) for v in warm_second.violations
        )
        assert cold_fp == warm1_fp == warm2_fp

    def test_ack_invalidates_cached_drift001(self, tmp_path: Path) -> None:
        """T-1454 regression: a `frob ack` that rewrites `frob.lock` (with no
        tracked SOURCE file digest changing) must invalidate a previously
        cached DRIFT001 result on the very next cached `frob check` -- the
        exact staleness the reporter observed workarounding with
        `FROB_NO_GATE_CACHE=1`. frob:tests
        src/frob/gates/__init__.py::_cacheable_gate_call"""
        widget = '''class Widget:
    """A widget."""

    def render(self, value: int) -> str:
        """Render the widget."""
        return str(value)
'''
        _write(tmp_path, "src/a.py", widget)
        _git_init(tmp_path)
        ref = "src/a.py::Widget.render"

        # Stale lock: DRIFT001 must fire and get cached.
        stale_lock = LockFile(
            entries=(LockEntry(ref=ref, facet="sig", digest="deadbeef"),)
        )
        assert write_lock(stale_lock, tmp_path / "frob.lock").is_ok

        cfg = GateConfig(root=str(tmp_path), base="main", gates=frozenset({"drift"}))
        stale_report = run_gates(cfg, use_cache=True).danger_ok
        assert any(v.rule == "DRIFT001" for v in stale_report.violations)

        # "frob ack": compute the real current digest and rewrite frob.lock
        # -- no tracked source file changes, so this is exactly the
        # side-channel-only edit the cache used to miss entirely.
        snap = _snapshot(tmp_path)
        real_digest = snap.symbols[ref].digests.sig
        acked_lock = LockFile(
            entries=(LockEntry(ref=ref, facet="sig", digest=real_digest),)
        )
        assert write_lock(acked_lock, tmp_path / "frob.lock").is_ok

        acked_report = run_gates(cfg, use_cache=True).danger_ok
        assert not any(v.rule == "DRIFT001" for v in acked_report.violations), (
            "stale cached DRIFT001 served across a frob ack boundary (T-1454)"
        )


# frob:ticket T-0602
class TestColdDiffOracle:
    """The correctness oracle T-0602 asks for: a full (cold) evaluation and
    a partial (cache-aware) evaluation from ANY prior cache state must
    agree, across random content edits, file adds, file removes, and
    scalar-extra (`debt`'s `current_date`/`current_version`) changes."""

    # frob:tests tests/test_gate_cache.py::TestColdDiffOracle.test_cache_agrees_with_cold_across_random_edits  # noqa: E501
    def test_cache_agrees_with_cold_across_random_edits(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/__init__.py::run_gates"""
        rng = random.Random(1729)
        _git_init(tmp_path)
        selected = frozenset(
            {"drift", "test", "policy", "parse_failures", "debt", "deprecated"}
        )
        cfg = GateConfig(root=str(tmp_path), base="main", gates=selected)
        files = [f"pkg/mod{i}.py" for i in range(4)]

        for round_ in range(8):
            action = rng.choice(["edit", "add", "remove", "noop"])
            if action == "edit" and files:
                target = rng.choice(files)
                _write(
                    tmp_path,
                    target,
                    f"def f_{round_}(x):\n    return x + {round_}\n",
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
            subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

            cold = run_gates(cfg, use_cache=False).danger_ok
            warm = run_gates(cfg, use_cache=True).danger_ok
            cold_fp = frozenset(
                (v.rule, v.file, v.line, v.message) for v in cold.violations
            )
            warm_fp = frozenset(
                (v.rule, v.file, v.line, v.message) for v in warm.violations
            )
            assert cold_fp == warm_fp, (
                f"round {round_} ({action}): cold/cache-aware evaluation disagree "
                f"symdiff={cold_fp ^ warm_fp}"
            )


# frob:ticket T-1445
class TestRootContentKey:
    """`root_content_key` (T-1445): the whole-tree conservative dependency
    key `_CACHEABLE_PROCESS_GATES` keys off of -- each git-tracked path's
    CURRENT ON-DISK CONTENT (a plain read), not `git ls-files -s`'s INDEX
    blob sha."""

    def test_stable_when_nothing_changes(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::root_content_key"""
        from frob.gates._gate_cache import root_content_key

        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        assert root_content_key(tmp_path) == root_content_key(tmp_path)

    def test_changes_on_tracked_file_edit(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::root_content_key"""
        from frob.gates._gate_cache import root_content_key

        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        before = root_content_key(tmp_path)
        _write(tmp_path, "a.py", "def f():\n    return 1\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        after = root_content_key(tmp_path)
        assert before != after

    def test_changes_on_uncommitted_edit_never_git_added(self, tmp_path: Path) -> None:
        """Regression test for the real incident this fixed: an edit to a
        git-TRACKED file that was never `git add`ed (the everyday state of
        an in-progress worktree agent's own checkout) MUST still change
        the key -- `git ls-files -s`'s INDEX blob sha would not see this
        edit at all, silently serving a stale cached result for every
        cacheable process-pool gate until the next `git add`."""
        from frob.gates._gate_cache import root_content_key

        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        before = root_content_key(tmp_path)
        _write(tmp_path, "a.py", "def f():\n    return 1\n")
        # Deliberately NO `git add` here.
        after = root_content_key(tmp_path)
        assert before != after

    def test_none_outside_a_git_repo(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::root_content_key"""
        from frob.gates._gate_cache import root_content_key

        assert root_content_key(tmp_path) is None


# frob:ticket T-1445
class TestRootGateCache:
    """`load_root_gate_cache`/`store_root_gate_cache` (T-1445): the
    whole-tree cache primitives `_CACHEABLE_PROCESS_GATES` gates use in
    place of `evaluate_cacheable_gate`'s per-touched-file tracking, since a
    process-pool gate reads `st.root`/`st.repo_root` directly rather than
    the indexed `GraphSnapshot`."""

    def test_miss_then_hit_skips_second_call(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::load_root_gate_cache
        frob:tests src/frob/gates/_gate_cache.py::store_root_gate_cache"""
        from frob.gates._gate_cache import (
            load_root_gate_cache,
            root_content_key,
            store_root_gate_cache,
        )

        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        key = root_content_key(tmp_path)
        assert load_root_gate_cache(tmp_path, "fake_root_gate", key) is None
        store_root_gate_cache(tmp_path, "fake_root_gate", key, (), ())
        assert load_root_gate_cache(tmp_path, "fake_root_gate", key) == ()

    def test_tree_edit_forces_miss(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::load_root_gate_cache"""
        from frob.gates._gate_cache import (
            load_root_gate_cache,
            root_content_key,
            store_root_gate_cache,
        )

        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        key1 = root_content_key(tmp_path)
        store_root_gate_cache(tmp_path, "fake_root_gate", key1, (), ())

        _write(tmp_path, "a.py", "def f():\n    return 1\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        key2 = root_content_key(tmp_path)
        assert key2 != key1
        assert load_root_gate_cache(tmp_path, "fake_root_gate", key2) is None

    def test_extra_change_forces_miss(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::load_root_gate_cache"""
        from frob.gates._gate_cache import (
            load_root_gate_cache,
            root_content_key,
            store_root_gate_cache,
        )

        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        key = root_content_key(tmp_path)
        store_root_gate_cache(tmp_path, "fake_root_gate", key, ("v1",), ())
        assert load_root_gate_cache(tmp_path, "fake_root_gate", key, ("v2",)) is None
        assert load_root_gate_cache(tmp_path, "fake_root_gate", key, ("v1",)) == ()

    def test_none_key_never_hits_and_never_stores(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/_gate_cache.py::load_root_gate_cache
        frob:tests src/frob/gates/_gate_cache.py::store_root_gate_cache"""
        from frob.gates._gate_cache import load_root_gate_cache, store_root_gate_cache

        _git_init(tmp_path)
        store_root_gate_cache(tmp_path, "fake_root_gate", None, (), ())
        assert not (tmp_path / ".frob" / "gate-cache.db").exists()
        assert load_root_gate_cache(tmp_path, "fake_root_gate", None) is None


# frob:ticket T-1445
class TestSplitProcessCache:
    """`_split_process_cache` (T-1445): `_build_jobs`'s process-pool
    counterpart to `_substitute_cacheable_jobs`."""

    def test_use_cache_false_returns_everything_as_misses(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/__init__.py::_split_process_cache"""
        from frob.gates import _build_jobs, _load_inputs, _split_process_cache

        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        selected = frozenset({"drift", "secrets"})
        cfg = GateConfig(root=str(tmp_path), base="main", gates=selected)
        st = _load_inputs(cfg).danger_ok
        _thread_jobs, process_jobs, _skipped = _build_jobs(selected, st)

        remaining, hits, pending = _split_process_cache(
            process_jobs, st, use_cache=False
        )
        assert remaining == process_jobs
        assert hits == {}
        assert pending == {}

    def test_hit_removes_gate_from_remaining(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/__init__.py::_split_process_cache"""
        from frob.gates import _build_jobs, _load_inputs, _split_process_cache
        from frob.gates._gate_cache import root_content_key, store_root_gate_cache

        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        selected = frozenset({"drift", "secrets"})
        cfg = GateConfig(root=str(tmp_path), base="main", gates=selected)
        st = _load_inputs(cfg).danger_ok
        _thread_jobs, process_jobs, _skipped = _build_jobs(selected, st)
        key = root_content_key(st.repo_root)
        store_root_gate_cache(st.repo_root, "secrets", key, (), ())

        remaining, hits, pending = _split_process_cache(
            process_jobs, st, use_cache=True
        )
        assert "secrets" not in remaining
        assert hits["secrets"] == ()
        assert "secrets" not in pending

    def test_miss_keeps_gate_pending(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/__init__.py::_split_process_cache"""
        from frob.gates import _build_jobs, _load_inputs, _split_process_cache

        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        selected = frozenset({"drift", "secrets"})
        cfg = GateConfig(root=str(tmp_path), base="main", gates=selected)
        st = _load_inputs(cfg).danger_ok
        _thread_jobs, process_jobs, _skipped = _build_jobs(selected, st)

        remaining, hits, pending = _split_process_cache(
            process_jobs, st, use_cache=True
        )
        assert "secrets" in remaining
        assert "secrets" not in hits
        assert "secrets" in pending


# frob:ticket T-1445
class TestRunGatesUseCacheProcessGates:
    """`run_gates(..., use_cache=True)` end-to-end over a
    `_CACHEABLE_PROCESS_GATES` member -- the CLI-facing behavior
    `TestSplitProcessCache`/`TestRootGateCache` verify piecewise."""

    def test_second_warm_run_serves_process_gate_from_cache(
        self, tmp_path: Path
    ) -> None:
        """frob:tests src/frob/gates/__init__.py::run_gates"""
        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"drift", "archgate"})
        )
        first = run_gates(cfg, use_cache=True).danger_ok
        second = run_gates(cfg, use_cache=True).danger_ok
        assert first.violations == second.violations
        assert second.stats.timing_s["archgate"] == 0.0

    def test_tracked_file_edit_forces_process_gate_recompute(
        self, tmp_path: Path
    ) -> None:
        """A real tree edit must force a fresh `archgate` result, not a
        stale cached one -- the T-1445 correctness bar mirrored from
        `TestEvaluateCacheableGate.test_edit_to_touched_file_forces_miss`."""
        _write(tmp_path, "a.py", "def f():\n    pass\n")
        _git_init(tmp_path)
        cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"drift", "archgate"})
        )
        run_gates(cfg, use_cache=True)
        _write(tmp_path, "a.py", "def f():\n    return 1\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        second = run_gates(cfg, use_cache=True).danger_ok
        assert second.stats.timing_s["archgate"] != 0.0, (
            "a tracked-file edit must force a real archgate re-run, not a "
            "stale cache hit"
        )


# frob:ticket T-1445
class TestColdDiffOracleProcessGates:
    """T-1445's own cold-diff oracle, `TestColdDiffOracle`'s shape widened
    to a `_CACHEABLE_PROCESS_GATES` selection: `run_gates(use_cache=False)`
    and `run_gates(use_cache=True)` must agree across random edits for the
    process-pool gates too, not just the thread-pool `_CACHEABLE_GATES`."""

    def test_cache_agrees_with_cold_across_random_edits(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/__init__.py::run_gates"""
        rng = random.Random(4104)
        _git_init(tmp_path)
        selected = frozenset({"drift", "secrets", "archgate", "opaque"})
        cfg = GateConfig(root=str(tmp_path), base="main", gates=selected)
        files = [f"pkg/mod{i}.py" for i in range(3)]

        for round_ in range(6):
            action = rng.choice(["edit", "add", "remove", "noop"])
            if action == "edit" and files:
                target = rng.choice(files)
                _write(
                    tmp_path,
                    target,
                    f"def f_{round_}(x):\n    return x + {round_}\n",
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
            subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

            cold = run_gates(cfg, use_cache=False).danger_ok
            warm = run_gates(cfg, use_cache=True).danger_ok
            cold_fp = frozenset(
                (v.rule, v.file, v.line, v.message) for v in cold.violations
            )
            warm_fp = frozenset(
                (v.rule, v.file, v.line, v.message) for v in warm.violations
            )
            assert cold_fp == warm_fp, (
                f"round {round_} ({action}): cold/cache-aware evaluation disagree "
                f"symdiff={cold_fp ^ warm_fp}"
            )


# frob:ticket T-1445
class TestCacheTransparencyProcessGates:
    """INV-050's shared observational-transparency harness
    (`tests/_cache_transparency.py`), parameterized over the T-1445
    process-gate cache surface -- the ticket's own acceptance note asking
    for exactly this."""

    def test_root_gate_cache_observationally_transparent(self, tmp_path: Path) -> None:
        """frob:tests src/frob/gates/__init__.py::run_gates"""
        from tests._cache_transparency import run_cold_warm_sweep

        _git_init(tmp_path)
        rng = random.Random(2718)
        selected = frozenset({"drift", "secrets", "archgate"})
        cfg = GateConfig(root=str(tmp_path), base="main", gates=selected)
        files = [f"pkg/mod{i}.py" for i in range(3)]

        def mutate(rng: random.Random, round_: int) -> None:
            kind = rng.choice(("edit", "add", "remove", "revert"))
            if kind == "edit" and files:
                target = rng.choice(files)
                _write(tmp_path, target, f"def f_{round_}():\n    return {round_}\n")
            elif kind == "add":
                new_file = f"pkg/extra{round_}.py"
                _write(tmp_path, new_file, f"def g_{round_}():\n    pass\n")
                files.append(new_file)
            elif kind == "remove" and files:
                target = rng.choice(files)
                path = tmp_path / target
                if path.exists():
                    path.unlink()
                files.remove(target)
            # "revert" (and any branch that found nothing to act on) is a
            # deliberate no-op round -- the transparency property must also
            # hold when nothing changed between two calls.
            subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

        def cold_fingerprint() -> frozenset:
            report = run_gates(cfg, use_cache=False).danger_ok
            return frozenset(
                (v.rule, v.file, v.line, v.message) for v in report.violations
            )

        def warm_fingerprint() -> frozenset:
            report = run_gates(cfg, use_cache=True).danger_ok
            return frozenset(
                (v.rule, v.file, v.line, v.message) for v in report.violations
            )

        run_cold_warm_sweep(rng, 6, mutate, cold_fingerprint, warm_fingerprint)
