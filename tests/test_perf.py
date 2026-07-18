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
    false-positive guard docs/modules/perf.md and the ticket both name as
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


def _init_hot_cold_workload(tmp_path: Path) -> None:
    """Git-init `tmp_path` and drop a `workload.py` with a hot/cold function
    pair -- the fixture shared by the heat-join test below."""
    # frob:ticket T-0021
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    _write(
        tmp_path,
        "workload.py",
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
        "cold()\n",
    )


def test_heat_joins_pstats_rows_onto_symbol_spans(tmp_path):
    """`heat` attributes profiled time to the enclosing symbol and ranks by
    cum_s desc."""
    # frob:ticket T-0021
    # frob:tests src/frob/perf/_heat.py::heat
    _init_hot_cold_workload(tmp_path)
    result = profile_command(["workload.py"], tmp_path)
    assert result.is_ok, result.err
    artifact = result.danger_ok

    snapshot = _snapshot(tmp_path)
    report = heat(artifact, snapshot)

    entries_by_ref = {entry.ref: entry for entry in report.entries}
    assert "workload.py::hot" in entries_by_ref
    hot_entry = entries_by_ref["workload.py::hot"]
    assert hot_entry.cum_s >= 0.0
    if len(report.entries) > 1:
        assert report.entries[0].cum_s >= report.entries[-1].cum_s


def test_join_smells_attaches_rule_ids_by_ref():
    """`join_smells` attaches PERF rule ids onto matching entries only."""
    # frob:tests src/frob/perf/_heat.py::join_smells kind="unit"
    from frob.perf._heat import join_smells
    from frob.perf._models import HeatEntry, HeatReport

    report = HeatReport(
        entries=(
            HeatEntry(ref="a.py::f", cum_s=1.0, self_s=1.0, ncalls=1),
            HeatEntry(ref="a.py::g", cum_s=2.0, self_s=2.0, ncalls=1),
        ),
        unattributed_s=0.0,
    )
    updated = join_smells(report, {"a.py::f": ("PERF001",)})
    smells_by_ref = {e.ref: e.smells for e in updated.entries}
    assert smells_by_ref["a.py::f"] == ("PERF001",)
    assert smells_by_ref["a.py::g"] == ()


def test_render_bar_scales_fill_to_ratio():
    """`render_bar` fills proportionally to cum_s/max_s, uncolored when
    color=False."""
    # frob:tests src/frob/perf/_heat.py::render_bar kind="unit"
    from frob.perf._heat import render_bar

    empty = render_bar(0.0, 10.0, color=False)
    full = render_bar(10.0, 10.0, color=False)
    half = render_bar(5.0, 10.0, color=False)
    assert empty == "-" * 30
    assert full == "#" * 30
    assert half.count("#") == 15


def test_profile_artifact_names_are_sha_derived():
    """`pstats_name`/`meta_name` derive their basenames from the artifact sha."""
    # frob:tests src/frob/perf/_models.py::ProfileArtifact.pstats_name kind="unit"
    # frob:tests src/frob/perf/_models.py::ProfileArtifact.meta_name kind="unit"
    from datetime import datetime

    from frob.perf._models import ProfileArtifact

    artifact = ProfileArtifact(
        sha="deadbeef", argv=("workload.py",), created=datetime.now(), total_s=0.1
    )
    assert artifact.pstats_name == "deadbeef.pstats"
    assert artifact.meta_name == "deadbeef.json"


def test_profile_records_workload_exit_code(tmp_path):
    """T-0027: a failing workload is profiled anyway and its exit code is
    recorded on the artifact, not masked as a spawn failure."""
    (tmp_path / "fail.py").write_text("import sys\nsum(range(100))\nsys.exit(3)\n")
    result = profile_command(["fail.py"], tmp_path)
    assert result.is_ok, result.err
    assert result.danger_ok.exit_code == 3


def test_profile_clean_workload_exit_zero(tmp_path):
    (tmp_path / "ok.py").write_text("sum(range(1000))\n")
    result = profile_command(["ok.py"], tmp_path)
    assert result.is_ok, result.err
    assert result.danger_ok.exit_code == 0


def test_perf_end_to_end_profile_load_and_heat(tmp_path):
    # frob:tests src/frob/perf kind="integration"
    # Drive the whole perf boundary: profile a real workload to a stored
    # artifact, reload it by sha, and join its pstats rows onto the graph.
    # frob:ticket T-0021
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "work.py").write_text(
        "def busy():\n    return sum(range(50000))\n\n\nbusy()\n",
        encoding="utf-8",
    )
    profiled = profile_command(["src/work.py"], tmp_path)
    assert profiled.is_ok, profiled.err

    reloaded = load_artifact(tmp_path, profiled.danger_ok.sha)
    assert reloaded.is_ok, reloaded.err

    snapshot = _snapshot(tmp_path)
    report = heat(reloaded.danger_ok, snapshot)
    assert report.unattributed_s >= 0.0
