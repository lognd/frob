"""Unit tests for REL303 (`_inbound_rate.py`): an unauthenticated flow into
a PII-carrying store with a declared retention bound but no declared rate
bound is a fired obligation (T-4112, H3-2, F-307).

SYNTHETIC FIXTURE, EXPLICITLY FLAGGED: frob's own tree has no HTTP-route/
auth-posture shape to dogfood this against (module docstring on
`_inbound_rate.py`), so every model here is a small hand-built
`KernelModel`, never drawn from frob's own design/frob.strata surface.
"""

from __future__ import annotations

from frob.strata import Flow, KernelModel, Node, Quantity, Waiver
from frob.strata._inbound_rate import (
    REL_MISSING_INBOUND_RATE,
    check_inbound_rate,
)


def _node(node_id: str, trust: str, attrs: tuple[str, ...] = ()) -> Node:
    return Node(id=node_id, trust=trust, attrs=attrs)


class TestMissingInboundRate:
    # frob:tests src/frob/strata/_inbound_rate.py::check_inbound_rate kind="unit"
    # frob:tests src/frob/strata/_inbound_rate.py::InboundRateViolation  # noqa: E501
    # frob:tests src/frob/strata/_inbound_rate.py::InboundRateReport  # noqa: E501
    def test_unauthenticated_write_with_retention_but_no_rate_fires(self):
        route = _node("public_route", "foreign")
        store = _node(
            "user_store",
            "trusted",
            attrs=("pii=identifier.email", "retention=30d"),
        )
        flow = Flow(id="f_collect", src="public_route", dst="user_store")
        model = KernelModel(nodes=(route, store), flows=(flow,))

        report = check_inbound_rate(model)

        assert report.is_ok
        violations = report.danger_ok.violations
        assert len(violations) == 1
        assert violations[0].rule == REL_MISSING_INBOUND_RATE
        assert violations[0].sub_target == "f_collect"

    # frob:tests src/frob/strata/_inbound_rate.py::check_inbound_rate kind="unit"
    def test_declared_rate_stays_quiet(self):
        route = _node("public_route", "foreign")
        store = _node(
            "user_store",
            "trusted",
            attrs=("pii=identifier.email", "retention=30d"),
        )
        flow = Flow(
            id="f_collect",
            src="public_route",
            dst="user_store",
            rate=Quantity(value=10.0, unit="req/s"),
        )
        model = KernelModel(nodes=(route, store), flows=(flow,))

        report = check_inbound_rate(model)

        assert report.is_ok
        assert report.danger_ok.violations == ()

    # frob:tests src/frob/strata/_inbound_rate.py::check_inbound_rate kind="unit"
    def test_authenticated_route_stays_quiet(self):
        route = _node("internal_route", "authenticated")
        store = _node(
            "user_store",
            "trusted",
            attrs=("pii=identifier.email", "retention=30d"),
        )
        flow = Flow(id="f_collect", src="internal_route", dst="user_store")
        model = KernelModel(nodes=(route, store), flows=(flow,))

        report = check_inbound_rate(model)

        assert report.is_ok
        assert report.danger_ok.violations == ()

    # frob:tests src/frob/strata/_inbound_rate.py::check_inbound_rate kind="unit"
    def test_non_carries_store_stays_quiet(self):
        route = _node("public_route", "foreign")
        store = _node("cache", "trusted", attrs=("retention=30d",))
        flow = Flow(id="f_collect", src="public_route", dst="cache")
        model = KernelModel(nodes=(route, store), flows=(flow,))

        report = check_inbound_rate(model)

        assert report.is_ok
        assert report.danger_ok.violations == ()

    # frob:tests src/frob/strata/_inbound_rate.py::check_inbound_rate kind="unit"
    def test_outbound_flow_from_store_never_fires(self):
        """REL303 must not re-fire on an outbound flow (module docstring:
        must not duplicate REL201 or fire in the opposite direction)."""
        store = _node(
            "user_store",
            "trusted",
            attrs=("pii=identifier.email", "retention=30d"),
        )
        sink = _node("archive", "trusted")
        flow = Flow(id="f_export", src="user_store", dst="archive")
        model = KernelModel(nodes=(store, sink), flows=(flow,))

        report = check_inbound_rate(model)

        assert report.is_ok
        assert report.danger_ok.violations == ()

    # frob:tests src/frob/strata/_inbound_rate.py::check_inbound_rate kind="unit"
    def test_waived_finding_is_suppressed(self):
        route = Node(
            id="public_route",
            trust="foreign",
            waives=(
                Waiver(rule="REL303:f_collect", reason="T-9999: tracked follow-up"),
            ),
        )
        store = _node(
            "user_store",
            "trusted",
            attrs=("pii=identifier.email", "retention=30d"),
        )
        flow = Flow(id="f_collect", src="public_route", dst="user_store")
        model = KernelModel(nodes=(route, store), flows=(flow,))

        report = check_inbound_rate(model)

        assert report.is_ok
        assert report.danger_ok.violations == ()
        assert len(report.danger_ok.waived) == 1
