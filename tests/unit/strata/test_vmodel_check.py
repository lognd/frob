"""Python-level evidence that `strata_core.vmodel_check` actually behaves per
T-3043's corrected closure semantics (docs/strata/vmodel.md).

T-3005/T-3007 bound their evidence to parser pytest node ids that never
touch graph code (an audit-found evidence-laundering hole, M6 in the
Fable design audit). This file exists so T-3043's fix has evidence that
genuinely exercises `vmodel_check` end to end through the same PyO3
boundary a real caller uses, not just `cargo test` (already run directly,
see the ticket's Done report) and not a parser test.
"""

# frob:ticket T-3043
from __future__ import annotations

import pytest

strata_core = pytest.importorskip(
    "strata_core",
    reason="strata_core native extension not built -- run `make core`",
)

# frob:tests strata-core/src/graph/vmodel.rs::check_no_orphan_requirements kind="unit"
# frob:tests strata-core/src/graph/vmodel.rs::check_no_unjustified_design kind="unit"
# frob:tests strata-core/src/graph/vmodel.rs::check_no_trace_cycle kind="unit"
# frob:tests strata-core/src/lib.rs::vmodel_check kind="unit"


def _violation_names(violations: list[tuple[str, str]]) -> set[str]:
    """Reduce vmodel_check's (rule_name, node_id) pairs to just the rule names."""
    return {name for name, _node in violations}


class TestVmodelCheckClosureSemantics:
    """T-3043 H2: closure must mean path-reachability, not local edge degree."""

    def test_mutual_satisfies_pair_with_zero_requirements_now_fires(self) -> None:
        """The exact audit escape: two design nodes satisfying each other,
        each verified by a test, with NO requirement node anywhere -- must
        now fire orphan_requirement and unjustified_design, where the old
        "any edge exists" check let it pass all four rules silently."""
        nodes = [
            ("design-a", "artifact", "system-design"),
            ("design-b", "artifact", "system-design"),
            ("itest-a", "test", "subsystem-integration-test-plan"),
            ("itest-b", "test", "subsystem-integration-test-plan"),
        ]
        edges = [
            ("satisfies", "design-a", "design-b"),
            ("satisfies", "design-b", "design-a"),
            ("verifies", "itest-a", "design-a"),
            ("verifies", "itest-b", "design-b"),
        ]
        errors, violations = strata_core.vmodel_check(nodes, edges)
        assert errors == []
        names = _violation_names(violations)
        assert "orphan_requirement" in names
        assert "unjustified_design" in names
        # rules 3/4 (verifies-based) are correctly satisfied here -- this
        # fixture isolates the rule 1/2 path-closure hole specifically.
        assert "untested_artifact" not in names
        assert "orphan_test" not in names

    def test_genuine_four_level_chain_is_quiet(self) -> None:
        """Positive control: a real requirement->spec->design->component
        chain, verified at each paired level, must stay fully closed."""
        nodes = [
            ("req-1", "artifact", "requirements"),
            ("spec-1", "artifact", "requirement-specification"),
            ("design-1", "artifact", "system-design"),
            ("component-1", "artifact", "component-design"),
            ("ctest-1", "test", "customer-test"),
            ("ctp-1", "test", "customer-test-plan"),
            ("sitp-1", "test", "subsystem-integration-test-plan"),
            ("unittest-1", "test", "component-unit-test"),
        ]
        edges = [
            ("satisfies", "spec-1", "req-1"),
            ("satisfies", "design-1", "spec-1"),
            ("satisfies", "component-1", "design-1"),
            ("verifies", "ctest-1", "req-1"),
            ("verifies", "ctp-1", "spec-1"),
            ("verifies", "sitp-1", "design-1"),
            ("verifies", "unittest-1", "component-1"),
        ]
        errors, violations = strata_core.vmodel_check(nodes, edges)
        assert errors == []
        assert violations == []

    def test_satisfies_cycle_fires_through_vmodel_check(self) -> None:
        """T-3043 H2's second finding: find_cycle existed but nothing called
        it from check_closure. A planted satisfies cycle must now surface
        as trace_cycle all the way through the PyO3 boundary."""
        nodes = [
            ("a", "artifact", "system-design"),
            ("b", "artifact", "system-design"),
            ("c", "artifact", "system-design"),
        ]
        edges = [
            ("satisfies", "a", "b"),
            ("satisfies", "b", "c"),
            ("satisfies", "c", "a"),
        ]
        errors, violations = strata_core.vmodel_check(nodes, edges)
        assert errors == []
        names = _violation_names(violations)
        assert "trace_cycle" in names
