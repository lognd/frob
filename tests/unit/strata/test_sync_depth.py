"""REL34x SYNC-CALL-CHAIN-DEPTH-bound unit coverage (T-0654,
`frob.strata._sync_depth`) -- `check_sync_chain_depth` is a pure
structural read of `KernelModel`, no `bind_code`/`tmp_path` needed
(module docstring: no proof-against-code companion, mirrors
`test_spof.py`'s convention)."""

from __future__ import annotations

from frob.strata import Flow, KernelModel, Node, Waiver
from frob.strata._sync_depth import (
    REL_SYNC_CHAIN_TOO_DEEP,
    SYNC_CHAIN_MAX_DEPTH,
    check_sync_chain_depth,
)


def _chain(length: int) -> tuple[tuple[Node, ...], tuple[Flow, ...]]:
    """A straight-line synchronous chain `n0 -> n1 -> ... -> n<length>`."""
    nodes = tuple(Node(id=f"n{i}", trust="trusted") for i in range(length + 1))
    flows = tuple(Flow(id=f"f{i}", src=f"n{i}", dst=f"n{i + 1}") for i in range(length))
    return nodes, flows


class TestSyncDepth:
    # frob:tests \
    # tests/unit/strata/test_sync_depth.py::TestSyncDepth.test_chain_below_bound_clean
    def test_chain_below_bound_clean(self):
        nodes, flows = _chain(SYNC_CHAIN_MAX_DEPTH - 1)
        model = KernelModel(nodes=nodes, flows=flows)
        report = check_sync_chain_depth(model)
        assert not [v for v in report.violations if v.rule == REL_SYNC_CHAIN_TOO_DEEP]

    # frob:tests \
    # tests/unit/strata/test_sync_depth.py::TestSyncDepth.test_chain_at_bound_fires
    def test_chain_at_bound_fires(self):
        nodes, flows = _chain(SYNC_CHAIN_MAX_DEPTH)
        model = KernelModel(nodes=nodes, flows=flows)
        report = check_sync_chain_depth(model)
        violations = [v for v in report.violations if v.rule == REL_SYNC_CHAIN_TOO_DEEP]
        assert {v.node for v in violations} == {f"n{SYNC_CHAIN_MAX_DEPTH}"}

    # frob:tests \
    # tests/unit/strata/test_sync_depth.py::TestSyncDepth.test_async_hop_breaks_the_cha\
    # in
    def test_async_hop_breaks_the_chain(self):
        nodes, flows = _chain(SYNC_CHAIN_MAX_DEPTH)
        # Mark the final hop async: the chain no longer reaches the bound
        # synchronously past that point.
        broken_flow = Flow(
            id=flows[-1].id,
            src=flows[-1].src,
            dst=flows[-1].dst,
            attrs=("async",),
        )
        flows = flows[:-1] + (broken_flow,)
        model = KernelModel(nodes=nodes, flows=flows)
        report = check_sync_chain_depth(model)
        assert not [v for v in report.violations if v.rule == REL_SYNC_CHAIN_TOO_DEEP]

    # frob:tests \
    # tests/unit/strata/test_sync_depth.py::TestSyncDepth.test_deep_chain_ok_exemption_\
    # discharges
    def test_deep_chain_ok_exemption_discharges(self):
        nodes, flows = _chain(SYNC_CHAIN_MAX_DEPTH)
        exempt = tuple(
            Node(id=n.id, trust=n.trust, attrs=("deep_chain_ok",))
            if n.id == f"n{SYNC_CHAIN_MAX_DEPTH}"
            else n
            for n in nodes
        )
        model = KernelModel(nodes=exempt, flows=flows)
        report = check_sync_chain_depth(model)
        assert not [v for v in report.violations if v.rule == REL_SYNC_CHAIN_TOO_DEEP]

    # frob:tests \
    # tests/unit/strata/test_sync_depth.py::TestSyncDepth.test_sync_cycle_is_unbounded_\
    # and_fires
    def test_sync_cycle_is_unbounded_and_fires(self):
        model = KernelModel(
            nodes=(
                Node(id="a", trust="trusted"),
                Node(id="b", trust="trusted"),
            ),
            flows=(
                Flow(id="f1", src="a", dst="b"),
                Flow(id="f2", src="b", dst="a"),
            ),
        )
        report = check_sync_chain_depth(model)
        violations = [v for v in report.violations if v.rule == REL_SYNC_CHAIN_TOO_DEEP]
        assert {v.node for v in violations} == {"a", "b"}
        assert all("unbounded" in v.detail for v in violations)

    # frob:tests \
    # tests/unit/strata/test_sync_depth.py::TestSyncDepth.test_waiver_discharges_finding
    def test_waiver_discharges_finding(self):
        nodes, flows = _chain(SYNC_CHAIN_MAX_DEPTH)
        target = f"n{SYNC_CHAIN_MAX_DEPTH}"
        waived_nodes = tuple(
            Node(
                id=n.id,
                trust=n.trust,
                waives=(
                    Waiver(
                        rule="REL340",
                        reason="reviewed, independent slow paths",
                    ),
                ),
            )
            if n.id == target
            else n
            for n in nodes
        )
        model = KernelModel(nodes=waived_nodes, flows=flows)
        report = check_sync_chain_depth(model)
        assert not [v for v in report.violations if v.rule == REL_SYNC_CHAIN_TOO_DEEP]
        assert {v.node for v in report.waived if v.rule == REL_SYNC_CHAIN_TOO_DEEP} == {
            target
        }
