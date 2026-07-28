"""ADR decision records + DEC gates (T-0004)."""

from __future__ import annotations

from pathlib import Path

from frob.gates import decisions_gate
from frob.gates.decisions import (
    DecisionError,
    _DecisionStatus,
    load_decisions,
)
from frob.graph import build_graph


def _snap(root: Path):
    return build_graph(root, root / ".frob" / "cache.db").danger_ok


def _record(root: Path, ad_id: str, status: str) -> None:
    d = root / "decisions"
    d.mkdir(exist_ok=True)
    (d / f"{ad_id}.md").write_text(
        f"---\nid: {ad_id}\ntitle: Use X\nstatus: {status}\n---\n\nContext and consequences.\n",
        encoding="utf-8",
    )


def test_load_decisions_parses_records(tmp_path):
    # frob:tests src/frob/gates/decisions.py::load_decisions
    _record(tmp_path, "AD-001", "accepted")
    decisions = load_decisions(tmp_path).danger_ok
    assert len(decisions) == 1
    assert decisions[0].status == _DecisionStatus.ACCEPTED


def test_malformed_record_is_err(tmp_path):
    (tmp_path / "decisions").mkdir()
    (tmp_path / "decisions" / "AD-001.md").write_text(
        "no frontmatter", encoding="utf-8"
    )
    result = load_decisions(tmp_path)
    assert result.is_err
    assert result.danger_err == DecisionError.Malformed


def test_dec001_dangling_decision_edge(tmp_path):
    # frob:tests src/frob/gates/__init__.py::decisions_gate
    # frob:tests src/frob/gates/decisions.py::decision_gate
    (tmp_path / "decisions").mkdir()  # exists but empty
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text(
        "# frob:decision AD-042\ndef f():\n    return 1\n", encoding="utf-8"
    )
    violations = decisions_gate(tmp_path, _snap(tmp_path))
    assert any(v.rule == "DEC001" and "AD-042" in v.message for v in violations)


# invariant spec: [INV-010](invariants/INV-010.md)
def test_dec002_accepted_decision_unanchored(tmp_path):
    _record(tmp_path, "AD-001", "accepted")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    violations = decisions_gate(tmp_path, _snap(tmp_path))
    assert any(v.rule == "DEC002" and "AD-001" in v.message for v in violations)


def test_accepted_and_anchored_passes(tmp_path):
    _record(tmp_path, "AD-001", "accepted")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text(
        "# frob:decision AD-001\ndef f():\n    return 1\n", encoding="utf-8"
    )
    violations = decisions_gate(tmp_path, _snap(tmp_path))
    assert violations == ()


def test_no_decisions_dir_skips(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    assert decisions_gate(tmp_path, _snap(tmp_path)) == ()


def _git_init(root: Path) -> None:
    """Minimal git repo bootstrap for T-0894's adopted-then-deleted
    check (mirrors tests/test_gates.py's own `_git_init` helper)."""
    import subprocess

    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / ".gitkeep").write_text("")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=root, check=True)


# frob:ticket T-0894
def test_never_adopted_decisions_dir_is_silent(tmp_path):
    """A `decisions/` dir that never existed in this branch's history
    stays silent -- DEC003 must not fire on a genuinely never-adopted
    decision-record set, only on one that existed and was deleted."""
    _git_init(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    violations = decisions_gate(tmp_path, _snap(tmp_path))
    assert not any(v.rule == "DEC003" for v in violations)


# frob:ticket T-0894
def test_deleted_after_adoption_fires_dec003(tmp_path):
    """T-0894: a `decisions/` dir committed once and then deleted fires
    DEC003 (unwaivable) rather than silently degrading to the
    "never adopted" empty-tuple posture."""
    import subprocess

    _git_init(tmp_path)
    _record(tmp_path, "AD-001", "accepted")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "adopt decisions"], cwd=tmp_path, check=True
    )
    (tmp_path / "decisions" / "AD-001.md").unlink()
    (tmp_path / "decisions").rmdir()

    violations = decisions_gate(tmp_path, _snap(tmp_path))

    assert any(v.rule == "DEC003" for v in violations)
