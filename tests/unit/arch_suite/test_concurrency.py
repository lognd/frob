"""Split from tests/unit/test_arch.py (T-1201)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.arch_suite.conftest import HAS_ARCH, analyze_project

pytestmark = pytest.mark.skipif(not HAS_ARCH, reason="frob.arch not available")




class TestForkPoolHazards:
    """`frob.arch._concurrency` -- pool-inside-pool, fork-after-threads,
    pipe-wait-deadlock, self-join-deadlock (docs/modules/arch.md#fork-pool-
    hazards)."""

    def test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool(
        self, tmp_path
    ):
        """A `ProcessPoolExecutor` construction reachable in the same
        function as a `ThreadPoolExecutor` construction fires
        `pool-inside-pool` at warning severity -- the T-0265 field-bug
        shape."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "combined.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor\n\n"
            "def run_combined(thread_jobs, process_jobs):\n"
            "    ppool = ProcessPoolExecutor(max_workers=2)\n"
            "    with ThreadPoolExecutor(max_workers=2) as tpool:\n"
            "        tpool.submit(lambda: None)\n"
            "    ppool.shutdown(wait=True)\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pool-inside-pool"]
        assert len(hits) == 1
        assert hits[0].severity == "warning"
        assert hits[0].symref == "combined.py::run_combined"

    def test_pool_inside_pool_discharges_on_real_repo_run_combined_jobs(self):
        """Acceptance (T-0767): the restructured gates tree carries ZERO
        fork/pool-hazard findings. T-0695's real-repo acceptance originally
        asserted `pool-inside-pool` FIRES on `_run_combined_jobs` (T-0581
        fixed the runtime ordering but left the structural co-occurrence in
        one function); the advisory channel is unwaivable by design, so
        T-0767 hoisted pool construction into `_open_process_pool` /
        `_run_thread_jobs` and this test's job flipped: it now regression-
        locks the discharge, across ALL four hazard categories so a future
        refactor reintroducing the co-occurrence (or any sibling hazard
        shape) in `src/frob/gates` fails loudly. The synthetic fixture
        above (`test_pool_inside_pool_fires_on_process_pool_alongside_
        thread_pool`) still proves the detector itself fires -- the
        detector was not weakened, only the real-repo hit discharged."""
        root = Path(__file__).parent.parent.parent / "src" / "frob" / "gates"
        result = analyze_project(root)
        hazard_categories = {
            "pool-inside-pool",
            "fork-after-threads",
            "pipe-wait-deadlock",
            "self-join-deadlock",
        }
        hits = [s for s in result.suggestions if s.category in hazard_categories]
        assert hits == []

    def test_self_join_deadlock_discharges_on_real_repo_vet_scan(self):
        """Acceptance (T-0794): `src/frob/vet` carries ZERO fork/pool-
        hazard findings. `_run_with_timeout` used to be dispatched as a
        worker task (`_scan_dependencies_parallel`'s `pool.submit`) AND
        itself construct+`shutdown` an inner single-worker pool in the
        same body -- the exact `self-join-deadlock` co-occurrence shape
        (T-0767 discharged the sibling `pool-inside-pool` case on
        `src/frob/gates` the same way). The advisory channel is
        unwaivable by design, so T-0794 hoisted the inner pool's
        construction into `_open_single_worker_pool` and its
        submit/await/shutdown into `_bounded_process_dependency`, leaving
        `_run_with_timeout` -- the function actually dispatched -- a pure
        orchestrator with no pool calls of its own. This test regression-
        locks the discharge, across ALL four hazard categories so a
        future refactor reintroducing the co-occurrence (or any sibling
        hazard shape) in `src/frob/vet` fails loudly. The synthetic
        fixture above (`test_self_join_deadlock_fires_when_dispatched_
        task_joins_its_pool`) still proves the detector itself fires --
        the detector was not weakened, only the real-repo hit
        discharged."""
        root = Path(__file__).parent.parent.parent / "src" / "frob" / "vet"
        result = analyze_project(root)
        hazard_categories = {
            "pool-inside-pool",
            "fork-after-threads",
            "pipe-wait-deadlock",
            "self-join-deadlock",
        }
        hits = [s for s in result.suggestions if s.category in hazard_categories]
        assert hits == []

    def test_fork_after_threads_fires_when_fork_follows_thread_start(self, tmp_path):
        """An `os.fork()` reachable AFTER a `Thread(...).start()` on the
        same function's line order fires `fork-after-threads`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "forker.py").write_text(
            "from __future__ import annotations\n"
            "import os\n"
            "import threading\n\n"
            "def spawn_then_fork():\n"
            "    t = threading.Thread(target=lambda: None)\n"
            "    t.start()\n"
            "    pid = os.fork()\n"
            "    return pid\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "fork-after-threads"]
        assert len(hits) == 1
        assert hits[0].symref == "forker.py::spawn_then_fork"

    def test_fork_before_threads_does_not_fire(self, tmp_path):
        """Forking BEFORE any thread starts is the safe order (T-0581's
        own fix shape) -- `fork-after-threads` must not fire on it."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "safe_forker.py").write_text(
            "from __future__ import annotations\n"
            "import os\n"
            "import threading\n\n"
            "def fork_then_spawn():\n"
            "    pid = os.fork()\n"
            "    t = threading.Thread(target=lambda: None)\n"
            "    t.start()\n"
            "    return pid\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "fork-after-threads"]
        assert hits == []

    def test_pipe_wait_deadlock_fires_without_communicate(self, tmp_path):
        """A `Popen(..., stdout=PIPE)` followed by a bare `.wait()` with no
        `.communicate()` anywhere in the function fires
        `pipe-wait-deadlock`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "piper.py").write_text(
            "from __future__ import annotations\n"
            "import subprocess\n\n"
            "def run_and_wait(cmd):\n"
            "    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)\n"
            "    proc.wait()\n"
            "    return proc.returncode\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pipe-wait-deadlock"]
        assert len(hits) == 1
        assert hits[0].symref == "piper.py::run_and_wait"

    def test_pipe_wait_deadlock_does_not_fire_with_communicate(self, tmp_path):
        """The same `Popen(..., stdout=PIPE)` shape, but drained via
        `.communicate()` instead of a bare `.wait()`, must not fire."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "safe_piper.py").write_text(
            "from __future__ import annotations\n"
            "import subprocess\n\n"
            "def run_and_communicate(cmd):\n"
            "    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)\n"
            "    out, err = proc.communicate()\n"
            "    return out\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pipe-wait-deadlock"]
        assert hits == []

    def test_self_join_deadlock_fires_when_dispatched_task_joins_its_pool(
        self, tmp_path
    ):
        """A function submitted to a pool elsewhere in the module, whose
        own body calls `.shutdown()`, fires `self-join-deadlock`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "selfjoin.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n"
            "def dispatch(pool):\n"
            "    pool.submit(worker, pool)\n\n"
            "def worker(pool):\n"
            "    pool.shutdown(wait=True)\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "self-join-deadlock"]
        assert len(hits) == 1
        assert hits[0].symref == "selfjoin.py::worker"

    def test_self_join_deadlock_does_not_fire_on_undispatched_join(self, tmp_path):
        """A function that calls `.join()` on a pool it owns, but is never
        itself submitted/started as a task, must not fire -- this is the
        ordinary caller-joins-its-own-pool shape, not the hazard."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "ordinary.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n"
            "def run_all(jobs):\n"
            "    pool = ThreadPoolExecutor(max_workers=2)\n"
            "    for job in jobs:\n"
            "        pool.submit(job)\n"
            "    pool.shutdown(wait=True)\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "self-join-deadlock"]
        assert hits == []

    def test_self_join_deadlock_does_not_fire_on_foreign_object_shutdown(
        self, tmp_path
    ):
        """T-3571: a function dispatched via `Thread(target=f, args=(obj,
        ...))` that calls `.shutdown()` on `obj` -- a FOREIGN object it was
        handed, not the dispatching `Thread` itself -- must not fire. This
        is the exact real shape of `_socketd.py::_idle_monitor`: it shuts
        down the `server` it was passed, never the `Thread` that dispatched
        it, which is the standard safe idle-shutdown pattern, not a self-
        join. Before T-3571 narrowed the detector to require the
        dispatcher's OWN object be passed back (`_DispatchRecord.self_pass_
        names`), this fired on any dispatched function that called
        shutdown/close/join on ANY parameter."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "idlemon.py").write_text(
            "from __future__ import annotations\n"
            "import threading\n\n"
            "def _idle_monitor(server, stop):\n"
            "    while not stop.is_set():\n"
            "        server.shutdown()\n"
            "        return\n\n"
            "def run_daemon(server, stop):\n"
            "    monitor = threading.Thread(target=_idle_monitor, args=(server, stop))\n"
            "    monitor.start()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "self-join-deadlock"]
        assert hits == []

    def test_self_join_deadlock_fires_on_genuine_thread_self_join(self, tmp_path):
        """T-3571 positive control: a function dispatched via `Thread(target
        =f, args=(t,))` where `t` IS the dispatching `Thread` object itself
        (passed to itself before `.start()`) and whose body calls
        `t.join()` -- the genuine self-join shape the narrowed correlation
        must still catch."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "genuine_selfjoin.py").write_text(
            "from __future__ import annotations\n"
            "import threading\n\n"
            "def worker(t):\n"
            "    t.join()\n\n"
            "def run():\n"
            "    t = threading.Thread(target=worker, args=(t,))\n"
            "    t.start()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "self-join-deadlock"]
        assert len(hits) == 1
        assert hits[0].symref == "genuine_selfjoin.py::worker"

    def test_self_join_deadlock_discharges_on_real_repo_socketd_idle_monitor(self):
        """Acceptance (T-3571): `src/frob/serve/_socketd.py` carries ZERO
        `self-join-deadlock` findings after the correlation narrowing --
        `_idle_monitor` shuts down the `server` object it was passed, not
        the dispatching `Thread`, and must not fire."""
        root = Path(__file__).parent.parent.parent / "src" / "frob" / "serve"
        result = analyze_project(root)
        hits = [
            s
            for s in result.suggestions
            if s.category == "self-join-deadlock" and "_socketd.py" in s.file
        ]
        assert hits == []


