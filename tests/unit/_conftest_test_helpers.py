"""Shared helper for tests that need `tests/conftest.py` loaded as a
standalone module (T-3252): DUP001 consolidation of the identical loader
`tests/unit/test_conftest_stackdump.py` and `tests/unit/test_conftest_
suite_result_status.py` each carried independently before this file
existed -- see `load_conftest_module`'s own docstring for why a standalone
import is needed at all.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

_CONFTEST_PATH = Path(__file__).resolve().parent.parent / "conftest.py"


def load_conftest_module(module_name: str) -> ModuleType:
    """Import `tests/conftest.py` as a standalone module (not via pytest's
    own plugin machinery, which already has it loaded once as a fixture
    provider) so a test can call its private/internal hooks directly
    against a FRESH module instance, without depending on pytest's own
    conftest-import identity or leaking state between call sites.

    `module_name` must be unique per caller (e.g. `"_t1433_conftest_under_
    test"`, `"_t3246_conftest_under_test"`) -- `importlib.util.spec_from_
    file_location` registers it as a real entry importable machinery could
    otherwise collide on if two callers reused the same name."""
    spec = importlib.util.spec_from_file_location(module_name, _CONFTEST_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
