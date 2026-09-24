"""Tests for MSCLOSE001 (T-3010): milestone-scoped V-model closure
(`frob.gates._strata_milestone_closure.milestone_closure_gate`).

Positive controls per T-3010's own tree entry: a configuration binding an
architecture that covers 3 of 5 declared obligations, with the remaining
2 marked as a `MilestoneGap`, must pass; the same graph with an undeclared
(un-gapped) missing obligation must fire -- exercised here at the smaller
1-covered/1-gapped/1-missing scale `test_partial_milestone_with_gap_
passes_the_ungapped_case_still_fires` covers in one fixture, to keep one
test asserting both halves of the same positive control.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip(
    "strata_core", reason="strata_core native extension not built -- run `make core`"
)

from frob.gates._strata_milestone_closure import (  # noqa: E402
    MILESTONE_GAP_REGISTRY,
    MilestoneGap,
    _milestone_gap_node_ids,
    milestone_closure_gate,
)


def _write(design_dir: Path, name: str, text: str) -> None:
    design_dir.mkdir(parents=True, exist_ok=True)
    (design_dir / name).write_text(text, encoding="utf-8")


@pytest.fixture(autouse=True)
def _clean_registry():
    """`MILESTONE_GAP_REGISTRY` is module-global state (T-3010's own
    hand-edited accounting table); each test restores it so no test's
    gap declarations leak into another's assertions."""
    saved = dict(MILESTONE_GAP_REGISTRY)
    yield
    MILESTONE_GAP_REGISTRY.clear()
    MILESTONE_GAP_REGISTRY.update(saved)


