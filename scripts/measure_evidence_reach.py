#!/usr/bin/env python3
"""T-3046 repo-wide measurement: for every DONE ticket's non-cmd evidence
id, classify `frob.graph.reach.classify_evidence_reach` against that
ticket's own `scope`/`evidence_scope`, and report the REACHES/
DOES_NOT_REACH/UNKNOWN counts.

Standalone rather than a wired `frob check` gate stage: `src/frob/gates/
__init__.py` (where every other gate's job-table entry lives) and
`docs/modules/gates.md` are both leased by T-3009 at the time T-3046 was
worked (see this ticket's Done report) -- wiring `evidence_reach_gate`
into the live pipeline is filed as a follow-up ticket, blocked on T-3009
landing, rather than hand-edited around the lease.

Usage: `uv run python scripts/measure_evidence_reach.py [--root PATH]`
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# frob:waive SYS003 reason="one-off T-3046 measurement script (scripts_ops); \
# design/frob.strata's Flow declarations are leased by T-3009 while this was worked, \
# so a real Flow entry cannot be added here -- see this file's own module docstring"
from frob.graph import build_graph

# frob:waive SYS003 reason="same one-off measurement-script exemption as the \
# frob.graph import immediately above"
from frob.graph.reach import EvidenceReach, classify_evidence_reach
from frob.tickets._models import TicketState, is_cmd_evidence
from frob.tickets._store import load_all


# frob:doc docs/modules/graph.md#evidence-reach-t-3046
# frob:tests tests/test_measure_evidence_reach.py::TestMeasureEvidenceReachMain.test_runs_clean_over_a_minimal_ticket_ledger  # noqa: E501
def measure_evidence_reach_main() -> int:
    """CLI entrypoint: `--root` defaults to the current repo root; prints
    one line per classified evidence id plus a summary count, and exits
    non-zero only on a genuine load/build failure (never on findings --
    this is a measurement tool, not a gate)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()

    tickets_result = load_all(root)
    if tickets_result.is_err:
        # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, same as \
        # scripts/branch_stranded_work_analysis.py's own identical bare-print waivers \
        # -- a one-shot measurement script run directly by a human/agent, not part of \
        # frob's own gate-rendered output surface"
        print(f"ERROR: load_all({root}) failed: {tickets_result.danger_err}")
        return 1
    tickets = tickets_result.danger_ok

    cache = root / ".frob" / "cache.db"
    snapshot_result = build_graph(root, cache)
    if snapshot_result.is_err:
        # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, see above"
        print(f"ERROR: build_graph({root}) failed: {snapshot_result.danger_err}")
        return 1
    snapshot = snapshot_result.danger_ok

    _classify_and_print(root, snapshot, tickets)
    return 0


def _classify_and_print(root: Path, snapshot, tickets) -> None:  # noqa: ANN001
    """The classify-every-ticket-and-print half of
    `measure_evidence_reach_main` (extracted per ARCH001): loops every
    DONE ticket's non-cmd evidence, classifies each id, prints every
    non-REACHES line as it goes, then the final REACHES/DOES_NOT_REACH/
    UNKNOWN summary."""
    counts = {
        EvidenceReach.REACHES: 0,
        EvidenceReach.DOES_NOT_REACH: 0,
        EvidenceReach.UNKNOWN: 0,
    }
    for ticket in sorted(tickets.values(), key=lambda t: t.id):
        if ticket.state != TicketState.DONE:
            continue
        scope = tuple(ticket.scope)
        evidence_scope = tuple(getattr(ticket, "evidence_scope", ()))
        if not scope and not evidence_scope:
            continue
        for evidence in ticket.evidence:
            if is_cmd_evidence(evidence):
                continue
            result = classify_evidence_reach(
                root, snapshot, scope, evidence, evidence_scope=evidence_scope
            )
            counts[result.status] += 1
            if result.status != EvidenceReach.REACHES:
                # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, see \
                # above"
                print(f"{ticket.id}: {result.status}: {evidence}: {result.reason}")

    total = sum(counts.values())
    # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, see above"
    print("---")
    # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, see above"
    print(f"total classified: {total}")
    for status, count in counts.items():
        pct = (100 * count / total) if total else 0
        # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, see above"
        print(f"  {status}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    sys.exit(measure_evidence_reach_main())
