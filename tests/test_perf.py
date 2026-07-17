"""Tests for frob.perf: PERF001..PERF004, artifact round-trip, heat join.

# frob:ticket T-0021
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.graph import build_graph
from frob.lang import parse_file
from frob.perf import heat, load_artifact, perf_rules, profile_command


def _snapshot(root: Path):
    # frob:ticket T-0021
    cache = root / ".frob" / "cache.db"
    return build_graph(root, cache).danger_ok


def _write(root: Path, name: str, src: str) -> Path:
    # frob:ticket T-0021
    path = root / name
    path.write_text(src)
    return path


def test_perf001_fires_on_list_membership_in_loop(tmp_path):
    """PERF001 fires: `x in data` inside a loop where `data` is a list."""
    # frob:ticket T-0021
    # frob:tests src/frob/perf/_rules.py::perf_rules
    src = (
        "def scan(items):\n"
        "    data = [1, 2, 3]\n"
        "    hits = 0\n"
        "    for x in items:\n"
        "        if x in data:\n"
        "            hits += 1\n"
        "    return hits\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert any(v.rule == "PERF001" for v in violations)


def test_perf001_does_not_fire_on_set_membership_in_loop(tmp_path):
    """PERF001 does not fire when the container is already a set -- the
    false-positive guard docs/perf.md and the ticket both name as
    priority #1."""
    # frob:ticket T-0021
    src = (
        "def scan(items):\n"
        "    data = {1, 2, 3}\n"
        "    hits = 0\n"
        "    for x in items:\n"
        "        if x in data:\n"
        "            hits += 1\n"
        "    return hits\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF001" for v in violations)


def test_perf001_does_not_fire_outside_a_loop(tmp_path):
    """PERF001 does not fire when the membership test is not inside a
    for/while body, even against a plain list."""
    # frob:ticket T-0021
    src = "def check_one(data, x):\n    data = [1, 2, 3]\n    return x in data\n"
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF001" for v in violations)


def test_perf002_fires_on_index_call_in_loop(tmp_path):
    """PERF002 fires: `.index()` call inside a loop."""
    # frob:ticket T-0021
    src = (
        "def find_all(items, haystack):\n"
        "    out = []\n"
        "    for x in items:\n"
        "        out.append(haystack.index(x))\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert any(v.rule == "PERF002" for v in violations)


def test_perf002_does_not_fire_outside_a_loop(tmp_path):
    """PERF002 does not fire on a single `.index()` call with no loop."""
    # frob:ticket T-0021
    src = "def find_one(haystack, needle):\n    return haystack.index(needle)\n"
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF002" for v in violations)


def test_perf003_fires_on_nested_loop_equality_join(tmp_path):
    """PERF003 fires: nested loops comparing items with `==`."""
    # frob:ticket T-0021
    src = (
        "def join(a, b):\n"
        "    out = []\n"
        "    for x in a:\n"
        "        for y in b:\n"
        "            if x == y:\n"
        "                out.append(x)\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert any(v.rule == "PERF003" for v in violations)


def test_perf003_does_not_fire_on_single_loop(tmp_path):
    """PERF003 does not fire when there is only one loop."""
    # frob:ticket T-0021
    src = "def total(a):\n    out = 0\n    for x in a:\n        out += x\n    return out\n"
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF003" for v in violations)


def test_perf004_fires_on_sort_in_loop(tmp_path):
    """PERF004 fires: `sorted()` call inside a loop over unchanged data."""
    # frob:ticket T-0021
    src = (
        "def rank(rounds, data):\n"
        "    out = []\n"
        "    for r in rounds:\n"
        "        out.append(sorted(data))\n"
        "    return out\n"
    )
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert any(v.rule == "PERF004" for v in violations)


def test_perf004_does_not_fire_on_sort_outside_a_loop(tmp_path):
    """PERF004 does not fire on a single top-level `sorted()` call."""
    # frob:ticket T-0021
    src = "def rank_once(data):\n    return sorted(data)\n"
    path = _write(tmp_path, "mod.py", src)
    parsed = parse_file(path).danger_ok
    snapshot = _snapshot(tmp_path)
    violations = perf_rules(snapshot, [parsed])
    assert not any(v.rule == "PERF004" for v in violations)


def test_profile_command_and_load_artifact_round_trip(tmp_path):
    """`profile_command` writes an artifact `load_artifact` can read back."""
    # frob:ticket T-0021
    # frob:tests src/frob/perf/_profile.py::profile_command
    # frob:tests src/frob/perf/_profile.py::load_artifact
    (tmp_path / "workload.py").write_text(
        "total = 0\nfor i in range(1000):\n    total += i\n"
    )
    result = profile_command(["workload.py"], tmp_path)
    assert result.is_ok, result.err
    artifact = result.danger_ok

    loaded = load_artifact(tmp_path)
    assert loaded.is_ok, loaded.err
    assert loaded.danger_ok.sha == artifact.sha

    by_ref = load_artifact(tmp_path, ref=artifact.sha)
    assert by_ref.is_ok
    assert by_ref.danger_ok.sha == artifact.sha


def test_load_artifact_no_artifact_is_err(tmp_path):
    """`load_artifact` returns `Err(NoArtifact)` when nothing was profiled."""
    # frob:ticket T-0021
    result = load_artifact(tmp_path)
    assert result.is_err
    assert result.danger_err.name == "NoArtifact"


def test_heat_joins_pstats_rows_onto_symbol_spans(tmp_path):
    """`heat` attributes profiled time to the enclosing symbol and ranks by
    cum_s desc."""
    # frob:ticket T-0021
    # frob:tests src/frob/perf/_heat.py::heat
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "workload.py").write_text(
        "def hot():\n"
        "    total = 0\n"
        "    for i in range(200000):\n"
        "        total += i\n"
        "    return total\n"
        "\n"
        "def cold():\n"
        "    return 1\n"
        "\n"
        "hot()\n"
        "cold()\n"
    )
    result = profile_command(["workload.py"], tmp_path)
    assert result.is_ok, result.err
    artifact = result.danger_ok

    snapshot = _snapshot(tmp_path)
    report = heat(artifact, snapshot)

    refs = [e.ref for e in report.entries]
    assert "workload.py::hot" in refs
    hot_entry = next(e for e in report.entries if e.ref == "workload.py::hot")
    assert hot_entry.cum_s >= 0.0
    if len(report.entries) > 1:
        assert report.entries[0].cum_s >= report.entries[-1].cum_s