class TestAsyncEventLoopHazards:
    """`frob.arch._async_hazards` -- blocking-call-in-async,
    nested-event-loop, unawaited-coroutine, async-zero-awaits (T-0696,
    child 3 of the T-0693 concurrency-hazard umbrella), and
    sequential-independent-awaits (T-1027, T-0698's own disclosed cut)."""

    def test_blocking_call_in_async_fires_on_time_sleep(self, tmp_path):
        """`time.sleep` reachable inside an `async def` body, with no
        executor dispatch, fires `blocking-call-in-async`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "blocker.py").write_text(
            "from __future__ import annotations\n"
            "import time\n\n"
            "async def poll():\n"
            "    time.sleep(1)\n"
            "    return True\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "blocking-call-in-async"]
        assert len(hits) == 1
        assert hits[0].symref == "blocker.py::poll"
        assert hits[0].severity == "warning"

    def test_blocking_call_in_async_does_not_fire_via_to_thread(self, tmp_path):
        """The same `time.sleep` call, but dispatched via
        `asyncio.to_thread`, must not fire -- it is correctly offloaded
        off the event loop."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "safe_blocker.py").write_text(
            "from __future__ import annotations\n"
            "import asyncio\n"
            "import time\n\n"
            "async def poll():\n"
            "    await asyncio.to_thread(time.sleep, 1)\n"
            "    return True\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "blocking-call-in-async"]
        assert hits == []

    def test_nested_event_loop_fires_on_asyncio_run_inside_coroutine(self, tmp_path):
        """`asyncio.run(...)` reachable inside an `async def` body fires
        `nested-event-loop` -- it raises RuntimeError at runtime since a
        coroutine already runs on a loop."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "nested.py").write_text(
            "from __future__ import annotations\n"
            "import asyncio\n\n"
            "async def outer():\n"
            "    asyncio.run(inner())\n\n"
            "async def inner():\n"
            "    return 1\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "nested-event-loop"]
        assert len(hits) == 1
        assert hits[0].symref == "nested.py::outer"

    def test_nested_event_loop_does_not_fire_at_top_level_sync_code(self, tmp_path):
        """`asyncio.run(...)` called from ordinary (non-async) top-level
        code is the standard entry-point shape -- must not fire."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "entrypoint.py").write_text(
            "from __future__ import annotations\n"
            "import asyncio\n\n"
            "async def main():\n"
            "    return 1\n\n"
            "def cli():\n"
            "    asyncio.run(main())\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "nested-event-loop"]
        assert hits == []

    def test_unawaited_coroutine_fires_on_bare_call_statement(self, tmp_path):
        """A bare call to a module-defined `async def` function, used as
        its own statement (neither awaited, gathered, nor stored), fires
        `unawaited-coroutine`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "dropped.py").write_text(
            "from __future__ import annotations\n\n"
            "async def fetch():\n"
            "    return 1\n\n"
            "def trigger():\n"
            "    fetch()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "unawaited-coroutine"]
        assert len(hits) == 1
        assert hits[0].symref == "dropped.py::trigger"

    def test_unawaited_coroutine_does_not_fire_when_awaited_or_stored(self, tmp_path):
        """The same call, but awaited in one function and stored (never
        called bare) in another, must not fire either time."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "kept.py").write_text(
            "from __future__ import annotations\n\n"
            "async def fetch():\n"
            "    return 1\n\n"
            "async def awaits_it():\n"
            "    return await fetch()\n\n"
            "def stores_it():\n"
            "    coro = fetch()\n"
            "    return coro\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "unawaited-coroutine"]
        assert hits == []

    def test_async_zero_awaits_fires_on_no_await_body(self, tmp_path):
        """An `async def` whose body never awaits anything fires
        `async-zero-awaits` at suggestion severity."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "noawait.py").write_text(
            "from __future__ import annotations\n\n"
            "async def compute():\n"
            "    x = 1 + 1\n"
            "    return x\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "async-zero-awaits"]
        assert len(hits) == 1
        assert hits[0].symref == "noawait.py::compute"
        assert hits[0].severity == "suggestion"

    def test_async_zero_awaits_does_not_fire_when_awaiting(self, tmp_path):
        """An `async def` that awaits something in its own body must not
        fire `async-zero-awaits`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "hasawait.py").write_text(
            "from __future__ import annotations\n"
            "import asyncio\n\n"
            "async def compute():\n"
            "    await asyncio.sleep(0)\n"
            "    return 1\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "async-zero-awaits"]
        assert hits == []

    def test_sequential_independent_awaits_fires_on_unrelated_calls(self, tmp_path):
        """Three sequential awaits, none reading an earlier one's bound
        name, fire ONE `sequential-independent-awaits` suggestion naming
        all three call sites."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "gatherable.py").write_text(
            "from __future__ import annotations\n\n"
            "async def fetch_all():\n"
            "    a = await fetch_one()\n"
            "    b = await fetch_two()\n"
            "    c = await fetch_three()\n"
            "    return a, b, c\n\n"
            "async def fetch_one(): ...\n"
            "async def fetch_two(): ...\n"
            "async def fetch_three(): ...\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s
            for s in result.suggestions
            if s.category == "sequential-independent-awaits"
        ]
        assert len(hits) == 1
        assert hits[0].symref == "gatherable.py::fetch_all"
        assert hits[0].severity == "suggestion"
        assert "fetch_one" in hits[0].message
        assert "fetch_two" in hits[0].message
        assert "fetch_three" in hits[0].message

    def test_sequential_independent_awaits_does_not_fire_when_second_reads_first(
        self, tmp_path
    ):
        """The second await's argument reads the first await's bound
        name -- a real sequential dependency, must not fire."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "dependent.py").write_text(
            "from __future__ import annotations\n\n"
            "async def pipeline():\n"
            "    a = await fetch_one()\n"
            "    b = await fetch_two(a)\n"
            "    return b\n\n"
            "async def fetch_one(): ...\n"
            "async def fetch_two(x): ...\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s
            for s in result.suggestions
            if s.category == "sequential-independent-awaits"
        ]
        assert hits == []

    def test_sequential_independent_awaits_does_not_fire_on_single_await(
        self, tmp_path
    ):
        """A single await has no sibling to be independent OF -- must not
        fire (this check needs 2+ awaits in the same run)."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "single.py").write_text(
            "from __future__ import annotations\n\n"
            "async def fetch():\n"
            "    a = await fetch_one()\n"
            "    return a\n\n"
            "async def fetch_one(): ...\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s
            for s in result.suggestions
            if s.category == "sequential-independent-awaits"
        ]
        assert hits == []


class TestLockOrderingHazards:
    """`frob.arch._lock_ordering` -- interprocedural lock-order-cycle and
    lock-identity-unresolved (T-0694, child 2 of the T-0693 concurrency-
    hazard umbrella)."""

    def test_two_lock_ab_ba_cycle_fires_within_one_function(self, tmp_path):
        """`f` acquires `lock_a` then `lock_b`; `g` acquires `lock_b` then
        `lock_a` -- the classic AB/BA two-lock deadlock, entirely within
        each function's own body, fires `lock-order-cycle`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "deadlock.py").write_text(
            "from __future__ import annotations\n"
            "import threading\n\n"
            "lock_a = threading.Lock()\n"
            "lock_b = threading.Lock()\n\n\n"
            "def f():\n"
            "    with lock_a:\n"
            "        with lock_b:\n"
            "            pass\n\n\n"
            "def g():\n"
            "    with lock_b:\n"
            "        with lock_a:\n"
            "            pass\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "lock-order-cycle"]
        assert len(hits) == 1
        assert "lock_a" in hits[0].message
        assert "lock_b" in hits[0].message
        assert "deadlock.py::f" in hits[0].message
        assert "deadlock.py::g" in hits[0].message
        assert hits[0].severity == "error"  # T-2379

    def test_two_lock_ab_ba_cycle_fires_across_call_paths_via_callees(self, tmp_path):
        """The SAME cycle, but each function's second lock is acquired
        inside a CALLEE, not its own body -- the interprocedural
        requirement: `f` acquires `lock_a` then calls `helper_b` (which
        acquires `lock_b`); `g` acquires `lock_b` then calls `helper_a`
        (which acquires `lock_a`). Must still fire `lock-order-cycle`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "via_callee.py").write_text(
            "from __future__ import annotations\n"
            "import threading\n\n"
            "lock_a = threading.Lock()\n"
            "lock_b = threading.Lock()\n\n\n"
            "def helper_b():\n"
            "    with lock_b:\n"
            "        pass\n\n\n"
            "def helper_a():\n"
            "    with lock_a:\n"
            "        pass\n\n\n"
            "def f():\n"
            "    with lock_a:\n"
            "        helper_b()\n\n\n"
            "def g():\n"
            "    with lock_b:\n"
            "        helper_a()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "lock-order-cycle"]
        assert len(hits) == 1
        assert "lock_a" in hits[0].message
        assert "lock_b" in hits[0].message

    def test_consistent_global_order_does_not_fire(self, tmp_path):
        """Every function acquires `lock_a` before `lock_b`, never the
        reverse -- a consistent global order must stay silent."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "consistent.py").write_text(
            "from __future__ import annotations\n"
            "import threading\n\n"
            "lock_a = threading.Lock()\n"
            "lock_b = threading.Lock()\n\n\n"
            "def f():\n"
            "    with lock_a:\n"
            "        with lock_b:\n"
            "            pass\n\n\n"
            "def g():\n"
            "    with lock_a:\n"
            "        with lock_b:\n"
            "            pass\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "lock-order-cycle"]
        assert hits == []

    def test_reentrant_same_lock_does_not_fire(self, tmp_path):
        """A function acquiring the SAME `RLock` twice (nested `with`) must
        not fire `lock-order-cycle` -- reentrant use of one lock is never
        an ordering hazard."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "reentrant.py").write_text(
            "from __future__ import annotations\n"
            "import threading\n\n"
            "lock_a = threading.RLock()\n\n\n"
            "def f():\n"
            "    with lock_a:\n"
            "        with lock_a:\n"
            "            pass\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "lock-order-cycle"]
        assert hits == []

    def test_unresolvable_lock_identity_is_advisory(self, tmp_path):
        """A `with` statement over a lock-shaped PARAMETER (no module/class-
        level construction site this resolver can identify) fires
        `lock-identity-unresolved` at suggestion severity, fail-closed,
        instead of being silently dropped -- and a plain `with open(...)`
        (no lock-shaped name) must not fire anything at all."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "unresolved.py").write_text(
            "from __future__ import annotations\n\n\n"
            "def f(some_lock):\n"
            "    with some_lock:\n"
            "        pass\n"
        )
        (src_dir / "plain_open.py").write_text(
            "def f():\n    with open('x') as fh:\n        pass\n"
        )
        result = analyze_project(src_dir)
        unresolved_hits = [
            s for s in result.suggestions if s.category == "lock-identity-unresolved"
        ]
        assert len(unresolved_hits) == 1
        assert unresolved_hits[0].symref == "unresolved.py::f"
        assert unresolved_hits[0].severity == "suggestion"
        open_hits = [
            s
            for s in result.suggestions
            if s.file == "plain_open.py"
            and s.category in ("lock-identity-unresolved", "lock-order-cycle")
        ]
        assert open_hits == []


