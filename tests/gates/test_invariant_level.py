"""Tests for INVLVL001 (T-3008): the multi-level invariant gate
(`frob.gates._invariant_level.invariant_level_gate`).

Positive controls per T-3008's tree entry: an invariant declared
`system-design`, verified only by a test tagged `component-unit`, must be
flagged INVLVL001; an invariant verified at its paired level
(`subsystem-integration`) must pass.
"""

from __future__ import annotations

from typing import Any

from frob.gates._invariant_level import invariant_level_gate
from frob.gates.invariants import Invariant, _Criticality


def _inv(**kwargs: Any) -> Invariant:
    """Minimal valid `Invariant` fixture, overridable per test."""
    defaults: dict[str, Any] = dict(
        id="INV-TEST-001",
        statement="a test statement",
        criticality=_Criticality.HIGH,
        evidence=(),
        path="invariants/INV-TEST-001.md",
        level=None,
        evidence_levels={},
    )
    defaults.update(kwargs)
    return Invariant(**defaults)


class TestInvariantLevelGate:
    # frob:tests src/frob/gates/_invariant_level.py::invariant_level_gate
    def test_quiet_when_no_level_declared(self) -> None:
        """An invariant with no `level` at all is never checked."""
        inv = _inv(
            evidence=("t.py::test_x",),
            evidence_levels={"t.py::test_x": "component-unit-test"},
        )
        assert invariant_level_gate((inv,)) == ()

    # frob:tests src/frob/gates/_invariant_level.py::invariant_level_gate
    def test_fires_on_a_level_mismatch(self) -> None:
        """T-3008's exact positive control: system-design invariant,
        evidence tagged component-unit (paired to component-design, not
        system-design) -- must fire."""
        inv = _inv(
            level="system-design",
            evidence=("t.py::test_x",),
            evidence_levels={"t.py::test_x": "component-unit-test"},
        )
        violations = invariant_level_gate((inv,))
        assert len(violations) == 1
        assert violations[0].rule == "INVLVL001"
        assert violations[0].severity.value == "warn"
        assert "INV-TEST-001" in violations[0].message

    # frob:tests src/frob/gates/_invariant_level.py::invariant_level_gate
    def test_quiet_when_verified_at_the_paired_level(self) -> None:
        """T-3008's must-stay-quiet twin: system-design paired with
        subsystem-integration-test-plan -- evidence tagged exactly that
        must not fire."""
        inv = _inv(
            level="system-design",
            evidence=("t.py::test_x",),
            evidence_levels={"t.py::test_x": "subsystem-integration-test-plan"},
        )
        assert invariant_level_gate((inv,)) == ()

    # frob:tests src/frob/gates/_invariant_level.py::invariant_level_gate
    def test_quiet_for_untagged_evidence(self) -> None:
        """An evidence entry present in `evidence` but absent from
        `evidence_levels` carries no level claim -- never flagged."""
        inv = _inv(
            level="system-design", evidence=("t.py::test_x",), evidence_levels={}
        )
        assert invariant_level_gate((inv,)) == ()

    # frob:tests src/frob/gates/_invariant_level.py::invariant_level_gate
    def test_multiple_invariants_only_mismatched_one_fires(self) -> None:
        """Two invariants, one correctly paired and one mismatched --
        exactly one finding, naming the mismatched one."""
        good = _inv(
            id="INV-GOOD-001",
            level="component-design",
            evidence=("t.py::test_good",),
            evidence_levels={"t.py::test_good": "component-unit-test"},
        )
        bad = _inv(
            id="INV-BAD-001",
            level="component-design",
            evidence=("t.py::test_bad",),
            evidence_levels={"t.py::test_bad": "customer-test"},
        )
        violations = invariant_level_gate((good, bad))
        assert len(violations) == 1
        assert "INV-BAD-001" in violations[0].message
