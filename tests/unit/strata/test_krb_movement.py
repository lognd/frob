"""Unit-level coverage for KRB001-004 movement proofs (T-0263,
`src/frob/strata/_krb_movement.py`) against hand-built `KernelModel`
values -- mirroring `test_host_isolation.py`'s unit-test shape.
End-to-end parse -> elaborate coverage lives in
`test_litmus_krb_movement.py`.
"""

from __future__ import annotations

from frob.strata._krb import krb_trust_flows
from frob.strata._krb_movement import (
    KRB_MOVEMENT_CATALOG,
    KRB_MOVEMENT_VIEWS,
    evaluate_constrained_delegation_blast_radius,
    evaluate_cross_realm_containment,
    evaluate_krb_movement_waived,
    evaluate_roastable_spn,
    evaluate_unconstrained_delegation,
)
from frob.strata._models import KernelModel, Node, Waiver
from frob.strata._scenarios import build_compromised_krb_scenario, evaluate_scenarios
from frob.strata._threat import check_catalog_completeness


class TestKrb001:
    # frob:tests src/frob/strata/_krb_movement.py::evaluate_unconstrained_delegation kind="unit"
    def test_fires(self):
        node = Node(
            id="app",
            trust="trusted",
            attrs=("krb_realm=CORP.EXAMPLE", "krb_delegation=unconstrained"),
        )
        model = KernelModel(nodes=(node,))
        violations = evaluate_unconstrained_delegation(model).danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "KRB001"
        assert violations[0].sub_target == "unconstrained-delegation"
        assert violations[0].node == "app"

    # frob:tests src/frob/strata/_krb_movement.py::evaluate_unconstrained_delegation kind="unit"
    def test_skips_constrained(self):
        node = Node(
            id="app",
            trust="trusted",
            attrs=(
                "krb_realm=CORP.EXAMPLE",
                "krb_delegation=constrained",
                "krb_delegation_target=HTTP/backend@CORP.EXAMPLE",
            ),
        )
        model = KernelModel(nodes=(node,))
        assert evaluate_unconstrained_delegation(model).danger_ok == ()


class TestKrb002:
    # frob:tests src/frob/strata/_krb_movement.py::evaluate_roastable_spn kind="unit"
    def test_fires(self):
        node = Node(
            id="app",
            trust="trusted",
            attrs=(
                "krb_spn=HTTP/app.corp.example@CORP.EXAMPLE",
                "krb_spn=MSSQL/app.corp.example@CORP.EXAMPLE",
            ),
        )
        model = KernelModel(nodes=(node,))
        violations = evaluate_roastable_spn(model).danger_ok
        assert len(violations) == 2
        assert {v.rule for v in violations} == {"KRB002"}
        assert {v.sub_target for v in violations} == {
            "HTTP/app.corp.example@CORP.EXAMPLE",
            "MSSQL/app.corp.example@CORP.EXAMPLE",
        }

    # frob:tests src/frob/strata/_krb_movement.py::evaluate_roastable_spn kind="unit"
    def test_no_spn_no_finding(self):
        node = Node(id="app", trust="trusted", attrs=("krb_realm=CORP.EXAMPLE",))
        model = KernelModel(nodes=(node,))
        assert evaluate_roastable_spn(model).danger_ok == ()

    # frob:tests src/frob/strata/_krb_movement.py::evaluate_krb_movement_waived kind="unit"
    def test_waivable_with_gmsa_reason(self):
        node = Node(
            id="app",
            trust="trusted",
            attrs=("krb_spn=HTTP/app.corp.example@CORP.EXAMPLE",),
            waives=(
                Waiver(
                    rule="KRB002:HTTP/app.corp.example@CORP.EXAMPLE",
                    reason="gMSA-backed account, rotated automatically by AD",
                ),
            ),
        )
        model = KernelModel(nodes=(node,))
        _krb001, krb002, _krb003, _krb004 = evaluate_krb_movement_waived(
            model
        ).danger_ok
        assert krb002.kept == ()
        assert len(krb002.waived) == 1


class TestKrb003:
    # frob:tests src/frob/strata/_krb_movement.py::evaluate_constrained_delegation_blast_radius kind="unit"
    def test_chains(self):
        # svc (authenticated) constrained-delegates to mid (authenticated),
        # which itself constrained-delegates to vault (trusted) -- a
        # two-hop S4U2Proxy chain that must be caught, not just the
        # immediate target.
        svc = Node(
            id="svc",
            trust="authenticated",
            attrs=(
                "krb_spn=HTTP/svc@CORP.EXAMPLE",
                "krb_delegation=constrained",
                "krb_delegation_target=HTTP/mid@CORP.EXAMPLE",
            ),
        )
        mid = Node(
            id="mid",
            trust="authenticated",
            attrs=(
                "krb_spn=HTTP/mid@CORP.EXAMPLE",
                "krb_delegation=constrained",
                "krb_delegation_target=HTTP/vault@CORP.EXAMPLE",
            ),
        )
        vault = Node(
            id="vault", trust="trusted", attrs=("krb_spn=HTTP/vault@CORP.EXAMPLE",)
        )
        model = KernelModel(nodes=(svc, mid, vault))
        violations = evaluate_constrained_delegation_blast_radius(model).danger_ok
        # `mid` also fires its OWN direct-target finding (it independently
        # constrained-delegates straight to `vault`) -- the chain finding
        # rooted at `svc` is the one this test cares about.
        assert len(violations) == 2
        by_node = {v.node: v for v in violations}
        assert by_node["svc"].rule == "KRB003"
        assert by_node["svc"].peer == "vault"
        assert "mid" in by_node["svc"].detail
        assert by_node["mid"].peer == "vault"

    # frob:tests src/frob/strata/_krb_movement.py::evaluate_constrained_delegation_blast_radius kind="unit"
    def test_non_chaining_same_trust_discharges(self):
        svc = Node(
            id="svc",
            trust="trusted",
            attrs=(
                "krb_spn=HTTP/svc@CORP.EXAMPLE",
                "krb_delegation=constrained",
                "krb_delegation_target=HTTP/backend@CORP.EXAMPLE",
            ),
        )
        backend = Node(
            id="backend", trust="trusted", attrs=("krb_spn=HTTP/backend@CORP.EXAMPLE",)
        )
        model = KernelModel(nodes=(svc, backend))
        assert evaluate_constrained_delegation_blast_radius(model).danger_ok == ()


