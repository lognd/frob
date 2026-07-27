"""End-to-end tests for `frob perf profile|heat` (docs/modules/perf.md).

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


class TestPerfCollect:
    """`frob perf collect --file ...` (T-0765): end-to-end CLI wiring for
    the T-0748 collector adapters."""

    def test_collect_resolves_a_real_python_hot_frame(self, tmp_path):
        """A hand-built `perf script` fixture naming a real function in
        this repo resolves through `resolve_stream` to a `python`-labeled
        decile row, readable in the CLI's plain-text output."""
        # frob:tests src/frob/app/perf_runner.py::run
        # frob:ticket T-0765
        repo_root = Path(__file__).resolve().parents[2]
        target = repo_root / "src" / "frob" / "perf" / "_hotgraph.py"
        text = target.read_text(encoding="utf-8")
        line = (
            next(
                i
                for i, line_text in enumerate(text.splitlines(), start=1)
                if line_text.startswith("def build_section_index(")
            )
            + 2
        )
        profile = tmp_path / "profile.perf.script"
        profile.write_text(
            "myprog  1 1 1.0: 1 cycles:\n"
            f"\t401234 build_section_index+0x10 "
            f"(src/frob/perf/_hotgraph.py:{line})\n"
        )
        result = run(
            "perf",
            "collect",
            "--path",
            str(repo_root),
            "--file",
            str(profile),
        )
        out = result.stdout + result.stderr
        assert result.returncode == 0, out
        assert "python" in out
        assert "decile" in out

    def test_collect_json_output_is_valid_json(self, tmp_path):
        """`frob perf collect --json` emits a machine-readable payload with
        `rows`/`unattributed_weight`/`sample_count`."""
        # frob:ticket T-0765
        import json

        profile = tmp_path / "profile.perf.script"
        profile.write_text(
            "myprog  1 1 1.0: 1 cycles:\n\t7fffaa unknown_native (no debuginfo)\n"
        )
        result = run("perf", "collect", "--file", str(profile), "--json")
        assert result.returncode == 0, result.stdout + result.stderr
        payload = json.loads(result.stdout)
        assert "rows" in payload and "unattributed_weight" in payload
        assert payload["sample_count"] == 1

    def test_collect_without_file_or_sampler_fails_cleanly(self, tmp_path):
        """`frob perf collect` with neither `--file` nor `--sampler` exits
        non-zero, not a traceback."""
        # frob:ticket T-0765
        result = run("perf", "collect", "--path", str(tmp_path))
        out = result.stdout + result.stderr
        assert result.returncode != 0
        assert "Traceback" not in out

    def test_collect_autodetects_cpuprofile_format(self, tmp_path):
        """`--format` omitted still resolves a `.cpuprofile` correctly via
        `detect_collector_format`'s extension check."""
        # frob:ticket T-0765
        fixture = (
            Path(__file__).resolve().parents[1]
            / "unit"
            / "perf"
            / "fixtures"
            / "sample.cpuprofile"
        )
        result = run("perf", "collect", "--file", str(fixture), "--json")
        assert result.returncode == 0, result.stdout + result.stderr


class TestCheckOnlyPerf:
    # frob:ticket T-0021

    def _init_perf001_fixture_repo(self, tmp_path) -> None:
        """A committed repo with one tested PERF001-tripping function, plus a
        pre-stamped `coverage.xml` so the run isolates PERF's own severity."""
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

    def test_perf001_fixture_warns_but_check_exits_zero(self, tmp_path):
        """`frob check --only gates` on a PERF001 fixture warns (default
        severity) but still exits 0 -- PERF defaults to warn, not error.
        Other gates (TEST001/TEST006/...) are satisfied first so the run
        isolates PERF's own severity, per the existing
        test_only_gates_passes_once_bound_and_tested pattern in
        tests/system/test_cli_check.py."""
        # frob:ticket T-0021
        self._init_perf001_fixture_repo(tmp_path)

        stamp = run("check", str(tmp_path), "--stamp-coverage")
        assert stamp.returncode == 0, stamp.stdout + stamp.stderr

        # frob:ticket T-0718
        # T-0806: `--stamp-coverage` writes `frob-coverage.lock.json` into
        # the working tree uncommitted; left as-is, the next `--only gates`
        # run sees a 1-file diff with no active ticket and PRE001/SCOPE001
        # (correctly) refuse it -- commit the stamp so this run's diff is
        # genuinely clean, matching the pattern in
        # test_only_gates_passes_once_bound_and_tested.
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "stamp", cwd=tmp_path)

        r = run("check", str(tmp_path), "--only", "gates")
        out = r.stdout + r.stderr
        assert "PERF001" in out
        assert r.returncode == 0, out
