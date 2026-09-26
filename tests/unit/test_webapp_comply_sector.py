"""frob.webapp._comply_sector coverage (T-5370): COMPLY117-122
sector-specific (HIPAA/GLBA/COPPA/FERPA) applicability-flag-gated
findings, one positive + one negative fixture per rule id under
tests/fixtures/webapp/comply1xx/sector/, plus a `no_flags` MUST-STAY-
QUIET control.

Gate wiring follows `frob.gates._taint_gate`'s T-5308 `websec_findings`
hook-discovery CONVENTION (this module's own docstring: `frob.webapp.
_comply_substrate` defines no comply-specific convention of its own).
T-5372 (`frob.webapp._comply_privacy`) widened `_taint_gate.py`'s
discovery module-basename prefix from `_websec_` alone to also match
`_comply_`, so `test_taint_gate_discovers_websec_comply_sector_hook`
below -- the real end-to-end positive control through `taint_gate()` --
depends on T-5372 landing first (see this leaf's own Done report).

frob:ticket T-5370
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._comply_sector import (
    ComplySectorFlags,
    comply_sector_findings,
    websec_findings,
)
from frob.webapp._detect import detect_frameworks

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "comply1xx" / "sector"
)

_CASES = [
    ("comply117_positive", "COMPLY117", True),
    ("comply117_negative", "COMPLY117", False),
    ("comply118_positive", "COMPLY118", True),
    ("comply118_negative", "COMPLY118", False),
    ("comply119_positive", "COMPLY119", True),
    ("comply119_negative", "COMPLY119", False),
    ("comply120_positive", "COMPLY120", True),
    ("comply120_negative", "COMPLY120", False),
    ("comply121_positive", "COMPLY121", True),
    ("comply121_negative", "COMPLY121", False),
    ("comply122_positive", "COMPLY122", True),
    ("comply122_negative", "COMPLY122", False),
]


# frob:tests src/frob/webapp/_comply_sector.py::ComplySectorFinding kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_comply_sector.py::comply_sector_findings kind="unit"
def test_comply_sector_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture (flag set, gap present)
    plants at least that rule id; the matching negative fixture (flag
    set, gap remedied) fires nothing for that rule."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = comply_sector_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) >= 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_comply_sector.py::comply_sector_findings kind="unit"
def test_comply_sector_findings_no_flags_must_stay_quiet() -> None:
    """MUST-STAY-QUIET control: `no_flags/` has no frob.toml at all (so
    every `[comply]` flag defaults False) and carries the EXACT gap
    shape `comply117_positive`/`comply121_positive` would otherwise
    fire on -- proving the flag short-circuit, not framework/content
    absence, is what keeps this quiet."""
    root = _FIXTURE_ROOT / "no_flags"
    assert comply_sector_findings(root) == ()


# frob:tests src/frob/webapp/_comply_sector.py::ComplySectorFlags kind="unit"
def test_comply_sector_flags_any_set() -> None:
    """`ComplySectorFlags.any_set` is False only when every flag is
    False, and True as soon as one flag is set."""
    assert ComplySectorFlags().any_set() is False
    assert ComplySectorFlags(financial_institution=True).any_set() is True
    assert ComplySectorFlags(edtech_student_data=True).any_set() is True


# frob:tests src/frob/webapp/_comply_sector.py::websec_findings kind="unit"
def test_websec_findings_hook_emits_gate_violation() -> None:
    """MUST-FIRE (positive control): the `taint_gate` module-discovery
    hook, called the way `taint_gate` calls it (with the caller's own
    already-computed `detect_frameworks` result), turns the COMPLY117
    fixture into one WARN-tier `Violation`."""
    root = _FIXTURE_ROOT / "comply117_positive"
    frameworks = detect_frameworks(root)
    assert frameworks
    violations = websec_findings(root, frameworks)
    matching = [v for v in violations if v.rule == "COMPLY117"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
    assert matching[0].file == "<repo>"


# frob:tests src/frob/webapp/_comply_sector.py::websec_findings kind="unit"
def test_websec_findings_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` never re-detects frameworks itself -- an empty
    `frameworks` set (the caller's own `detect_frameworks` result)
    short-circuits to `()` even for a fixture directory that would
    otherwise plant a finding."""
    root = _FIXTURE_ROOT / "comply117_positive"
    assert websec_findings(root, frozenset()) == ()


# frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
def test_taint_gate_discovers_websec_comply_sector_hook(tmp_path: Path) -> None:
    """MUST-FIRE (positive control): a real git repo with a Django
    framework marker, a `frob.toml` opting `financial_institution=true`,
    and no privacy-notice content produces a `COMPLY117` `Violation`
    through `taint_gate` end to end -- discovery finds
    `_comply_sector.websec_findings` with no hard-coded `_taint_gate.py`
    call site for this rule family. DEPENDS on T-5372's `_taint_gate.py`
    module-prefix widening (`_websec_` -> also `_comply_`) having landed
    on `dev` first -- see this leaf's own Done report."""
    import subprocess as sp

    sp.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    sp.run(["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True)
    sp.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "manage.py").write_text("import django\n", encoding="utf-8")
    (tmp_path / "frob.toml").write_text(
        "[comply]\nfinancial_institution = true\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text(
        "# Example bank app\nNo privacy notice content here.\n", encoding="utf-8"
    )
    sp.run(["git", "add", "."], cwd=tmp_path, check=True)
    sp.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)

    violations = taint_gate(tmp_path)
    comply = [v for v in violations if v.rule == "COMPLY117"]
    assert len(comply) == 1
    assert comply[0].severity.value == "warn"
    assert comply[0].file == "<repo>"
