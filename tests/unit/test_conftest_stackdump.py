"""T-1433: unit coverage for `tests/conftest.py`'s `SIGUSR1` stack-dump
handler -- the between-tests/session-teardown wedge diagnostic the two
`make coverage` incidents actually needed (pytest's own per-test
`--timeout` watchdog cannot reach that state; see T-1433's ticket body)."""

from __future__ import annotations

import importlib
import importlib.util
import os
import signal
import sys
from pathlib import Path

import pytest

if sys.platform == "win32":  # pragma: no cover - POSIX-only feature
    pytest.skip("SIGUSR1 is POSIX-only", allow_module_level=True)

_CONFTEST_PATH = Path(__file__).resolve().parent.parent / "conftest.py"


# frob:waive WIRE001 reason="a private test-fixture helper used only by \
# TestStackdumpHandler's own methods below, in this same file -- there is no \
# production caller to wire it to by design, it exists solely to load \
# tests/conftest.py as a standalone module for direct unit testing" follow_up="T-1466"
def _load_conftest():
    """Import `tests/conftest.py` as a standalone module (not via pytest's
    own plugin machinery, which already has it loaded once as a fixture
    provider) so these tests can call its private stack-dump helpers
    directly without depending on pytest's conftest-import identity."""
    spec = importlib.util.spec_from_file_location(
        "_t1433_conftest_under_test", _CONFTEST_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestStackdumpHandler:
    """T-1433: `_install_stackdump_handler`/`_dump_all_thread_stacks`."""

    # frob:tests tests/unit/test_conftest_stackdump.py::TestStackdumpHandler.test_sigusr1_writes_all_thread_stacks_when_enabled  # noqa: E501
    def test_sigusr1_writes_all_thread_stacks_when_enabled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With `FROB_COVERAGE_STACKDUMP=1` set, installing the handler and
        then raising `SIGUSR1` in-process writes a `.frob/stackdumps/
        pid-<pid>.txt` file containing a recognizable stack-dump marker --
        the exact artifact a coordinator investigating a wedge would go
        looking for."""
        module = _load_conftest()
        monkeypatch.setenv(module._STACKDUMP_ENV, "1")
        monkeypatch.chdir(tmp_path)
        previous = signal.getsignal(signal.SIGUSR1)
        try:
            module._install_stackdump_handler()
            os.kill(os.getpid(), signal.SIGUSR1)
            dump_path = tmp_path / ".frob" / "stackdumps" / f"pid-{os.getpid()}.txt"
            assert dump_path.is_file(), list((tmp_path / ".frob").rglob("*"))
            content = dump_path.read_text(encoding="utf-8")
            assert "SIGUSR1 stack dump" in content
            assert str(os.getpid()) in content
        finally:
            signal.signal(signal.SIGUSR1, previous)

    # frob:tests tests/unit/test_conftest_stackdump.py::TestStackdumpHandler.test_handler_not_installed_when_env_unset  # noqa: E501
    def test_handler_not_installed_when_env_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without `FROB_COVERAGE_STACKDUMP` set (the default for an
        ordinary `pytest`/`frob test` invocation), installing must be a
        no-op -- the default handler (whatever it was before) stays in
        place, so an unrelated `SIGUSR1` sender is not silently
        intercepted by a debug-only feature."""
        module = _load_conftest()
        monkeypatch.delenv(module._STACKDUMP_ENV, raising=False)
        previous = signal.getsignal(signal.SIGUSR1)
        try:
            module._install_stackdump_handler()
            assert signal.getsignal(signal.SIGUSR1) is previous
        finally:
            signal.signal(signal.SIGUSR1, previous)


class TestSelfScanHeavyGrouping:
    """T-1433: `pytest_collection_modifyitems`'s full-repo self-scan
    xdist-group forcing -- the mitigation for the root-caused "node down:
    Not properly terminated" worker deaths (kernel OOM-kill, no
    faulthandler fault trace captured, matching an uncatchable SIGKILL)."""

    # frob:tests tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping.test_self_scan_heavy_tests_share_one_xdist_group  # noqa: E501
    def test_self_scan_heavy_tests_share_one_xdist_group(self) -> None:
        """A collected item whose name matches one of the known full-repo
        self-scan tests gets the SAME `xdist_group` marker as the others --
        the exact grouping that makes `--dist=loadgroup` schedule them
        onto one worker sequentially instead of several workers at once."""
        module = _load_conftest()

        class _FakeItem:
            def __init__(self, name: str) -> None:
                self.name = name
                self.own_markers: list = []

            def add_marker(self, marker) -> None:  # noqa: ANN001
                self.own_markers.append(marker)

        items = [
            _FakeItem("test_sys_gate_zero_violations"),
            _FakeItem("test_repo_design_and_declarations_are_self_conformant"),
            _FakeItem("test_repo_unrestricted_scan_is_clean"),
            _FakeItem("test_something_unrelated"),
        ]
        module.pytest_collection_modifyitems(config=None, items=items)

        group_names = set()
        for item in items[:3]:
            assert len(item.own_markers) == 1, item.name
            marker = item.own_markers[0]
            assert marker.name == "xdist_group"
            group_names.add(marker.kwargs["name"])
        assert group_names == {"frob_self_scan_heavy"}
        assert items[3].own_markers == []