class TestKrb004:
    # frob:tests src/frob/strata/_krb_movement.py::evaluate_cross_realm_containment kind="unit"
    def test_fires(self):
        low = Node(
            id="low_kdc",
            trust="authenticated",
            attrs=(
                "krb_realm=LOW.EXAMPLE",
                "krb_kdc",
                "krb_trust=high_kdc:one-way:True",
            ),
        )
        high = Node(
            id="high_kdc", trust="trusted", attrs=("krb_realm=HIGH.EXAMPLE", "krb_kdc")
        )
        nodes = (low, high)
        model = KernelModel(nodes=nodes, flows=krb_trust_flows(nodes))
        violations = evaluate_cross_realm_containment(model).danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "KRB004"
        assert violations[0].node == "low_kdc"
        assert violations[0].peer == "high_kdc"

    # frob:tests src/frob/strata/_krb_movement.py::evaluate_cross_realm_containment kind="unit"
    def test_same_trust_realms_discharge(self):
        a = Node(
            id="a_kdc",
            trust="trusted",
            attrs=("krb_realm=A.EXAMPLE", "krb_kdc", "krb_trust=b_kdc:two-way:True"),
        )
        b = Node(id="b_kdc", trust="trusted", attrs=("krb_realm=B.EXAMPLE", "krb_kdc"))
        nodes = (a, b)
        model = KernelModel(nodes=nodes, flows=krb_trust_flows(nodes))
        assert evaluate_cross_realm_containment(model).danger_ok == ()


class TestKrbScen:
    # frob:tests src/frob/strata/_krb_movement.py::evaluate_krb_movement_waived kind="unit"
    def test_all(self):
        """A compromised node with unconstrained delegation can reach ANY
        other node -- the true worst-case blast radius KRB001 names.
        `NoFlow` claims to every other node must REFUTE, not vacuously
        prove, over the scenario's rewritten closure."""
        app = Node(
            id="app",
            trust="trusted",
            attrs=("krb_delegation=unconstrained",),
        )
        other = Node(id="other", trust="trusted", attrs=())
        model = KernelModel(nodes=(app, other))
        scenario = build_compromised_krb_scenario(model, "app", "compromise-app")
        assert scenario.is_ok
        model_with_scenario = model.model_copy(
            update={"scenarios": (scenario.danger_ok,)}
        )
        results = evaluate_scenarios(model_with_scenario).danger_ok
        assert len(results) == 1
        scenario_result = results[0]
        assert len(scenario_result.results) == 1
        assert scenario_result.results[0].verdict.value == "refuted"

    # frob:tests src/frob/strata/_krb_movement.py::evaluate_krb_movement_waived kind="unit"
    def test_constrained_bounded_to_targets(self):
        """A compromised node with constrained delegation can only reach
        its resolved `target` SPN's owning node -- an UNRELATED third node
        stays outside the blast radius (correctly PROVED)."""
        app = Node(
            id="app",
            trust="trusted",
            attrs=(
                "krb_spn=HTTP/app@CORP.EXAMPLE",
                "krb_delegation=constrained",
                "krb_delegation_target=HTTP/backend@CORP.EXAMPLE",
            ),
        )
        backend = Node(
            id="backend", trust="trusted", attrs=("krb_spn=HTTP/backend@CORP.EXAMPLE",)
        )
        unrelated = Node(id="unrelated", trust="trusted", attrs=())
        model = KernelModel(nodes=(app, backend, unrelated))
        scenario = build_compromised_krb_scenario(model, "app", "compromise-app")
        assert scenario.is_ok
        model_with_scenario = model.model_copy(
            update={"scenarios": (scenario.danger_ok,)}
        )
        results = evaluate_scenarios(model_with_scenario).danger_ok
        assert len(results) == 1
        by_claim = {r.claim_id: r.verdict.value for r in results[0].results}
        assert by_claim["krb-blast-radius:app:backend"] == "refuted"
        assert by_claim["krb-blast-radius:app:unrelated"] == "proved"

    # frob:tests src/frob/strata/_krb_movement.py::evaluate_krb_movement_waived kind="unit"
    def test_unknown_node_fails_closed(self):
        model = KernelModel(nodes=(Node(id="app", trust="trusted", attrs=()),))
        scenario = build_compromised_krb_scenario(model, "does-not-exist", "compromise")
        assert scenario.is_err


class TestKrbCatalog:
    # frob:tests src/frob/strata/_krb_movement.py::KRB_MOVEMENT_CATALOG kind="unit"
    def test_catalog_completeness_over_own_view(self):
        violations = check_catalog_completeness(
            "krb-movement-baseline", KRB_MOVEMENT_CATALOG, (), KRB_MOVEMENT_VIEWS
        ).danger_ok
        assert violations == ()
