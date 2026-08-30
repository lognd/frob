"""T-3490: a live-repo regression pin for WIRE002 (`frob.gates._wire.
wire_gate`'s follow_up-ticket-accountability rule), mirroring `tests/
test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo`'s shape.

MOTIVATING CASE: 12 separate `frob:waive WIRE001` sites across 5 files
(src/frob/app/ticket_runner/_land_cmd.py, src/frob/gates/_arch.py,
src/frob/gates/_coverage_sites.py, src/frob/gates/_render_lint.py,
tests/unit/test_new_ticket_scope_overlap_warning.py) all cited the SAME
ticket, T-2057, as their `follow_up=` accountability anchor for a
deliberately-permanent (not actually pending) WIRE001 waiver posture --
"a genuinely-wired-but-not-externally-called symbol" needs SOME open
ticket to point at (WIRE002 requires one), and T-2057 served that role
for years. T-2057 was then DROPPED for unrelated reasons (blocked
pending a sound site-identity mapping), silently orphaning all 12
waivers at once -- a single upstream ticket-state change breaking 5
files nothing about this rule's own design anticipated. This test pins
the fix (re-pointed at a still-open replacement ticket) so a future
closure of THAT replacement fails HERE, immediately, instead of
resurfacing as an unattributed post-land sweep regression the way T-3490
itself did.
"""

from __future__ import annotations

from pathlib import Path

from frob.gates._wire import _wire002_violations
from frob.graph import build_graph
from frob.tickets._archive import load_queue


# frob:ticket T-3490
def test_wire002_zero_against_live_repo(tmp_path: Path) -> None:
    """Every live `frob:waive WIRE001` in this repo binds to a real, open
    `follow_up` ticket -- zero WIRE002 findings repo-wide."""
    root = Path(__file__).resolve().parents[3]
    snapshot = build_graph(root, tmp_path / "cache.db").danger_ok
    queue = load_queue(root).danger_ok
    violations = _wire002_violations(snapshot, queue)
    assert violations == [], f"unexpected WIRE002 finding(s): {violations}"
