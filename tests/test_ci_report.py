"""Tests for frob.ci_report -- structured CI failure reporting on top of
frob.ghio (docs/modules/ci_report.md). Every test fakes at the
frob.ghio boundary (monkeypatching job_log/view_run) so this file never
depends on gh or a real network call, mirroring tests/test_ghio.py's own
discipline."""

from __future__ import annotations

from pathlib import Path

import pytest
from typani import Err, Ok

import frob.ci_report as ci_report_mod
from frob.ci_report import (
    TestFailure,
    build_job_report,
    build_run_report,
    parse_pytest_log,
)
from frob.ghio import GhError, JobLog, JobSummary, RunDetail

_CLEAN_LOG = """\
collected 3 items

test_a.py::test_one PASSED
test_a.py::test_two PASSED

============================== 3 passed in 1.23s ==============================
"""

_FAILING_LOG = """\
collected 4 items

=================================== FAILURES ===================================
_______________________ test_one _______________________
    assert 1 == 2
AssertionError: assert 1 == 2

=========================== short test summary info ============================
FAILED test_a.py::test_one - AssertionError: assert 1 == 2
FAILED test_a.py::test_two - AssertionError: assert 5 == 6
FAILED test_a.py::test_three - ValueError: bad value '123'
=================== 3 failed, 1 passed in 4.56s ====================
"""

_TRUNCATED_LOG = """\
collected 40 items

test_a.py::test_one PASSED
test_a.py::test_two PASSED
"""


class TestParsePytestLog:
    def test_parses_named_failures(self) -> None:
        # frob:tests src/frob/ci_report.py::parse_pytest_log
        outcome, failures = parse_pytest_log(_FAILING_LOG, truncated=False)
        assert outcome == "failures"
        node_ids = {f.node_id for f in failures}
        assert node_ids == {
            "test_a.py::test_one",
            "test_a.py::test_two",
            "test_a.py::test_three",
        }
        # the two AssertionErrors on differing values must share a
        # cluster signature; the ValueError must not.
        assert failures[0].signature == failures[1].signature
        assert failures[2].signature != failures[0].signature

    def test_clean_run_is_no_failures(self) -> None:
        # frob:tests src/frob/ci_report.py::parse_pytest_log
        outcome, failures = parse_pytest_log(_CLEAN_LOG, truncated=False)
        assert outcome == "clean"
        assert failures == ()

    def test_no_result_line_is_not_recoverable(self) -> None:
        # frob:tests src/frob/ci_report.py::parse_pytest_log
        outcome, failures = parse_pytest_log(_TRUNCATED_LOG, truncated=False)
        assert outcome == "not_recoverable"
        assert failures == ()

    def test_truncated_with_no_evidence_is_not_recoverable(self) -> None:
        # frob:tests src/frob/ci_report.py::parse_pytest_log
        outcome, failures = parse_pytest_log(_TRUNCATED_LOG, truncated=True)
        assert outcome == "not_recoverable"
        assert failures == ()

    def test_never_reports_clean_for_a_truncated_run_with_apparent_result(
        self,
    ) -> None:
        # frob:tests src/frob/ci_report.py::parse_pytest_log
        # A cancelled run whose captured bytes happen to end on a clean
        # result line must still not be trusted as clean.
        outcome, failures = parse_pytest_log(_CLEAN_LOG, truncated=True)
        assert outcome == "not_recoverable"
        assert failures == ()


