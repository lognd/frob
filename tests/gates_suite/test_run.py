import os
import subprocess
from pathlib import Path

import pytest

from frob.gates import (
    GateConfig,
    GateError,
    Severity,
    Violation,
    run_gates,
)
from frob.gitio import Diff, Hunk
from frob.graph import GraphSnapshot
from frob.tickets._store import write_ticket
from tests.conftest import (
    _first_rule,
    _git_init,
    _module_level_process_violation,
    _snapshot,
    _ticket,
    _write,
)


# frob:ticket T-0541
# frob:ticket T-0542
# frob:ticket T-0543
class TestRunGates:
    def test_run_gates_end_to_end(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::run_gates
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _git_init(tmp_path)
        cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"drift", "coverage"})
        )
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        assert "drift" in report.stats.counts
        assert "coverage" in report.stats.counts
        assert isinstance(report.violations, tuple)
        assert isinstance(report.waived, tuple)

    def test_run_gates_skips_scope_without_ticket(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"scope", "prework"})
        )
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        assert "scope" in report.stats.skipped
        assert "prework" in report.stats.skipped

    # frob:tests src/frob/gates/__init__.py::_build_ticket_scoped_jobs
    # frob:ticket T-0541
    # frob:ticket T-0542
    # frob:ticket T-0543
    def test_run_gates_blocks_scope_and_prework_when_no_ticket_touches_source(
        self, tmp_path: Path
    ) -> None:
        """B9: an off-convention branch (or `main`) with no `--ticket` and a
        diff that touches real source must not silently skip SCOPE001/
        PRE001 -- it must block instead."""
        _git_init(tmp_path)
        _write(tmp_path, "src/pkg/a.py", "def helper(x):\n    return x\n")
        cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"scope", "prework"})
        )
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        assert "scope" not in report.stats.skipped
        assert "prework" not in report.stats.skipped
        assert any(v.rule == "SCOPE001" for v in report.violations)
        assert any(v.rule == "PRE001" for v in report.violations)

    # frob:tests src/frob/gates/__init__.py::_build_ticket_scoped_jobs
    # frob:ticket T-0541
    # frob:ticket T-0542
    # frob:ticket T-0543
    def test_run_gates_still_skips_scope_and_prework_for_ledger_only_diff(
        self, tmp_path: Path
    ) -> None:
        """B9's fix must not fire on a `tickets.md`-only diff (ledger
        maintenance, e.g. archiving closed tickets, is a legitimate
        no-ticket main-branch operation)."""
        _git_init(tmp_path)
        _write(tmp_path, "tickets.md", "# tickets\n")
        cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"scope", "prework"})
        )
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        assert "scope" in report.stats.skipped
        assert "prework" in report.stats.skipped

    # frob:tests src/frob/gates/__init__.py::_b9_exempt_file
    # frob:ticket T-1817
    def test_run_gates_still_skips_scope_and_prework_for_sharded_ticket_diff(
        self, tmp_path: Path
    ) -> None:
        """T-1817: the same ledger exemption as `tickets.md` must cover the
        sharded `tickets/<id>/*` layout -- `frob ticket start`/`sweep`'s own
        auto-commit writes exactly this shape, and it must not trip a false
        PRE001/SCOPE001 on an otherwise clean, unscoped audit."""
        _git_init(tmp_path)
        _write(tmp_path, "tickets/T-0001/done-report.md", "## Done report\n")
        cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"scope", "prework"})
        )
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        assert "scope" in report.stats.skipped
        assert "prework" in report.stats.skipped

    # frob:tests src/frob/gates/__init__.py::_no_active_ticket_violation
    # frob:ticket T-1817
    def test_no_active_ticket_violation_names_the_diff_base(
        self, tmp_path: Path
    ) -> None:
        """T-1817: the B9 blocking message must name the merge-base `diff`
        was computed against -- otherwise the reported "N file(s)" count is
        unexplainable from a reader's clean `git status`."""
        _git_init(tmp_path)
        _write(tmp_path, "src/pkg/a.py", "def helper(x):\n    return x\n")
        cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"scope", "prework"})
        )
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        scope001 = next(v for v in report.violations if v.rule == "SCOPE001")
        assert "merge-base" in scope001.message

    # frob:tests src/frob/gates/__init__.py::_build_ticket_scoped_jobs
    # frob:ticket T-0541
    def test_run_gates_blocks_prework_when_diff_load_fails_with_no_ticket(
        self, tmp_path: Path
    ) -> None:
        """B9 remainder: a repo with no git history at all (detached-HEAD-
        shaped: `working_diff` has no merge-base and fails outright) and no
        derivable ticket must still block PRE001 loudly, not silently skip
        it. Before this fix, `_load_diff`'s degraded-empty placeholder made
        `no_ticket_blocks` see zero touched files, so PRE001 skipped even
        though the diff genuinely failed to load -- the exact B9 escape,
        reached through the diff-load-failure door instead of the
        off-convention-branch-name door. SCOPE001 already had a matching
        unconditional `diff_load_failed` check; PRE001 did not."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "m.py").write_text("def f(x):\n    return x\n")
        cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"scope", "prework"})
        )
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        assert "prework" not in report.stats.skipped
        pre001 = _first_rule(report.violations, "PRE001")
        assert pre001 is not None
        assert "failed to load" in pre001.message


# frob:ticket T-1148
class TestNativeAvailabilityGate:
    """T-1148: a declared `[[native]]` that fails to import must short-
    circuit `run_gates` with ONE honest `NATIVE001` finding, never a
    cascade of misattributed downstream errors (the 2026-07-28 incident's
    43 spurious DRIFT002s)."""

    def test_unimportable_native_short_circuits_run_gates_with_one_finding(
        self, tmp_path: Path
    ) -> None:
        _git_init(tmp_path)
        _write(
            tmp_path,
            "frob.toml",
            '[[native]]\nname = "frob_definitely_not_a_real_native_xyz"\n'
            'build_cmd = "uv run frob natives build"\n',
        )
        cfg = GateConfig(root=str(tmp_path), base="main")
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        assert len(report.violations) == 1
        violation = report.violations[0]
        assert violation.rule == "NATIVE001"
        assert "frob_definitely_not_a_real_native_xyz" in violation.message
        assert "uv run frob natives build" in violation.message
        assert report.waived == ()

    def test_every_native_importable_runs_the_normal_pipeline(
        self, tmp_path: Path
    ) -> None:
        """No `[[native]]` declared at all (the common case for a repo with
        no compiled extensions) must never trip the T-1148 short-circuit --
        `run_gates` proceeds to its normal multi-gate pipeline exactly as
        before this ticket."""
        _git_init(tmp_path)
        cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"scope", "prework"})
        )
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        assert not any(v.rule == "NATIVE001" for v in report.violations)


class TestRunJobsTimingAttribution:
    """T-0232: `_run_jobs` must attribute each job its OWN cost, not a
    number smeared across every job sharing the thread pool."""

    def test_cpu_bound_neighbor_does_not_inflate_a_cheap_jobs_timing(self) -> None:
        """Pin the regression this ticket was filed against: run one
        deliberately CPU-heavy job (busy-loops, holds the GIL) alongside
        several genuinely cheap jobs on the same `ThreadPoolExecutor`, as
        `_run_jobs` does for real gates. Wall-clock timing (the old
        behavior) would have every cheap job's *elapsed* converge toward
        the heavy job's -- the exact "secrets=39.71s sys=39.71s
        tickets=39.69s" symptom this ticket reports. CPU-time attribution
        must not: each cheap job's own reported cost stays small and
        distinct from the heavy job's, regardless of how long the run
        takes in total.
        """
        from collections.abc import Callable

        from frob.gates import _run_jobs

        def heavy() -> tuple[Violation, ...]:
            # Pure-Python busy work: holds the GIL, no I/O yields.
            total = 0
            for i in range(30_000_000):
                total += i
            return ()

        def cheap() -> tuple[Violation, ...]:
            return ()

        jobs: dict[str, Callable[[], tuple[Violation, ...]]] = {
            "heavy": heavy,
            "cheap_a": cheap,
            "cheap_b": cheap,
            "cheap_c": cheap,
        }
        _, _, timing = _run_jobs(jobs)

        assert timing["heavy"] > 0.05
        for name in ("cheap_a", "cheap_b", "cheap_c"):
            # A cheap job's OWN cpu time stays near zero; under the old
            # wall-clock scheme this would have been pulled up toward
            # timing["heavy"] by GIL contention.
            assert timing[name] < timing["heavy"] / 2, (
                f"{name} timing {timing[name]:.3f}s was pulled toward the "
                f"heavy job's {timing['heavy']:.3f}s -- attribution is "
                "shared/wrong again"
            )


# frob:ticket T-0947
class TestProcessPoolGates:
    """T-0415: CPU-bound gates (archgate, sys, clones, perf, pii_structural,
    secrets -- docs/audits/perf.md H3) run in a `ProcessPoolExecutor`
    instead of the shared thread pool, so the GIL no longer serializes
    them. `_run_combined_jobs` must (a) actually dispatch process jobs to a
    worker process, and (b) merge results back in `_CANONICAL_GATE_ORDER`
    regardless of pool/completion order, so output stays deterministic.

    T-0947 added `test_open_process_pool_preloads_forkserver_when_available`
    to this class -- covering `_open_process_pool`'s `forkserver`+preload
    cold-start fix -- without otherwise changing this class's pre-existing
    T-0415 tests."""

    def test_process_job_runs_in_a_separate_process(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_run_combined_jobs
        # frob:tests src/frob/gates/__init__.py::_run_process_gate
        # frob:waive COV006 reason="two \
        # sound-but-invisible-to-the-name-based-call-graph shapes in this file \
        # (T-0516): (1) this test submits _run_process_gate to a ProcessPoolExecutor \
        # by function reference (ppool.submit(_run_process_gate, ...)), not a \
        # name-call token in the test's own body; (2) \
        # test_canonical_gate_order_matches_all_gates and its siblings in \
        # TestGateOrderSetEquality below check _CANONICAL_GATE_ORDER/_ALL_GATES \
        # set-equality directly and never call _merge_canonical_order, the consumer \
        # whose correctness that invariant protects -- module-level constants have no \
        # symref for the graph to track. T-0525 gave COV006 a per-edge symref, so this \
        # waiver now only covers THIS edge (test's own frob:tests -> \
        # _merge_canonical_order binding); test_all_gates_is_subset_of_canonical_order \
        # below carries its own matching frob:waive COV006 (same reasoning, not a \
        # blanket reach); test_canonical_order_names_no_nonexistent_gate needs none -- \
        # its frob:tests directive lives inside its docstring, not a `#` comment, so \
        # it never creates a real TESTS edge for COV006 to flag in the first place \
        # (verified: a waiver placed there fired WAIVE004, 0 matching findings) (the \
        # T-0516 calibration ticket this comment used to point at)"

        from frob.gates import _ProcessJob, _run_combined_jobs

        process_jobs = {
            "archgate": _ProcessJob(
                _module_level_process_violation, (tmp_path, "archgate")
            ),
            "sys": _ProcessJob(_module_level_process_violation, (tmp_path, "sys")),
        }
        violations, counts, timing = _run_combined_jobs({}, process_jobs)
        assert counts["archgate"] == 1
        assert counts["sys"] == 1
        assert "archgate" in timing
        assert "sys" in timing
        pids = {v.message.split(":")[1] for v in violations}
        assert str(os.getpid()) not in pids, (
            "process-pool job ran in the parent process, not a worker -- "
            "no real parallelism"
        )

    def test_combined_jobs_merge_in_canonical_order(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_run_combined_jobs
        """Merge order must follow `_CANONICAL_GATE_ORDER` (drift before
        sys before archgate), not submission or completion order across
        the two pools -- this is what keeps `frob check` output byte-
        identical to the pre-T-0415 single-pool run."""
        from collections.abc import Callable

        from frob.gates import _ProcessJob, _run_combined_jobs

        def cheap_thread() -> tuple[Violation, ...]:
            return (
                Violation(
                    rule="A",
                    severity=Severity.WARN,
                    file="x",
                    line=1,
                    message="thread-drift",
                ),
            )

        thread_jobs: dict[str, Callable[[], tuple[Violation, ...]]] = {
            "drift": cheap_thread
        }
        process_jobs = {
            "sys": _ProcessJob(_module_level_process_violation, (tmp_path, "sys")),
            "archgate": _ProcessJob(
                _module_level_process_violation, (tmp_path, "archgate")
            ),
        }
        violations, _, _ = _run_combined_jobs(thread_jobs, process_jobs)
        assert violations[0].rule == "A"
        tags = [v.message.split(":")[0] for v in violations[1:]]
        # _CANONICAL_GATE_ORDER places "sys" before "archgate".
        assert tags == ["sys", "archgate"]

    def test_run_gates_output_is_identical_across_repeated_runs(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::run_gates
        """End-to-end determinism proof (T-0415 constraint 2): selecting a
        mix of thread-pool and process-pool gates and running `run_gates`
        twice on the same tree must produce byte-identical violation
        tuples (same content, same order) despite the process pool's
        results arriving in whatever order the OS schedules them."""
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _git_init(tmp_path)
        selected = frozenset({"drift", "coverage", "sys", "archgate", "secrets"})
        cfg = GateConfig(root=str(tmp_path), base="main", gates=selected)

        first = run_gates(cfg)
        second = run_gates(cfg)
        assert first.is_ok
        assert second.is_ok
        report1 = first.danger_ok
        report2 = second.danger_ok
        assert report1.violations == report2.violations
        assert report1.stats.counts == report2.stats.counts

    def test_combined_parallel_path_matches_fully_serial_path(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_run_combined_jobs
        # frob:tests src/frob/gates/__init__.py::_build_jobs
        """T-0415's explicit correctness requirement: the parallel path
        (thread pool + process pool via `_run_combined_jobs`) must produce
        the same violation SET as calling every job function serially,
        in-process, one at a time -- no double-work, no dropped results,
        no reordering-induced content drift. Compares as a sorted
        multiset (rule, file, line, message) since a purely serial
        for-loop naturally visits jobs in dict order, which already
        matches `_CANONICAL_GATE_ORDER` for `_build_jobs`'s output, but
        the assertion is written order-independent to test content, not
        incidental iteration order."""
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _git_init(tmp_path)
        selected = frozenset({"drift", "coverage", "sys", "archgate", "secrets"})
        cfg = GateConfig(root=str(tmp_path), base="main", gates=selected)

        from frob.gates import _build_jobs, _load_inputs, _run_combined_jobs

        inputs = _load_inputs(cfg)
        assert inputs.is_ok
        st = inputs.danger_ok
        thread_jobs, process_jobs, _skipped = _build_jobs(selected, st)

        parallel_violations, _, _ = _run_combined_jobs(thread_jobs, process_jobs)

        serial_violations: list[Violation] = [
            v for job in thread_jobs.values() for v in job()
        ] + [v for pj in process_jobs.values() for v in pj.func(*pj.args)]

        def key(v: Violation) -> tuple:
            return (v.rule, v.file, v.line, v.message)

        parallel_sorted = sorted(parallel_violations, key=key)
        serial_sorted = sorted(serial_violations, key=key)
        assert parallel_sorted == serial_sorted
        assert len(parallel_violations) == len(serial_violations)

    def test_open_process_pool_preloads_forkserver_when_available(
        self, tmp_path: Path
    ) -> None:
        # frob:ticket T-0947
        # frob:tests src/frob/gates/__init__.py::_open_process_pool
        # frob:tests src/frob/gates/__init__.py::_process_pool_start_method
        """T-0947: `_open_process_pool` must pick `forkserver` (with
        `_FORKSERVER_PRELOAD` set on the context) whenever this platform's
        `multiprocessing.get_all_start_methods()` offers it, and must
        actually call `set_forkserver_preload` on THAT context object
        (asserted via the context's own `_preload` attribute, not just
        absence of an exception) -- a `==` -> `!=` mutation on the
        start-method check would silently skip the preload call on every
        platform that supports `forkserver` (this repo's own CI/dev
        platform included) while still passing every OTHER test in this
        class, since none of them inspect the constructed pool's own
        `mp_context`."""
        import multiprocessing
        import multiprocessing.forkserver as mp_forkserver

        from frob.gates import (
            _FORKSERVER_PRELOAD,
            _open_process_pool,
            _process_pool_start_method,
            _ProcessJob,
        )

        process_jobs = {
            "clones": _ProcessJob(_module_level_process_violation, (tmp_path, "x")),
        }
        ppool = _open_process_pool(process_jobs)
        try:
            ctx = ppool._mp_context
            expected_method = _process_pool_start_method()
            assert ctx.get_start_method() == expected_method  # ty: ignore[unresolved-attribute]
            if expected_method == "forkserver":
                # `set_forkserver_preload` stores its argument on the
                # process-wide `multiprocessing.forkserver._forkserver`
                # singleton's own `_preload_modules` list, not on the
                # context object itself -- reading it back proves the
                # preload call actually ran rather than merely that no
                # exception was raised.
                assert list(
                    mp_forkserver._forkserver._preload_modules  # ty: ignore[unresolved-attribute]
                ) == list(_FORKSERVER_PRELOAD)
        finally:
            ppool.shutdown(wait=True)
        # frob:ticket T-3665
        # T-3665: NOT `assert "forkserver" in multiprocessing.get_all_
        # start_methods()` -- that hardcodes a POSIX-only platform
        # capability (CPython's `multiprocessing` never registers
        # `forkserver` on win32, since it needs `os.fork`), which is
        # real and not something `_process_pool_start_method` can work
        # around; that function's own contract (falls back to `spawn`
        # when `forkserver` is unavailable) is exactly what the
        # conditional block above already exercises. This closing
        # assertion re-checks the property that actually holds on every
        # platform: whichever method `_open_process_pool` picked is one
        # `multiprocessing` genuinely offers here.
        assert expected_method in multiprocessing.get_all_start_methods()

    # frob:ticket T-3665
    # frob:tests src/frob/gates/__init__.py::_process_pool_start_method kind="unit"
    def test_process_pool_start_method_falls_back_to_spawn_without_forkserver(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-3665 (win32 gates_suite campaign, T-3659): reproduces, on
        ANY platform, the exact win32 shape `_process_pool_start_method`
        must handle -- `multiprocessing.get_all_start_methods()`
        reporting `["spawn"]` only, no `"forkserver"` (CPython never
        registers `forkserver` on win32, since it needs `os.fork`).
        `_process_pool_start_method()` must fall back to `"spawn"`
        rather than raising or returning something
        `get_all_start_methods()` does not actually offer -- this is the
        exact property `test_open_process_pool_preloads_forkserver_when_
        available`'s OWN final assertion (before this ticket's fix)
        failed to check for on win32, by hardcoding `"forkserver" in
        get_all_start_methods()` unconditionally instead of checking
        against whichever method was actually chosen."""
        import multiprocessing

        from frob.gates import _process_pool_start_method

        monkeypatch.setattr(multiprocessing, "get_all_start_methods", lambda: ["spawn"])
        assert _process_pool_start_method() == "spawn"


