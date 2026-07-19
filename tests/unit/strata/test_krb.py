"""Unit-level coverage for `std.krb`'s attr-desugar/read-back pair (T-0262,
`src/frob/strata/_krb.py`): `krb_attrs` (desugar), `krb_manifest_for`
(read-back), `krb_trust_flows` (domain-trust edge synthesis), and
`flow_authenticates_via` (flow-level read-back) against hand-built values,
mirroring `test_host.py`'s unit-test shape. End-to-end parse -> elaborate
coverage lives in `test_litmus_krb.py`.
"""

from __future__ import annotations

from frob.strata._elaborate import elaborate
from frob.strata._errors import StrataError
from frob.strata._facts import build_facts
from frob.strata._krb import (
    KrbDelegationKind,
    KrbTrust,
    flow_authenticates_via,
    krb_attrs,
    krb_manifest_for,
    krb_trust_flows,
)
from frob.strata._models import Flow, Node
from frob.strata._parse import parse_module


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


class TestKrbValidation:
    """Regression coverage for review-round-2 findings on T-0262.

    A `spn` with no `runs_as` service account on the same node to bind it
    to is a dangling reference by a different name (`_elaborate.py::
    _validate_krb`, `StrataError.MalformedKrb`) -- fails closed rather
    than silently elaborating a principal-less SPN.
    """

    # frob:tests src/frob/strata/_elaborate.py::_validate_krb kind="unit"
    def test_spn_without_runs_as_is_malformed(self):
        src = """
module m
node app: trusted {
    spn "HTTP/app.corp.example@CORP.EXAMPLE";
}
"""
        module = parse_module(src).danger_ok
        result = elaborate(module)
        assert result.is_err
        assert result.danger_err is StrataError.MalformedKrb

    # frob:tests src/frob/strata/_elaborate.py::_validate_krb kind="unit"
    def test_spn_with_runs_as_elaborates_cleanly(self):
        src = """
module m
node app: trusted {
    runs_as "app-svc";
    spn "HTTP/app.corp.example@CORP.EXAMPLE";
}
"""
        module = parse_module(src).danger_ok
        result = elaborate(module)
        assert result.is_ok


def _reach(src_text: str, start: str) -> dict[str, tuple[str, ...]]:
    """Parse+elaborate+build_facts one `.strata` snippet, then walk `reachable`."""
    module = parse_module(src_text).danger_ok
    model = elaborate(module).danger_ok
    facts = build_facts(model).danger_ok
    return facts.reachable(start, through_barriers=True)


class TestTrustChainReachability:
    """Reviewer's exact reproduction (T-0262 round 2, review-verified sound
    for direction/two-way synthesis but NOT for the `transitive` flag) --
    a three-realm one-way trust chain `a --trusts--> b --trusts--> c`.

    KNOWN GAP (T-draft-f9f9fe96, docs/strata/krb.md#known-gap-transitive-
    is-recorded-not-yet-enforced-t-draft-f9f9fe96): `KrbTrust.transitive`
    round-trips correctly through the AST/manifest, but the synthesized
    `Flow`s carry no signal `FactBase.reachable`'s shared BFS can use to
    stop a non-transitive hop from chaining -- so BOTH tests below observe
    `reach(a, c) is True` today. The all-transitive case is the CORRECT
    kernel behavior (transitive trusts SHOULD chain). The all-non-
    transitive case is the DISCLOSED BUG: it should refute once
    T-draft-f9f9fe96's terminal-edge support lands in `strata-core/src/
    lib.rs` -- this test is a trip-wire, not an endorsement: when that
    ticket lands, this assertion must flip to `is False` (do not just
    delete it).
    """

    _CHAIN_TEMPLATE = """
module m
node a: trusted {{
    realm "A.EXAMPLE";
    kdc;
    trusts b direction "one-way"{a_transitive};
}}
node b: trusted {{
    realm "B.EXAMPLE";
    kdc;
    trusts c direction "one-way"{b_transitive};
}}
node c: trusted {{
    realm "C.EXAMPLE";
    kdc;
}}
"""

    def test_transitive_chain_reaches_across_both_hops(self):
        src = self._CHAIN_TEMPLATE.format(
            a_transitive=" transitive", b_transitive=" transitive"
        )
        paths = _reach(src, "a")
        assert "b" in paths
        assert "c" in paths

    # KNOWN GAP trip-wire -- see class docstring. Currently `is True`
    # (the bug); must become `is False` once T-draft-f9f9fe96 lands.
    def test_non_transitive_chain_currently_over_reaches_known_gap(self):
        src = self._CHAIN_TEMPLATE.format(a_transitive="", b_transitive="")
        paths = _reach(src, "a")
        assert "b" in paths  # single-hop reach is always correct
        assert "c" in paths  # BUG: should be absent once terminal edges land