class TestMilestoneClosureGate:
    # frob:tests src/frob/gates/_strata_milestone_closure.py::milestone_closure_gate
    def test_quiet_on_no_design_dir(self, tmp_path: Path) -> None:
        """No design/ directory at all -- silent, same posture as vmodel_gate."""
        assert milestone_closure_gate(tmp_path, "v1.0.0") == ()

    # frob:tests src/frob/gates/_strata_milestone_closure.py::milestone_closure_gate
    def test_quiet_no_vmodel_declarations(self, tmp_path: Path) -> None:
        """A design dir with ordinary .strata files but zero vmodel_node
        declarations stays silent -- nothing to check yet."""
        design_dir = tmp_path / "design"
        _write(design_dir, "m.strata", "module m\nnode n : trusted { }\n")
        assert milestone_closure_gate(tmp_path, "v1.0.0") == ()

    # frob:tests src/frob/gates/_strata_milestone_closure.py::milestone_closure_gate
    def test_fires_msclose001_on_an_ungapped_uncovered_obligation(
        self, tmp_path: Path
    ) -> None:
        """An artifact with no verifying test and no declared gap fires."""
        design_dir = tmp_path / "design"
        _write(
            design_dir,
            "m.strata",
            "module m\n"
            'vmodel_node obligation_1 kind "artifact" level "requirements" '
            'code_ref "o1.rs";\n',
        )
        violations = milestone_closure_gate(tmp_path, "v1.0.0")
        assert len(violations) == 1
        assert violations[0].rule == "MSCLOSE001"
        assert violations[0].severity.value == "warn"
        assert "obligation_1" in violations[0].message

    # frob:tests src/frob/gates/_strata_milestone_closure.py::milestone_closure_gate
    # frob:tests src/frob/gates/_strata_milestone_closure.py::MILESTONE_GAP_REGISTRY
    # frob:tests src/frob/gates/_strata_milestone_closure.py::MilestoneGap
    def test_quiet_when_gap_is_declared(self, tmp_path: Path) -> None:
        """The SAME uncovered artifact as above, but this milestone
        declares a reasoned gap for it -- must not fire."""
        design_dir = tmp_path / "design"
        _write(
            design_dir,
            "m.strata",
            "module m\n"
            'vmodel_node obligation_1 kind "artifact" level "requirements" '
            'code_ref "o1.rs";\n',
        )
        MILESTONE_GAP_REGISTRY["v1.0.0"] = {
            "obligation_1": MilestoneGap(
                reason="T-9999: deferred to the next milestone"
            )
        }
        assert milestone_closure_gate(tmp_path, "v1.0.0") == ()

    # frob:tests src/frob/gates/_strata_milestone_closure.py::milestone_closure_gate
    def test_partial_milestone_with_gap_passes_the_ungapped_case_still_fires(
        self, tmp_path: Path
    ) -> None:
        """T-3010's tree positive control: a configuration binding an
        architecture that covers most obligations (here, one verified by
        a test) with the rest gapped passes; adding one MORE, un-gapped
        obligation to the same graph must fire on exactly that one."""
        design_dir = tmp_path / "design"
        _write(
            design_dir,
            "m.strata",
            "module m\n"
            'vmodel_node covered kind "artifact" level "requirements" code_ref "c.rs";\n'
            'vmodel_node ctest kind "test" level "customer-test" runnable "t.py::ctest";\n'
            'vmodel_edge kind "verifies" src ctest dst covered;\n'
            'vmodel_node gapped kind "artifact" level "requirements" code_ref "g.rs";\n',
        )
        MILESTONE_GAP_REGISTRY["v1.0.0"] = {
            "gapped": MilestoneGap(reason="T-9999: deferred to the next milestone")
        }
        assert milestone_closure_gate(tmp_path, "v1.0.0") == ()

        _write(
            design_dir,
            "m.strata",
            "module m\n"
            'vmodel_node covered kind "artifact" level "requirements" code_ref "c.rs";\n'
            'vmodel_node ctest kind "test" level "customer-test" runnable "t.py::ctest";\n'
            'vmodel_edge kind "verifies" src ctest dst covered;\n'
            'vmodel_node gapped kind "artifact" level "requirements" code_ref "g.rs";\n'
            'vmodel_node missing kind "artifact" level "requirements" code_ref "m.rs";\n',
        )
        violations = milestone_closure_gate(tmp_path, "v1.0.0")
        assert len(violations) == 1
        assert "missing" in violations[0].message

    # frob:tests src/frob/gates/_strata_milestone_closure.py::milestone_closure_gate
    def test_default_milestone_reads_frob_toml(self, tmp_path: Path) -> None:
        """No explicit `milestone` -- falls back to `[tickets].
        default_milestone`, and a gap declared for THAT milestone name
        applies."""
        design_dir = tmp_path / "design"
        _write(
            design_dir,
            "m.strata",
            "module m\n"
            'vmodel_node obligation_1 kind "artifact" level "requirements" '
            'code_ref "o1.rs";\n',
        )
        (tmp_path / "frob.toml").write_text(
            '[tickets]\ndefault_milestone = "v2.0.0"\n', encoding="utf-8"
        )
        MILESTONE_GAP_REGISTRY["v2.0.0"] = {
            "obligation_1": MilestoneGap(reason="T-9999: deferred")
        }
        assert milestone_closure_gate(tmp_path) == ()


class TestMilestoneGapNodeIds:
    # frob:tests src/frob/gates/_strata_milestone_closure.py::_milestone_gap_node_ids
    def test_refuses_a_blank_reason(self) -> None:
        """A `MilestoneGap` with a blank/whitespace-only `reason` is
        treated as NOT gapped -- unaccounted-for, same as a missing cell."""
        MILESTONE_GAP_REGISTRY["v1.0.0"] = {
            "obligation_1": MilestoneGap(reason="   "),
            "obligation_2": MilestoneGap(reason="T-9999: real reason"),
        }
        try:
            ids = _milestone_gap_node_ids("v1.0.0")
        finally:
            MILESTONE_GAP_REGISTRY.clear()
        assert ids == frozenset({"obligation_2"})
