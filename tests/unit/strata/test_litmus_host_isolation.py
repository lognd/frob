"""HOST001/HOST002 litmus fixture coverage (T-0256, mirroring
`test_litmus_waive.py`'s parse -> elaborate -> evaluate round-trip
discipline): a real shared-user VULN model that genuinely fires both
rules, and a real isolated HARDENED model (disjoint paths/ports plus
explicit waivers for the two structurally-unprovable sub-targets) that
fully discharges -- both round-tripped through the real `strata_core`
parser, never a hand-built `KernelModel`/`Waiver` value.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, elaborate, parse_module
from frob.strata._host_isolation import evaluate_host_isolation_waived

_LITMUS_DIR = Path(__file__).resolve().parent / "litmus"


def _load_model(filename: str) -> KernelModel:
    """Parse+elaborate one `.strata` fixture under `litmus/` end to end."""
    text = (_LITMUS_DIR / filename).read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    return elaborate(module).danger_ok


class TestHostIsolationVulnLitmus:
    # frob:tests src/frob/strata/_host_isolation.py::evaluate_host_isolation_waived kind="unit"
    def test_shared_user_model_fires_host001_and_host002(self):
        model = _load_model("host_isolation_vuln.strata")
        host001, host002 = evaluate_host_isolation_waived(model).danger_ok
        assert host001.kept != ()
        assert host002.kept != ()
        sub_targets_001 = {v.sub_target for v in host001.kept}
        assert "shared-writable-path" in sub_targets_001
        assert "cross-user-socket" in sub_targets_001
        assert "shared-group" in sub_targets_001
        sub_targets_002 = {v.sub_target for v in host002.kept}
        assert "sudoers" in sub_targets_002


class TestHostIsolationHardenedLitmus:
    # frob:tests src/frob/strata/_host_isolation.py::evaluate_host_isolation_waived kind="unit"
    def test_isolated_model_discharges(self):
        model = _load_model("host_isolation_hardened.strata")
        host001, host002 = evaluate_host_isolation_waived(model).danger_ok
        assert host001.kept == ()
        assert host002.kept == ()
        assert host001.stale == ()
        assert host002.stale == ()
        # both waivers actually fired and were consumed, never a no-op
        assert len(host001.waived) == 1
        assert len(host002.waived) == 2
