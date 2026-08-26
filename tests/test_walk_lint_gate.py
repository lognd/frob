"""Tests for frob.gates._walk_lint -- WALK001
(docs/modules/gates.md#walk001-unpruned-traversal-t-0471).

Fixture snippets below are synthetic `tempfile`-backed git repos, same
posture as `tests/test_pii_structural_gate.py`.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

from frob.gates._walk_lint import (
    _scan_platform_guards,
    _scan_python_walks,
    walk_lint_gate,
)


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


class TestPlatform001:
    """PLATFORM001 (T-2919): a POSIX/Windows-only primitive's absence
    guard must declare a cross-platform path or refuse loudly, never
    warn-and-continue -- the exact shape T-2918 fixed in
    `_rapid_sweep.py::_baseline_lock`."""

    #: The "warn-and-continue" fixture: this is a byte-for-byte MODEL of
    #: `_baseline_lock`'s shape BEFORE T-2918 -- a real platform-optional
    #: primitive whose absence guard logs a warning and proceeds as if
    #: nothing were wrong. This MUST fire.
    _WARN_AND_CONTINUE_SRC = (
        "import importlib\n"
        "from contextlib import contextmanager\n"
        "\n"
        "fcntl = None\n"
        "try:\n"
        "    fcntl = importlib.import_module('fcntl')\n"
        "except ImportError:\n"
        "    fcntl = None\n"
        "\n"
        "@contextmanager\n"
        "def acquire(path):\n"
        "    if fcntl is None:\n"
        "        _log.warning('lock is a NO-OP on this platform')\n"
        "        yield\n"
        "        return\n"
        "    fd = _open(path)\n"
        "    fcntl.flock(fd, fcntl.LOCK_EX)\n"
        "    try:\n"
        "        yield\n"
        "    finally:\n"
        "        fcntl.flock(fd, fcntl.LOCK_UN)\n"
    )

    #: The "loud refusal" fixture: T-2918's OWN real fix shape --
    #: identical probe, but the absence guard raises instead of logging
    #: and falling through. This MUST stay quiet.
    _LOUD_REFUSAL_SRC = (
        "import importlib\n"
        "from contextlib import contextmanager\n"
        "\n"
        "fcntl = None\n"
        "try:\n"
        "    fcntl = importlib.import_module('fcntl')\n"
        "except ImportError:\n"
        "    fcntl = None\n"
        "\n"
        "msvcrt = None\n"
        "try:\n"
        "    msvcrt = importlib.import_module('msvcrt')\n"
        "except ImportError:\n"
        "    msvcrt = None\n"
        "\n"
        "class LockUnavailable(RuntimeError):\n"
        "    pass\n"
        "\n"
        "@contextmanager\n"
        "def acquire(path):\n"
        "    if fcntl is None and msvcrt is None:\n"
        "        raise LockUnavailable('no lock primitive on this platform')\n"
        "    yield\n"
    )

    def test_warn_and_continue_fires(self) -> None:
        # frob:tests src/frob/gates/_walk_lint.py::_scan_platform_guards
        tree = ast.parse(self._WARN_AND_CONTINUE_SRC)
        sites = _scan_platform_guards(tree)
        assert len(sites) == 1
        assert sites[0].names == ("fcntl",)

    def test_loud_refusal_is_quiet(self) -> None:
        # frob:tests src/frob/gates/_walk_lint.py::_scan_platform_guards
        tree = ast.parse(self._LOUD_REFUSAL_SRC)
        assert _scan_platform_guards(tree) == ()

    def test_no_platform_probe_is_quiet(self) -> None:
        """A module with no restricted-module try/except-ImportError probe
        at all has nothing for PLATFORM001 to anchor on, regardless of
        what its `if X is None:` guards do."""
        # frob:tests src/frob/gates/_walk_lint.py::_scan_platform_guards
        src = (
            "z3 = None\n"
            "try:\n"
            "    import z3\n"
            "except ImportError:\n"
            "    z3 = None\n"
            "\n"
            "def f():\n"
            "    if z3 is None:\n"
            "        _log.warning('z3 unavailable, skipping SMT check')\n"
            "        return\n"
        )
        tree = ast.parse(src)
        assert _scan_platform_guards(tree) == ()

    def test_gate_fires_end_to_end(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_walk_lint.py::walk_lint_gate
        _init_repo(tmp_path)
        pkg = tmp_path / "src" / "frob"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "offender.py").write_text(self._WARN_AND_CONTINUE_SRC)
        _commit(tmp_path)

        violations = walk_lint_gate(tmp_path)

        platform_hits = [v for v in violations if v.rule == "PLATFORM001"]
        assert len(platform_hits) == 1
        assert platform_hits[0].file == "src/frob/offender.py"

    def test_gate_stays_quiet_on_properly_guarded_module(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_walk_lint.py::walk_lint_gate
        _init_repo(tmp_path)
        pkg = tmp_path / "src" / "frob"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "guarded.py").write_text(self._LOUD_REFUSAL_SRC)
        _commit(tmp_path)

        violations = walk_lint_gate(tmp_path)

        assert not any(v.rule == "PLATFORM001" for v in violations)

    #: T-2934: the real false positive measured on
    #: `frob.tickets._land_git_ops.reclaim_orphaned_squash_residue` --
    #: logs, then takes a typed `Ok(False)` exit (typani convention)
    #: instead of continuing as if the missing primitive did not matter.
    #: This MUST stay quiet.
    _TYPED_RESULT_REFUSAL_SRC = (
        "import importlib\n"
        "from typani import Ok\n"
        "\n"
        "_fcntl = None\n"
        "try:\n"
        "    _fcntl = importlib.import_module('fcntl')\n"
        "except ImportError:\n"
        "    _fcntl = None\n"
        "\n"
        "def reclaim(root):\n"
        "    if _fcntl is None:\n"
        "        _log.warning('cannot safely reclaim without fcntl')\n"
        "        return Ok(False)\n"
        "    return Ok(True)\n"
    )

    def test_typed_result_refusal_is_quiet(self) -> None:
        """T-2934: `return Ok(False)` (a real, controlled abort) must not
        fire -- only a plain `return`/fallthrough with no typed
        constructor is a true warn-and-continue."""
        # frob:tests src/frob/gates/_walk_lint.py::_scan_platform_guards
        tree = ast.parse(self._TYPED_RESULT_REFUSAL_SRC)
        assert _scan_platform_guards(tree) == ()

    def test_typed_err_refusal_is_quiet(self) -> None:
        # frob:tests src/frob/gates/_walk_lint.py::_scan_platform_guards
        src = self._TYPED_RESULT_REFUSAL_SRC.replace(
            "from typani import Ok", "from typani import Err"
        ).replace("return Ok(False)", "return Err('unavailable')")
        tree = ast.parse(src)
        assert _scan_platform_guards(tree) == ()

    def test_plain_return_with_no_typed_constructor_still_fires(self) -> None:
        """Guards against over-narrowing: a bare `return`/`return None`
        with no `Ok`/`Err` wrapper is NOT a typed exit and must still
        fire -- this is exactly `_WARN_AND_CONTINUE_SRC`'s own shape,
        re-asserted here as a negative control on the narrowing itself."""
        # frob:tests src/frob/gates/_walk_lint.py::_scan_platform_guards
        src = (
            "import importlib\n"
            "\n"
            "fcntl = None\n"
            "try:\n"
            "    fcntl = importlib.import_module('fcntl')\n"
            "except ImportError:\n"
            "    fcntl = None\n"
            "\n"
            "def f():\n"
            "    if fcntl is None:\n"
            "        _log.warning('degraded')\n"
            "        return\n"
        )
        tree = ast.parse(src)
        assert len(_scan_platform_guards(tree)) == 1
