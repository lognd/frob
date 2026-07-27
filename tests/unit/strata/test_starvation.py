"""T-0703 STARVATION/THROUGHPUT obligation unit coverage
(`frob.strata._starvation`) -- mirrors `test_access.py`/`test_spof.py`'s
"construct a `KernelModel`/`Module` directly, test the check function"
convention: the underlying access-mode/demand grammar is covered by
`test_access.py`/`test_demand.py`'s own unit tests, this file covers the
REL380/REL381/REL382/REL383 obligation logic built on top of them.
"""

from __future__ import annotations

from frob.strata import Capacity, Flow, KernelModel, Node, Quantity
from frob.strata._ast import Module, ResourceDecl
from frob.strata._facts import build_facts
from frob.strata._starvation import (
    REL_SERIALIZATION_DEMAND_UNDECLARED,
    REL_SERIALIZATION_UTILIZATION,
    REL_UNBOUNDED_WAIT,
    REL_WRITER_STARVATION,
    check_starvation_obligations,
)


def _facts_for(model: KernelModel):
    return build_facts(model).danger_ok


class TestUtilization:
    # frob:tests tests/unit/strata/test_starvation.py::TestUtilization.test_over_capacity_demand_fires_with_arithmetic
    def test_over_capacity_demand_fires_with_arithmetic(self):
        """T-0703 acceptance criterion: 500k declared users flowing to a
        db with mode=exclusive and no declared capacity (default holding
        time) fires REL380, and the detail shows the arithmetic."""
        model = KernelModel(
            nodes=(
                Node(id="entry", trust="trusted", users=500000.0),
                Node(
                    id="db",
                    trust="trusted",
                    attrs=("access=ledger:exclusive",),
                ),
            ),
            flows=(Flow(id="f1", src="entry", dst="db"),),
        )
        module = Module(name="m")
        facts = _facts_for(model)
        report = check_starvation_obligations(model, module, facts)
        assert [v.rule for v in report.violations] == [REL_SERIALIZATION_UTILIZATION]
        violation = report.violations[0]
        assert violation.node == "db"
        assert violation.resource == "ledger"
        assert "500000" in violation.detail
        assert "utilization=" in violation.detail

    # frob:tests tests/unit/strata/test_starvation.py::TestUtilization.test_declared_capacity_within_bounds_is_clean
    def test_declared_capacity_within_bounds_is_clean(self):
        """A declared capacity comfortably above demand does not fire."""
        model = KernelModel(
            nodes=(
                Node(id="entry", trust="trusted", users=10.0),
                Node(
                    id="db",
                    trust="trusted",
                    attrs=("access=ledger:exclusive",),
                    capacity=Capacity(
                        service_rate=Quantity(value=1000.0, unit="per_second")
                    ),
                ),
            ),
            flows=(Flow(id="f1", src="entry", dst="db"),),
        )
        module = Module(name="m")
        facts = _facts_for(model)
        report = check_starvation_obligations(model, module, facts)
        assert report.violations == ()

    # frob:tests tests/unit/strata/test_starvation.py::TestUtilization.test_undeclared_demand_fails_closed
    def test_undeclared_demand_fails_closed(self):
        """T-0703 acceptance criterion: the same exclusive-mode db with
        NO upstream `users`/`rate` declaration fires REL381
        (demand-undeclared), not a silent skip."""
        model = KernelModel(
            nodes=(
                Node(id="entry", trust="trusted"),
                Node(
                    id="db",
                    trust="trusted",
                    attrs=("access=ledger:exclusive",),
                ),
            ),
            flows=(Flow(id="f1", src="entry", dst="db"),),
        )
        module = Module(name="m")
        facts = _facts_for(model)
        report = check_starvation_obligations(model, module, facts)
        assert [v.rule for v in report.violations] == [
            REL_SERIALIZATION_DEMAND_UNDECLARED
        ]
        assert report.violations[0].node == "db"

    # frob:tests tests/unit/strata/test_starvation.py::TestUtilization.test_arbitrated_by_node_is_the_serialization_point
    def test_arbitrated_by_node_is_the_serialization_point(self):
        """A resource's declared `arbitrated_by` node is itself the
        serialization point, even though it declares no `access` clause
        of its own."""
        model = KernelModel(
            nodes=(
                Node(id="entry", trust="trusted", users=500000.0),
                Node(id="reader", trust="trusted", attrs=("access=cache:read",)),
                Node(id="arbiter", trust="trusted"),
            ),
            flows=(Flow(id="f1", src="entry", dst="arbiter"),),
        )
        module = Module(
            name="m",
            resources=(ResourceDecl(id="cache", arbitrated_by="arbiter"),),
        )
        facts = _facts_for(model)
        report = check_starvation_obligations(model, module, facts)
        assert any(
            v.rule == REL_SERIALIZATION_UTILIZATION and v.node == "arbiter"
            for v in report.violations
        )

    # frob:tests tests/unit/strata/test_starvation.py::TestUtilization.test_read_only_accessor_is_not_a_serialization_point
    def test_read_only_accessor_is_not_a_serialization_point(self):
        """A plain `read`-mode accessor with no arbiter/write-like
        peer is not a serialization point at all -- no REL380/REL381."""
        model = KernelModel(
            nodes=(
                Node(id="entry", trust="trusted", users=500000.0),
                Node(id="cache", trust="trusted", attrs=("access=cache:read",)),
            ),
            flows=(Flow(id="f1", src="entry", dst="cache"),),
        )
        module = Module(name="m")
        facts = _facts_for(model)
        report = check_starvation_obligations(model, module, facts)
        assert report.violations == ()


