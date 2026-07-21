"""KRB001-004 litmus fixture coverage (T-0263, mirroring
`test_litmus_host_isolation.py`'s parse -> elaborate -> evaluate
round-trip discipline): a real VULN model (unconstrained delegation, a
roastable SPN, a constrained-delegation chain escalating to a
higher-trust vault, a one-way trust from a low- into a high-trust realm)
that genuinely fires all four rules, and a real HARDENED model
(constrained-only delegation bounded to same-trust targets, same-trust
realms, the one unavoidable roastable-SPN honest gap discharged via an
explicit gMSA waiver) that fully discharges -- both round-tripped
through the real `strata_core` parser, never a hand-built `KernelModel`/
`Waiver` value.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, elaborate, parse_module
from frob.strata._krb_movement import evaluate_krb_movement_waived

_LITMUS_DIR = Path(__file__).resolve().parent / "litmus"


def _load_model(filename: str) -> KernelModel:
    """Parse+elaborate one `.strata` fixture under `litmus/` end to end."""
    text = (_LITMUS_DIR / filename).read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    return elaborate(module).danger_ok


class TestKrbMovementVulnLitmus:
    # frob:tests src/frob/strata/_krb_movement.py::evaluate_krb_movement_waived kind="unit"
    def test_vuln_model_fires_all_four_rules(self):
        model = _load_model("krb_movement_vuln.strata")
        krb001, krb002, krb003, krb004 = evaluate_krb_movement_waived(model).danger_ok

        assert krb001.kept != ()
        assert {v.node for v in krb001.kept} == {"app"}

        assert krb002.kept != ()
        roasted_nodes = {v.node for v in krb002.kept}
        assert "app" in roasted_nodes
        assert "mid" in roasted_nodes
        assert "vault" in roasted_nodes

        assert krb003.kept != ()
        assert {v.node for v in krb003.kept} == {"mid"}
        assert {v.peer for v in krb003.kept} == {"vault"}

        assert krb004.kept != ()
        assert {(v.node, v.peer) for v in krb004.kept} == {("low_kdc", "high_kdc")}


class TestKrbMovementHardenedLitmus:
    # frob:tests src/frob/strata/_krb_movement.py::evaluate_krb_movement_waived kind="unit"
    def test_hardened_model_discharges(self):
        model = _load_model("krb_movement_hardened.strata")
        krb001, krb002, krb003, krb004 = evaluate_krb_movement_waived(model).danger_ok

        assert krb001.kept == ()
        assert krb001.stale == ()

        # KRB002 fires on both declared SPNs (no gMSA vocabulary exists
        # to structurally prove it false, module docstring) but each is
        # fully discharged by the fixture's explicit gMSA-attestation
        # waiver.
        assert krb002.kept == ()
        assert len(krb002.waived) == 2
        assert krb002.stale == ()

        assert krb003.kept == ()
        assert krb003.stale == ()

        assert krb004.kept == ()
        assert krb004.stale == ()
