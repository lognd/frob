"""frob.webapp._a11y_structure coverage: one positive (violation) and one
negative (clean) control per A11Y101-115, plus a discovery/wiring check
for frob.gates._a11y_gate.

frob:ticket T-5323
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.gates._a11y_gate import a11y_gate
from frob.lang import raw_tree
from frob.webapp._a11y_structure import A11yFileContext, a11y_findings
from frob.webapp._detect import FrameworkKind

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "a11y1xx"
    / "structure"
)

_SOME_FRAMEWORK = frozenset({FrameworkKind.NEXTJS})


def _ctx(rel_path: str) -> A11yFileContext:
    """Parse `rel_path` (relative to the structure fixture dir) via
    `frob.lang.raw_tree` into an `A11yFileContext`."""
    path = _FIXTURE_ROOT / rel_path
    result = raw_tree(path)
    assert result.is_ok, f"raw_tree({path}) failed: {result}"
    tree, source, language = result.danger_ok
    return A11yFileContext(
        file=rel_path, language=language, source=source, root=tree.root_node
    )


def _rule_hits(rel_path: str, rule: str) -> list:
    """Every `rule`-tagged finding `a11y_findings` reports for `rel_path`."""
    findings = a11y_findings(_ctx(rel_path), _SOME_FRAMEWORK)
    return [f for f in findings if f.rule == rule]


def test_no_framework_short_circuits_to_empty():
    """MUST-FIRE: an empty frameworks set skips scanning entirely, even
    for an otherwise-violating fixture."""
    findings = a11y_findings(_ctx("a11y101_violation.html"), frozenset())
    assert findings == ()


# frob:tests src/frob/webapp/_a11y_structure.py::a11y_findings kind="unit"
# frob:tests src/frob/webapp/_a11y_structure.py::A11yFileContext kind="unit"
def test_a11y101_missing_alt():
    """MUST-FIRE: A11Y101 fires on the violation fixture, not the clean one."""
    assert len(_rule_hits("a11y101_violation.html", "A11Y101")) == 1
    assert _rule_hits("a11y101_clean.html", "A11Y101") == []


def test_a11y102_svg_missing_name():
    """MUST-FIRE: A11Y102 fires on an unlabeled role=img svg."""
    assert len(_rule_hits("a11y102_violation.html", "A11Y102")) == 1
    assert _rule_hits("a11y102_clean.html", "A11Y102") == []


def test_a11y103_skipped_heading_level():
    """MUST-FIRE: A11Y103 fires on an h1 -> h3 jump."""
    assert len(_rule_hits("a11y103_violation.html", "A11Y103")) == 1
    assert _rule_hits("a11y103_clean.html", "A11Y103") == []


def test_a11y104_duplicate_h1():
    """MUST-FIRE: A11Y104 fires on a second <h1>."""
    assert len(_rule_hits("a11y104_violation.html", "A11Y104")) == 1
    assert _rule_hits("a11y104_clean.html", "A11Y104") == []


def test_a11y105_missing_title():
    """MUST-FIRE: A11Y105 fires when <head> has no <title>."""
    assert len(_rule_hits("a11y105_violation.html", "A11Y105")) == 1
    assert _rule_hits("a11y105_clean.html", "A11Y105") == []


def test_a11y106_missing_lang():
    """MUST-FIRE: A11Y106 fires when <html> has no lang attribute."""
    assert len(_rule_hits("a11y106_violation.html", "A11Y106")) == 1
    assert _rule_hits("a11y106_clean.html", "A11Y106") == []


def test_a11y107_empty_lang():
    """MUST-FIRE: A11Y107 fires when <html lang=""> is empty."""
    assert len(_rule_hits("a11y107_violation.html", "A11Y107")) == 1
    assert _rule_hits("a11y107_clean.html", "A11Y107") == []


def test_a11y108_link_no_name():
    """MUST-FIRE: A11Y108 fires on an <a> with no accessible name."""
    assert len(_rule_hits("a11y108_violation.html", "A11Y108")) == 1
    assert _rule_hits("a11y108_clean.html", "A11Y108") == []


def test_a11y109_button_no_name():
    """MUST-FIRE: A11Y109 fires on a <button> with no accessible name."""
    assert len(_rule_hits("a11y109_violation.html", "A11Y109")) == 1
    assert _rule_hits("a11y109_clean.html", "A11Y109") == []


def test_a11y110_generic_link_text():
    """MUST-FIRE: A11Y110 fires on "click here" link text."""
    assert len(_rule_hits("a11y110_violation.html", "A11Y110")) == 1
    assert _rule_hits("a11y110_clean.html", "A11Y110") == []


def test_a11y111_unlabeled_input():
    """MUST-FIRE: A11Y111 fires on an input with no associated label."""
    assert len(_rule_hits("a11y111_violation.html", "A11Y111")) == 1
    assert _rule_hits("a11y111_clean.html", "A11Y111") == []


def test_a11y112_missing_autocomplete():
    """MUST-FIRE: A11Y112 fires on an identity input with no autocomplete."""
    assert len(_rule_hits("a11y112_violation.html", "A11Y112")) == 1
    assert _rule_hits("a11y112_clean.html", "A11Y112") == []


# frob:tests src/frob/webapp/_a11y_substrate.py::all_elements kind="unit"
def test_a11y113_duplicate_id():
    """MUST-FIRE: A11Y113 fires on a repeated id attribute value."""
    assert len(_rule_hits("a11y113_violation.html", "A11Y113")) == 1
    assert _rule_hits("a11y113_clean.html", "A11Y113") == []


def test_a11y114_invalid_role():
    """MUST-FIRE: A11Y114 fires on an unrecognized ARIA role value."""
    assert len(_rule_hits("a11y114_violation.html", "A11Y114")) == 1
    assert _rule_hits("a11y114_clean.html", "A11Y114") == []


def test_a11y115_invalid_aria_attribute():
    """MUST-FIRE: A11Y115 fires on a misspelled aria-* attribute name."""
    assert len(_rule_hits("a11y115_violation.html", "A11Y115")) == 1
    assert _rule_hits("a11y115_clean.html", "A11Y115") == []


def _init_repo(tmp_path: Path) -> None:
    """Shared git scaffolding for a throwaway a11y_gate fixture repo --
    same shape `tests/unit/gates/test_cov002_strata_declarations.py`
    already uses for a real-`frob.gates.run_gates`-adjacent gate test."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)