class TestSeverityOverrides:
    def test_override_downgrades_and_ignores_garbage(self, tmp_path, monkeypatch):
        from frob.gates import Severity, Violation, _apply_severity_overrides

        (tmp_path / "frob.toml").write_text(
            '[gates.severity]\nCOV001 = "warn"\nDRIFT001 = "error"\nBAD = "loud"\n',
            encoding="utf-8",
        )
        violations = (
            Violation(
                rule="COV001",
                severity=Severity.ERROR,
                file="a.py",
                line=1,
                message="m",
            ),
            Violation(
                rule="SCOPE001",
                severity=Severity.ERROR,
                file="b.py",
                line=2,
                message="m",
            ),
        )
        out = _apply_severity_overrides(violations, tmp_path)
        assert out[0].severity == Severity.WARN
        assert out[1].severity == Severity.ERROR

    def test_no_frob_toml_is_identity(self, tmp_path):
        from frob.gates import Severity, Violation, _apply_severity_overrides

        violations = (
            Violation(
                rule="COV001",
                severity=Severity.ERROR,
                file="a.py",
                line=1,
                message="m",
            ),
        )
        assert _apply_severity_overrides(violations, tmp_path) == violations

    def test_sec110_promoted_to_error_gates_a_real_repo_toml(self, tmp_path):
        # frob:tests src/frob/gates/_waive.py::_apply_severity_overrides kind="unit"
        # T-0973 before-fails/after-passes fixture: proves the SEC110
        # WARN -> ERROR promotion in this repo's own frob.toml actually
        # changes gate outcome, not merely that the override table parses.
        # FAIL: with no [gates.severity] entry for SEC110 (the pre-T-0973
        # posture), an unwaived SEC110 finding stays WARN and never blocks
        # `frob check`.
        from frob.gates import Severity, Violation, _apply_severity_overrides

        (tmp_path / "frob.toml").write_text("", encoding="utf-8")
        finding = (
            Violation(
                rule="SEC110",
                severity=Severity.WARN,
                file="src/frob/example.py",
                line=1,
                message="reads os.environ.get(...)",
            ),
        )
        before = _apply_severity_overrides(finding, tmp_path)
        assert before[0].severity == Severity.WARN, (
            "FAIL case: no override leaves SEC110 at WARN"
        )

        # PASS: this repo's real frob.toml (with T-0973's SEC110 = "error"
        # line in place) promotes the same finding to ERROR.
        repo_root = Path(__file__).resolve().parents[2]
        after = _apply_severity_overrides(finding, repo_root)
        assert after[0].severity == Severity.ERROR, (
            "PASS case: repo frob.toml now gates SEC110 at ERROR"
        )


