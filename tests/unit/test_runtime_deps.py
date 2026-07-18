"""Drift-lock: every unguarded top-level third-party import in src/frob
must be declared in [project].dependencies (T-0152).

A dep that resolves only through the dev group works under `uv run` but
crashes a bare wheel install at import time (the T-0152 incident:
packaging was dev-only while frob.vet._cve imported it at module level).
This test fails in CI the moment a new undeclared import lands.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SRC = _REPO / "src" / "frob"

# import name -> distribution name as it appears in [project].dependencies
_DIST_FOR_IMPORT = {
    "typani": "typani",
    "pydantic": "pydantic",
    "tree_sitter": "tree-sitter",
    "tree_sitter_python": "tree-sitter-python",
    "tree_sitter_cpp": "tree-sitter-cpp",
    "tree_sitter_language_pack": "tree-sitter-language-pack",
    "yaml": "pyyaml",
    "jinja2": "jinja2",
    "packaging": "packaging",
}

# imports that are intentionally NOT runtime deps: optional extras (their
# import sites must be guarded), and the in-repo native crates.
_ALLOWED_UNDECLARED = {
    "z3",  # frob[smt] extra; probe_smt_equivalence guards the import
    "strata_core",  # local native crate, shipped with the wheel build
    "frob_core",  # local native crate, shipped with the wheel build
    "frob",  # self-imports
}


def _declared_dists() -> set[str]:
    # frob:ticket T-0152
    with (_REPO / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)
    deps = data["project"]["dependencies"]
    return {d.split(">")[0].split("=")[0].split("<")[0].strip() for d in deps}


def _top_level_imports(path: Path) -> set[str]:
    # frob:ticket T-0152
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in tree.body:  # module body only: guarded/lazy imports excluded
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
    return found


class TestRuntimeDepsDeclared:
    # frob:tests src/frob/vet/_cve.py
    # frob:ticket T-0152

    def test_every_unguarded_third_party_import_is_declared(self) -> None:
        declared = _declared_dists()
        missing: dict[str, set[str]] = {}
        for path in sorted(_SRC.rglob("*.py")):
            for name in _top_level_imports(path):
                if name in sys.stdlib_module_names or name in _ALLOWED_UNDECLARED:
                    continue
                dist = _DIST_FOR_IMPORT.get(name)
                if dist is None or dist not in declared:
                    missing.setdefault(name, set()).add(str(path.relative_to(_REPO)))
        assert not missing, (
            "unguarded top-level imports with no [project].dependencies "
            f"declaration (add the dep or guard the import): {missing}"
        )

    def test_packaging_regression_is_locked(self) -> None:
        # The exact T-0152 incident: packaging imported by vet._cve.
        assert "packaging" in _declared_dists()
        assert "packaging" in _top_level_imports(_SRC / "vet" / "_cve.py")
