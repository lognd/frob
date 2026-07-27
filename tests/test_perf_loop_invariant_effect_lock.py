"""Detector lock for T-0775: frob's perf lint must catch the rev-parse
incident's structural shape -- an effectful callee (subprocess spawn)
invoked inside a loop with loop-invariant arguments, across a module
boundary.

This is the shape every existing PERF rule missed on 2026-07-22
(`read_all_leases` -> `git_common_dir` spawned per ticket row): PERF001-004
are per-function lexical heuristics and the fixture below contains none of
their trigger tokens; PERF005/006 need recursion; PERF007 needs the callee
invoked from 2+ distinct top-level symbols plus frob.toml config -- here it
is ONE caller looping. T-0775's PERF008
(`frob.perf._loop_effects.loop_invariant_effect_violations`) is the
detector that closes this gap: it fires on `caller.py`'s loop, naming
`common_dir` as transitively reaching the `subprocess.run` spawn, per this
lock's own documented instruction ("When T-0775 lands ... tighten the
assertion to the new rule id").
"""

from __future__ import annotations

from pathlib import Path

from frob.graph import build_graph
from frob.lang import parse_file
from frob.perf import perf_rules

_HELPER_SRC = (
    "import subprocess\n"
    "\n"
    "\n"
    "def common_dir(root):\n"
    "    spawned = subprocess.run(\n"
    "        ['git', '-C', str(root), 'rev-parse', '--git-common-dir'],\n"
    "        capture_output=True,\n"
    "    )\n"
    "    return spawned.stdout\n"
)

_CALLER_SRC = (
    "from helper import common_dir\n"
    "\n"
    "\n"
    "def list_rows(root, tickets):\n"
    "    rows = []\n"
    "    for ticket in tickets:\n"
    "        rows.append((ticket, common_dir(root)))\n"
    "    return rows\n"
)


# frob:ticket T-0775
def test_loop_invariant_spawning_callee_in_loop_is_flagged(tmp_path: Path) -> None:
    # frob:tests src/frob/perf/_rules.py::perf_rules kind="integration"
    helper = tmp_path / "helper.py"
    helper.write_text(_HELPER_SRC)
    caller = tmp_path / "caller.py"
    caller.write_text(_CALLER_SRC)

    parsed = [parse_file(helper).danger_ok, parse_file(caller).danger_ok]
    snapshot = build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
    violations = perf_rules(snapshot, parsed)

    caller_hits = [
        v for v in violations if v.rule == "PERF008" and "caller.py" in str(v.file)
    ]
    assert caller_hits, (
        "PERF008 did not fire on caller.py's loop over a process-spawning, "
        "loop-invariant callee -- the exact shape of the 2026-07-22 "
        f"rev-parse incident (all violations: {violations})"
    )
