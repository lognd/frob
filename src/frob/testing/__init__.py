"""Touched-set test selection and execution across languages (docs/modules/testing.md).

`frob test` is the single entry point that computes what was touched (diff
vs base), selects every test obligated to those symbols via the obligation
graph (`frob.graph`), and runs them through per-language runners -- so "run
the right tests" is one command in any repo, any language, any worktree.
This is the executable counterpart of the TEST gate family: the gates prove
the bindings exist, `frob test` runs the bound tests.
"""

from __future__ import annotations

from frob.testing._collect import (
    collect_python_tests,
    collect_rust_tests,
    drop_collection_cache,
)
from frob.testing._models import (
    CollectedTests,
    NativeSpec,
    RunnerOutcome,
    RunnerSpec,
    SelectConfig,
    SelectionReport,
    TestRunReport,
)
from frob.testing._runners import (
    TestingError,
    load_natives,
    load_runners,
    run_selected,
)
from frob.testing._select import extension_language, select_tests

__all__ = [
    "CollectedTests",
    "NativeSpec",
    "RunnerOutcome",
    "RunnerSpec",
    "SelectConfig",
    "SelectionReport",
    "TestRunReport",
    "TestingError",
    "collect_python_tests",
    "collect_rust_tests",
    "drop_collection_cache",
    "extension_language",
    "load_natives",
    "load_runners",
    "run_selected",
    "select_tests",
]
