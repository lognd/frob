"""Tests for ARCH001 (T-0289): frob.arch's complexity-aware long-function
rule, and frob.gates._arch.arch_gate's waiver/ceiling wiring."""

from __future__ import annotations

from pathlib import Path

from frob.arch import analyze_project
from frob.gates import GateConfig, run_gates


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _flat_long_source(name: str) -> str:
    """A long-but-FLAT function: linear setup, no branching/looping --
    must NOT trigger long-function under the complexity-aware rule."""
    lines = [f"def {name}(config: dict) -> dict:", '    """Flat setup, no branches."""']
    for i in range(40):
        lines.append(f'    v{i} = config.get("k{i}", {i})')
    lines.append('    return {"ok": True}')
    return "\n".join(lines) + "\n"


def _complex_long_source(name: str, waiver: str = "") -> str:
    """A long AND structurally complex function (nested try/if/for) --
    must trigger long-function under the complexity-aware rule."""
    lines = [waiver] if waiver else []
    lines += [f"def {name}(items):", '    """Long and complex."""', "    total = 0"]
    for i in range(30):
        lines.append(
            f"    try:\n        if items[{i}] and total:\n"
            "            for x in range(3):\n"
            "                if x:\n                    total += x\n"
            "    except Exception:\n        pass"
        )
    lines.append("    return total")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# frob.arch: complexity-aware long-function (Part 1)
# ---------------------------------------------------------------------------


class TestArchComplexityAware:
    def test_flat_long_function_not_flagged(self, tmp_path):
        _write(tmp_path, "src/flat.py", _flat_long_source("flat_long"))
        result = analyze_project(tmp_path / "src")
        long_issues = [s for s in result.suggestions if s.category == "long-function"]
        assert long_issues == []

    def test_complex_long_function_flagged(self, tmp_path):
        _write(tmp_path, "src/complexf.py", _complex_long_source("complex_long"))
        result = analyze_project(tmp_path / "src")
        long_issues = [s for s in result.suggestions if s.category == "long-function"]
        assert any("complex_long" in s.message for s in long_issues)

    def test_complex_long_function_carries_symref_and_metric(self, tmp_path):
        _write(tmp_path, "src/complexf.py", _complex_long_source("complex_long"))
        result = analyze_project(tmp_path / "src")
        [issue] = [s for s in result.suggestions if s.category == "long-function"]
        assert issue.symref == "complexf.py::complex_long"
        assert issue.metric is not None and issue.metric > 30


# ---------------------------------------------------------------------------
# frob.gates._arch.arch_gate: ARCH001, waivers, ceilings (Part 2)
# ---------------------------------------------------------------------------


class TestArchGateWaivers:
    def test_reasoned_waive_honored(self, tmp_path):
        src = _complex_long_source(
            "complex_long",
            waiver='# frob:waive ARCH001 reason="justified, dispatch-heavy" ceiling="9999"',
        )
        _write(tmp_path, "src/complexf.py", src)
        cfg = GateConfig(root=str(tmp_path), base="main", gates=frozenset({"archgate"}))
        report = run_gates(cfg).danger_ok
        assert not any(v.rule == "ARCH001" for v in report.violations)
        assert any(v.rule == "ARCH001" for v in report.waived)

    def test_unreasoned_waive_rejected(self, tmp_path):
        src = _complex_long_source("complex_long", waiver="# frob:waive ARCH001")
        _write(tmp_path, "src/complexf.py", src)
        cfg = GateConfig(root=str(tmp_path), base="main", gates=frozenset({"archgate"}))
        report = run_gates(cfg).danger_ok
        assert any(v.rule == "WAIVE001" for v in report.violations)
        # The un-reasoned directive never became a waive edge, so ARCH001
        # still fires (kept, not suppressed).
        assert any(v.rule == "ARCH001" for v in report.violations)

    def test_ceiling_refires_when_grown_past_it(self, tmp_path):
        src = _complex_long_source(
            "complex_long",
            waiver='# frob:waive ARCH001 reason="justified, small" ceiling="50"',
        )
        _write(tmp_path, "src/complexf.py", src)
        cfg = GateConfig(root=str(tmp_path), base="main", gates=frozenset({"archgate"}))
        report = run_gates(cfg).danger_ok
        # The function is well over 50 lines -- the waiver's ceiling no
        # longer covers it, so ARCH001 must still be kept, not waived.
        assert any(v.rule == "ARCH001" for v in report.violations)
        assert not any(v.rule == "ARCH001" for v in report.waived)

    def test_no_finding_no_violation(self, tmp_path):
        _write(tmp_path, "src/flat.py", _flat_long_source("flat_long"))
        cfg = GateConfig(root=str(tmp_path), base="main", gates=frozenset({"archgate"}))
        report = run_gates(cfg).danger_ok
        assert not any(v.rule == "ARCH001" for v in report.violations)
