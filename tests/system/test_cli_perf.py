"""End-to-end tests for `frob perf profile|heat` (docs/perf.md).

# frob:ticket T-0021
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.system.conftest import run


def _git(*args: str, cwd: Path) -> None:
    # frob:ticket T-0021
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class TestPerfProfileAndHeat:
    # frob:ticket T-0021

    def test_profile_then_heat_shows_hot_function(self, tmp_path):
        """`frob perf profile -- python -c "<loop>"` then `frob perf heat
        --top 3` surfaces the hot function ranked first."""
        # frob:tests src/frob/app/perf_runner.py::run
        # frob:ticket T-0021
        _git("init", "-q", "-b", "main", cwd=tmp_path)
        _git("config", "user.email", "test@example.com", cwd=tmp_path)
        _git("config", "user.name", "Test", cwd=tmp_path)
        (tmp_path / "workload.py").write_text(
            "def hot():\n"
            "    total = 0\n"
            "    for i in range(300000):\n"
            "        total += i\n"
            "    return total\n"
            "\n"
            "hot()\n"
        )
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)

        profiled = run(
            "perf", "profile", "--path", str(tmp_path), "--", "python", "workload.py"
        )
        assert profiled.returncode == 0, profiled.stdout + profiled.stderr
        assert "sha=" in profiled.stdout

        heated = run("perf", "heat", "--path", str(tmp_path), "--top", "3")
        out = heated.stdout + heated.stderr
        assert heated.returncode == 0, out
        assert "workload.py::hot" in out

    def test_heat_json_output_is_valid_json(self, tmp_path):
        """`frob perf heat --json` emits a machine-readable payload."""
        # frob:ticket T-0021
        import json

        _git("init", "-q", "-b", "main", cwd=tmp_path)
        _git("config", "user.email", "test@example.com", cwd=tmp_path)
        _git("config", "user.name", "Test", cwd=tmp_path)
        (tmp_path / "workload.py").write_text("total = sum(range(1000))\n")
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)

        run("perf", "profile", "--path", str(tmp_path), "--", "python", "workload.py")
        heated = run("perf", "heat", "--path", str(tmp_path), "--json")
        assert heated.returncode == 0, heated.stdout + heated.stderr
        payload = json.loads(heated.stdout)
        assert "entries" in payload and "unattributed_s" in payload

    def test_heat_without_artifact_fails_cleanly(self, tmp_path):
        """`frob perf heat` with no prior profile exits non-zero, not a
        traceback."""
        # frob:ticket T-0021
        _git("init", "-q", "-b", "main", cwd=tmp_path)
        heated = run("perf", "heat", "--path", str(tmp_path))
        assert heated.returncode != 0
        assert "Traceback" not in (heated.stdout + heated.stderr)


class TestCheckOnlyPerf:
    # frob:ticket T-0021

    def test_perf001_fixture_warns_but_check_exits_zero(self, tmp_path):
        """`frob check --only gates` on a PERF001 fixture warns (default
        severity) but still exits 0 -- PERF defaults to warn, not error.
        Other gates (TEST001/TEST006/...) are satisfied first so the run
        isolates PERF's own severity, per the existing
        test_only_gates_passes_once_bound_and_tested pattern in
        tests/system/test_cli_check.py."""
        # frob:ticket T-0021
        _git("init", "-q", "-b", "main", cwd=tmp_path)
        _git("config", "user.email", "test@example.com", cwd=tmp_path)
        _git("config", "user.name", "Test", cwd=tmp_path)
        (tmp_path / "pkg.py").write_text(
            "def scan(items):\n"
            "    data = [1, 2, 3]\n"
            "    hits = 0\n"
            "    for x in items:\n"
            "        if x in data:\n"
            "            hits += 1\n"
            "    return hits\n"
        )
        (tmp_path / "test_pkg.py").write_text(
            "from pkg import scan\n\n"
            "def test_scan() -> None:\n"
            "    # frob:tests pkg.py::scan\n"
            "    assert scan([1]) == 1\n"
        )
        (tmp_path / "coverage.xml").write_text(
            '<?xml version="1.0" ?><coverage line-rate="1.0"></coverage>'
        )
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)

        stamp = run("check", str(tmp_path), "--stamp-coverage")
        assert stamp.returncode == 0, stamp.stdout + stamp.stderr

        r = run("check", str(tmp_path), "--only", "gates")
        out = r.stdout + r.stderr
        assert "PERF001" in out
        assert r.returncode == 0, out