class TestSharedStateRaceHazards:
    """`src/frob/arch/_shared_state_race.py` -- unguarded-shared-write
    (T-0697, child 4 of the T-0693 concurrency-hazard umbrella)."""

    def test_unguarded_write_from_thread_submitted_function_fires(self, tmp_path):
        """A module-level dict written from a thread-submitted function
        with no enclosing lock fires `unguarded-shared-write`, naming the
        write site and the writing function."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "race.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n"
            "cache = {}\n\n\n"
            "def worker():\n"
            "    cache['x'] = 1\n\n\n"
            "def dispatch():\n"
            "    with ThreadPoolExecutor() as ex:\n"
            "        ex.submit(worker)\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "unguarded-shared-write"]
        assert len(hits) == 1
        assert "cache" in hits[0].message
        assert "race.py::worker" in hits[0].message
        assert hits[0].severity == "error"  # T-2379

    def test_same_write_under_with_lock_does_not_fire(self, tmp_path):
        """The same shape, but the write is enclosed by `with lock:` --
        must stay silent."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "race_guarded.py").write_text(
            "from __future__ import annotations\n"
            "import threading\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n"
            "cache = {}\n"
            "lock = threading.Lock()\n\n\n"
            "def worker():\n"
            "    with lock:\n"
            "        cache['x'] = 1\n\n\n"
            "def dispatch():\n"
            "    with ThreadPoolExecutor() as ex:\n"
            "        ex.submit(worker)\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "unguarded-shared-write"]
        assert hits == []

    def test_write_reachable_via_callee_of_dispatched_function_fires(self, tmp_path):
        """The dispatched function itself does nothing but call a helper
        that performs the unguarded write -- still fires, since the write
        is reachable from the dispatch point through the call graph."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "race_via_callee.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n"
            "totals = []\n\n\n"
            "def helper():\n"
            "    totals.append(1)\n\n\n"
            "def worker():\n"
            "    helper()\n\n\n"
            "def dispatch():\n"
            "    with ThreadPoolExecutor() as ex:\n"
            "        ex.submit(worker)\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "unguarded-shared-write"]
        assert len(hits) == 1
        assert "race_via_callee.py::helper" in hits[0].message
        assert "totals" in hits[0].message

    def test_write_not_reachable_from_any_dispatch_does_not_fire(self, tmp_path):
        """A module-level list written by a function that is never
        dispatched to a thread/task anywhere in the module -- must stay
        silent (plain sequential code is not this check's target)."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "sequential.py").write_text(
            "from __future__ import annotations\n\n"
            "totals = []\n\n\n"
            "def only_caller():\n"
            "    totals.append(1)\n\n\n"
            "def main():\n"
            "    only_caller()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "unguarded-shared-write"]
        assert hits == []

    def test_async_create_task_dispatch_fires_same_as_thread_submit(self, tmp_path):
        """A coroutine dispatched via `asyncio.create_task` that writes an
        unguarded module-level dict fires identically to the thread-submit
        shape."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "race_async.py").write_text(
            "from __future__ import annotations\n"
            "import asyncio\n\n"
            "state = {}\n\n\n"
            "async def worker():\n"
            "    state['x'] = 1\n\n\n"
            "async def dispatch():\n"
            "    asyncio.create_task(worker())\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "unguarded-shared-write"]
        assert len(hits) == 1
        assert "state" in hits[0].message
        assert "race_async.py::worker" in hits[0].message


class TestConcurrencyModelMismatch:
    """`src/frob/arch/_concurrency_model.py` -- gil-bound-in-threadpool and
    ipc-overhead-in-processpool (T-0698, child 5 of the T-0693
    concurrency-hazard umbrella)."""

    def test_cpu_bound_loop_in_threadpool_fires_gil_bound(self, tmp_path):
        """A pure-arithmetic loop function submitted to a ThreadPoolExecutor
        fires `gil-bound-in-threadpool`, naming the loop."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "cpu_thread.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n\n"
            "def crunch():\n"
            "    total = 0\n"
            "    for i in range(10_000_000):\n"
            "        total += i * i\n"
            "    return total\n\n\n"
            "def dispatch():\n"
            "    with ThreadPoolExecutor() as ex:\n"
            "        ex.submit(crunch)\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s for s in result.suggestions if s.category == "gil-bound-in-threadpool"
        ]
        assert len(hits) == 1
        assert "crunch" in hits[0].message
        assert hits[0].severity == "suggestion"

    def test_io_bound_socket_read_in_threadpool_does_not_fire(self, tmp_path):
        """A socket-read function dispatched to a ThreadPoolExecutor is the
        CORRECT model (IO-bound work belongs in a thread pool) -- must stay
        silent."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "io_thread.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n\n"
            "def read_socket(sock):\n"
            "    return sock.recv(4096)\n\n\n"
            "def dispatch(sock):\n"
            "    with ThreadPoolExecutor() as ex:\n"
            "        ex.submit(read_socket, sock)\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s for s in result.suggestions if s.category == "gil-bound-in-threadpool"
        ]
        assert hits == []

    def test_trivial_io_task_in_processpool_fires_ipc_overhead(self, tmp_path):
        """A trivially small IO-bound task dispatched to a
        ProcessPoolExecutor fires `ipc-overhead-in-processpool`."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "io_process.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ProcessPoolExecutor\n\n\n"
            "def fetch_page(url):\n"
            "    return requests.get(url)\n\n\n"
            "def dispatch(url):\n"
            "    with ProcessPoolExecutor() as ex:\n"
            "        ex.submit(fetch_page, url)\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s for s in result.suggestions if s.category == "ipc-overhead-in-processpool"
        ]
        assert len(hits) == 1
        assert "fetch_page" in hits[0].message

    def test_mixed_loop_and_io_function_never_fires_either_advisory(self, tmp_path):
        """A function that both loops AND calls IO is MIXED/UNKNOWN -- never
        confidently classified, so no advisory fires even when dispatched
        to a thread pool."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "mixed.py").write_text(
            "from __future__ import annotations\n"
            "from concurrent.futures import ThreadPoolExecutor\n\n\n"
            "def mixed_work(urls):\n"
            "    results = []\n"
            "    for url in urls:\n"
            "        results.append(requests.get(url))\n"
            "    return results\n\n\n"
            "def dispatch(urls):\n"
            "    with ThreadPoolExecutor() as ex:\n"
            "        ex.submit(mixed_work, urls)\n"
        )
        result = analyze_project(src_dir)
        hits = [
            s
            for s in result.suggestions
            if s.category in ("gil-bound-in-threadpool", "ipc-overhead-in-processpool")
        ]
        assert hits == []
