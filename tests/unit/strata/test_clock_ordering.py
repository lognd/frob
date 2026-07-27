"""REL37x CLOCK/ORDERING-ASSUMPTIONS-obligation family unit coverage
(T-0657, `frob.strata._clock_ordering`) -- mirrors `test_retry.py`'s
`tmp_path` real-file convention for proof-against-code (bind_code-backed,
so it needs a real file tree, not just an in-memory `KernelModel`)."""

from __future__ import annotations

from pathlib import Path

from frob.strata import Flow, KernelModel, Node, Waiver
from frob.strata._clock_ordering import (
    REL_MISSING_ORDERING_STRATEGY,
    REL_UNPROVEN_ORDERING_STRATEGY,
    REL_WALL_CLOCK_ONLY,
    check_clock_ordering_obligations,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMissingOrderingStrategy:
    # frob:tests \
    # tests/unit/strata/test_clock_ordering.py::TestMissingOrderingStrategy.test_clock_\
    # dependent_flow_without_ordering_strategy_fires
    def test_clock_dependent_flow_without_ordering_strategy_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="replica_a", trust="trusted"),
                Node(id="replica_b", trust="trusted"),
            ),
            flows=(
                Flow(
                    id="f1",
                    src="replica_a",
                    dst="replica_b",
                    attrs=("clock_dependent",),
                ),
            ),
        )
        result = check_clock_ordering_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_ORDERING_STRATEGY
        ]
        assert {v.sub_target for v in missing} == {"f1"}

    # frob:tests \
    # tests/unit/strata/test_clock_ordering.py::TestMissingOrderingStrategy.test_discha\
    # rged_and_non_clock_dependent_flows_clean
    def test_discharged_and_non_clock_dependent_flows_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(id="replica_a", trust="trusted"),
                Node(id="replica_b", trust="trusted"),
                Node(id="replica_c", trust="trusted"),
            ),
            flows=(
                Flow(
                    id="f1",
                    src="replica_a",
                    dst="replica_b",
                    attrs=("clock_dependent", "ordering_strategy"),
                ),
                Flow(id="f2", src="replica_b", dst="replica_c"),
            ),
        )
        result = check_clock_ordering_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_ORDERING_STRATEGY
        ]

    # frob:tests \
    # tests/unit/strata/test_clock_ordering.py::TestMissingOrderingStrategy.test_waiver\
    # _discharges_finding
    def test_waiver_discharges_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="replica_a",
                    trust="trusted",
                    waives=(
                        Waiver(
                            rule="REL370:f1",
                            reason="legacy flow, ordering tracked in T-9910",
                        ),
                    ),
                ),
                Node(id="replica_b", trust="trusted"),
            ),
            flows=(
                Flow(
                    id="f1",
                    src="replica_a",
                    dst="replica_b",
                    attrs=("clock_dependent",),
                ),
            ),
        )
        result = check_clock_ordering_obligations(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not [
            v for v in report.violations if v.rule == REL_MISSING_ORDERING_STRATEGY
        ]
        assert {
            v.sub_target
            for v in report.waived
            if v.rule == REL_MISSING_ORDERING_STRATEGY
        } == {"f1"}


class TestUnprovenOrderingStrategy:
    # frob:tests \
    # tests/unit/strata/test_clock_ordering.py::TestUnprovenOrderingStrategy.test_decla\
    # red_with_no_code_evidence_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(tmp_path, "src/widget/_io.py", "def sync():\n    return push()\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="replica_a",
                    trust="trusted",
                    attrs=("code=src/widget/**",),
                ),
                Node(id="replica_b", trust="trusted"),
            ),
            flows=(
                Flow(
                    id="f1",
                    src="replica_a",
                    dst="replica_b",
                    attrs=("clock_dependent", "ordering_strategy"),
                ),
            ),
        )
        result = check_clock_ordering_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_ORDERING_STRATEGY
        ]
        assert {v.sub_target for v in violations} == {"f1"}

    # frob:tests \
    # tests/unit/strata/test_clock_ordering.py::TestUnprovenOrderingStrategy.test_decla\
    # red_with_real_code_evidence_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_io.py",
            "def sync(event):\n"
            "    stamp = vector_clock.tick()\n"
            "    return push(event, stamp)\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="replica_a",
                    trust="trusted",
                    attrs=("code=src/widget/**",),
                ),
                Node(id="replica_b", trust="trusted"),
            ),
            flows=(
                Flow(
                    id="f1",
                    src="replica_a",
                    dst="replica_b",
                    attrs=("clock_dependent", "ordering_strategy"),
                ),
            ),
        )
        result = check_clock_ordering_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule in {REL_UNPROVEN_ORDERING_STRATEGY, REL_WALL_CLOCK_ONLY}
        ]

    # frob:tests \
    # tests/unit/strata/test_clock_ordering.py::TestUnprovenOrderingStrategy.test_decla\
    # red_with_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(id="replica_a", trust="trusted"),
                Node(id="replica_b", trust="trusted"),
            ),
            flows=(
                Flow(
                    id="f1",
                    src="replica_a",
                    dst="replica_b",
                    attrs=("clock_dependent", "ordering_strategy"),
                ),
            ),
        )
        result = check_clock_ordering_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule in {REL_UNPROVEN_ORDERING_STRATEGY, REL_WALL_CLOCK_ONLY}
        ]


class TestWallClockOnly:
    # frob:tests \
    # tests/unit/strata/test_clock_ordering.py::TestWallClockOnly.test_bare_wall_clock_\
    # read_fires_rel372
    def test_bare_wall_clock_read_fires_rel372(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_io.py",
            "import time\n\ndef sync(event):\n    ts = time.time()\n    return push(event, ts)\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="replica_a",
                    trust="trusted",
                    attrs=("code=src/widget/**",),
                ),
                Node(id="replica_b", trust="trusted"),
            ),
            flows=(
                Flow(
                    id="f1",
                    src="replica_a",
                    dst="replica_b",
                    attrs=("clock_dependent", "ordering_strategy"),
                ),
            ),
        )
        result = check_clock_ordering_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v for v in result.danger_ok.violations if v.rule == REL_WALL_CLOCK_ONLY
        ]
        assert {v.sub_target for v in violations} == {"f1"}
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_ORDERING_STRATEGY
        ]
