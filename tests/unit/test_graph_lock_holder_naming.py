"""Tests for `frob.graph.cache`'s lock-holder naming (T-4282).

Kept in its own small file rather than `tests/unit/test_graph_cache.py`:
that file's own pre-existing, unrelated test classes carry heavy
private-helper fan-out into dozens of other modules, and scoping it into
this narrow ticket pulled in that whole unrelated closure (measured via
`frob check --ticket T-4282 --only scope`: adding it produced ~80 SCOPE002
"probable under-capture" findings across files this ticket never touches).
A fresh, minimal file has no such history to drag in.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from frob.graph import cache as graph_cache


# frob:ticket T-4282
class TestLockHolderNaming:
    """T-4282 obligation [2]: a `CacheLocked` raised once the retry budget
    is exhausted must NAME the holding process, not just report "database
    is locked" -- the missing detail that sent the T-4258 incident's
    investigation down a corruption hypothesis before the real holder was
    found by hand-inspecting file descriptors."""

    # frob:tests src/frob/graph/cache.py::_lock_holder_pids_linux
    def test_lock_holder_pids_linux_finds_a_real_open_fd(self, tmp_path: Path) -> None:
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux-only /proc probe")
        target = tmp_path / "held.txt"
        target.write_text("x")
        proc = subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                "-c",
                f"f = open({str(target)!r}); import time; time.sleep(5)",
            ],
        )
        try:
            deadline = time.monotonic() + 4.0
            pids: tuple[int, ...] = ()
            while time.monotonic() < deadline:
                pids = graph_cache._lock_holder_pids_linux(target)
                if pids:
                    break
                time.sleep(0.05)
            assert proc.pid in pids
        finally:
            proc.kill()
            proc.wait()

    # frob:tests src/frob/graph/cache.py::_lock_holder_pids_linux
    def test_lock_holder_pids_excludes_self(self, tmp_path: Path) -> None:
        if not sys.platform.startswith("linux"):
            pytest.skip("Linux-only /proc probe")
        target = tmp_path / "held.txt"
        handle = target.open("w")
        try:
            assert os.getpid() not in graph_cache._lock_holder_pids_linux(target)
        finally:
            handle.close()

    # frob:tests src/frob/graph/cache.py::_describe_lock_holders
    def test_describe_lock_holders_reports_pid_and_command(self, monkeypatch) -> None:
        monkeypatch.setattr(graph_cache, "_lock_holder_pids", lambda path: (4242,))  # noqa: ARG005
        monkeypatch.setattr(
            graph_cache, "_holder_cmdline", lambda pid: "frob serve --root /repo"  # noqa: ARG005
        )
        desc = graph_cache._describe_lock_holders(Path("/fake/cache.db"))
        assert "4242" in desc
        assert "frob serve --root /repo" in desc

    # frob:tests src/frob/graph/cache.py::_describe_lock_holders
    def test_describe_lock_holders_degrades_without_a_path(self) -> None:
        assert "holder unknown" in graph_cache._describe_lock_holders(None)

    # frob:tests src/frob/graph/cache.py::_describe_lock_holders
    def test_describe_lock_holders_degrades_with_no_pid_found(self, monkeypatch) -> None:
        monkeypatch.setattr(graph_cache, "_lock_holder_pids", lambda path: ())  # noqa: ARG005
        desc = graph_cache._describe_lock_holders(Path("/fake/cache.db"))
        assert "no process found" in desc

    # frob:tests src/frob/graph/cache.py::_with_lock_retry
    def test_with_lock_retry_names_holder_in_cache_locked_message(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr(graph_cache, "_lock_holder_pids", lambda path: (4242,))  # noqa: ARG005
        monkeypatch.setattr(
            graph_cache, "_holder_cmdline", lambda pid: "frob serve --root /repo"  # noqa: ARG005
        )
        monkeypatch.setattr(graph_cache, "_LOCK_TOTAL_TIMEOUT_SECONDS", 0.03)

        def _always_locked() -> None:
            raise sqlite3.OperationalError("database is locked")

        try:
            graph_cache._with_lock_retry(
                _always_locked, what="test-op", path=Path("/fake/cache.db")
            )
        except graph_cache.CacheLocked as exc:
            assert "4242" in str(exc)
            assert "frob serve --root /repo" in str(exc)
        else:
            raise AssertionError("expected CacheLocked to be raised")

    # frob:tests src/frob/graph/cache.py::_with_lock_retry
    def test_with_lock_retry_states_holder_unknown_without_a_path(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr(graph_cache, "_LOCK_TOTAL_TIMEOUT_SECONDS", 0.03)

        def _always_locked() -> None:
            raise sqlite3.OperationalError("database is locked")

        try:
            graph_cache._with_lock_retry(_always_locked, what="test-op")
        except graph_cache.CacheLocked as exc:
            assert "holder unknown" in str(exc)
        else:
            raise AssertionError("expected CacheLocked to be raised")

    # frob:tests src/frob/graph/cache.py::_connect_with_backoff
    def test_connect_with_backoff_raises_cache_locked_naming_holder(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        cache = tmp_path / "cache.db"
        monkeypatch.setattr(graph_cache, "_lock_holder_pids", lambda path: (9999,))  # noqa: ARG005
        monkeypatch.setattr(graph_cache, "_holder_cmdline", lambda pid: None)  # noqa: ARG005
        monkeypatch.setattr(graph_cache, "_LOCK_TOTAL_TIMEOUT_SECONDS", 0.03)

        def _always_locked(*_args, **_kwargs):  # noqa: ANN002, ANN003, ANN202
            # A real `sqlite3.connect(..., timeout=T)` busy-waits internally
            # for up to T seconds before raising -- this mock stands in for
            # that wait so `_connect_with_backoff`'s deadline is actually
            # reached in finite iterations, instead of spinning forever
            # because no wall-clock time ever passes between attempts.
            time.sleep(0.005)
            raise sqlite3.OperationalError("database is locked")

        monkeypatch.setattr(graph_cache.sqlite3, "connect", _always_locked)
        try:
            graph_cache._connect_with_backoff(cache)
        except graph_cache.CacheLocked as exc:
            assert "9999" in str(exc)
        else:
            raise AssertionError("expected CacheLocked to be raised")
