"""Unit-level coverage for `std.krb`'s attr-desugar/read-back pair (T-0262,
`src/frob/strata/_krb.py`): `krb_attrs` (desugar), `krb_manifest_for`
(read-back), `krb_trust_flows` (domain-trust edge synthesis), and
`flow_authenticates_via` (flow-level read-back) against hand-built values,
mirroring `test_host.py`'s unit-test shape. End-to-end parse -> elaborate
coverage lives in `test_litmus_krb.py`.
"""

from __future__ import annotations

from frob.strata._krb import (
    KrbDelegationKind,
    KrbTrust,
    flow_authenticates_via,
    krb_attrs,
    krb_manifest_for,
    krb_trust_flows,
)
from frob.strata._models import Flow, Node


class TestKrbAttrs:
    # frob:tests src/frob/strata/_krb.py::krb_attrs kind="unit"
    def test_desugars(self):
        attrs = krb_attrs(
            realm="CORP.EXAMPLE",
            is_kdc=True,
            spns=("HTTP/app@CORP.EXAMPLE",),
            delegation="constrained",
            delegation_targets=("HTTP/backend@CORP.EXAMPLE",),
            trusts=(("partner_kdc", "two-way", True),),
        )
        assert attrs == (
            "krb_realm=CORP.EXAMPLE",
            "krb_kdc",
            "krb_spn=HTTP/app@CORP.EXAMPLE",
            "krb_delegation=constrained",
            "krb_delegation_target=HTTP/backend@CORP.EXAMPLE",
            "krb_trust=partner_kdc:two-way:True",
        )

    # frob:tests src/frob/strata/_krb.py::krb_attrs kind="unit"
    def test_no_clauses_desugars_to_empty(self):
        attrs = krb_attrs(
            realm=None,
            is_kdc=False,
            spns=(),
            delegation=None,
            delegation_targets=(),
            trusts=(),
        )
        assert attrs == ()


class TestKrbManifest:
    # frob:tests src/frob/strata/_krb.py::krb_manifest_for kind="unit"
    def test_reads(self):
        node = Node(
            id="app",
            trust="trusted",
            attrs=(
                "krb_realm=CORP.EXAMPLE",
                "krb_spn=HTTP/app@CORP.EXAMPLE",
                "krb_delegation=unconstrained",
                "krb_trust=partner_kdc:one-way:False",
            ),
        )
        manifest = krb_manifest_for(node)
        assert manifest is not None
        assert manifest.realm == "CORP.EXAMPLE"
        assert manifest.is_kdc is False
        assert manifest.spns == ("HTTP/app@CORP.EXAMPLE",)
        assert manifest.delegation is KrbDelegationKind.UNCONSTRAINED
        assert manifest.trusts == (
            KrbTrust(target="partner_kdc", direction="one-way", transitive=False),
        )

    # frob:tests src/frob/strata/_krb.py::krb_manifest_for kind="unit"
    def test_node_with_no_krb_attrs_returns_none(self):
        node = Node(id="app", trust="trusted", attrs=("code=src/**",))
        assert krb_manifest_for(node) is None


class TestKrbTrustFlows:
    # frob:tests src/frob/strata/_krb.py::krb_trust_flows kind="unit"
    def test_sync(self):
        a = Node(id="a", trust="trusted", attrs=("krb_trust=b:one-way:False",))
        b = Node(id="b", trust="trusted", attrs=())
        flows = krb_trust_flows((a, b))
        assert flows == (
            Flow(id="krb-trust:a:b", src="a", dst="b", attrs=("krb_trust",)),
        )

    # frob:tests src/frob/strata/_krb.py::krb_trust_flows kind="unit"
    def test_two_way_synthesizes_reverse_edge_too(self):
        a = Node(id="a", trust="trusted", attrs=("krb_trust=b:two-way:False",))
        b = Node(id="b", trust="trusted", attrs=())
        flows = krb_trust_flows((a, b))
        assert {(f.src, f.dst) for f in flows} == {("a", "b"), ("b", "a")}

    # frob:tests src/frob/strata/_krb.py::krb_trust_flows kind="unit"
    def test_no_trusts_synthesizes_nothing(self):
        a = Node(id="a", trust="trusted", attrs=())
        assert krb_trust_flows((a,)) == ()


class TestFlowAuthVia:
    # frob:tests src/frob/strata/_krb.py::flow_authenticates_via kind="unit"
    def test_read(self):
        flow = Flow(id="f1", src="a", dst="b", attrs=("krb_ticket=tgt",))
        assert flow_authenticates_via(flow) == "tgt"

    # frob:tests src/frob/strata/_krb.py::flow_authenticates_via kind="unit"
    def test_flow_with_no_krb_attrs_returns_none(self):
        flow = Flow(id="f1", src="a", dst="b")
        assert flow_authenticates_via(flow) is None
