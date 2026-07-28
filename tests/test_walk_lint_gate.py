"""Tests for frob.gates._walk_lint -- WALK001
(docs/modules/gates.md#walk001-unpruned-traversal-t-0471).

Fixture snippets below are synthetic `tempfile`-backed git repos, same
posture as `tests/test_pii_structural_gate.py`.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

from frob.gates._walk_lint import _scan_python_walks, walk_lint_gate


# frob:waive DUP001 reason="parallel per-domain test scaffolding across 9 sibling test modules \
# (9 sites) -- each file exercises a structurally similar check for \
# a distinct domain/module with the same arrange-act shape; \
# extracting would blur which domain owns which check"
def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "checkout", "-q", "-b", "main")


def _commit(root: Path, message: str = "commit") -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


class TestRglob:
    """WALK001: raw `Path.rglob` always fires (unconditionally recursive)."""

    # invariant spec: [INV-005](invariants/INV-005.md)
    def test_raw_rglob_fires(self) -> None:
        # frob:tests src/frob/gates/_walk_lint.py::_scan_python_walks
        src = "def f(root):\n    return list(root.rglob('*'))\n"
        tree = ast.parse(src)
        sites = _scan_python_walks(tree)
        assert len(sites) == 1
        assert "rglob" in sites[0].call_desc

    def test_gate_fires_on_new_raw_root_rglob(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_walk_lint.py::walk_lint_gate
        _init_repo(tmp_path)
        pkg = tmp_path / "src" / "frob"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "offender.py").write_text(
            "from pathlib import Path\n"
            "\n"
            "def collect(root: Path):\n"
            "    return list(root.rglob('*'))\n"
        )
        _commit(tmp_path)

        violations = walk_lint_gate(tmp_path)

        rules = {v.rule for v in violations}
        assert "WALK001" in rules
        offender_hits = [v for v in violations if v.file == "src/frob/offender.py"]
        assert len(offender_hits) == 1
        assert offender_hits[0].line == 4


class TestConditionalGlob:
    """WALK001: `.glob`/`.iglob` only fire when the pattern is `"**"`-shaped."""

    def test_recursive_glob_pattern_fires(self) -> None:
        # frob:tests src/frob/gates/_walk_lint.py::_scan_python_walks
        src = "def f(root):\n    return list(root.glob('**/*.py'))\n"
        tree = ast.parse(src)
        assert len(_scan_python_walks(tree)) == 1

    def test_non_recursive_glob_pattern_is_silent(self) -> None:
        # frob:tests src/frob/gates/_walk_lint.py::_scan_python_walks
        src = "def f(root):\n    return list(root.glob('*.py'))\n"
        tree = ast.parse(src)
        assert _scan_python_walks(tree) == ()


class TestOsWalk:
    """WALK001: bare `os.walk(...)` fires, dotted or bare-imported."""

    def test_dotted_os_walk_fires(self) -> None:
        # frob:tests src/frob/gates/_walk_lint.py::_scan_python_walks
        src = "import os\n\ndef f(root):\n    return list(os.walk(root))\n"
        tree = ast.parse(src)
        assert len(_scan_python_walks(tree)) == 1

    def test_bare_imported_walk_fires(self) -> None:
        # frob:tests src/frob/gates/_walk_lint.py::_scan_python_walks
        src = "from os import walk\n\ndef f(root):\n    return list(walk(root))\n"
        tree = ast.parse(src)
        assert len(_scan_python_walks(tree)) == 1

    def test_local_function_named_walk_is_not_flagged(self) -> None:
        """A locally-defined recursive function that happens to be named
        `walk` (a tree-sitter-node walker, not `os.walk`) must never fire --
        the real false positive T-0471's dogfooding run caught in
        `frob.vet._capability`."""
        # frob:tests src/frob/gates/_walk_lint.py::_scan_python_walks
        src = (
            "def scan(tree):\n"
            "    def walk(node):\n"
            "        for child in node.children:\n"
            "            walk(child)\n"
            "    walk(tree.root_node)\n"
        )
        tree = ast.parse(src)
        assert _scan_python_walks(tree) == ()

    def test_aliased_os_walk_import_fires(self) -> None:
        # frob:tests src/frob/gates/_walk_lint.py::_scan_python_walks
        src = "from os import walk as w\n\ndef f(root):\n    return list(w(root))\n"
        tree = ast.parse(src)
        assert len(_scan_python_walks(tree)) == 1


class TestHelper:
    """WALK001: a call to the shared `frob.excludes` helper is silent."""

    # frob:waive DUP001 reason="parallel test methods within test_walk_lint_gate.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def test_helper_call_is_silent(self) -> None:
        # frob:tests src/frob/gates/_walk_lint.py::_scan_python_walks
        src = (
            "from frob.excludes import iter_files\n"
            "\n"
            "def f(root):\n"
            "    return iter_files(root, suffix='.py')\n"
        )
        tree = ast.parse(src)
        assert _scan_python_walks(tree) == ()

    # frob:waive DUP001 reason="parallel test methods within test_walk_lint_gate.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def test_walk_pruned_call_is_silent(self) -> None:
        # frob:tests src/frob/gates/_walk_lint.py::_scan_python_walks
        src = (
            "from frob.excludes import walk_pruned\n"
            "\n"
            "def f(root):\n"
            "    return list(walk_pruned(root))\n"
        )
        tree = ast.parse(src)
        assert _scan_python_walks(tree) == ()


class TestSelfMatchExclusion:
    """WALK001 skips its own module and `frob/excludes.py` outright."""

    def test_own_files_not_scanned(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_walk_lint.py::walk_lint_gate
        _init_repo(tmp_path)
        pkg = tmp_path / "src" / "frob" / "gates"
        pkg.mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        (pkg / "__init__.py").write_text("")
        (pkg / "_walk_lint.py").write_text(
            "from pathlib import Path\n"
            "\n"
            "def f(root: Path):\n"
            "    return list(root.rglob('*'))\n"
        )
        excludes_dir = tmp_path / "src" / "frob"
        (excludes_dir / "excludes.py").write_text(
            "import os\n\n\ndef walk_pruned(root):\n"
            "    for entry in os.walk(root):\n        yield entry\n"
        )
        _commit(tmp_path)

        violations = walk_lint_gate(tmp_path)

        assert violations == ()
