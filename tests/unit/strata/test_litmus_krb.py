"""`std.krb` litmus fixture coverage (T-0262, mirroring `test_litmus_host.py`'s
parse -> elaborate round-trip discipline): the declared/undeclared pair
round-trips through the real `strata_core` parser, proving `krb_attrs`'s
attr-desugar convention, `krb_manifest_for`'s read-back, `krb_trust_flows`'s
synthesized cross-realm edge, and `flow_authenticates_via`'s read-back all
survive real source text, not just a hand-built `KernelModel`. T-0262 is
model+vocabulary-only (delegation-abuse obligations are T-0263), so there is
no vuln/hardened firing pair to litmus here -- the pair instead covers "krb
declared" vs "krb absent", the one behavioral fork `krb_manifest_for` has
(module docstring, mirrors `test_litmus_host.py`'s own scope note).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, elaborate, parse_module
from frob.strata._krb import (
    KrbDelegationKind,
    flow_authenticates_via,
    krb_manifest_for,
)

_LITMUS_DIR = Path(__file__).resolve().parent / "litmus"


def _load_model(filename: str) -> KernelModel:
    """Parse+elaborate one `.strata` fixture under `litmus/` end to end."""
    text = (_LITMUS_DIR / filename).read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    return elaborate(module).danger_ok


class TestKrbDeclaredLitmus:
    # frob:tests src/frob/strata/_krb.py::krb_manifest_for kind="unit"
    def test_declared_manifest_round_trips_every_field(self):
        model = _load_model("krb_declared.strata")
        node = next(n for n in model.nodes if n.id == "app")
        manifest = krb_manifest_for(node)
        assert manifest is not None
        assert manifest.realm == "CORP.EXAMPLE"
        assert manifest.is_kdc is False
        assert manifest.spns == ("HTTP/app.corp.example@CORP.EXAMPLE",)
        assert manifest.delegation is KrbDelegationKind.CONSTRAINED
        assert manifest.delegation_targets == (
            "HTTP/backend.corp.example@CORP.EXAMPLE",
        )

    # frob:tests src/frob/strata/_krb.py::krb_trust_flows kind="unit"
    def test_two_way_transitive_trust_synthesizes_both_directions(self):
        model = _load_model("krb_declared.strata")
        trust_flows = {(f.src, f.dst) for f in model.flows if "krb_trust" in f.attrs}
        assert trust_flows == {
            ("corp_kdc", "partner_kdc"),
            ("partner_kdc", "corp_kdc"),
        }

    # frob:tests src/frob/strata/_krb.py::flow_authenticates_via kind="unit"
    def test_flow_authenticates_via_reads_ticket_kind(self):
        model = _load_model("krb_declared.strata")
        flow = next(f for f in model.flows if f.id == "app_to_backend")
        assert flow_authenticates_via(flow) == "st"

    # frob:tests src/frob/strata/_krb.py::krb_manifest_for kind="unit"
    def test_kdc_node_manifest_has_no_delegation(self):
        model = _load_model("krb_declared.strata")
        node = next(n for n in model.nodes if n.id == "corp_kdc")
        manifest = krb_manifest_for(node)
        assert manifest is not None
        assert manifest.is_kdc is True
        assert manifest.realm == "CORP.EXAMPLE"
        assert manifest.delegation is None


class TestKrbUndeclaredLitmus:
    # frob:tests src/frob/strata/_krb.py::krb_manifest_for kind="unit"
    def test_undeclared_node_has_no_manifest(self):
        model = _load_model("krb_undeclared.strata")
        node = next(n for n in model.nodes if n.id == "app")
        assert krb_manifest_for(node) is None
