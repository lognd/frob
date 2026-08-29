"""Unit tests for `frob.lang._extract.extract_import_edges` /
`frob.lang.extract_import_edges` (docs/modules/lang.md#extraction-api).

T-3417: `extract_import_edges` is the function CYCLE001's import
graph (`frob.check._python._build_import_graph`, `frob.app.cycle_runner`)
relies on to decide which edges are import-time vs. deferred (T-3350) --
correctness here decides whether the cycle detector counts an edge at all,
so it needs direct unit coverage of the `import_time` flag independent of
the system-level positive-control fixtures already committed in
tests/system/test_cli_cycle.py. Covers all six shapes the flag must
distinguish: module-level (import_time=True), function-local
(import_time=False), class-body (import_time=False), `if TYPE_CHECKING:`
(import_time=False), module-level inside `try:`/`except ImportError:`
(STILL import_time=True -- the block runs unconditionally at import time),
and a module-level `if sys.version_info:` guard (STILL import_time=True --
same reasoning)."""

from __future__ import annotations

from pathlib import Path

from frob.lang import extract_import_edges, raw_tree
from frob.lang._extract import extract_import_edges as extract_import_edges_tree


def _edges_for(tmp_path: Path, source: str) -> tuple[tuple[str, bool], ...]:
    """`extract_import_edges` over `source` written to a scratch `sample.py`,
    exercised through BOTH the tree-level and path-level entry points to
    confirm they agree (mirrors test_lang_primitives.py's tree/path pairing
    for `extract_imports`)."""
    path = tmp_path / "sample.py"
    path.write_text(source)
    tree, _src, lang = raw_tree(path).danger_ok
    tree_edges = extract_import_edges_tree(tree, lang)
    path_edges = extract_import_edges(path).danger_ok
    assert tree_edges == path_edges
    return tree_edges


def test_module_level_import_is_import_time(tmp_path: Path):
    # frob:tests src/frob/lang/_extract.py::extract_import_edges kind="unit"
    # frob:tests src/frob/lang/__init__.py::extract_import_edges kind="unit"
    """A plain top-level `import os` is import_time=True."""
    edges = _edges_for(tmp_path, "import os\n")
    assert ("os", True) in edges


def test_function_local_import_is_deferred(tmp_path: Path):
    # frob:tests src/frob/lang/_extract.py::extract_import_edges kind="unit"
    """An import inside a function body is import_time=False -- deferring
    is the standard remedy for a cycle, not a second occurrence of one."""
    edges = _edges_for(tmp_path, "def use():\n    import os\n    return os\n")
    assert ("os", False) in edges
    assert ("os", True) not in edges


def test_class_body_import_is_deferred(tmp_path: Path):
    # frob:tests src/frob/lang/_extract.py::extract_import_edges kind="unit"
    """An import directly in a class body (not a method) is also
    import_time=False -- it executes only when the class statement itself
    runs, which this repo's scope-depth walk treats the same as any other
    deferring scope."""
    edges = _edges_for(tmp_path, "class Foo:\n    import os\n")
    assert ("os", False) in edges
    assert ("os", True) not in edges


def test_type_checking_import_is_deferred(tmp_path: Path):
    # frob:tests src/frob/lang/_extract.py::extract_import_edges kind="unit"
    """`if TYPE_CHECKING:` never executes at runtime, so its import is
    import_time=False."""
    edges = _edges_for(
        tmp_path,
        "from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    import os\n",
    )
    assert ("os", False) in edges
    assert ("os", True) not in edges


def test_dotted_type_checking_import_is_deferred(tmp_path: Path):
    # frob:tests src/frob/lang/_extract.py::extract_import_edges kind="unit"
    """`if typing.TYPE_CHECKING:` (dotted form) is recognized the same as
    the bare-name form."""
    edges = _edges_for(
        tmp_path, "import typing\n\nif typing.TYPE_CHECKING:\n    import os\n"
    )
    assert ("os", False) in edges
    assert ("os", True) not in edges


def test_try_except_import_error_is_import_time(tmp_path: Path):
    # frob:tests src/frob/lang/_extract.py::extract_import_edges kind="unit"
    """A module-level `try:`/`except ImportError:` import runs
    unconditionally at import time (only its OUTCOME is conditional), so
    it is import_time=True -- NOT exempt the way `if TYPE_CHECKING:` is."""
    edges = _edges_for(
        tmp_path, "try:\n    import os\nexcept ImportError:\n    os = None\n"
    )
    assert ("os", True) in edges
    assert ("os", False) not in edges


def test_sys_version_info_guarded_import_is_import_time(tmp_path: Path):
    # frob:tests src/frob/lang/_extract.py::extract_import_edges kind="unit"
    """A module-level `if sys.version_info:` guarded import also runs at
    import time (conditionally, but still while the module is loading), so
    it is import_time=True -- only a `TYPE_CHECKING` guard is exempt."""
    edges = _edges_for(
        tmp_path,
        "import sys\n\nif sys.version_info >= (3, 11):\n    import os\n",
    )
    assert ("os", True) in edges
    assert ("os", False) not in edges


def test_mixed_module_and_deferred_import_of_the_same_name(tmp_path: Path):
    # frob:tests src/frob/lang/_extract.py::extract_import_edges kind="unit"
    """When the SAME module is imported both at module level and again
    inside a function, both edges are reported -- one True, one False --
    rather than collapsing to a single import_time value."""
    edges = _edges_for(
        tmp_path, "import os\n\ndef use():\n    import os\n    return os\n"
    )
    assert ("os", True) in edges
    assert ("os", False) in edges