# frob:ticket T-0399
class TestOptInGates:
    """dup_gate/fuzz_gate/perf_gate are opt-in (default off in frob.toml);
    each gate must genuinely no-op when its config key is absent, and this
    is verified against a real GraphSnapshot/Diff rather than mocked."""

    # invariant spec: [INV-011](invariants/INV-011.md)
    def test_dup_gate_off_by_default(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_dup.py::dup_gate
        from frob.gates import dup_gate

        _write(tmp_path, "src/a.py", "def foo():\n    return 1\n")
        snap = _snapshot(tmp_path)
        diff = Diff(base="main", hunks=())
        violations = dup_gate(tmp_path, snap, diff)
        assert violations == ()

    # Bodies padded past DupConfig's default min_tokens=40 floor (dup_gate's
    # frob.toml reader only exposes enforce/threshold, not min_tokens, so
    # the fixture must clear the real default rather than a lowered one).
    _DUP_CLONE_SOURCE = (
        "def compute_total(items):\n"
        "    total = 0\n"
        "    for item in items:\n"
        "        total = total + item\n"
        "        if total > 1000:\n"
        "            total = 1000\n"
        "        total = total - 0\n"
        "        total = total + 0\n"
        "        total = total - 0\n"
        "        total = total + 0\n"
        "        total = total - 0\n"
        "    return total\n"
        "\n"
        "\n"
        "def compute_sum(values):\n"
        "    total = 0\n"
        "    for value in values:\n"
        "        total = total + value\n"
        "        if total > 1000:\n"
        "            total = 1000\n"
        "        total = total - 0\n"
        "        total = total + 0\n"
        "        total = total - 0\n"
        "        total = total + 0\n"
        "        total = total - 0\n"
        "    return total\n"
    )

    def test_dup_gate_fires_on_planted_clone_when_enabled(self, tmp_path: Path) -> None:
        """T-0191: [dup].enforce=true wires the smart R1-R5 pipeline into the
        gate -- a planted alpha-renamed clone (compute_total/compute_sum,
        identical after R3 canonicalization) must fail the gate when one
        side is touched."""
        # frob:tests src/frob/gates/_dup.py::dup_gate
        from frob.dup import _core as dup_core
        from frob.gates import dup_gate

        if not dup_core.core_available():
            pytest.skip("frob-core native extension not installed")
        _write(tmp_path, "src/a.py", self._DUP_CLONE_SOURCE)
        _write(
            tmp_path,
            "frob.toml",
            "[dup]\nenforce = true\nthreshold = 0.8\n",
        )
        snap = _snapshot(tmp_path)
        # compute_total is the first symbol in the file (lines 1-12).
        diff = Diff(base="main", hunks=(Hunk(file="src/a.py", span=(1, 12)),))
        violations = dup_gate(tmp_path, snap, diff)
        assert any(v.rule == "DUP001" for v in violations), violations

    def test_dup_gate_planted_clone_waived_passes(self, tmp_path: Path) -> None:
        """T-0191: a `frob:waive DUP001 reason=...` directive on the touched
        clone suppresses the violation via the normal waiver path -- the
        gate itself still reports it (waiving happens post-gate), but
        `_apply_waivers` removes it from the kept set with a reason."""
        from frob.dup import _core as dup_core
        from frob.gates import _apply_waivers, dup_gate

        if not dup_core.core_available():
            pytest.skip("frob-core native extension not installed")
        waived_source = (
            "def compute_total(items):\n"
            '    # frob:waive DUP001 reason="known clone, tracked in T-0191 fixture"\n'
            "    total = 0\n"
            "    for item in items:\n"
            "        total = total + item\n"
            "        if total > 1000:\n"
            "            total = 1000\n"
            "        total = total - 0\n"
            "        total = total + 0\n"
            "        total = total - 0\n"
            "        total = total + 0\n"
            "        total = total - 0\n"
            "    return total\n"
            "\n"
            "\n"
            "def compute_sum(values):\n"
            "    total = 0\n"
            "    for value in values:\n"
            "        total = total + value\n"
            "        if total > 1000:\n"
            "            total = 1000\n"
            "        total = total - 0\n"
            "        total = total + 0\n"
            "        total = total - 0\n"
            "        total = total + 0\n"
            "        total = total - 0\n"
            "    return total\n"
        )
        _write(tmp_path, "src/a.py", waived_source)
        _write(
            tmp_path,
            "frob.toml",
            "[dup]\nenforce = true\nthreshold = 0.8\n",
        )
        snap = _snapshot(tmp_path)
        diff = Diff(base="main", hunks=(Hunk(file="src/a.py", span=(1, 13)),))
        violations = dup_gate(tmp_path, snap, diff)
        assert any(v.rule == "DUP001" for v in violations), violations

        kept, waived = _apply_waivers(violations, snap)
        assert _first_rule(kept, "DUP001") is None
        waived_dup001 = _first_rule(waived, "DUP001")
        assert waived_dup001 is not None
        assert waived_dup001.waived is not None

    # frob:ticket T-0399
    def test_dup_gate_fails_closed_when_enforced_but_core_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0399 (gates-quality audit finding 2): [dup].enforce=true with
        frob-core unavailable must emit a blocking DUP003 ERROR, not
        silently return no violations -- a requested-but-unavailable
        control fails CLOSED."""
        # frob:tests src/frob/gates/_dup.py::dup_gate
        import frob.dup as dup_module
        from frob.gates import dup_gate

        monkeypatch.setattr(dup_module, "core_available", lambda: False)
        _write(tmp_path, "src/a.py", "def foo():\n    return 1\n")
        _write(tmp_path, "frob.toml", "[dup]\nenforce = true\n")
        snap = _snapshot(tmp_path)
        diff = Diff(base="main", hunks=())
        violations = dup_gate(tmp_path, snap, diff)
        assert len(violations) == 1
        assert violations[0].rule == "DUP003"
        assert violations[0].severity == Severity.ERROR

    def test_fuzz_gate_off_by_default(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fuzz.py::fuzz_gate
        # frob:tests src/frob/fuzz kind="integration"
        from frob.gates import fuzz_gate

        _write(tmp_path, "src/a.py", "def foo(x: int) -> int:\n    return x\n")
        snap = _snapshot(tmp_path)
        violations = fuzz_gate(tmp_path, snap)
        assert violations == ()

    def test_perf_gate_flags_list_membership_in_loop(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::perf_gate
        from frob.gates import perf_gate

        _write(
            tmp_path,
            "src/a.py",
            "def scan(items):\n"
            "    data = [1, 2, 3]\n"
            "    hits = 0\n"
            "    for x in items:\n"
            "        if x in data:\n"
            "            hits += 1\n"
            "    return hits\n",
        )
        snap = _snapshot(tmp_path)
        violations = perf_gate(tmp_path, snap)
        assert any(v.rule == "PERF001" for v in violations)

    def test_perf_gate_silences_unscannable_files(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::perf_gate
        # T-0203: non-code files (md/toml/json) have no registered tree-sitter
        # grammar and are unscannable by design -- perf_gate must filter them
        # out by extension before ever calling parse_file, so no
        # UnsupportedLanguage skip line is emitted for any of them.
        from frob.gates import perf_gate

        _write(tmp_path, "src/a.py", "def scan(x):\n    return x\n")
        _write(tmp_path, "docs/guides/agent-playbook.md", "# Playbook\n\nSome text.\n")
        _write(tmp_path, "pyproject.toml", "[project]\nname = 'x'\n")
        _write(tmp_path, "data.json", '{"key": "value"}\n')
        snap = _snapshot(tmp_path)

        with caplog.at_level("DEBUG", logger="frob.gates"):
            violations = perf_gate(tmp_path, snap)

        assert violations == ()
        assert not any("skipping unparsed" in rec.message for rec in caplog.records)
        assert not any("UnsupportedLanguage" in rec.message for rec in caplog.records)

    def test_perf_gate_still_reports_genuine_parse_failure(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::perf_gate
        # T-0203: a file with a registered grammar (.py) that still fails to
        # parse is a real failure, not a by-design skip -- it must still get
        # a visible skip message. tree-sitter's python grammar is too
        # error-tolerant to reliably produce a genuine ParseFailed from
        # source text alone (T-0203 investigation), so `parse_file` is
        # patched at the `frob.gates` import site to return the Err this
        # code path exists to surface.
        from typani import Err

        from frob.lang import LangError
        from frob.lang import parse_file as real_parse_file

        _write(tmp_path, "src/broken.py", "def scan(x):\n    return x\n")
        snap = _snapshot(tmp_path)

        # T-3034: `parse_file` gained a keyword-only `expect_heterogeneous`
        # param (T-2575) after this fake was written; the real caller now
        # passes it, so the fake must accept it too.
        def _fake_parse_file(path: Path, *, expect_heterogeneous: bool = False):
            if path.name == "broken.py":
                return Err(LangError.ParseFailed)
            return real_parse_file(path, expect_heterogeneous=expect_heterogeneous)

        monkeypatch.setattr("frob.lang.parse_file", _fake_parse_file)

        from frob.gates import perf_gate

        with caplog.at_level("DEBUG", logger="frob.gates"):
            perf_gate(tmp_path, snap)

        assert any(
            "skipping unparsed" in rec.message and "src/broken.py" in rec.message
            for rec in caplog.records
        )

    # frob:ticket T-2314
    def test_perf_gate_reports_a_repo_relative_file_not_absolute(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::perf_gate
        """T-2314 (MUST FAIL FIRST on main): before this fix, `perf_gate`'s
        `Violation.file` carried an ABSOLUTE path (`parse_file(root /
        rel_path)`'s `ParsedFile.path` flowed straight through to
        `_violation`), while every other gate -- and `frob:waive`'s own
        graph-derived edge `src` -- uses a repo-relative path. This is the
        root cause of the waiver-defect T-2314 exists to fix: `_match_
        waiver`'s file-level fallback does exact string equality, so an
        absolute `violation.file` could never match a relative waiver
        `src`."""
        from frob.gates import perf_gate

        _write(
            tmp_path,
            "src/a.py",
            "def scan(items):\n"
            "    for group in items:\n"
            "        for x in sorted(group):\n"
            "            pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = perf_gate(tmp_path, snap)
        assert violations, "expected at least one PERF004 violation"
        for v in violations:
            assert not Path(v.file).is_absolute(), (
                f"{v.rule} at {v.file!r} carries an absolute path"
            )
            assert v.file == "src/a.py"

    # frob:ticket T-3662
    # frob:tests src/frob/gates/__init__.py::_relativize_perf_violation_file kind="unit"
    def test_perf_gate_file_is_posix_shaped_for_a_nested_path(
        self, tmp_path: Path
    ) -> None:
        """T-3662 (win32 gates_suite campaign, T-3659): a NESTED PERF004
        site's `Violation.file` must always be POSIX-shaped (never a
        native separator) -- `test_perf_gate_reports_a_repo_relative_
        file_not_absolute`'s single-level `src/a.py` fixture cannot
        distinguish `str()` from `.as_posix()` on any platform (no
        separator appears either way); a nested path is where the two
        WOULD differ if `_relativize_perf_violation_file` regressed back
        to bare `str(rel)`."""
        from frob.gates import perf_gate

        _write(
            tmp_path,
            "src/nested/a.py",
            "def scan(items):\n"
            "    for group in items:\n"
            "        for x in sorted(group):\n"
            "            pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = perf_gate(tmp_path, snap)
        assert violations, "expected at least one PERF004 violation"
        for v in violations:
            assert v.file == "src/nested/a.py"
            assert "\\" not in v.file

    # frob:ticket T-2314
    def test_frob_waive_perf004_suppresses_the_named_finding(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::perf_gate
        """POSITIVE CONTROL 1: a PERF site carrying `frob:waive PERF004
        reason="..."` is suppressed once `_apply_waivers` runs over
        `perf_gate`'s own output -- the exact shape T-2314's ticket body
        names as REQUIRED acceptance criterion [0]."""
        from frob.gates import perf_gate
        from frob.gates._waive import _apply_waivers

        _write(
            tmp_path,
            "src/a.py",
            "def scan(items):\n"
            "    for group in items:\n"
            '        # frob:waive PERF004 reason="test waiver"\n'
            "        for x in sorted(group):\n"
            "            pass\n",
        )
        snap = _snapshot(tmp_path)
        kept, waived = _apply_waivers(perf_gate(tmp_path, snap), snap)
        assert not any(v.rule == "PERF004" for v in kept)
        assert any(v.rule == "PERF004" for v in waived)

    # frob:ticket T-2314
    def test_frob_waive_perf004_does_not_blanket_suppress_other_sites(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::perf_gate
        """MUST-STILL-PASS control (T-2314 acceptance [1]): an UNWAIVED
        genuine PERF004 site still reports -- the fix is a correct path
        normalization, never a blanket suppression of the rule."""
        from frob.gates import perf_gate
        from frob.gates._waive import _apply_waivers

        _write(
            tmp_path,
            "src/a.py",
            "def scan(items):\n"
            "    for group in items:\n"
            "        for x in sorted(group):\n"
            "            pass\n",
        )
        snap = _snapshot(tmp_path)
        kept, waived = _apply_waivers(perf_gate(tmp_path, snap), snap)
        assert any(v.rule == "PERF004" for v in kept)
        assert not waived

    # frob:ticket T-2314
    def test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses(
        self, frob_self_scan_snapshot: GraphSnapshot
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::perf_gate
        """POSITIVE CONTROL 3 (T-2314 acceptance): the ALREADY-EXISTING
        `frob:waive PERF008 reason="..."` at
        `src/frob/app/ticket_runner/_rapid_sweep.py:1652` -- the decisive
        control that proved this was a real mechanism defect, not one
        agent's malformed directive -- now actually suppresses its own
        finding when run against the real repo tree.

        T-3532: consumes the session-scoped `frob_self_scan_snapshot`
        fixture (this test's own name is already in `tests/conftest.py`'s
        `_SELF_SCAN_HEAVY_NAME_SUBSTRINGS`, pinning it to the same
        `frob_self_scan_heavy` xdist worker as every other consumer of
        that fixture) instead of this module's own `_snapshot(repo_root)`
        helper, which rebuilt a whole-repo `build_graph` snapshot
        independently AND pointed at this repo's real `.frob/cache.db`
        rather than a throwaway one."""
        from frob.gates import perf_gate
        from frob.gates._waive import _apply_waivers

        repo_root = Path(__file__).resolve().parents[2]
        snap = frob_self_scan_snapshot
        kept, waived = _apply_waivers(perf_gate(repo_root, snap), snap)
        assert not any(
            v.rule == "PERF008"
            and v.file == "src/frob/app/ticket_runner/_rapid_sweep.py"
            for v in kept
        ), "the existing _rapid_sweep.py:1652 waiver should suppress this finding"


class TestPerfReachDegradedMarker:
    """`_perf_reach_degraded_marker` (T-1578): a content-stale-but-still-
    importable `frob_core` is invisible to NATIVE001 (import-failure
    only) -- this closes that gap with a distinct `GateStats.skipped`
    marker name."""

    def test_no_stale_natives_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_perf_reach_degraded_marker
        from frob.gates import _perf_reach_degraded_marker

        monkeypatch.setattr("frob.strata.stale_natives", lambda root: ())

        assert _perf_reach_degraded_marker(tmp_path) is None

    def test_stale_frob_core_returns_the_marker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_perf_reach_degraded_marker
        from types import SimpleNamespace

        from frob.gates import (
            PERF_REACH_DEGRADED_SKIP_MARKER,
            _perf_reach_degraded_marker,
        )

        stale_entry = SimpleNamespace(spec=SimpleNamespace(name="frob_core"))
        monkeypatch.setattr("frob.strata.stale_natives", lambda root: (stale_entry,))

        assert _perf_reach_degraded_marker(tmp_path) == PERF_REACH_DEGRADED_SKIP_MARKER

    def test_stale_strata_core_also_returns_the_marker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_perf_reach_degraded_marker
        """T-1620: `strata_core` (the tree-sitter native EVERY perf rule's
        own parsed INPUT depends on via `frob.lang.parse_file`, not just
        the frob_core-reach-dependent PERF008/012) must ALSO trip this
        marker -- a stale-but-importable `strata_core` can silently parse
        fewer/wrong symbols, under-reporting even the natively-independent
        PERF001-004 lexical rules. Before T-1620 this returned None,
        which is exactly the gap the 2026-08-05 incident measured (PERF004
        read zero findings against a stale worktree while this marker
        reported healthy)."""
        from types import SimpleNamespace

        from frob.gates import (
            PERF_REACH_DEGRADED_SKIP_MARKER,
            _perf_reach_degraded_marker,
        )

        stale_entry = SimpleNamespace(spec=SimpleNamespace(name="strata_core"))
        monkeypatch.setattr("frob.strata.stale_natives", lambda root: (stale_entry,))

        assert _perf_reach_degraded_marker(tmp_path) == PERF_REACH_DEGRADED_SKIP_MARKER

    def test_stale_unrelated_native_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_perf_reach_degraded_marker
        """A stale native that is NEITHER `frob_core` NOR `strata_core`
        (this repo declares only those two today, but the check is a
        frozenset membership test, not a hardcoded pair) must not trip
        this perf-specific marker."""
        from types import SimpleNamespace

        from frob.gates import _perf_reach_degraded_marker

        stale_entry = SimpleNamespace(spec=SimpleNamespace(name="some_other_native"))
        monkeypatch.setattr("frob.strata.stale_natives", lambda root: (stale_entry,))

        assert _perf_reach_degraded_marker(tmp_path) is None


class TestScopeDigest:
    def test_digest_is_stable_and_scope_sensitive(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_digest kind="unit"
        from frob.gates import scope_digest

        _write(tmp_path, "src/a.py", "def a():\n    return 1\n")
        _write(tmp_path, "src/b.py", "def b():\n    return 2\n")
        snap = _snapshot(tmp_path)

        digest = scope_digest(("src/a.py",), snap)
        # Deterministic: the same scope over the same snapshot hashes identically.
        assert digest == scope_digest(("src/a.py",), snap)
        assert len(digest) == 64  # sha256 hexdigest
        # A wider scope that pulls in another matching file must change the hash.
        assert scope_digest(("src/*.py",), snap) != digest

    def test_non_matching_scope_is_empty_hash(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_digest kind="unit"
        from frob.gates import scope_digest

        _write(tmp_path, "src/a.py", "def a():\n    return 1\n")
        snap = _snapshot(tmp_path)

        # A scope matching nothing hashes the empty set -- distinct from any
        # scope that matches at least one file, and identical across snapshots.
        empty = scope_digest(("does/not/exist/*.py",), snap)
        assert empty == scope_digest(("nothing_here/*",), snap)
        assert empty != scope_digest(("src/a.py",), snap)


# frob:ticket T-0688
class TestRunGatesQueueFailureThreadsRealTicketError:
    """T-2710: `run_gates` used to collapse ANY ticket-queue load failure
    into the bare `GateError.QueueUnavailable` sentinel -- a reader could
    not tell a duplicate id from a malformed frontmatter file without a
    separate `frob ticket list`/`frob ticket show <id>` run. It must now
    propagate the REAL `TicketError` `load_queue` hit."""

    # frob:tests \
    # tests/gates_suite/test_run.py::TestRunGatesQueueFailureThreadsRealTicketError.test_duplicate_id_across_active_and_archive_surfaces_as_ticketerror  # noqa: E501
    def test_duplicate_id_across_active_and_archive_surfaces_as_ticketerror(
        self, tmp_path: Path
    ) -> None:
        """Must-fire control: the same id present in both v2-mode active
        and archive storage (T-2678's own DuplicateId incident shape)
        makes `load_queue` -- and therefore `run_gates` -- fail with the
        real `TicketError.DuplicateId`, not the generic
        `GateError.QueueUnavailable` sentinel."""
        from frob.tickets import TicketError
        from frob.tickets._store import write_archived_ticket

        _git_init(tmp_path)
        ticket = _ticket()
        write_ticket(tmp_path, ticket).danger_ok
        write_archived_ticket(tmp_path, ticket).danger_ok

        result = run_gates(GateConfig(root=str(tmp_path)))

        assert result.is_err
        assert result.danger_err == TicketError.DuplicateId
        assert result.danger_err != GateError.QueueUnavailable


# frob:ticket T-1155
class TestNewGateRuleDynamicResolution:
    """T-1155: `_new_gate_rule_acceptance.new_gate_rule_ids` must locate
    `_KNOWN_GATE_RULES` dynamically among `src/frob/gates/*.py` (any file,
    not a hard-coded path) and raise loudly -- never warn-and-skip -- when
    the literal cannot be resolved to exactly one candidate. Regression
    fixture for the T-1153 incident: the preflight silently going dark
    after T-1139 moved the literal from `gates/__init__.py` to
    `gates/_waive.py`."""

    def _git(self, root: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)

    def _init_repo(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._git(root, "init", "-q", "-b", "main")
        self._git(root, "config", "user.email", "test@example.com")
        self._git(root, "config", "user.name", "Test")

    # frob:tests tests/gates_suite/test_run.py::TestNewGateRuleDynamicResolution.test_resolves_when_literal_lives_in_a_different_file  # noqa: E501
    def test_resolves_when_literal_lives_in_a_different_file(
        self, tmp_path: Path
    ) -> None:
        """The literal starts life in `__init__.py`, then moves to
        `_waive.py` (mirroring the real T-1139 move) -- new-rule detection
        must keep working across that boundary revision with no code
        change of its own, proving resolution is dynamic, not tied to
        either specific filename."""
        from frob.tickets._new_gate_rule_acceptance import new_gate_rule_ids

        self._init_repo(tmp_path)
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        base_source = (
            "_KNOWN_GATE_RULES = frozenset(\n"
            "    {\n"
            '        "COV001",\n'
            '        "TEST001",\n'
            "    }\n"
            ")\n"
        )
        (gates_dir / "__init__.py").write_text(base_source, encoding="utf-8")
        self._git(tmp_path, "add", "-A")
        self._git(tmp_path, "commit", "-q", "-m", "base: literal lives in __init__.py")

        # Move the literal to _waive.py, exactly like T-1139, and add a
        # new rule id at the same time.
        (gates_dir / "__init__.py").write_text(
            "from frob.gates._waive import _KNOWN_GATE_RULES\n", encoding="utf-8"
        )
        (gates_dir / "_waive.py").write_text(
            base_source.replace(
                '        "TEST001",\n', '        "TEST001",\n        "NEWRULE001",\n'
            ),
            encoding="utf-8",
        )

        found = new_gate_rule_ids(tmp_path, base_ref="main")
        assert found == ("NEWRULE001",)

    # frob:tests tests/gates_suite/test_run.py::TestNewGateRuleDynamicResolution.test_raises_when_literal_missing_from_every_candidate  # noqa: E501
    def test_raises_when_literal_missing_from_every_candidate(
        self, tmp_path: Path
    ) -> None:
        """No `src/frob/gates/*.py` file carries the `_KNOWN_GATE_RULES`
        literal at all -- a structural resolution failure that must raise
        `GateRuleRegistryUnresolvable` loudly, never warn-and-skip the
        way the pre-T-1155 hard-coded-path version did."""
        from frob.tickets._new_gate_rule_acceptance import (
            GateRuleRegistryUnresolvable,
            new_gate_rule_ids,
        )

        self._init_repo(tmp_path)
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        (gates_dir / "__init__.py").write_text("# nothing here\n", encoding="utf-8")
        self._git(tmp_path, "add", "-A")
        self._git(tmp_path, "commit", "-q", "-m", "base: no registry literal anywhere")

        with pytest.raises(GateRuleRegistryUnresolvable):
            new_gate_rule_ids(tmp_path, base_ref="main")

    def test_no_gates_package_at_all_is_empty_not_a_raise(self, tmp_path: Path) -> None:
        """A checkout with no `src/frob/gates/` package at all (not a
        frob-gates repo) is the pre-existing "nothing to detect" case,
        distinct from a package that HAS the directory but lost the
        literal -- must stay `()`, never raise."""
        from frob.tickets._new_gate_rule_acceptance import new_gate_rule_ids

        self._init_repo(tmp_path)
        (tmp_path / "README.md").write_text("hi\n", encoding="utf-8")
        self._git(tmp_path, "add", "-A")
        self._git(tmp_path, "commit", "-q", "-m", "init")

        assert new_gate_rule_ids(tmp_path, base_ref="main") == ()