# frob:tests src/frob/gates/_a11y_gate.py::a11y_gate kind="unit"
def test_a11y_gate_discovers_hook_and_scans_tracked_files(tmp_path: Path):
    """MUST-FIRE: a11y_gate, run end-to-end over a throwaway git repo with
    a framework marker and a planted A11Y101/A11Y106 violation, discovers
    frob.webapp._a11y_structure's a11y_findings hook (pkgutil.iter_modules)
    and reports the planted findings at the right file/line -- the same
    positive-control shape the Done report's manual verification used."""
    _init_repo(tmp_path)
    (tmp_path / "package.json").write_text('{"dependencies": {"next": "14.0.0"}}\n')
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "index.html").write_text(
        "<!doctype html>\n"
        "<html>\n"
        "  <head><title>Home</title></head>\n"
        "  <body>\n"
        '    <img src="cat.png" />\n'
        "  </body>\n"
        "</html>\n"
    )
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=tmp_path, check=True)

    violations = a11y_gate(tmp_path)

    rules = {v.rule for v in violations}
    assert "A11Y101" in rules
    assert "A11Y106" in rules
    assert all(v.file == "pages/index.html" for v in violations)


def test_a11y_gate_no_framework_short_circuits_to_empty(tmp_path: Path):
    """a11y_gate returns () for a repo with no detected web framework,
    even with a violating html fixture present -- the same T-5302
    no-framework short-circuit every WEBSEC/COMPLY/A11Y/SEO family uses."""
    _init_repo(tmp_path)
    (tmp_path / "index.html").write_text("<html><body><img/></body></html>\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=tmp_path, check=True)

    assert a11y_gate(tmp_path) == ()
