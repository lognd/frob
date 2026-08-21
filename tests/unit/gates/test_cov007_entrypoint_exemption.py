"""T-2551: COV007's declared-entrypoint exemption, pinned in both
directions.

The exemption is keyed on the project's own `[[refs.entrypoint]]`
declaration (a per-file statement carrying a mandatory reason), never on a
path shape like `.claude/hooks/*` -- a glob exemption silently mutes the
rule for every file a directory later grows, which is this repo's own
"an exemption matching the normal case disables the guard" failure.

Lives in its own file rather than tests/test_gates.py because that file is
under another in-progress ticket's write lease.
"""

from __future__ import annotations

from pathlib import Path

from frob.gates import coverage_gate
from frob.gitio import Diff
from frob.graph import build_graph
from frob.testing import CollectedTests
from frob.tickets import TicketQueue

_PRIVATE_HELPER_WITH_ANCHOR = (
    'def _helper(x):\n    """helper"""\n    # frob:doc docs/x.md#helper\n    return x\n'
)


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parents -- local test helper."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _cov007_rules(root: Path) -> list[str]:
    """Every COV007 rule id `coverage_gate` reports for the tree at `root`."""
    snapshot = build_graph(root, root / ".frob" / "cache.db").danger_ok
    violations = coverage_gate(
        root,
        snapshot,
        TicketQueue(tickets={}),
        Diff(base="x", hunks=()),
        CollectedTests(node_ids=frozenset()),
    )
    return [v.rule for v in violations if v.rule == "COV007"]


def _seed_executable(root: Path) -> None:
    """A python executable carrying a doc anchor on a private helper."""
    _write(root, "scripts/tool.py", _PRIVATE_HELPER_WITH_ANCHOR)
    _write(root, "docs/x.md", "# Helper\n")


# frob:ticket T-2551
class TestCov007EntrypointExemption:
    """T-2551: a DECLARED executable is exempt; an undeclared one is not."""

    def test_declared_entrypoint_is_exempt(self, tmp_path: Path) -> None:
        """An executable is run, never imported, so it has no importable
        public surface for COV007's remedy to move the anchor onto."""
        # frob:tests src/frob/gates/__init__.py::_cov007
        _seed_executable(tmp_path)
        _write(
            tmp_path,
            "frob.toml",
            "[[refs.entrypoint]]\n"
            'path = "scripts/tool.py"\n'
            'reason = "run by a human, never imported"\n',
        )
        assert _cov007_rules(tmp_path) == []

    def test_same_file_undeclared_still_fires(self, tmp_path: Path) -> None:
        """Byte-identical tree minus the declaration: the exemption is keyed
        on the stated fact, so an undeclared sibling in the same directory
        is NOT muted."""
        # frob:tests src/frob/gates/__init__.py::_cov007
        _seed_executable(tmp_path)
        _write(tmp_path, "frob.toml", "[dup]\nenforce = false\n")
        assert _cov007_rules(tmp_path) == ["COV007"]

    def test_library_module_still_fires_when_another_file_is_declared(
        self, tmp_path: Path
    ) -> None:
        """A declaration exempts ONLY the file it names -- a library module
        with a private doc anchor still fires alongside it."""
        # frob:tests src/frob/gates/__init__.py::_cov007
        _seed_executable(tmp_path)
        _write(tmp_path, "src/lib.py", _PRIVATE_HELPER_WITH_ANCHOR)
        _write(
            tmp_path,
            "frob.toml",
            "[[refs.entrypoint]]\n"
            'path = "scripts/tool.py"\n'
            'reason = "run by a human, never imported"\n',
        )
        assert _cov007_rules(tmp_path) == ["COV007"]
