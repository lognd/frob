"""frob.doctor: native-extension diagnosis (T-0319)."""

from __future__ import annotations

import importlib
import threading
from pathlib import Path

import pytest

from frob import doctor
from frob.process._lock import derived_state_lock


def test_run_diagnosis_natives_present(monkeypatch, tmp_path: Path):
    # frob:tests src/frob/doctor.py::run_diagnosis
    """Every `NATIVE_EXTENSIONS` entry importing cleanly reports healthy=True
    and no remediation. Uses an isolated `tmp_path` root (T-1321) rather
    than the real checkout, so a fresh CI clone missing scaffold-managed
    git hooks does not fold unrelated scaffold drift into this natives-only
    assertion."""

    class _Fake:
        __version__ = "9.9.9"

    monkeypatch.setattr(importlib, "import_module", lambda name: _Fake())
    report = doctor.run_diagnosis(root=tmp_path)
    assert report.healthy is True
    assert report.remediation is None
    assert {ext.name for ext in report.extensions} == set(doctor.NATIVE_EXTENSIONS)
    assert all(ext.available for ext in report.extensions)
    assert all(ext.version == "9.9.9" for ext in report.extensions)


def test_run_diagnosis_natives_absent(monkeypatch, tmp_path: Path):
    # frob:tests src/frob/doctor.py::run_diagnosis
    """A missing native extension reports healthy=False with the exact
    `REMEDIATION_HINT` and no version for the failing extension. Uses an
    isolated `tmp_path` root (T-1321) so this stays a natives-only check."""

    def _raise(name: str):
        raise ImportError(f"No module named {name!r}")

    monkeypatch.setattr(importlib, "import_module", _raise)
    report = doctor.run_diagnosis(root=tmp_path)
    assert report.healthy is False
    assert report.remediation == doctor.REMEDIATION_HINT
    assert all(not ext.available for ext in report.extensions)
    assert all(ext.version is None for ext in report.extensions)


def test_run_diagnosis_partial_availability(monkeypatch, tmp_path: Path):
    # frob:tests src/frob/doctor.py::run_diagnosis
    """One extension importable and the other missing is still unhealthy
    overall (healthy is an all-or-nothing verdict, not per-extension).
    Uses an isolated `tmp_path` root (T-1321) so this stays a natives-only
    check."""

    def _selective(name: str):
        if name == "frob_core":
            return object()
        raise ImportError(name)

    monkeypatch.setattr(importlib, "import_module", _selective)
    report = doctor.run_diagnosis(root=tmp_path)
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


# frob:ticket T-1218
# frob:waive PII012 reason="test name mirrors the run_diagnosis API symbol it \
# exercises; repository self-check machinery, no person-related data anywhere in the \
# test"
def test_run_diagnosis_reports_stale_binary_floor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # frob:tests src/frob/doctor.py::run_diagnosis
    """T-1218: a `frob.toml` `min_frob_version` floor above the invoked
    version makes `healthy` False, populates `DoctorReport.stale_binary`,
    and folds the warning into `remediation` -- the bare-frob-0.9.0
    incident this check exists for."""

    class _Fake:
        __version__ = "9.9.9"

    monkeypatch.setattr(importlib, "import_module", lambda name: _Fake())
    monkeypatch.setattr(
        doctor,
        "stale_binary_warning",
        lambda root: (
            "frob: WARNING -- invoked frob 0.9.0 is older than "
            "this repo's declared floor 0.277.0"
        ),
    )

    report = doctor.run_diagnosis(root=tmp_path)

    assert report.healthy is False
    assert report.stale_binary is not None
    assert "0.9.0" in report.stale_binary
    assert report.remediation is not None
    assert "0.277.0" in report.remediation


# frob:ticket T-1218
# frob:waive PII012 reason="test name mirrors the run_diagnosis API symbol it \
# exercises; repository self-check machinery, no person-related data anywhere in the \
# test"
def test_run_diagnosis_stale_binary_none_when_no_floor(tmp_path: Path) -> None:
    # frob:tests src/frob/doctor.py::run_diagnosis
    """No `frob.toml` `min_frob_version` in a fresh directory leaves
    `stale_binary` `None` and does not affect `healthy` on its own."""
    report = doctor.run_diagnosis(root=tmp_path)
    assert report.stale_binary is None


@pytest.mark.parametrize("name", list(doctor.NATIVE_EXTENSIONS))
def test_native_extensions_are_the_expected_set(name):
    # frob:tests src/frob/doctor.py::NATIVE_EXTENSIONS
    """`NATIVE_EXTENSIONS` names exactly the two natives frob depends on."""
    assert name in ("frob_core", "strata_core")


# frob:ticket T-0879
def test_run_diagnosis_holds_exclusive_lock_blocking_a_shared_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # frob:tests src/frob/doctor.py::run_diagnosis
    """`run_diagnosis`'s fingerprint-read + manifest-write span holds
    `derived_state_lock(root, exclusive=True)` (T-0879) -- a concurrent
    SHARED acquisition from another thread must block until `run_diagnosis`
    releases it, and must succeed immediately afterward (the writer never
    incorrectly blocks a reader that arrives once it is done)."""
    entered = threading.Event()
    release = threading.Event()
    original_write = doctor._write_drift_manifest

    def _slow_write(root: Path, fingerprints: dict[str, str]) -> None:
        entered.set()
        release.wait(timeout=5)
        original_write(root, fingerprints)

    monkeypatch.setattr(doctor, "_write_drift_manifest", _slow_write)

    writer_thread = threading.Thread(target=lambda: doctor.run_diagnosis(tmp_path))
    writer_thread.start()
    assert entered.wait(timeout=5), "run_diagnosis never reached its write span"

    reader_acquired = threading.Event()

    def _try_shared() -> None:
        with derived_state_lock(tmp_path, exclusive=False):
            reader_acquired.set()

    reader_thread = threading.Thread(target=_try_shared)
    reader_thread.start()
    reader_thread.join(timeout=0.3)
    assert not reader_acquired.is_set(), (
        "a SHARED reader acquired the lock while run_diagnosis's EXCLUSIVE "
        "writer span was still in progress"
    )

    release.set()
    writer_thread.join(timeout=5)
    reader_thread.join(timeout=5)
    assert reader_acquired.is_set(), (
        "the reader never acquired the lock after the writer released it"
    )
