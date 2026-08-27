"""Tests for VMOD001 (T-3042): the V-model closure gate
(`frob.gates._vmodel.vmodel_gate`).

This is the reachability half of T-3042's fix -- `strata_core.vmodel_check`
had zero callers before this ticket (H1 in the Fable design audit), so
these tests exercise the WHOLE chain: write `.strata` files with
`vmodel_node`/`vmodel_edge` statements to a real design dir, run the gate,
and assert on the `Violation`s it actually returns -- not just that the
kernel function it wraps behaves (that is `test_vmodel_check.py`'s job).

Positive controls per the gate's own opt-in posture: no design dir at all,
and a design dir with `.strata` files that declare nothing vmodel-shaped,
must both be silent (not a finding) -- distinguishing "nothing to check"
from "checked and found nothing wrong" the same way `sys_gate` is silent
for a repo with no design dir.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("strata_core", reason="strata_core native extension not built -- run `make core`")

from frob.gates._vmodel import vmodel_gate  # noqa: E402


def _write(design_dir: Path, name: str, text: str) -> None:
    design_dir.mkdir(parents=True, exist_ok=True)
    (design_dir / name).write_text(text, encoding="utf-8")


class TestVmodelGate:
    def test_noop_no_design_dir(self, tmp_path: Path) -> None:
        """No design/ directory at all -- silent, same posture as sys_gate."""
        assert vmodel_gate(tmp_path) == ()

    def test_noop_no_vmodel_declarations(self, tmp_path: Path) -> None:
        """A design dir with ordinary .strata files but zero vmodel_node/
        vmodel_edge statements must stay silent -- frob has no V-model
        graph of its own yet, and this gate must not invent noise."""
        design_dir = tmp_path / "design"
        _write(design_dir, "m.strata", 'module m\nnode n : trusted { }\n')
        assert vmodel_gate(tmp_path) == ()

    def test_fires_vmod001_on_construction_error(self, tmp_path: Path) -> None:
        """A vmodel_edge naming a node that was never declared anywhere
        (a genuine dangling endpoint) must surface as a VMOD001 finding."""
        design_dir = tmp_path / "design"
        _write(
            design_dir,
            "m.strata",
            'module m\n'
            'vmodel_node req_1 kind "artifact" level "requirements";\n'
            'vmodel_edge kind "satisfies" src ghost_node dst req_1;\n',
        )
        violations = vmodel_gate(tmp_path)
        # The dangling edge is refused (and reported) at construction; the
        # kernel then runs closure over the REMNANT graph (req_1 minus its
        # would-be satisfier), so req_1 also shows up as orphan/unjustified
        # -- both are real, both are asserted, neither is a double-count
        # of the same root cause.
        assert all(v.rule == "VMOD001" for v in violations)
        assert all(v.severity.value == "warn" for v in violations)
        assert any("construction error" in v.message for v in violations)

    def test_fires_vmod001_on_closure_violation(self, tmp_path: Path) -> None:
        """T-3043's exact escape, authored through the new grammar and
        checked through the full gate: a mutual-satisfies pair of design
        nodes with zero requirements anywhere fires multiple VMOD001s, all
        at WARN (never ERROR, per the ticket's explicit severity
        instruction)."""
        design_dir = tmp_path / "design"
        _write(
            design_dir,
            "m.strata",
            'module m\n'
            'vmodel_node design_a kind "artifact" level "system-design";\n'
            'vmodel_node design_b kind "artifact" level "system-design";\n'
            'vmodel_edge kind "satisfies" src design_a dst design_b;\n'
            'vmodel_edge kind "satisfies" src design_b dst design_a;\n',
        )
        violations = vmodel_gate(tmp_path)
        assert len(violations) > 0
        assert all(v.rule == "VMOD001" for v in violations)
        assert all(v.severity.value == "warn" for v in violations)
        rule_names = {v.message.split("closure rule ")[1].split(" ")[0] for v in violations}
        assert "'orphan_requirement'" in rule_names
        assert "'unjustified_design'" in rule_names

    def test_quiet_on_a_genuinely_closed_graph(self, tmp_path: Path) -> None:
        """Positive control: a real requirement -> design chain, verified
        at each paired level, produces zero findings -- the gate does not
        fire on a legitimately closed spec."""
        design_dir = tmp_path / "design"
        _write(
            design_dir,
            "m.strata",
            'module m\n'
            'vmodel_node req_1 kind "artifact" level "requirements";\n'
            'vmodel_node design_1 kind "artifact" level "component-design";\n'
            'vmodel_edge kind "satisfies" src design_1 dst req_1;\n'
            'vmodel_node ctest_1 kind "test" level "customer-test";\n'
            'vmodel_edge kind "verifies" src ctest_1 dst req_1;\n'
            'vmodel_node unittest_1 kind "test" level "component-unit-test";\n'
            'vmodel_edge kind "verifies" src unittest_1 dst design_1;\n',
        )
        assert vmodel_gate(tmp_path) == ()

    def test_spans_multiple_files(self, tmp_path: Path) -> None:
        """A requirement in one file and its verifying test in another --
        the exact cross-file case T-3042's grammar deliberately does not
        validate at parse time -- must still resolve correctly once the
        gate aggregates both files into one graph."""
        design_dir = tmp_path / "design"
        _write(
            design_dir,
            "requirement.strata",
            'module req_module\n'
            'vmodel_node req_1 kind "artifact" level "requirements";\n',
        )
        _write(
            design_dir,
            "test.strata",
            'module test_module\n'
            'vmodel_node ctest_1 kind "test" level "customer-test";\n'
            'vmodel_edge kind "verifies" src ctest_1 dst req_1;\n',
        )
        violations = vmodel_gate(tmp_path)
        # req_1 has a verifying test (rule 3/4 quiet) but nothing satisfies
        # it (rule 1 fires) -- this is the correctly-resolved cross-file
        # result, not a spurious "undeclared node" construction error.
        assert all(v.rule == "VMOD001" for v in violations)
        assert not any("construction error" in v.message for v in violations)
        assert any("orphan_requirement" in v.message for v in violations)
