"""frob.webapp._a11y_statement coverage: positive/negative controls for
the accessibility-statement content-lint's per-file gate hook contract,
plus an end-to-end `frob.gates._a11y_gate.a11y_gate` integration test
(T-5454: the module's original `(root, frameworks)` shape crashed the
real gate, which only ever calls `a11y_findings(ctx, frameworks)`).

frob:ticket T-5324
frob:ticket T-5454
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.gates._a11y_gate import a11y_gate
from frob.lang import raw_tree
from frob.webapp._a11y_statement import a11y_findings
from frob.webapp._a11y_structure import A11yFileContext
from frob.webapp._detect import FrameworkKind

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "a11y1xx"
    / "statement"
)

_NEXTJS = frozenset({FrameworkKind.NEXTJS})


def _ctx(root: Path, rel_path: str) -> A11yFileContext:
    """Parse `root/rel_path` via `frob.lang.raw_tree` into an
    `A11yFileContext` shaped exactly like the real gate hands hooks."""
    path = root / rel_path
    result = raw_tree(path)
    assert result.is_ok, f"raw_tree({path}) failed: {result}"
    tree, source, language = result.danger_ok
    return A11yFileContext(
        file=rel_path, language=language, source=source, root=tree.root_node
    )


# frob:tests src/frob/webapp/_a11y_statement.py::a11y_findings kind="unit"
def test_a11y_findings_complete_statement_is_clean():
    """MUST-STAY-QUIET: a statement page covering all seven required
    sections, called AS the statement page (ctx.file matches), reports no
    section findings."""
    root = _FIXTURE_ROOT / "complete"
    findings = a11y_findings(_ctx(root, "pages/accessibility.tsx"), _NEXTJS)
    assert findings == ()


# frob:tests src/frob/webapp/_a11y_statement.py::a11y_findings kind="unit"
def test_a11y_findings_partial_statement_reports_missing_sections():
    """MUST-FIRE: a statement page covering only commitment+contact,
    called AS the statement page, reports the five other required
    sections as missing, each its own rule id, none of the two present
    sections."""
    root = _FIXTURE_ROOT / "partial"
    findings = a11y_findings(_ctx(root, "pages/accessibility.tsx"), _NEXTJS)
    rules = {v.rule for v in findings}
    assert rules == {"A11Y125", "A11Y126", "A11Y127", "A11Y128"}
    assert all(v.file == "pages/accessibility.tsx" for v in findings)


# frob:tests src/frob/webapp/_a11y_statement.py::a11y_findings kind="unit"
def test_a11y_findings_non_statement_file_is_always_quiet():
    """MUST-STAY-QUIET (regression, T-5454): called on a file that is NOT
    the statement page, reports nothing at all -- this hook deliberately
    never reports "no statement page exists anywhere in this repo" from a
    single per-file call (module docstring's "known gap" section: an
    earlier `Path.cwd()`-approximated version of that check falsely fired
    on unrelated files in a sibling hook's own gate test)."""
    root = _FIXTURE_ROOT / "missing"
    findings = a11y_findings(_ctx(root, "pages/index.tsx"), _NEXTJS)
    assert findings == ()


# frob:tests src/frob/webapp/_a11y_statement.py::_locate_statement_page kind="unit"
def test_locate_statement_page_explicit_root():
    """`_locate_statement_page` (an explicit-root helper, never called
    from the hook itself) correctly distinguishes a repo that has the
    candidate page on disk from one that does not."""
    from frob.webapp._a11y_statement import _locate_statement_page

    assert _locate_statement_page(_FIXTURE_ROOT / "complete", _NEXTJS) is True
    assert _locate_statement_page(_FIXTURE_ROOT / "missing", _NEXTJS) is False


# frob:tests src/frob/webapp/_a11y_statement.py::a11y_findings kind="unit"
def test_a11y_findings_no_frameworks_short_circuits_to_empty():
    """An empty `frameworks` set skips scanning entirely, matching the
    T-5302 short-circuit posture every other WEBSEC/COMPLY/A11Y/SEO
    family hook takes."""
    root = _FIXTURE_ROOT / "complete"
    findings = a11y_findings(_ctx(root, "pages/accessibility.tsx"), frozenset())
    assert findings == ()


def _init_repo(tmp_path: Path) -> None:
    """Shared git scaffolding for a throwaway a11y_gate fixture repo --
    same shape `tests/unit/test_webapp_a11y_structure.py::_init_repo`
    already uses for its own real-`a11y_gate`-adjacent test.

    frob:ticket T-5454
    frob:waive DUP001 reason="same 3-line git-init test seed shared by every a11y_gate-adjacent test file, T-5454"
    frob:waive DUP002 reason="same 3-line git-init test seed shared by every a11y_gate-adjacent test file, T-5454"
    """
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)


# frob:tests src/frob/gates/_a11y_gate.py::a11y_gate kind="unit"
def test_a11y_gate_does_not_crash_and_fires_statement_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """MUST-FIRE (regression, T-5454): a11y_gate, run end-to-end over a
    throwaway git repo with a framework marker and a planted, section-
    incomplete accessibility statement page, does NOT raise (the bug this
    ticket fixes -- the gate always calls hooks as `(ctx, frameworks)`,
    never `(root, frameworks)`) and this module's rule fires on the
    planted page at the right file."""
    _init_repo(tmp_path)
    (tmp_path / "package.json").write_text('{"dependencies": {"next": "14.0.0"}}\n')
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "accessibility.tsx").write_text(
        "export default function A() {\n"
        "  return <main>"
        "<p>We are committed to accessibility.</p>"
        "</main>;\n"
        "}\n"
    )
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=tmp_path, check=True)

    monkeypatch.chdir(tmp_path)
    violations = a11y_gate(tmp_path)

    statement_violations = [
        v for v in violations if v.file == "pages/accessibility.tsx"
    ]
    assert statement_violations, "expected at least one missing-section finding"
    assert all(v.rule.startswith("A11Y1") for v in statement_violations)
    # the planted page has the commitment sentence but nothing else -- all
    # four consolidated rule ids still fire (each pairs commitment/standard,
    # contact/limitations, measures/prerequisites, tested -- module
    # docstring's "A11Y125-A11Y128" note) since every OTHER section is
    # missing, including standard which shares A11Y125 with commitment
    assert {"A11Y125", "A11Y126", "A11Y127", "A11Y128"} == {
        v.rule for v in statement_violations
    }
