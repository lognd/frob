"""Unit tests for SYS114/SYS115 (`_outbound_destination.py`): an outbound
flow to a foreign node must be destination-constrained (SYS114) and every
outbound-to-foreign flow needs a declared rate once a sibling flow already
has one (SYS115) (T-4113, H3-3, F-307).

SYNTHETIC FIXTURE, EXPLICITLY FLAGGED: frob makes no outbound network calls
to a foreign host as part of its own operation (module docstring on
`_outbound_destination.py`), so every model AND stub source file here is
hand-built under `tests/unit/strata/fixtures/outbound_destination/`, never
drawn from frob's own `design/frob.strata` surface.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.strata import Flow, KernelModel, Node, Quantity
from frob.strata._outbound_destination import (
    SYS_MISSING_OUTBOUND_RATE,
    SYS_UNCONSTRAINED_DESTINATION,
    check_outbound_destination,
    check_outbound_rate,
)

_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "outbound_destination"


def _node(node_id: str, trust: str, attrs: tuple[str, ...] = ()) -> Node:
    return Node(id=node_id, trust=trust, attrs=attrs)


class TestOutboundDestinationConstraint:
    # frob:tests src/frob/strata/_outbound_destination.py::check_outbound_destination \
    # kind="unit"
    def test_hardcoded_literal_host_fires(self):
        backend = _node(
            "backend",
            "trusted",
            attrs=("code=fixtures/outbound_destination/hardcoded.py",),
        )
        media_host = _node("media_host", "foreign")
        flow = Flow(id="f_fetch", src="backend", dst="media_host")
        model = KernelModel(nodes=(backend, media_host), flows=(flow,))

        report = check_outbound_destination(model, _FIXTURE_ROOT.parent.parent)

        assert report.is_ok
        violations = report.danger_ok.violations
        assert len(violations) == 1
        assert violations[0].rule == SYS_UNCONSTRAINED_DESTINATION
        assert violations[0].sub_target == "f_fetch"

    # frob:tests src/frob/strata/_outbound_destination.py::check_outbound_destination \
    # kind="unit"
    def test_config_bound_host_stays_quiet(self):
        backend = _node(
            "backend",
            "trusted",
            attrs=("code=fixtures/outbound_destination/configured.py",),
        )
        media_host = _node("media_host", "foreign")
        flow = Flow(id="f_fetch", src="backend", dst="media_host")
        model = KernelModel(nodes=(backend, media_host), flows=(flow,))

        report = check_outbound_destination(model, _FIXTURE_ROOT.parent.parent)

        assert report.is_ok
        assert report.danger_ok.violations == ()

    # frob:tests src/frob/strata/_outbound_destination.py::check_outbound_destination \
    # kind="unit"
    def test_internal_flow_never_fires(self):
        backend = _node(
            "backend",
            "trusted",
            attrs=("code=fixtures/outbound_destination/hardcoded.py",),
        )
        internal = _node("internal", "trusted")
        flow = Flow(id="f_local", src="backend", dst="internal")
        model = KernelModel(nodes=(backend, internal), flows=(flow,))

        report = check_outbound_destination(model, _FIXTURE_ROOT.parent.parent)

        assert report.is_ok
        assert report.danger_ok.violations == ()

    # frob:tests src/frob/strata/_outbound_destination.py::check_outbound_destination \
    # kind="unit"
    def test_waived_finding_is_suppressed(self):
        backend = Node(
            id="backend",
            trust="trusted",
            attrs=("code=fixtures/outbound_destination/hardcoded.py",),
            waives=(
                pytest.importorskip("frob.strata").Waiver(
                    rule="SYS114:f_fetch", reason="T-9999: tracked follow-up"
                ),
            ),
        )
        media_host = _node("media_host", "foreign")
        flow = Flow(id="f_fetch", src="backend", dst="media_host")
        model = KernelModel(nodes=(backend, media_host), flows=(flow,))

        report = check_outbound_destination(model, _FIXTURE_ROOT.parent.parent)

        assert report.is_ok
        assert report.danger_ok.violations == ()
        assert len(report.danger_ok.waived) == 1


class TestOutboundRateLint:
    # frob:tests src/frob/strata/_outbound_destination.py::check_outbound_rate \
    # kind="unit"
    def test_missing_rate_with_sibling_rate_fires(self):
        backend = _node("backend", "trusted")
        media_host = _node("media_host", "foreign")
        image_host = _node("image_host", "foreign")
        f_no_rate = Flow(id="f_no_rate", src="backend", dst="media_host")
        f_with_rate = Flow(
            id="f_with_rate",
            src="backend",
            dst="image_host",
            rate=Quantity(value=5.0, unit="req/s"),
        )
        model = KernelModel(
            nodes=(backend, media_host, image_host), flows=(f_no_rate, f_with_rate)
        )

        report = check_outbound_rate(model)

        assert report.is_ok
        violations = report.danger_ok.violations
        assert len(violations) == 1
        assert violations[0].rule == SYS_MISSING_OUTBOUND_RATE
        assert violations[0].sub_target == "f_no_rate"

    # frob:tests src/frob/strata/_outbound_destination.py::check_outbound_rate \
    # kind="unit"
    def test_every_flow_with_rate_stays_quiet(self):
        backend = _node("backend", "trusted")
        media_host = _node("media_host", "foreign")
        image_host = _node("image_host", "foreign")
        f1 = Flow(
            id="f1",
            src="backend",
            dst="media_host",
            rate=Quantity(value=1.0, unit="req/s"),
        )
        f2 = Flow(
            id="f2",
            src="backend",
            dst="image_host",
            rate=Quantity(value=2.0, unit="req/s"),
        )
        model = KernelModel(nodes=(backend, media_host, image_host), flows=(f1, f2))

        report = check_outbound_rate(model)

        assert report.is_ok
        assert report.danger_ok.violations == ()

    # frob:tests src/frob/strata/_outbound_destination.py::check_outbound_rate \
    # kind="unit"
    def test_lone_outbound_flow_with_no_sibling_stays_quiet(self):
        """No sibling flow declares a rate at all, so there is nothing to
        contrast against (module docstring: narrower/cheaper than SYS114,
        only fires on an internal inconsistency, not a bare absence)."""
        backend = _node("backend", "trusted")
        media_host = _node("media_host", "foreign")
        flow = Flow(id="f_only", src="backend", dst="media_host")
        model = KernelModel(nodes=(backend, media_host), flows=(flow,))

        report = check_outbound_rate(model)

        assert report.is_ok
        assert report.danger_ok.violations == ()
