"""Unit tests for `frob.app.ci_runner` (T-2982, CI-1: `frob ci report
<run-id>`). Every test fakes at the `frob.ci_report.build_run_report`
boundary (mirrors `tests/test_ci_report.py`'s own `frob.ghio` boundary
fake), so this file never depends on `gh` being installed or authenticated.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typani import Err, Ok

import frob.app.ci_runner as ci_runner_mod
from frob.app.ci_runner import run
from frob.app.config import AppConfig
from frob.ci_report import FailureCluster, JobReport, RunReport, TestFailure
from frob.ghio import GhError

_KNOWN_CLUSTER_REPORT = RunReport(
    run_id="1074",
    conclusion="failure",
    jobs=(
        JobReport(
            job_id="j1",
            name="ubuntu",
            conclusion="failure",
            outcome="failures",
            failures=(
                TestFailure(
                    node_id="tests/test_x.py::test_one",
                    kind="failed",
                    reason="AssertionError: assert 1 == 2",
                    signature="failed:AssertionError:assert # == #",
                ),
                TestFailure(
                    node_id="tests/test_x.py::test_two",
                    kind="failed",
                    reason="AssertionError: assert 3 == 4",
                    signature="failed:AssertionError:assert # == #",
                ),
            ),
            clusters=(
                FailureCluster(
                    signature="failed:AssertionError:assert # == #",
                    node_ids=(
                        "tests/test_x.py::test_one",
                        "tests/test_x.py::test_two",
                    ),
                    sample_reason="AssertionError: assert 1 == 2",
                ),
            ),
            truncated=False,
        ),
        JobReport(
            job_id="j2",
            name="macos",
            conclusion="failure",
            outcome="failures",
            failures=(
                TestFailure(
                    node_id="tests/test_x.py::test_one",
                    kind="failed",
                    reason="AssertionError: assert 1 == 2",
                    signature="failed:AssertionError:assert # == #",
                ),
                TestFailure(
                    node_id="tests/test_y.py::test_platform_only",
                    kind="failed",
                    reason="OSError: mac-only",
                    signature="failed:OSError:mac-only",
                ),
            ),
            clusters=(
                FailureCluster(
                    signature="failed:AssertionError:assert # == #",
                    node_ids=("tests/test_x.py::test_one",),
                    sample_reason="AssertionError: assert 1 == 2",
                ),
                FailureCluster(
                    signature="failed:OSError:mac-only",
                    node_ids=("tests/test_y.py::test_platform_only",),
                    sample_reason="OSError: mac-only",
                ),
            ),
            truncated=False,
        ),
    ),
)

_GREEN_REPORT = RunReport(
    run_id="2000",
    conclusion="success",
    jobs=(
        JobReport(
            job_id="j1",
            name="ubuntu",
            conclusion="success",
            outcome="clean",
            failures=(),
            clusters=(),
            truncated=False,
        ),
        JobReport(
            job_id="j2",
            name="macos",
            conclusion="success",
            outcome="clean",
            failures=(),
            clusters=(),
            truncated=False,
        ),
    ),
)


def _cfg(**overrides: Any) -> AppConfig:
    """A minimal `AppConfig` for `frob ci report`, mirroring `tests/
    unit/verify/test_verify_runner.py`'s own minimal-construction
    precedent."""
    base: dict[str, Any] = {"ci_command": "report", "ci_run_id": "1074"}
    base.update(overrides)
    return AppConfig(**base)


class TestCiReportParity:
    # frob:tests src/frob/app/ci_runner.py::run kind="unit"
    def test_parity_with_build_run_report(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A fixture log with a known cluster signature: `frob ci report
        --json`'s output equals `build_run_report`'s own return
        (`RunReport.model_dump()`), the parity control this leaf's brief
        requires."""
        monkeypatch.setattr(
            ci_runner_mod,
            "build_run_report",
            lambda root, run_id: Ok(_KNOWN_CLUSTER_REPORT),
        )
        cfg = _cfg(ci_json=True, ci_path=tmp_path)
        run(cfg)
        printed = capsys.readouterr().out
        rendered = json.loads(printed)
        assert rendered == json.loads(_KNOWN_CLUSTER_REPORT.model_dump_json())

    # frob:tests src/frob/app/ci_runner.py::_print_report_human kind="unit"
    def test_human_output_names_the_known_cluster_and_diff(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(
            ci_runner_mod,
            "build_run_report",
            lambda root, run_id: Ok(_KNOWN_CLUSTER_REPORT),
        )
        cfg = _cfg(ci_path=tmp_path)
        run(cfg)
        printed = capsys.readouterr().out
        assert "tests/test_x.py::test_one" in printed
        assert "tests/test_y.py::test_platform_only" in printed
        # cross-platform diff: the AssertionError signature is shared,
        # the OSError signature is macos-only.
        assert "shared:" in printed
        assert "macos-only:" in printed
        assert "test_x.py" in printed


class TestCiReportMustStayQuiet:
    # frob:tests src/frob/app/ci_runner.py::_print_report_human kind="unit"
    def test_fully_green_run_prints_zero_failures_not_empty(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A fully green run prints an explicit statement of zero
        failures -- never empty output, which would be indistinguishable
        from a report that failed to run at all (the silent-zero doctrine
        `frob.ci_report`'s own module docstring applies)."""
        monkeypatch.setattr(
            ci_runner_mod, "build_run_report", lambda root, run_id: Ok(_GREEN_REPORT)
        )
        cfg = _cfg(ci_path=tmp_path)
        run(cfg)
        printed = capsys.readouterr().out
        assert printed.strip() != ""
        assert "no failures" in printed


class TestCiReportErrors:
    # frob:tests src/frob/app/ci_runner.py::run kind="unit"
    def test_gh_missing_is_a_named_error_not_a_traceback(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """`gh` missing from PATH: `build_run_report` propagates
        `Err(GhError.NotInstalled)` -- `frob ci report` must render that
        named message and exit non-zero, never raise."""
        monkeypatch.setattr(
            ci_runner_mod,
            "build_run_report",
            lambda root, run_id: Err(GhError.NotInstalled),
        )
        cfg = _cfg(ci_path=tmp_path)
        with pytest.raises(SystemExit) as exc:
            run(cfg)
        assert exc.value.code != 0
        printed = capsys.readouterr().out
        assert "not installed" in printed.lower()
