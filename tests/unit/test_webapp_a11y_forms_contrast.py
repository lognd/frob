"""frob.webapp._a11y_forms_contrast coverage: A11Y129-135 positive/negative
controls (calling the `a11y_findings(ctx, frameworks)` hook directly, the
`A11yFileContext` per-file shape T-5323's gate hands every `frob.webapp
._a11y_*` module), a standalone `contrast_ratio` check, and a real
end-to-end control through `frob.gates._a11y_gate.a11y_gate` proving this
module's hook is actually discovered and wired, not merely catalogued.

frob:ticket T-5322
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.gates._a11y_gate import a11y_gate
from frob.lang import raw_tree
from frob.webapp._a11y_forms_contrast import a11y_findings, contrast_ratio
from frob.webapp._a11y_structure import A11yFileContext
from frob.webapp._detect import FrameworkKind

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "a11y1xx"
    / "forms_contrast"
)

_SOME_FRAMEWORK = frozenset({FrameworkKind.NEXTJS})

# One (fixture-dir, filename) pair per rule id's positive/negative control
# -- each fixture dir carries exactly one file, matching the gate's own
# one-file-one-ctx call shape.
_CASES = [
    ("a11y129_positive", "violation.html", "A11Y129", True),
    ("a11y129_negative", "clean.html", "A11Y129", False),
    ("a11y130_positive", "violation.html", "A11Y130", True),
    ("a11y130_negative", "clean.html", "A11Y130", False),
    ("a11y131_positive", "violation.html", "A11Y131", True),
    ("a11y131_negative", "clean.html", "A11Y131", False),
    ("a11y132_positive", "violation.html", "A11Y132", True),
    ("a11y132_negative", "clean.html", "A11Y132", False),
    ("a11y133_positive", "violation.css", "A11Y133", True),
    ("a11y133_negative", "clean.css", "A11Y133", False),
    ("a11y134_positive", "violation.css", "A11Y134", True),
    ("a11y134_negative", "clean.css", "A11Y134", False),
    ("a11y135_positive", "violation.scss", "A11Y135", True),
    ("a11y135_negative", "clean.scss", "A11Y135", False),
]


def _ctx(fixture_dir: str, filename: str) -> A11yFileContext:
    """Parse `<fixture_dir>/<filename>` via `frob.lang.raw_tree` into the
    `A11yFileContext` shape the real gate hands every hook."""
    path = _FIXTURE_ROOT / fixture_dir / filename
    result = raw_tree(path)
    assert result.is_ok, f"raw_tree({path}) failed: {result}"
    tree, source, language = result.danger_ok
    return A11yFileContext(
        file=f"{fixture_dir}/{filename}",
        language=language,
        source=source,
        root=tree.root_node,
    )


# frob:tests src/frob/webapp/_a11y_forms_contrast.py::contrast_ratio kind="unit"
def test_contrast_ratio_black_on_white_is_21_to_1():
    """MUST-FIRE: black-on-white is the WCAG maximum, 21:1."""
    assert contrast_ratio((0, 0, 0), (255, 255, 255)) == 21.0


# frob:tests src/frob/webapp/_a11y_forms_contrast.py::contrast_ratio kind="unit"
def test_contrast_ratio_is_symmetric():
    """Order of the two colors passed to `contrast_ratio` does not matter."""
    a, b = (0, 0, 0), (255, 255, 255)
    assert contrast_ratio(a, b) == contrast_ratio(b, a)


# frob:tests src/frob/webapp/_a11y_forms_contrast.py::a11y_findings kind="unit"
def test_a11y_findings_empty_frameworks_short_circuits():
    """Empty `frameworks` must short-circuit to `()` with no scan at all."""
    ctx = _ctx("a11y129_positive", "violation.html")
    assert a11y_findings(ctx, frozenset()) == ()


# frob:tests src/frob/webapp/_a11y_forms_contrast.py::a11y_findings kind="unit"
# frob:tests src/frob/webapp/_a11y_forms_contrast.py::_redundant_entry_findings \
# kind="unit"
# frob:tests src/frob/webapp/_a11y_forms_contrast.py::_accessible_auth_findings \
# kind="unit"
# frob:tests src/frob/webapp/_a11y_forms_contrast.py::_contrast_findings_for_root \
# kind="unit"
@pytest.mark.parametrize("fixture_dir,filename,rule,expect_finding", _CASES)
def test_a11y_findings_fixture(
    fixture_dir: str, filename: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants exactly that rule id;
    the matching negative fixture fires nothing for that rule."""
    ctx = _ctx(fixture_dir, filename)
    findings = a11y_findings(ctx, _SOME_FRAMEWORK)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


def _init_repo(tmp_path: Path) -> None:
    """Shared git scaffolding for a throwaway `a11y_gate` fixture repo --
    same shape `tests/unit/test_webapp_a11y_structure.py::_init_repo`
    already uses for its own real-gate positive control."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)


# frob:tests src/frob/gates/_a11y_gate.py::a11y_gate kind="unit"
# frob:tests src/frob/webapp/_a11y_forms_contrast.py::a11y_findings kind="unit"
def test_a11y_gate_discovers_forms_contrast_hook_end_to_end(tmp_path: Path):
    """MUST-FIRE: `frob.gates._a11y_gate.a11y_gate`, run end-to-end over a
    throwaway git repo with a framework marker and a planted A11Y131
    (CAPTCHA-with-no-alternative) violation, discovers this module's
    `a11y_findings` hook via `pkgutil.iter_modules` (T-5323's convention)
    and reports the planted finding at the right file -- proof this hook
    is actually wired into the live gate, not merely catalogued."""
    _init_repo(tmp_path)
    (tmp_path / "package.json").write_text('{"dependencies": {"next": "14.0.0"}}\n')
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "signin.html").write_text(
        "<!doctype html>\n"
        '<html lang="en">\n'
        "  <head><title>Sign in</title></head>\n"
        "  <body>\n"
        "    <form>\n"
        '      <div class="g-captcha-widget">Prove you are human</div>\n'
        "    </form>\n"
        "  </body>\n"
        "</html>\n"
    )
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=tmp_path, check=True)

    violations = a11y_gate(tmp_path)

    rules = {v.rule for v in violations}
    assert "A11Y131" in rules
    assert any(
        v.rule == "A11Y131" and v.file == "pages/signin.html" for v in violations
    )
