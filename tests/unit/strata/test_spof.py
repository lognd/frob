"""REL25x SPOF-detection unit coverage (T-0645, `frob.strata._spof`) --
`check_spof` is a pure structural read of `KernelModel`, no `bind_code`/
`tmp_path` needed (module docstring: no proof-against-code companion)."""

from __future__ import annotations

from frob.strata import Capacity, Flow, KernelModel, Node, Quantity, Waiver
from frob.strata._spof import REL_SPOF, check_spof


def _rate(value: float = 1.0) -> Quantity:
    return Quantity(value=value, unit="req/s")


class TestSpof:
    # frob:tests tests/unit/strata/test_spof.py::TestSpof.test_singleton_node_with_critical_inbound_fires
    def test_singleton_node_with_critical_inbound_fires(self):
        model = KernelModel(
            nodes=(
                Node(id="web", trust="untrusted"),
                Node(id="inventory", trust="trusted"),
            ),
            flows=(Flow(id="f1", src="web", dst="inventory", attrs=("critical",)),),
        )
        report = check_spof(model)
        violations = [v for v in report.violations if v.rule == REL_SPOF]
        assert {v.node for v in violations} == {"inventory"}

    # frob:tests tests/unit/strata/test_spof.py::TestSpof.test_declared_singleton_capacity_fires
    def test_declared_singleton_capacity_fires(self):
        model = KernelModel(
            nodes=(
                Node(id="web", trust="untrusted"),
                Node(
                    id="inventory",
                    trust="trusted",
                    capacity=Capacity(service_rate=_rate(), replicas_max=1),
                ),
            ),
            flows=(Flow(id="f1", src="web", dst="inventory", attrs=("critical",)),),
        )
        report = check_spof(model)
        violations = [v for v in report.violations if v.rule == REL_SPOF]
        assert {v.node for v in violations} == {"inventory"}

    # frob:tests tests/unit/strata/test_spof.py::TestSpof.test_replicated_capacity_clean
    def test_replicated_capacity_clean(self):
        model = KernelModel(
            nodes=(
                Node(id="web", trust="untrusted"),
                Node(
                    id="inventory",
                    trust="trusted",
                    capacity=Capacity(
                        service_rate=_rate(), replicas_min=2, replicas_max=3
                    ),
                ),
            ),
            flows=(Flow(id="f1", src="web", dst="inventory", attrs=("critical",)),),
        )
        report = check_spof(model)
        assert not [v for v in report.violations if v.rule == REL_SPOF]

    # frob:tests tests/unit/strata/test_spof.py::TestSpof.test_redundant_exemption_clean
    def test_redundant_exemption_clean(self):
        model = KernelModel(
            nodes=(
                Node(id="web", trust="untrusted"),
                Node(id="inventory", trust="trusted", attrs=("redundant",)),
            ),
            flows=(Flow(id="f1", src="web", dst="inventory", attrs=("critical",)),),
        )
        report = check_spof(model)
        assert not [v for v in report.violations if v.rule == REL_SPOF]

    # frob:tests tests/unit/strata/test_spof.py::TestSpof.test_non_critical_flow_clean
    def test_non_critical_flow_clean(self):
        model = KernelModel(
            nodes=(
                Node(id="web", trust="untrusted"),
                Node(id="inventory", trust="trusted"),
            ),
            flows=(Flow(id="f1", src="web", dst="inventory"),),
        )
        report = check_spof(model)
        assert not [v for v in report.violations if v.rule == REL_SPOF]

    # frob:tests tests/unit/strata/test_spof.py::TestSpof.test_waiver_on_one_node_keeps_sibling_node_finding
    def test_waiver_on_one_node_keeps_sibling_node_finding(self):
        model = KernelModel(
            nodes=(
                Node(id="web", trust="untrusted"),
                Node(
                    id="legacy_inventory",
                    trust="trusted",
                    waives=(
                        Waiver(
                            rule="REL250",
                            reason="legacy singleton, tracked in T-0645-followup",
                        ),
                    ),
                ),
                Node(id="other_inventory", trust="trusted"),
            ),
            flows=(
                Flow(
                    id="f1",
                    src="web",
                    dst="legacy_inventory",
                    attrs=("critical",),
                ),
                Flow(
                    id="f2",
                    src="web",
                    dst="other_inventory",
                    attrs=("critical",),
                ),
            ),
        )
        report = check_spof(model)
        kept = {v.node for v in report.violations if v.rule == REL_SPOF}
        waived = {v.node for v in report.waived if v.rule == REL_SPOF}
        assert kept == {"other_inventory"}
        assert waived == {"legacy_inventory"}
