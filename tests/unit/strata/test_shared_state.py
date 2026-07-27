"""REL36x NO-SHARED-MUTABLE-STATE-ACROSS-SERVICE-BOUNDARIES unit coverage
(T-0656, `frob.strata._shared_state`) -- `check_shared_state` is a pure
structural read of `KernelModel`, no `bind_code`/`tmp_path` needed
(module docstring: no proof-against-code companion, mirrors
`test_spof.py`'s convention)."""

from __future__ import annotations

from frob.strata import Flow, KernelModel, Node, Waiver
from frob.strata._shared_state import REL_SHARED_MUTABLE_STATE, check_shared_state


class TestSharedState:
    # frob:tests \
    # tests/unit/strata/test_shared_state.py::TestSharedState.test_mutable_node_shared_\
    # by_two_services_fires
    def test_mutable_node_shared_by_two_services_fires(self):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="svc_b", trust="trusted"),
                Node(id="shared_db", trust="trusted"),
            ),
            flows=(
                Flow(id="f1", src="svc_a", dst="shared_db"),
                Flow(id="f2", src="svc_b", dst="shared_db"),
            ),
        )
        report = check_shared_state(model)
        violations = [
            v for v in report.violations if v.rule == REL_SHARED_MUTABLE_STATE
        ]
        assert {v.node for v in violations} == {"shared_db"}

    # frob:tests \
    # tests/unit/strata/test_shared_state.py::TestSharedState.test_read_only_accessor_s\
    # till_fires
    def test_read_only_accessor_still_fires(self):
        # svc_b only READS shared_db (a flow FROM shared_db) while svc_a
        # writes it -- still 2 distinct accessors of mutable state
        # (module docstring: broader than REL29x's writer-only count).
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="svc_b", trust="trusted"),
                Node(id="shared_db", trust="trusted"),
            ),
            flows=(
                Flow(id="f1", src="svc_a", dst="shared_db"),
                Flow(id="f2", src="shared_db", dst="svc_b"),
            ),
        )
        report = check_shared_state(model)
        violations = [
            v for v in report.violations if v.rule == REL_SHARED_MUTABLE_STATE
        ]
        assert {v.node for v in violations} == {"shared_db"}

    # frob:tests \
    # tests/unit/strata/test_shared_state.py::TestSharedState.test_single_writer_clean
    def test_single_writer_clean(self):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="own_db", trust="trusted"),
            ),
            flows=(Flow(id="f1", src="svc_a", dst="own_db"),),
        )
        report = check_shared_state(model)
        assert not [v for v in report.violations if v.rule == REL_SHARED_MUTABLE_STATE]

    # frob:tests \
    # tests/unit/strata/test_shared_state.py::TestSharedState.test_immutable_node_touch\
    # ed_by_many_is_clean
    def test_immutable_node_touched_by_many_is_clean(self):
        # broadcast_topic is never written INTO (no flow lands on it) --
        # not "mutable" by this module's definition, so 2 distinct
        # downstream consumers reading FROM it is not REL360's concern.
        model = KernelModel(
            nodes=(
                Node(id="broadcast_topic", trust="trusted"),
                Node(id="consumer_a", trust="trusted"),
                Node(id="consumer_b", trust="trusted"),
            ),
            flows=(
                Flow(id="f1", src="broadcast_topic", dst="consumer_a"),
                Flow(id="f2", src="broadcast_topic", dst="consumer_b"),
            ),
        )
        report = check_shared_state(model)
        assert not [v for v in report.violations if v.rule == REL_SHARED_MUTABLE_STATE]

    # frob:tests \
    # tests/unit/strata/test_shared_state.py::TestSharedState.test_shared_state_ok_exem\
    # ption_discharges
    def test_shared_state_ok_exemption_discharges(self):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="svc_b", trust="trusted"),
                Node(id="shared_db", trust="trusted", attrs=("shared_state_ok",)),
            ),
            flows=(
                Flow(id="f1", src="svc_a", dst="shared_db"),
                Flow(id="f2", src="svc_b", dst="shared_db"),
            ),
        )
        report = check_shared_state(model)
        assert not [v for v in report.violations if v.rule == REL_SHARED_MUTABLE_STATE]

    # frob:tests \
    # tests/unit/strata/test_shared_state.py::TestSharedState.test_owner_attr_alone_doe\
    # s_not_discharge
    def test_owner_attr_alone_does_not_discharge(self):
        # REL29x's `owner` attr does NOT discharge REL360 (module
        # docstring: reconciling conflicts is a different question from
        # whether direct sharing should happen at all).
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="svc_b", trust="trusted"),
                Node(id="shared_db", trust="trusted", attrs=("owner=svc_a",)),
            ),
            flows=(
                Flow(id="f1", src="svc_a", dst="shared_db"),
                Flow(id="f2", src="svc_b", dst="shared_db"),
            ),
        )
        report = check_shared_state(model)
        violations = [
            v for v in report.violations if v.rule == REL_SHARED_MUTABLE_STATE
        ]
        assert {v.node for v in violations} == {"shared_db"}

    # frob:tests \
    # tests/unit/strata/test_shared_state.py::TestSharedState.test_waiver_discharges_fi\
    # nding
    def test_waiver_discharges_finding(self):
        model = KernelModel(
            nodes=(
                Node(id="svc_a", trust="trusted"),
                Node(id="svc_b", trust="trusted"),
                Node(
                    id="shared_db",
                    trust="trusted",
                    waives=(
                        Waiver(
                            rule="REL360",
                            reason="legacy shared db, migration tracked in T-9910",
                        ),
                    ),
                ),
            ),
            flows=(
                Flow(id="f1", src="svc_a", dst="shared_db"),
                Flow(id="f2", src="svc_b", dst="shared_db"),
            ),
        )
        report = check_shared_state(model)
        assert not [v for v in report.violations if v.rule == REL_SHARED_MUTABLE_STATE]
        assert {
            v.node for v in report.waived if v.rule == REL_SHARED_MUTABLE_STATE
        } == {"shared_db"}
