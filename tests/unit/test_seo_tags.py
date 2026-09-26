"""frob.webapp._seo_tags coverage (T-5374): SEO101-112 per-page-tag
findings, one positive + one negative fixture per rule id under
tests/fixtures/webapp/seo1xx/tags/.

frob:ticket T-5374
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.webapp._detect import FrameworkKind
from frob.webapp._seo_tags import seo_tag_findings, websec_findings

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "seo1xx" / "tags"
)

_CASES = [
    ("seo101_positive", "SEO101", True),
    ("seo101_negative", "SEO101", False),
    ("seo102_positive", "SEO102", True),
    ("seo102_negative", "SEO102", False),
    ("seo103_positive", "SEO103", True),
    ("seo103_negative", "SEO103", False),
    ("seo104_positive", "SEO104", True),
    ("seo104_negative", "SEO104", False),
    ("seo105_positive", "SEO105", True),
    ("seo105_negative", "SEO105", False),
    ("seo106_positive", "SEO106", True),
    ("seo106_negative", "SEO106", False),
    ("seo107_positive", "SEO107", True),
    ("seo107_negative", "SEO107", False),
    ("seo108_positive", "SEO108", True),
    ("seo108_negative", "SEO108", False),
    ("seo109_positive", "SEO109", True),
    ("seo109_negative", "SEO109", False),
    ("seo110_positive", "SEO110", True),
    ("seo110_negative", "SEO110", False),
    ("seo111_positive", "SEO111", True),
    ("seo111_negative", "SEO111", False),
    ("seo112_positive", "SEO112", True),
    ("seo112_negative", "SEO112", False),
]


# frob:tests src/frob/webapp/_seo_tags.py::WebsecSeoTagFinding kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_seo_tags.py::seo_tag_findings kind="unit"
def test_seo_tag_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants exactly that rule
    id; the matching negative fixture (the tag present/unique/valid)
    fires nothing for that rule id."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = seo_tag_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) >= 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_seo_tags.py::seo_tag_findings kind="unit"
def test_seo_tag_findings_no_framework_short_circuits(tmp_path: Path) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain a
    head-less page that would otherwise plant findings once parsed."""
    (tmp_path / "page.html").write_text(
        "<!DOCTYPE html><html><head><title>x</title></head><body></body></html>",
        encoding="utf-8",
    )
    assert seo_tag_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_seo_tags.py::websec_findings kind="unit"
def test_websec_findings_emits_violation_when_called_directly() -> None:
    """`websec_findings(root, frameworks)` turns a SEO103 finding into a
    `Violation` when handed a non-empty `frameworks` set, without
    re-running `detect_frameworks` -- called directly (module docstring's
    DISCOVERY CONVENTION section: no live gate discovers this hook yet,
    `_seo_tags` does not match `_taint_gate`'s `_websec_*` prefix)."""
    root = _FIXTURE_ROOT / "seo103_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.FLASK}))
    matching = [v for v in violations if v.rule == "SEO103"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_seo_tags.py::websec_findings kind="unit"
def test_websec_findings_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set
    without touching the filesystem, even over a fixture that would
    otherwise plant a SEO103 finding."""
    root = _FIXTURE_ROOT / "seo103_positive"
    assert websec_findings(root, frozenset()) == ()
