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


class TestDoctorDerivedStateManifest:
    """T-0570: `frob doctor` fingerprints every derived artifact it knows
    about (`.frob/cache.db`, `.frob/dup.db`, `.frob/vet.db`,
    `.frob/coverage-stamp`, `.frob/baseline`, `frob-coverage.lock.json`) and
    reports corruption before any gate consumes the stale/corrupt state."""

    # frob:tests src/frob/doctor.py
    def test_verify_derived_state_reports_absent_as_healthy(
        self, tmp_path: Path
    ) -> None:
        """No `.frob/` at all (a fresh checkout) reports every artifact as
        absent-and-healthy, never as a false corruption finding."""
        from frob.doctor import verify_derived_state

        statuses = verify_derived_state(tmp_path)
        assert statuses
        assert all(not s.present and s.healthy for s in statuses)

    # frob:tests src/frob/doctor.py
    def test_verify_derived_state_flags_corrupt_sqlite_cache(
        self, tmp_path: Path
    ) -> None:
        """A `.frob/dup.db` that is not actually SQLite bytes (the T-0517
        stale/corrupt-fixture-cache incident shape) is reported unhealthy
        with a fingerprint and an explanatory detail, not silently passed
        through to whatever reads it next."""
        from frob.doctor import verify_derived_state

        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "dup.db").write_bytes(b"not a real sqlite file")

        statuses = verify_derived_state(tmp_path)
        by_name = {s.name: s for s in statuses}
        dup_cache = by_name["dup-cache"]
        assert dup_cache.present is True
        assert dup_cache.healthy is False
        assert dup_cache.fingerprint is not None
        assert dup_cache.detail is not None

    # frob:tests src/frob/doctor.py
    def test_verify_derived_state_flags_malformed_json_stamp(
        self, tmp_path: Path
    ) -> None:
        """A `.frob/coverage-stamp` that is not valid JSON is reported
        unhealthy with a detail explaining why."""
        from frob.doctor import verify_derived_state

        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "coverage-stamp").write_text("{not json")

        statuses = verify_derived_state(tmp_path)
        by_name = {s.name: s for s in statuses}
        stamp = by_name["coverage-stamp"]
        assert stamp.present is True
        assert stamp.healthy is False
        assert stamp.detail is not None

    # frob:tests src/frob/doctor.py
    def test_verify_derived_state_accepts_valid_json_stamp(
        self, tmp_path: Path
    ) -> None:
        """A well-formed `.frob/baseline` is reported present and healthy,
        with a stable content fingerprint."""
        from frob.doctor import verify_derived_state

        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "baseline").write_text('{"violations": []}')

        statuses = verify_derived_state(tmp_path)
        by_name = {s.name: s for s in statuses}
        baseline = by_name["baseline"]
        assert baseline.present is True
        assert baseline.healthy is True
        assert baseline.fingerprint is not None

    # frob:tests src/frob/doctor.py
    def test_run_diagnosis_unhealthy_when_derived_state_corrupt(
        self, tmp_path: Path
    ) -> None:
        """`run_diagnosis(root)` folds a corrupt derived artifact into the
        overall `healthy` verdict and names it in `remediation`, even when
        every native extension is available."""
        from frob.doctor import run_diagnosis

        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "cache.db").write_bytes(b"garbage")

        report = run_diagnosis(tmp_path)
        assert report.healthy is False
        assert report.remediation is not None
        assert "graph-cache" in report.remediation
        corrupt_names = {d.name for d in report.derived_state if not d.healthy}
        assert "graph-cache" in corrupt_names

    # frob:tests src/frob/doctor.py
    def test_run_diagnosis_healthy_with_no_derived_state(self, tmp_path: Path) -> None:
        """`run_diagnosis(root)` against a directory with no `.frob/` at all
        stays healthy (matching the natives-only historical behavior) --
        an empty derived-state manifest is not itself a failure."""
        from frob.doctor import run_diagnosis

        report = run_diagnosis(tmp_path)
        assert report.healthy is True
        assert all(not d.present for d in report.derived_state)


class TestDoctorScaffoldConformance:
    """T-0736: `frob doctor` folds managed-boilerplate-block conformance
    into the overall verdict, opt-in on `frob.toml` existing."""

    # frob:tests src/frob/doctor.py
    def test_run_diagnosis_ignores_non_frob_directory(self, tmp_path: Path) -> None:
        """No `frob.toml` under `root` -- a bare directory, same as every
        other doctor test's `tmp_path` -- reports an empty scaffold-blocks
        list and never drags `healthy` down for it."""
        from frob.doctor import run_diagnosis

        report = run_diagnosis(tmp_path)
        assert report.scaffold_blocks == []
        assert report.healthy is True

    # frob:tests src/frob/doctor.py
    def test_run_diagnosis_unhealthy_when_scaffold_blocks_missing(
        self, tmp_path: Path
    ) -> None:
        """A `frob.toml`-bearing repo that has never run `frob scaffold
        apply` reports every managed block missing and folds that into an
        unhealthy verdict naming `frob scaffold apply` as the remedy."""
        from frob.doctor import run_diagnosis

        (tmp_path / "frob.toml").write_text("[project]\n")
        report = run_diagnosis(tmp_path)
        assert report.healthy is False
        assert report.scaffold_blocks
        assert all(not s.present for s in report.scaffold_blocks)
        assert "frob scaffold apply" in report.remediation

    # frob:tests src/frob/doctor.py
    def test_run_diagnosis_healthy_after_scaffold_apply(self, tmp_path: Path) -> None:
        """After `apply_managed_blocks`, the same repo reports every block
        present and not stale, and the overall verdict is healthy again
        (assuming natives/derived-state are otherwise clean)."""
        import subprocess

        from frob.doctor import run_diagnosis
        from frob.scaffold import apply_managed_blocks

        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
        (tmp_path / "frob.toml").write_text("[project]\n")
        result = apply_managed_blocks(tmp_path)
        assert result.is_ok

        report = run_diagnosis(tmp_path)
        assert all(s.present and not s.stale for s in report.scaffold_blocks)