class TestWriterStarvation:
    # frob:tests tests/unit/strata/test_starvation.py::TestWriterStarvation.test_read_heavy_writer_with_no_alpha_fires_advisory
    def test_read_heavy_writer_with_no_alpha_fires_advisory(self):
        """T-0703 acceptance criterion: a read-preferring lock with no
        alpha/fairness on a read-heavy resource fires REL382, even with
        no declared capacity/demand at all (low utilization)."""
        model = KernelModel(
            nodes=(
                Node(id="reader_a", trust="trusted", attrs=("access=cache:read",)),
                Node(id="reader_b", trust="trusted", attrs=("access=cache:read",)),
                Node(id="writer", trust="trusted", attrs=("access=cache:write",)),
            ),
        )
        module = Module(name="m")
        facts = _facts_for(model)
        report = check_starvation_obligations(model, module, facts)
        assert any(
            v.rule == REL_WRITER_STARVATION and v.node == "writer"
            for v in report.violations
        )

    # frob:tests tests/unit/strata/test_starvation.py::TestWriterStarvation.test_alpha_accessor_discharges
    def test_alpha_accessor_discharges(self):
        """The same read-heavy resource with an `alpha` accessor
        declared does NOT fire REL382 -- the fairness/upgrade discipline
        the obligation asks for is present."""
        model = KernelModel(
            nodes=(
                Node(id="reader_a", trust="trusted", attrs=("access=cache:read",)),
                Node(id="writer", trust="trusted", attrs=("access=cache:alpha",)),
            ),
        )
        module = Module(name="m")
        facts = _facts_for(model)
        report = check_starvation_obligations(model, module, facts)
        assert not any(v.rule == REL_WRITER_STARVATION for v in report.violations)


class TestUnboundedWait:
    # frob:tests tests/unit/strata/test_starvation.py::TestUnboundedWait.test_contended_write_access_with_no_timeout_fires
    def test_contended_write_access_with_no_timeout_fires(self):
        """A write-mode accessor of a resource with a second accessor
        (contended) and no `timeout` attr fires REL383."""
        model = KernelModel(
            nodes=(
                Node(id="writer", trust="trusted", attrs=("access=cache:write",)),
                Node(id="reader", trust="trusted", attrs=("access=cache:read",)),
            ),
        )
        module = Module(name="m")
        facts = _facts_for(model)
        report = check_starvation_obligations(model, module, facts)
        assert any(
            v.rule == REL_UNBOUNDED_WAIT and v.node == "writer"
            for v in report.violations
        )

    # frob:tests tests/unit/strata/test_starvation.py::TestUnboundedWait.test_declared_timeout_discharges
    def test_declared_timeout_discharges(self):
        """The same contended write accessor declaring `timeout` on
        itself does not fire REL383."""
        model = KernelModel(
            nodes=(
                Node(
                    id="writer",
                    trust="trusted",
                    attrs=("access=cache:write", "timeout"),
                ),
                Node(id="reader", trust="trusted", attrs=("access=cache:read",)),
            ),
        )
        module = Module(name="m")
        facts = _facts_for(model)
        report = check_starvation_obligations(model, module, facts)
        assert not any(v.rule == REL_UNBOUNDED_WAIT for v in report.violations)

    # frob:tests tests/unit/strata/test_starvation.py::TestUnboundedWait.test_lone_accessor_is_not_contended
    def test_lone_accessor_is_not_contended(self):
        """A single accessor of a resource has no peer, so it is not
        contended -- REL383 does not fire."""
        model = KernelModel(
            nodes=(Node(id="writer", trust="trusted", attrs=("access=cache:write",)),),
        )
        module = Module(name="m")
        facts = _facts_for(model)
        report = check_starvation_obligations(model, module, facts)
        assert not any(v.rule == REL_UNBOUNDED_WAIT for v in report.violations)
