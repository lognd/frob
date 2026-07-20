# frob:waive SCOPE001 reason="T-0319 scope comma-joined, matches nothing (T-0241 bug)"
"""End-to-end litmus for `frob doctor` (T-0319): a first-class CLI surface
for the native-extension check that `docs/guides/install.md`'s T-0316
section previously described only as a manual `python3 -c "import
strata_core, frob_core"` paragraph.

`tests/fixtures/fake_no_native/strata_core.py` shadows the real compiled
extension via `PYTHONPATH` order (same fixture `test_cli_native_missing.py`
uses), so the natives-absent case exercises the real subprocess CLI path
end to end, not a monkeypatched import.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

FROB = [sys.executable, "-m", "frob"]

_FAKE_NATIVE_DIR = str(Path(__file__).parent.parent / "fixtures" / "fake_no_native")


def _run_with_faked_missing_native(
    *args: str, cwd: Path
) -> subprocess.CompletedProcess:
    """Run `frob <args>` in a subprocess whose `PYTHONPATH` shadows the real
    `strata_core` with the raise-on-import fixture, so `frob doctor` sees
    exactly what a natives-less `uv tool install frob` sees."""
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        _FAKE_NATIVE_DIR
        if not existing
        else f"{_FAKE_NATIVE_DIR}{os.pathsep}{existing}"
    )
    return subprocess.run(
        FROB + list(args), cwd=cwd, capture_output=True, text=True, env=env
    )


class TestDoctorCli:
    # frob:tests src/frob/doctor.py
    def test_doctor_reports_healthy_when_natives_present(self, tmp_path: Path) -> None:
        """A normal environment (this worktree's own built natives) reports
        healthy and exits 0."""
        r = subprocess.run(
            FROB + ["doctor"], cwd=tmp_path, capture_output=True, text=True
        )
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "frob_core" in out
        assert "strata_core" in out

    def test_doctor_json_reports_healthy_when_natives_present(
        self, tmp_path: Path
    ) -> None:
        """`--json` emits a parseable `DoctorReport` with `healthy: true`."""
        r = subprocess.run(
            FROB + ["doctor", "--json"], cwd=tmp_path, capture_output=True, text=True
        )
        assert r.returncode == 0, r.stdout + r.stderr
        report = json.loads(r.stdout)
        assert report["healthy"] is True
        assert report["remediation"] is None
        names = {ext["name"] for ext in report["extensions"]}
        assert names == {"frob_core", "strata_core"}

    def test_doctor_fails_loud_when_native_missing(self, tmp_path: Path) -> None:
        """A faked-missing `strata_core` exits nonzero and prints the exact
        remediation, not a silent/degraded pass."""
        r = _run_with_faked_missing_native("doctor", cwd=tmp_path)
        out = r.stdout + r.stderr
        assert r.returncode != 0, out
        assert "strata_core" in out
        assert "NOT importable" in out or "not importable" in out
        assert "make core" in out or "make install-tool" in out

    def test_doctor_json_fails_loud_when_native_missing(self, tmp_path: Path) -> None:
        """`--json` on a natives-missing environment reports `healthy: false`
        with the remediation hint and still exits nonzero."""
        r = _run_with_faked_missing_native("doctor", "--json", cwd=tmp_path)
        assert r.returncode != 0, r.stdout + r.stderr
        report = json.loads(r.stdout)
        assert report["healthy"] is False
        assert report["remediation"]
        by_name = {ext["name"]: ext for ext in report["extensions"]}
        assert by_name["strata_core"]["available"] is False
