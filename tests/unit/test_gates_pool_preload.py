"""T-3670 round 16: `frob.gates._run_process_jobs_serially_in_process` --
the `FROB_DISABLE_POOL_PRELOAD=1` degraded path that runs process-pool
gate jobs directly in the calling process/thread instead of via a
`ProcessPoolExecutor`, so a CI diag run can rule the pool in or out as
the win32 SIGINT sender without losing gate coverage. See
`docs/modules/process.md`'s T-3670 section for the full evidence chain
(T-3589/T-3648/T-3651/T-3657 lineage).
"""

from __future__ import annotations

from frob.findings import Severity, Violation
from frob.gates import _ProcessJob, _run_process_jobs_serially_in_process


def _fake_gate(count: int) -> tuple[Violation, ...]:
    """Picklable-shaped fake process-pool gate job: returns `count`
    trivial `Violation`s so the test can assert the accumulators saw
    exactly what this function returned."""
    return tuple(
        Violation(
            rule="FAKE001",
            severity=Severity.WARN,
            file="fake.py",
            line=i,
            message=f"fake violation {i}",
        )
        for i in range(count)
    )


# frob:ticket T-3670
class TestRunProcessJobsSerially:
    """T-3670: `_run_process_jobs_serially_in_process` must behave as a
    drop-in accumulator-populating replacement for the real
    `ProcessPoolExecutor` path (`_submit_process_pool` + `_drain_futures`
    combined), just serial and in-process."""

    # frob:tests src/frob/gates/__init__.py::_run_process_jobs_serially_in_process
    def test_runs_every_job_and_populates_accumulators(self) -> None:
        process_jobs = {
            "job_a": _ProcessJob(func=_fake_gate, args=(2,)),
            "job_b": _ProcessJob(func=_fake_gate, args=(0,)),
        }
        raw: dict[str, tuple[Violation, ...]] = {}
        counts: dict[str, int] = {}
        timing: dict[str, float] = {}

        _run_process_jobs_serially_in_process(process_jobs, raw, counts, timing)

        assert set(raw) == {"job_a", "job_b"}
        assert len(raw["job_a"]) == 2
        assert raw["job_b"] == ()
        assert counts["job_a"] == 2
        assert counts["job_b"] == 0
        assert timing["job_a"] >= 0.0
        assert timing["job_b"] >= 0.0

    # frob:tests src/frob/gates/__init__.py::_run_process_jobs_serially_in_process
    def test_empty_jobs_is_a_noop(self) -> None:
        raw: dict[str, tuple[Violation, ...]] = {}
        counts: dict[str, int] = {}
        timing: dict[str, float] = {}

        _run_process_jobs_serially_in_process({}, raw, counts, timing)

        assert raw == {}
        assert counts == {}
        assert timing == {}
