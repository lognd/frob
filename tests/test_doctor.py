# frob:waive SCOPE001 reason="T-0319 scope comma-joined, matches nothing (T-0241 bug)"
"""frob.doctor: native-extension diagnosis (T-0319)."""

from __future__ import annotations

import importlib

import pytest

from frob import doctor


def test_run_diagnosis_natives_present(monkeypatch):
    # frob:tests src/frob/doctor.py::run_diagnosis
    """Every `NATIVE_EXTENSIONS` entry importing cleanly reports healthy=True
    and no remediation."""

    class _Fake:
        __version__ = "9.9.9"

    monkeypatch.setattr(importlib, "import_module", lambda name: _Fake())
    report = doctor.run_diagnosis()
    assert report.healthy is True
    assert report.remediation is None
    assert {ext.name for ext in report.extensions} == set(doctor.NATIVE_EXTENSIONS)
    assert all(ext.available for ext in report.extensions)
    assert all(ext.version == "9.9.9" for ext in report.extensions)


def test_run_diagnosis_natives_absent(monkeypatch):
    # frob:tests src/frob/doctor.py::run_diagnosis
    """A missing native extension reports healthy=False with the exact
    `REMEDIATION_HINT` and no version for the failing extension."""

    def _raise(name: str):
        raise ImportError(f"No module named {name!r}")

    monkeypatch.setattr(importlib, "import_module", _raise)
    report = doctor.run_diagnosis()
    assert report.healthy is False
    assert report.remediation == doctor.REMEDIATION_HINT
    assert all(not ext.available for ext in report.extensions)
    assert all(ext.version is None for ext in report.extensions)


def test_run_diagnosis_partial_availability(monkeypatch):
    # frob:tests src/frob/doctor.py::run_diagnosis
    """One extension importable and the other missing is still unhealthy
    overall (healthy is an all-or-nothing verdict, not per-extension)."""

    def _selective(name: str):
        if name == "frob_core":
            return object()
        raise ImportError(name)

    monkeypatch.setattr(importlib, "import_module", _selective)
    report = doctor.run_diagnosis()
    assert report.healthy is False
    assert report.remediation == doctor.REMEDIATION_HINT
    by_name = {ext.name: ext for ext in report.extensions}
    assert by_name["frob_core"].available is True
    assert by_name["strata_core"].available is False


def test_run_diagnosis_reports_frob_version():
    # frob:tests src/frob/doctor.py::run_diagnosis
    """`frob_version` is always a non-empty string, whether or not the
    distribution is registered (falls back to 'unknown')."""
    report = doctor.run_diagnosis()
    assert isinstance(report.frob_version, str)
    assert report.frob_version != ""


@pytest.mark.parametrize("name", list(doctor.NATIVE_EXTENSIONS))
def test_native_extensions_are_the_expected_set(name):
    # frob:tests src/frob/doctor.py::NATIVE_EXTENSIONS
    """`NATIVE_EXTENSIONS` names exactly the two natives frob depends on."""
    assert name in ("frob_core", "strata_core")
