"""Direct-call coverage for `frob.app.doctor_runner.run` (T-1276).

`doctor_runner.run` is only exercised today via subprocess CLI tests
(`tests/system/test_cli_doctor.py`), which pytest-cov cannot attribute
back to the running process -- hence its 0.0% branch-coverage TEST005
finding despite already being behaviorally tested end to end. These
tests call `run(cfg)` directly against a hand-built `AppConfig`, with
`frob.doctor.run_diagnosis` monkeypatched, exercising every branch:
healthy plain text, healthy json, unhealthy plain text (exit 1,
remediation printed), unhealthy json (exit 1), and the "healthy but no
remediation text" edge the module docstring calls out (must print an
empty string, never the literal word "None").
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from frob.app import doctor_runner
from frob.app.config import AppConfig
from frob.doctor import DoctorReport, LiveLandProcess, NativeExtensionStatus


def _cfg(**overrides: object) -> AppConfig:
    """Minimal `AppConfig` for a `frob doctor` invocation."""
    base: dict[str, Any] = {
        "subcommand": "doctor",
        "doctor_json": False,
        "color": "never",
        "no_color": True,
    }
    base.update(overrides)
    return AppConfig(**base)


# frob:ticket T-1634
def _report(
    *,
    healthy: bool,
    remediation: str | None,
    live_land_process: LiveLandProcess | None = None,
) -> DoctorReport:
    return DoctorReport(
        frob_version="9.9.9",
        extensions=[
            NativeExtensionStatus(name="frob_core", available=healthy, version="1.0"),
            NativeExtensionStatus(
                name="strata_core",
                available=healthy,
                version="1.0" if healthy else None,
            ),
        ],
        healthy=healthy,
        remediation=remediation,
        live_land_process=live_land_process,
    )


class TestDoctorRunnerHealthy:
    # frob:tests \
    # tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerHealthy.test_healthy_plai\
    # n_prints_all_available_and_does_not_exit
    def test_healthy_plain_prints_all_available_and_does_not_exit(
        self, monkeypatch, capsys
    ) -> None:
        """A healthy report in plain mode prints the good-status line and
        returns normally (no `sys.exit`)."""
        # frob:waive PII012 reason="'run_diagnosis' names the repository self-check API symbol this test patches; frob doctor inspects tooling, never person-related data"  # noqa: E501
        # `run_diagnosis` is imported lazily inside `run`; patch the source.
        import frob.doctor as doctor_mod

        monkeypatch.setattr(
            doctor_mod, "run_diagnosis", lambda: _report(healthy=True, remediation=None)
        )
        doctor_runner.run(_cfg())
        out = capsys.readouterr().out
        assert "all native extensions available" in out
        assert "frob_core" in out and "strata_core" in out

    # frob:tests \
    # tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerHealthy.test_healthy_json\
    # _emits_parseable_report
    def test_healthy_json_emits_parseable_report(self, monkeypatch, caplog) -> None:
        """`--json` emits the report's JSON on the log channel and does not
        exit when healthy."""
        import frob.doctor as doctor_mod

        monkeypatch.setattr(
            doctor_mod, "run_diagnosis", lambda: _report(healthy=True, remediation=None)
        )
        caplog.set_level("INFO")
        doctor_runner.run(_cfg(doctor_json=True))
        payload = next(
            json.loads(r.message) for r in caplog.records if r.message.startswith("{")
        )
        assert payload["healthy"] is True


class TestDoctorRunnerUnhealthy:
    # frob:tests \
    # tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy.test_unhealthy_\
    # plain_exits_1_and_prints_remediation
    def test_unhealthy_plain_exits_1_and_prints_remediation(
        self, monkeypatch, capsys
    ) -> None:
        """An unhealthy report in plain mode prints the remediation text and
        exits 1 -- scriptable as a preflight check."""
        import frob.doctor as doctor_mod

        monkeypatch.setattr(
            doctor_mod,
            "run_diagnosis",
            lambda: _report(healthy=False, remediation="run: make core"),
        )
        with pytest.raises(SystemExit) as exc:
            doctor_runner.run(_cfg())
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "native extensions missing" in out
        assert "run: make core" in out

    # frob:tests \
    # tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy.test_unhealthy_\
    # no_remediation_prints_empty_not_none
    def test_unhealthy_no_remediation_prints_empty_not_none(
        self, monkeypatch, capsys
    ) -> None:
        """T-0448's deliberate fix: an unhealthy report with no remediation
        text prints an empty remediation line, never the literal word
        "None" from an unguarded f-string interpolation of `str | None`."""
        import frob.doctor as doctor_mod

        monkeypatch.setattr(
            doctor_mod,
            "run_diagnosis",
            lambda: _report(healthy=False, remediation=None),
        )
        with pytest.raises(SystemExit):
            doctor_runner.run(_cfg())
        out = capsys.readouterr().out
        assert "None" not in out

    # frob:tests \
    # tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy.test_unhealthy_\
    # json_exits_1
    def test_unhealthy_json_exits_1(self, monkeypatch) -> None:
        """`--json` on an unhealthy report still exits 1, matching the
        plain-mode preflight-check contract."""
        import frob.doctor as doctor_mod

        monkeypatch.setattr(
            doctor_mod,
            "run_diagnosis",
            lambda: _report(healthy=False, remediation="run: make core"),
        )
        with pytest.raises(SystemExit) as exc:
            doctor_runner.run(_cfg(doctor_json=True))
        assert exc.value.code == 1


# frob:ticket T-1634
class TestDoctorRunnerOrphanedLandLockDisclosure:
    """T-1634: a CONFIRMED-dead land.lock holder no longer makes
    `DoctorReport.healthy` `False`, but `run`'s plain-text output still
    discloses it -- these tests exercise `_print_orphaned_land_lock_
    disclosure` through `run` directly (not just via `frob.doctor`'s own
    unit tests), since the CLI-facing disclosure text is `doctor_runner`'s
    own responsibility, not `frob.doctor`'s."""

    # frob:ticket T-1634
    # frob:tests \
    # tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerOrphanedLandLockDisclosur\
    # e.test_healthy_report_with_confirmed_dead_holder_prints_self_healing_line
    def test_healthy_report_with_confirmed_dead_holder_prints_self_healing_line(
        self, monkeypatch, capsys
    ) -> None:
        """A `healthy=True` report carrying a CONFIRMED-dead
        `live_land_process` still prints an explicit disclosure line and
        does NOT exit -- the finding is surfaced, not silently dropped,
        even though it no longer fails the health check."""
        import frob.doctor as doctor_mod

        dead = LiveLandProcess(
            pid=999999,
            session_id="orphaned-session",
            started_at="2026-08-04T00:00:00+00:00",
            alive=False,
        )
        monkeypatch.setattr(
            doctor_mod,
            "run_diagnosis",
            lambda: _report(healthy=True, remediation=None, live_land_process=dead),
        )
        doctor_runner.run(_cfg())
        out = capsys.readouterr().out
        assert "orphaned land.lock" in out
        assert "999999" in out
        assert "self-healing" in out

    # frob:ticket T-1634
    # frob:tests \
    # tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerOrphanedLandLockDisclosur\
    # e.test_healthy_report_with_no_land_lock_prints_nothing_extra
    def test_healthy_report_with_no_land_lock_prints_nothing_extra(
        self, monkeypatch, capsys
    ) -> None:
        """A healthy report with no land.lock holder at all (the common
        case) prints no orphaned-lock line."""
        import frob.doctor as doctor_mod

        monkeypatch.setattr(
            doctor_mod,
            "run_diagnosis",
            lambda: _report(healthy=True, remediation=None, live_land_process=None),
        )
        doctor_runner.run(_cfg())
        out = capsys.readouterr().out
        assert "orphaned land.lock" not in out