class TestBuildJobReport:
    def test_clean_job(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # frob:tests src/frob/ci_report.py::build_job_report
        job = JobSummary(job_id="j1", name="ubuntu", status="completed", conclusion="success")
        monkeypatch.setattr(
            ci_report_mod,
            "job_log",
            lambda root, run_id, job_id: Ok(
                JobLog(job_id=job_id, text=_CLEAN_LOG, empty=False, truncated=False)
            ),
        )
        result = build_job_report(tmp_path, "r1", job)
        assert result.is_ok
        report = result.danger_ok
        assert report.outcome == "clean"
        assert report.failures == ()
        assert report.clusters == ()

    def test_failures_clustered(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ci_report.py::build_job_report
        job = JobSummary(job_id="j2", name="macos", status="completed", conclusion="failure")
        monkeypatch.setattr(
            ci_report_mod,
            "job_log",
            lambda root, run_id, job_id: Ok(
                JobLog(job_id=job_id, text=_FAILING_LOG, empty=False, truncated=False)
            ),
        )
        result = build_job_report(tmp_path, "r1", job)
        assert result.is_ok
        report = result.danger_ok
        assert report.outcome == "failures"
        assert len(report.failures) == 3
        # two AssertionErrors cluster together, one ValueError stands alone
        assert len(report.clusters) == 2
        sizes = sorted(len(c.node_ids) for c in report.clusters)
        assert sizes == [1, 2]

    def test_empty_log_propagates_gherror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ci_report.py::build_job_report
        job = JobSummary(job_id="j3", name="windows", status="completed", conclusion="failure")
        monkeypatch.setattr(
            ci_report_mod, "job_log", lambda root, run_id, job_id: Err(GhError.EmptyLog)
        )
        result = build_job_report(tmp_path, "r1", job)
        assert result.is_err
        assert result.danger_err == GhError.EmptyLog


class TestBuildRunReport:
    def test_all_jobs_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ci_report.py::build_run_report
        jobs = (
            JobSummary(job_id="j1", name="ubuntu", status="completed", conclusion="success"),
            JobSummary(job_id="j2", name="macos", status="completed", conclusion="failure"),
        )
        monkeypatch.setattr(
            ci_report_mod,
            "view_run",
            lambda root, run_id: Ok(
                RunDetail(run_id=run_id, status="completed", conclusion="failure", jobs=jobs)
            ),
        )

        def fake_job_log(root, run_id, job_id):  # noqa: ANN001, ANN201
            text = _CLEAN_LOG if job_id == "j1" else _FAILING_LOG
            return Ok(JobLog(job_id=job_id, text=text, empty=False, truncated=False))

        monkeypatch.setattr(ci_report_mod, "job_log", fake_job_log)

        result = build_run_report(tmp_path, "r1")
        assert result.is_ok
        report = result.danger_ok
        assert report.run_id == "r1"
        assert len(report.jobs) == 2
        by_id = {j.job_id: j for j in report.jobs}
        assert by_id["j1"].outcome == "clean"
        assert by_id["j2"].outcome == "failures"

    def test_one_job_log_failure_degrades_not_aborts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ci_report.py::build_run_report
        jobs = (
            JobSummary(job_id="j1", name="ubuntu", status="completed", conclusion="cancelled"),
            JobSummary(job_id="j2", name="macos", status="completed", conclusion="failure"),
        )
        monkeypatch.setattr(
            ci_report_mod,
            "view_run",
            lambda root, run_id: Ok(
                RunDetail(run_id=run_id, status="completed", conclusion="cancelled", jobs=jobs)
            ),
        )

        def fake_job_log(root, run_id, job_id):  # noqa: ANN001, ANN201
            if job_id == "j1":
                return Err(GhError.EmptyLog)
            return Ok(JobLog(job_id=job_id, text=_FAILING_LOG, empty=False, truncated=False))

        monkeypatch.setattr(ci_report_mod, "job_log", fake_job_log)

        result = build_run_report(tmp_path, "r1")
        assert result.is_ok
        report = result.danger_ok
        assert len(report.jobs) == 2
        by_id = {j.job_id: j for j in report.jobs}
        # the cancelled ubuntu job never silently reports zero failures
        assert by_id["j1"].outcome == "not_recoverable"
        assert by_id["j1"].failures == ()
        # the unrelated macos job's own report is unaffected
        assert by_id["j2"].outcome == "failures"
        assert len(by_id["j2"].failures) == 3


def test_test_failure_model_is_frozen() -> None:
    # frob:tests src/frob/ci_report.py::TestFailure
    failure = TestFailure(node_id="x::y", kind="failed", reason="boom", signature="failed:boom")
    with pytest.raises(Exception):
        failure.node_id = "changed"  # type: ignore[misc]
