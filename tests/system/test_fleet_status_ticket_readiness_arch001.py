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

import pytest

from tests.system.conftest import run


class TestFleetStatusTicketReadinessArch001:
    # T-3247: `run("check", "--only", "arch")` spawns a real `frob check`
    # subprocess against this repo's own whole tree (`tests/system/conftest.
    # py::run`) -- measured 52.98s warm-cache locally. The 2026-08-28 CI
    # run's own faulthandler dump caught this test still inside `subprocess.
    # communicate` at the 100s mark on a CI runner, well past the local
    # baseline; 300s gives headroom above the observed near-miss without
    # raising the global 120s ceiling (docs/guides/testing.md#per-test-
    # timeout-ci-hardening, same reasoning T-0742 used for
    # test_scaffold_dx.py).
    @pytest.mark.timeout(300)
    def test_ticket_readiness_is_not_an_arch001_finding(self) -> None:
        # T-3247: `run`'s own DEFAULT_RUN_TIMEOUT_S (T-2980) caps a call
        # with no explicit `timeout=` at 100s, independent of this test's
        # own @pytest.mark.timeout(300) above -- raise it to match, or a
        # slow-but-legitimate run still hits the 100s inner cap first.
        result = run("check", "--only", "arch", timeout=300)
        combined = result.stdout + result.stderr
        assert "ticket_readiness" not in combined, (
            f"ticket_readiness reappeared in an ARCH001/ARCH103 finding:\n{combined}"
        )
