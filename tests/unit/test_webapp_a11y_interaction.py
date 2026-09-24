"""frob.webapp._a11y_interaction coverage (T-5321): A11Y116-124 keyboard,
focus, target-size, and motion findings, one positive + one negative
fixture per rule id under tests/fixtures/webapp/a11y1xx/interaction/,
plus a real frob.gates._a11y_gate discovery + discovered-hook-firing
check (frob.gates._a11y_gate.a11y_gate's own private hook-discovery
helper, not the full scan -- see
test_a11y_gate_discovers_a11y_interaction_hook's own docstring for why).

frob:ticket T-5321
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.gates import _a11y_gate as a11y_gate_module
from frob.lang import raw_tree
from frob.webapp._a11y_interaction import a11y_findings
from frob.webapp._a11y_structure import A11yFileContext
from frob.webapp._detect import FrameworkKind

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "a11y1xx"
    / "interaction"
)

_FRAMEWORKS = frozenset({FrameworkKind.VITE})

_CASES = [
    ("a11y116_positive", "A11Y116", True),
    ("a11y116_negative", "A11Y116", False),
    ("a11y117_positive", "A11Y117", True),
    ("a11y117_negative", "A11Y117", False),
    ("a11y118_positive", "A11Y118", True),
    ("a11y118_negative", "A11Y118", False),
    ("a11y119_positive", "A11Y119", True),
    ("a11y119_negative", "A11Y119", False),
    ("a11y120_positive", "A11Y120", True),
    ("a11y120_negative", "A11Y120", False),
    ("a11y121_positive", "A11Y121", True),
    ("a11y121_negative", "A11Y121", False),
    ("a11y122_positive", "A11Y122", True),
    ("a11y122_negative", "A11Y122", False),
    ("a11y123_positive", "A11Y123", True),
    ("a11y123_negative", "A11Y123", False),
    ("a11y124_positive", "A11Y124", True),
    ("a11y124_negative", "A11Y124", False),
]

# Each fixture dir holds exactly one source file (page.html or style.css) --
# the same file name every time within a family, so the file name can be
# derived from the fixture dir's own extension-implying rule.
_CSS_RULES = {"A11Y117", "A11Y120", "A11Y121", "A11Y122"}


def _fixture_file(fixture_dir: str, rule: str) -> str:
    """The one source file name a given fixture dir holds -- `style.css`
    for the CSS-family rules, `page.html` for everything else."""
    return "style.css" if rule in _CSS_RULES else "page.html"


def _ctx(fixture_dir: str, rule: str) -> A11yFileContext:
    """Parse the fixture file for `fixture_dir` via `frob.lang.raw_tree`
    into an `A11yFileContext` -- the same shape
    `frob.gates._a11y_gate.a11y_gate` hands every discovered hook."""
    rel = _fixture_file(fixture_dir, rule)
    path = _FIXTURE_ROOT / fixture_dir / rel
    result = raw_tree(path)
    assert result.is_ok, f"raw_tree({path}) failed: {result}"
    tree, source, language = result.danger_ok
    return A11yFileContext(
        file=rel, language=language, source=source, root=tree.root_node
    )


# frob:tests src/frob/webapp/_a11y_interaction.py::a11y_findings kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
def test_a11y_interaction_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants exactly that rule
    id; the matching negative fixture fires nothing for that rule."""
    findings = a11y_findings(_ctx(fixture_dir, rule), _FRAMEWORKS)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_a11y_interaction.py::a11y_findings kind="unit"
def test_a11y_interaction_empty_frameworks_short_circuits() -> None:
    """An empty `frameworks` short-circuits to `()` even over a context
    that would otherwise plant an A11Y118 finding (T-5321's gate-hook
    contract: the gate detects frameworks once, not once per leaf)."""
    ctx = _ctx("a11y118_positive", "A11Y118")
    assert a11y_findings(ctx, frozenset()) == ()


# frob:tests src/frob/webapp/_a11y_interaction.py::a11y_findings kind="unit"
def test_a11y_interaction_positive_control_returns_correct_rule() -> None:
    """Positive control: a planted violation returns exactly the expected
    rule id, not merely a non-empty result (silent-zero guard)."""
    findings = a11y_findings(_ctx("a11y118_positive", "A11Y118"), _FRAMEWORKS)
    assert findings, "expected at least one finding from the positive fixture"
    assert any(f.rule == "A11Y118" for f in findings)


def _init_repo(tmp_path: Path) -> None:
    """A throwaway git repo `frob.gates._a11y_gate.a11y_gate` can scan --
    the same fixture-repo shape T-5323's own gate test uses."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)


# frob:tests src/frob/gates/_a11y_gate.py::a11y_gate kind="unit"
def test_a11y_gate_discovers_a11y_interaction_hook(tmp_path: Path) -> None:
    """MUST-FIRE (real discovery, not a direct hook call):
    `frob.gates._a11y_gate`'s own `pkgutil.iter_modules`-based hook
    discovery (exercised by a real `a11y_gate` invocation over a
    throwaway git repo) finds `frob.webapp._a11y_interaction`'s
    `a11y_findings` and it is in the discovered set -- proof the T-5323
    gate wiring actually reaches this leaf, not just that `a11y_findings`
    works when called directly.

    A full `a11y_gate(tmp_path)` scan is NOT run here: as of this writing
    a SIBLING hook module (`frob.webapp._a11y_statement`, T-5324) still
    uses the pre-T-5323 `a11y_findings(root, frameworks)` shape instead
    of the real `a11y_findings(ctx, frameworks)` contract, so
    `a11y_gate.a11y_gate` crashes with a `TypeError` for ANY repo with
    ANY detected framework today, unconditionally and unrelated to this
    leaf's own fixture content (filed as T-5448, out of this
    ticket's declared scope -- `src/frob/webapp/_a11y_statement.py`).
    This test therefore calls the gate's own private discovery helper
    directly rather than the full scan, so it exercises the real
    `pkgutil`-based wiring this leaf depends on without being coupled to
    an unrelated sibling module's bug."""
    hooks = a11y_gate_module._discover_hooks()
    hook_modules = {hook.__module__ for hook in hooks}
    assert "frob.webapp._a11y_interaction" in hook_modules


# frob:tests src/frob/webapp/_a11y_interaction.py::a11y_findings kind="unit"
def test_a11y_gate_discovered_hook_fires_on_planted_violation(tmp_path: Path) -> None:
    """MUST-FIRE: the hook `frob.gates._a11y_gate` actually discovers for
    this leaf (same lookup `test_a11y_gate_discovers_a11y_interaction_hook`
    proves), called the same way `a11y_gate` itself would call it (one
    already-parsed `A11yFileContext`, the real `frob.lang.raw_tree`
    parse), reports A11Y118 for a planted positive-tabindex violation."""
    _init_repo(tmp_path)
    (tmp_path / "index.html").write_text(
        "<!doctype html>\n"
        "<html>\n"
        "  <body>\n"
        '    <div tabindex="7">bad order</div>\n'
        "  </body>\n"
        "</html>\n"
    )
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=tmp_path, check=True)

    hooks = {hook.__module__: hook for hook in a11y_gate_module._discover_hooks()}
    hook = hooks["frob.webapp._a11y_interaction"]

    result = raw_tree(tmp_path / "index.html")
    assert result.is_ok
    tree, source, language = result.danger_ok
    ctx = A11yFileContext(
        file="index.html", language=language, source=source, root=tree.root_node
    )

    violations = hook(ctx, _FRAMEWORKS)

    rules = {v.rule for v in violations}
    assert "A11Y118" in rules
    assert all(v.file == "index.html" for v in violations)
