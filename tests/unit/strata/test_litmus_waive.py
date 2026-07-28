"""`waive` clause litmus fixture coverage (T-0174, mirroring T-0155's
`test_litmus_lint.py` discipline): a genuinely-firing LINT004 finding
suppressed by a matching `waive` clause, and a genuinely-stale `waive`
clause reported as SYSWAIVE002, both round-tripped through the real
`strata_core` parser (`parse_module -> elaborate -> evaluate_exhaustiveness`
/ `check_self_conformance`), never a hand-built `KernelModel`/`Waiver`
value for the surface-syntax half of the proof."""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, elaborate, parse_module
from frob.strata._audit import evaluate_exhaustiveness
from frob.strata._waive import STALE_WAIVER_RULE

_LITMUS_DIR = Path(__file__).resolve().parent / "litmus"


def _load_model(filename: str) -> KernelModel:
    """Parse+elaborate one `.strata` fixture under `litmus/` end to end."""
    text = (_LITMUS_DIR / filename).read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    return elaborate(module).danger_ok


class TestWaiveLitmus:
    # frob:tests src/frob/strata/_waive.py::apply_waivers kind="unit"
    def test_matched_waiver_suppresses_the_finding(self):
        """`node_waived`'s real LINT004 finding never appears in `gaps`
        (scoped to `node_waived` -- `node_multi` deliberately also holds
        an unwaived LINT004 finding of its own, per the sub-target
        discrimination fixture below)."""
        model = _load_model("waive_lint.strata")
        report = evaluate_exhaustiveness(model)
        assert report.is_ok
        lint_gaps = [
            g
            for g in report.danger_ok.gaps
            if g.family == "lint" and g.target == "node_waived"
        ]
        assert lint_gaps == []

    # frob:tests src/frob/strata/_waive.py::apply_waivers kind="unit"
    def test_matched_waiver_is_surfaced_in_waived_with_reason(self):
        """A waived finding is kept and visible -- never a silent drop
        (module docstring's "loud in output" requirement)."""
        model = _load_model("waive_lint.strata")
        report = evaluate_exhaustiveness(model)
        waived = [
            g
            for g in report.danger_ok.waived
            if g.family == "lint" and g.target == "node_waived"
        ]
        assert len(waived) == 1
        assert "WAIVED" in waived[0].detail
        assert "no kill switch yet, tracked in T-0200" in waived[0].detail
        assert "T-0200" in waived[0].detail

    # frob:tests src/frob/strata/_waive.py::apply_waivers kind="unit"
    def test_stale_waiver_reported_as_syswaive002_gap(self):
        """`node_stale`'s `waive` clause matches nothing (its LINT004 never
        fires) -- the drift-lock: STALE waivers fail, not silently pass."""
        model = _load_model("waive_lint.strata")
        report = evaluate_exhaustiveness(model)
        stale_gaps = [g for g in report.danger_ok.gaps if g.rule == STALE_WAIVER_RULE]
        assert len(stale_gaps) == 1
        assert stale_gaps[0].target == "node_stale"
        assert stale_gaps[0].family == "waiver"
        assert not report.danger_ok.proved

    # frob:tests src/frob/strata/_waive.py::apply_waivers kind="unit"
    def test_stale_fails(self):
        """A model with a stale waiver never reports PROVED -- the
        SYSWAIVE002 gap keeps `AuditReport.proved` false (module
        docstring's drift-lock requirement)."""
        model = _load_model("waive_lint.strata")
        report = evaluate_exhaustiveness(model)
        assert report.is_ok
        assert report.danger_ok.proved is False

    # frob:tests src/frob/strata/_waive.py::apply_waivers kind="unit"
    # invariant spec: [INV-036](invariants/INV-036.md)
    def test_sub_target_waiver_does_not_suppress_a_different_sub_target(self):
        """T-0174 REJECT round, the critical fixture: `node_multi` fires
        THREAT003 for BOTH CWE-78 (exec) and CWE-89 (sql). It declares
        `waive "THREAT003:CWE-78" ...` -- ONLY CWE-78 may be waived;
        CWE-89 on the SAME node, SAME rule, MUST still fire as an
        unwaived gap. A waiver naming sub-target A must never suppress a
        finding whose sub-target is B (the exact blanket-waiver bug this
        round exists to close)."""
        model = _load_model("waive_lint.strata")
        report = evaluate_exhaustiveness(model)
        assert report.is_ok

        cwe78_gaps = [
            g
            for g in report.danger_ok.gaps
            if g.rule == "THREAT003"
            and g.target == "node_multi"
            and g.sub_target == "CWE-78"
        ]
        assert cwe78_gaps == []

        cwe89_gaps = [
            g
            for g in report.danger_ok.gaps
            if g.rule == "THREAT003"
            and g.target == "node_multi"
            and g.sub_target == "CWE-89"
        ]
        assert len(cwe89_gaps) == 1

        cwe78_waived = [
            g
            for g in report.danger_ok.waived
            if g.rule == "THREAT003"
            and g.target == "node_multi"
            and g.sub_target == "CWE-78"
        ]
        assert len(cwe78_waived) == 1
        assert "THREAT003:CWE-78" in cwe78_waived[0].detail

        cwe89_waived = [
            g
            for g in report.danger_ok.waived
            if g.rule == "THREAT003"
            and g.target == "node_multi"
            and g.sub_target == "CWE-89"
        ]
        assert cwe89_waived == []
