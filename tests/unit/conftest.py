# frob:ticket T-1511
"""Shared `tests/unit/**` test-support fixtures/stand-ins. `pytest.fixture`
functions here are auto-injected by pytest's own conftest discovery; plain
classes (e.g. `_FakeCompletedProcess`) are NOT auto-injected and must be
imported explicitly (`from tests.unit.conftest import _FakeCompletedProcess`)
-- `tests/` is a real package (`tests/__init__.py`), so this is a normal
absolute import, not pytest plugin machinery."""

from __future__ import annotations


# frob:ticket T-1511
class _FakeCompletedProcess:
    """Minimal `subprocess.CompletedProcess`-shaped stand-in for a
    monkeypatched `guarded_subprocess_run` return -- promoted here from two
    identical per-file copies (`tests/unit/test_check_ts_runners.py`,
    `tests/unit/test_check_native_cargo_runners.py`) once a second consumer
    confirmed the duplication (T-1511's own follow-up criterion: "if more
    runner tests want the same stub")."""

    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
