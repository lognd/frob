"""T-2213 regression: `scripts/fleet_status.py::ticket_readiness` had grown
to 80 lines (ARCH001, threshold 60) and lost its `frob:doc` edge (COV001)
after seven separate lands in one day. Split along the questions it
answers (`_scope_diverges_from_lease`, `_ticket_dispatchable`) rather than
an arbitrary line-count halving, and restored the `frob:doc
docs/guides/coordinator-scripts.md#ticket_readiness` anchor.

Runs the real `frob check --only arch` CLI against this repo (the same
tool `frob check` itself runs) and asserts `ticket_readiness` no longer
appears in an ARCH001 finding.
"""

from __future__ import annotations

from tests.system.conftest import run


class TestFleetStatusTicketReadinessArch001:
    def test_ticket_readiness_is_not_an_arch001_finding(self) -> None:
        result = run("check", "--only", "arch")
        combined = result.stdout + result.stderr
        assert "ticket_readiness" not in combined, (
            "ticket_readiness reappeared in an ARCH001/ARCH103 finding:\n"
            f"{combined}"
        )
