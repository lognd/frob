"""Detector lock for T-0775: frob's perf lint must catch the rev-parse
incident's structural shape -- an effectful callee (subprocess spawn)
invoked inside a loop with loop-invariant arguments, across a module
boundary.

This is the shape every existing PERF rule missed on 2026-07-22
(`read_all_leases` -> `git_common_dir` spawned per ticket row): PERF001-004
are per-function lexical heuristics and the fixture below contains none of
their trigger tokens; PERF005/006 need recursion; PERF007 needs the callee
invoked from 2+ distinct top-level symbols plus frob.toml config -- here it
is ONE caller looping. So today `perf_rules` returns nothing for this
fixture and the test xfails (documented lint gap). When T-0775 lands its
loop-invariant effectful call detector through `perf_rules`, the unexpected
pass hard-errors (strict), forcing the marker's removal -- at which point
ALSO tighten the assertion to the new rule id so the lock names the rule
it guards.
"""

from __future__ import annotations

from pathlib import Path

import pytest

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
@pytest.mark.xfail(
    strict=True,
    reason=(
        "T-0775 not yet landed: no perf rule detects an effectful "
        "(process-spawning) callee invoked in a loop with loop-invariant "
        "arguments across a module boundary. When the detector lands this "
        "xpasses; remove the marker and pin the assertion to its rule id."
    ),
)
def test_loop_invariant_spawning_callee_in_loop_is_flagged(tmp_path: Path) -> None:
    # frob:tests src/frob/perf/_rules.py::perf_rules kind="system"
    helper = tmp_path / "helper.py"
    helper.write_text(_HELPER_SRC)
    caller = tmp_path / "caller.py"
    caller.write_text(_CALLER_SRC)

    parsed = [parse_file(helper).danger_ok, parse_file(caller).danger_ok]
    snapshot = build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
    violations = perf_rules(snapshot, parsed)

    caller_hits = [v for v in violations if "caller.py" in str(v.file)]
    assert caller_hits, (
        "no perf rule fired on caller.py's loop over a process-spawning, "
        "loop-invariant callee -- the exact shape of the 2026-07-22 "
        f"rev-parse incident (all violations: {violations})"
    )
