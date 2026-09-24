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
    # frob:tests src/frob/ci_report.py::TestFailure
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


_CI_FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "ci_report"


class TestParseSuiteResultLog:
    """T-5477: `parse_pytest_log` recognizing this repo's OWN
    `tests/conftest.py` xdist `SUITE-RESULT:`/`SUITE-RESULT-FAILED:`
    summary (with a `gh api .../logs` ISO-timestamp line prefix), which
    vanilla pytest's own `_RESULT_LINE`/`_SUMMARY_LINE` regexes never
    match under this repo's `-n auto --dist=loadgroup` addopts (module
    docstring's WHY NOT POSITIONAL section). Fixtures are TRIMMED real
    captures from CI run 35951365410 (dev @ 9e0c89bb19)."""

    # frob:tests tests/test_ci_report.py::TestParseSuiteResultLog.test_recovers_all_19_real_failing_node_ids  # noqa: E501
    # frob:tests src/frob/ci_report.py::parse_pytest_log kind="unit"
    def test_recovers_all_19_real_failing_node_ids(self) -> None:
        """MUST-FIRE: the real trimmed ubuntu log (run 35951365410, job
        107480417008) recovers exactly the 19 failing node ids the
        module's own docstring says it exists to name -- the SAME set
        that was, before this fix, extracted by hand (ticket body)."""
        text = (_CI_FIXTURE_ROOT / "run_35951365410_ubuntu_trimmed.log").read_text(
            encoding="utf-8"
        )
        outcome, failures = parse_pytest_log(text, truncated=False)
        assert outcome == "failures"
        node_ids = {f.node_id for f in failures}
        assert len(node_ids) == 19, node_ids
        assert (
            "tests/gates_suite/test_sys_assume_template.py::"
            "TestSelfaudit001TemplatedAssume::"
            "test_red_on_todays_design_frob_strata" in node_ids
        )
        assert (
            "tests/vet_suite/test_fingerprint.py::TestFingerprintScan::"
            "test_scan_directory_fingerprints_excludes_the_catalog_itself" in node_ids
        )

    # frob:tests tests/test_ci_report.py::TestParseSuiteResultLog.test_nested_subprocess_vanilla_failed_line_is_not_the_outer_result  # noqa: E501
    # frob:tests src/frob/ci_report.py::parse_pytest_log kind="unit"
    def test_nested_subprocess_vanilla_failed_line_is_not_the_outer_result(
        self,
    ) -> None:
        """The fixture also contains a NESTED, vanilla-pytest-shaped
        `FAILED tests/integration/test_logging_integration.py::... -
        AssertionError: ...` line and its own `1 failed, 16 passed`
        summary, from `test_scaffold_dx.py`'s generated-project pytest
        subprocess -- neither must appear in the recovered node ids nor
        change the outer run's own failed-count (SUITE-RESULT is always
        authoritative once present, per `_parse_suite_result_log`'s own
        docstring)."""
        text = (_CI_FIXTURE_ROOT / "run_35951365410_ubuntu_trimmed.log").read_text(
            encoding="utf-8"
        )
        _outcome, failures = parse_pytest_log(text, truncated=False)
        node_ids = {f.node_id for f in failures}
        assert (
            "tests/integration/test_logging_integration.py::"
            "test_log_line_reaches_stdout" not in node_ids
        )
        assert len(node_ids) == 19, node_ids

    # frob:tests tests/test_ci_report.py::TestParseSuiteResultLog.test_passing_job_stays_quiet  # noqa: E501
    # frob:tests src/frob/ci_report.py::parse_pytest_log kind="unit"
    def test_passing_job_stays_quiet(self) -> None:
        """MUST-STAY-QUIET: a real passing job's trimmed log
        (`SUITE-RESULT: exitstatus=0 ... failed=0`) reports `"clean"`
        with zero failures -- the SUITE-RESULT path must not manufacture
        findings out of a genuinely green run."""
        text = (_CI_FIXTURE_ROOT / "passing_job_trimmed.log").read_text(
            encoding="utf-8"
        )
        outcome, failures = parse_pytest_log(text, truncated=False)
        assert outcome == "clean"
        assert failures == ()


class TestBuildJobReport:
    # frob:tests src/frob/ci_report.py::JobReport
    def test_clean_job(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # frob:tests src/frob/ci_report.py::build_job_report
        job = JobSummary(
            job_id="j1", name="ubuntu", status="completed", conclusion="success"
        )
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

    # frob:tests src/frob/ci_report.py::JobReport
    # frob:tests src/frob/ci_report.py::FailureCluster
    def test_failures_clustered(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ci_report.py::build_job_report
        job = JobSummary(
            job_id="j2", name="macos", status="completed", conclusion="failure"
        )
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
        job = JobSummary(
            job_id="j3", name="windows", status="completed", conclusion="failure"
        )
        monkeypatch.setattr(
            ci_report_mod, "job_log", lambda root, run_id, job_id: Err(GhError.EmptyLog)
        )
        result = build_job_report(tmp_path, "r1", job)
        assert result.is_err
        assert result.danger_err == GhError.EmptyLog


class TestBuildRunReport:
    # frob:tests src/frob/ci_report.py::RunReport
    def test_all_jobs_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ci_report.py::build_run_report
        jobs = (
            JobSummary(
                job_id="j1", name="ubuntu", status="completed", conclusion="success"
            ),
            JobSummary(
                job_id="j2", name="macos", status="completed", conclusion="failure"
            ),
        )
        monkeypatch.setattr(
            ci_report_mod,
            "view_run",
            lambda root, run_id: Ok(
                RunDetail(
                    run_id=run_id, status="completed", conclusion="failure", jobs=jobs
                )
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
            JobSummary(
                job_id="j1", name="ubuntu", status="completed", conclusion="cancelled"
            ),
            JobSummary(
                job_id="j2", name="macos", status="completed", conclusion="failure"
            ),
        )
        monkeypatch.setattr(
            ci_report_mod,
            "view_run",
            lambda root, run_id: Ok(
                RunDetail(
                    run_id=run_id, status="completed", conclusion="cancelled", jobs=jobs
                )
            ),
        )

        def fake_job_log(root, run_id, job_id):  # noqa: ANN001, ANN201
            if job_id == "j1":
                return Err(GhError.EmptyLog)
            return Ok(
                JobLog(job_id=job_id, text=_FAILING_LOG, empty=False, truncated=False)
            )

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
    failure = TestFailure(
        node_id="x::y", kind="failed", reason="boom", signature="failed:boom"
    )
    with pytest.raises(Exception):
        failure.node_id = "changed"  # type: ignore[misc]
