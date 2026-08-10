"""T-1927 population-projected capacity evaluator unit coverage
(`frob.strata._capacity`) -- mirrors `test_starvation.py`'s own
"construct a `KernelModel` directly, test the check function" convention.
Kept separate from `test_capacity.py` (pre-existing propagated-demand/
skew/growth-horizon arithmetic coverage for `docs/strata/kernel.md
#capacity-semantics`) -- that file predates this ticket and covers a
different concern (capacity ARITHMETIC primitives), not this module's
own THRESHOLD-comparison evaluator.
"""

from __future__ import annotations

from frob.strata import Capacity, Flow, KernelModel, Node, Quantity, StrataError
from frob.strata._capacity import (
    CAPACITY_PROJECTED_OVER_THRESHOLD,
    project_capacity,
)
from frob.strata._facts import build_facts


def _facts_for(model: KernelModel):
    return build_facts(model).danger_ok


def _capacity(rate: float, replicas_max: int = 1) -> Capacity:
    return Capacity(
        service_rate=Quantity(value=rate, unit="req/s"),
        replicas_max=replicas_max,
    )


class TestProjectCapacityUnscaled:
    # frob:tests src/frob/strata/_capacity.py::project_capacity kind="unit"
    def test_over_capacity_current_demand_fires(self):
        model = KernelModel(
            nodes=(
                Node(id="entry", trust="foreign", users=50.0),
                Node(id="api", trust="trusted", capacity=_capacity(10.0)),
            ),
            flows=(Flow(id="f1", src="entry", dst="api"),),
        )
        report = project_capacity(model, _facts_for(model)).danger_ok
        assert [v.node for v in report.violations] == ["api"]
        assert report.scale_factor == 1.0
        assert CAPACITY_PROJECTED_OVER_THRESHOLD in report.violations[0].detail

    # frob:tests src/frob/strata/_capacity.py::project_capacity kind="unit"
    def test_within_capacity_is_clean(self):
        model = KernelModel(
            nodes=(
                Node(id="entry", trust="foreign", users=10.0),
                Node(id="api", trust="trusted", capacity=_capacity(1000.0)),
            ),
            flows=(Flow(id="f1", src="entry", dst="api"),),
        )
        report = project_capacity(model, _facts_for(model)).danger_ok
        assert report.violations == ()

    # frob:tests src/frob/strata/_capacity.py::project_capacity kind="unit"
    def test_node_with_no_capacity_declared_is_never_checked(self):
        model = KernelModel(
            nodes=(
                Node(id="entry", trust="foreign", users=500000.0),
                Node(id="api", trust="trusted"),
            ),
            flows=(Flow(id="f1", src="entry", dst="api"),),
        )
        report = project_capacity(model, _facts_for(model)).danger_ok
        assert report.violations == ()

    # frob:tests src/frob/strata/_capacity.py::project_capacity kind="unit"
    def test_capacity_scales_with_replicas_max_unlike_rel380(self):
        # REL380 deliberately compares single-replica capacity; this
        # evaluator answers "total throughput", so replicas_max=10
        # multiplies the ceiling.
        model = KernelModel(
            nodes=(
                Node(id="entry", trust="foreign", users=50.0),
                Node(
                    id="api",
                    trust="trusted",
                    capacity=_capacity(10.0, replicas_max=10),
                ),
            ),
            flows=(Flow(id="f1", src="entry", dst="api"),),
        )
        report = project_capacity(model, _facts_for(model)).danger_ok
        assert report.violations == ()


class TestProjectCapacityScaled:
    # frob:tests src/frob/strata/_capacity.py::project_capacity kind="unit"
    def test_population_scales_demand_linearly(self):
        model = KernelModel(
            nodes=(
                Node(id="entry", trust="foreign", users=10.0),
                Node(id="api", trust="trusted", capacity=_capacity(10.0)),
            ),
            flows=(Flow(id="f1", src="entry", dst="api"),),
        )
        # Current demand (10 users) is well under 10/s capacity; scaling
        # to population=1000 (100x the declared baseline of 10) pushes
        # demand over.
        facts = _facts_for(model)
        clean = project_capacity(model, facts).danger_ok
        assert clean.violations == ()
        scaled = project_capacity(model, facts, population=1000.0).danger_ok
        assert scaled.scale_factor == 100.0
        assert [v.node for v in scaled.violations] == ["api"]

    # frob:tests src/frob/strata/_capacity.py::project_capacity kind="unit"
    def test_population_with_no_baseline_fails_closed(self):
        model = KernelModel(
            nodes=(
                Node(id="entry", trust="foreign"),
                Node(id="api", trust="trusted", capacity=_capacity(10.0)),
            ),
            flows=(Flow(id="f1", src="entry", dst="api"),),
        )
        result = project_capacity(model, _facts_for(model), population=1000.0)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_capacity.py::project_capacity kind="unit"
    def test_baseline_population_reported_on_report(self):
        model = KernelModel(
            nodes=(
                Node(id="entry", trust="foreign", users=250.0),
                Node(id="api", trust="trusted", capacity=_capacity(1000.0)),
            ),
            flows=(Flow(id="f1", src="entry", dst="api"),),
        )
        report = project_capacity(model, _facts_for(model)).danger_ok
        assert report.baseline_population == 250.0

    # frob:tests src/frob/strata/_capacity.py::project_capacity kind="unit"
    def test_no_users_anywhere_baseline_is_none(self):
        model = KernelModel(nodes=(Node(id="api", trust="trusted"),))
        report = project_capacity(model, _facts_for(model)).danger_ok
        assert report.baseline_population is None
