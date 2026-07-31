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

import pytest

from frob.app import doctor_runner
from frob.app.config import AppConfig
from frob.doctor import DoctorReport, NativeExtensionStatus


def _cfg(**overrides) -> AppConfig:
    """Minimal `AppConfig` for a `frob doctor` invocation."""
    base = {
        "subcommand": "doctor",
        "doctor_json": False,
        "color": "never",
        "no_color": True,
    }
    base.update(overrides)
    return AppConfig(**base)


def _report(*, healthy: bool, remediation: str | None) -> DoctorReport:
    return DoctorReport(
        frob_version="9.9.9",
        extensions=[
            NativeExtensionStatus(name="frob_core", available=healthy, version="1.0"),
            NativeExtensionStatus(
                name="strata_core", available=healthy, version="1.0" if healthy else None
            ),
        ],
        healthy=healthy,
        remediation=remediation,
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
            doctor_mod, "run_diagnosis", lambda: _report(healthy=False, remediation=None)
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
