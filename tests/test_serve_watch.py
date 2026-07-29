"""Tests for `frob.serve._watch` (T-1094): the FS-watch push invalidation
layer over `frob.serve._warm`'s pull-based warm-state cache.
"""

from __future__ import annotations

import time
from pathlib import Path

from frob.serve import _warm
from frob.serve._watch import WatchThread, watch_tick

# DUP001: reuse test_serve.py's own fixtures rather than duplicating them --
# both files build the same "one tracked file, one git-init'd repo" shape.
from tests.test_serve import _git_init, _write

_SAMPLE_PY = (
    '"""Module docstring."""\n\n\n'
    "def helper(x):\n"
    "    # frob:doc docs/x.md#helper\n"
    "    return x\n"
)


class TestWatchTick:
    def test_no_change_leaves_state_cached(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_serve_watch.py::TestWatchTick.test_no_change_leaves_state_cached
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        _warm._invalidate(tmp_path)

        first_key, first_changed = watch_tick(tmp_path, None)
        assert first_changed is False

        second_key, second_changed = watch_tick(tmp_path, first_key)
        assert second_changed is False
        assert second_key == first_key

    def test_change_invalidates_and_prewarms(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_serve_watch.py::TestWatchTick.test_change_invalidates_and_prewarms
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        _warm._invalidate(tmp_path)

        key, _ = watch_tick(tmp_path, None)
        cached_before = _warm._STATES.get(str(tmp_path.resolve()))
        assert cached_before is not None

        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY + "\n# edited\n")
        new_key, changed = watch_tick(tmp_path, key)

        assert changed is True
        assert new_key != key
        # The tick pre-warmed the cache itself -- a subsequent pull-path
        # call must hit it, not rebuild again.
        cached_after = _warm._STATES.get(str(tmp_path.resolve()))
        assert cached_after is not None
        assert cached_after.dirty_key == new_key

    def test_watch_tick_never_disagrees_with_pull_signal(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_serve_watch.py::TestWatchTick.test_watch_tick_never_disagrees_with\
        # _pull_signal
        # Differential harness (T-1094 acceptance [1]): across a
        # randomized sequence of edits, watch_tick's own "changed" verdict
        # must always agree with directly comparing two independent
        # _repo_dirty_key calls bracketing the same edit -- the exact
        # signal the pull path (frob.serve._warm._warm_state) checks on
        # every client query. This holds by construction (watch_tick
        # calls the identical function), but is exercised here on the real
        # code path rather than only argued in prose.
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        _warm._invalidate(tmp_path)

        last_key = None
        prior_pull_key = _warm._repo_dirty_key(tmp_path)

        edits = [False, True, True, False, True, False, False, True]
        for i, do_edit in enumerate(edits):
            if do_edit:
                _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY + f"\n# edit {i}\n")
            watch_key, watch_changed = watch_tick(tmp_path, last_key)
            pull_key = _warm._repo_dirty_key(tmp_path)
            pull_changed = last_key is not None and pull_key != prior_pull_key
            assert watch_changed == pull_changed
            assert watch_key == pull_key
            last_key = watch_key
            prior_pull_key = pull_key


class TestWatchThread:
    def test_change_fires_on_change_callback(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_serve_watch.py::TestWatchThread.test_change_fires_on_change_callba\
        # ck
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        _warm._invalidate(tmp_path)

        calls = []
        watcher = WatchThread(
            tmp_path, poll_interval_s=0.05, on_change=lambda: calls.append(1)
        )
        watcher.start()
        try:
            time.sleep(0.2)
            _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY + "\n# edited\n")
            deadline = time.monotonic() + 5.0
            while not calls and time.monotonic() < deadline:
                time.sleep(0.05)
            assert calls, "on_change was never called after an on-disk edit"
        finally:
            watcher.stop()

    def test_stop_joins_promptly(self, tmp_path: Path) -> None:
        # frob:tests tests/test_serve_watch.py::TestWatchThread.test_stop_joins_promptly
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        _warm._invalidate(tmp_path)

        watcher = WatchThread(tmp_path, poll_interval_s=0.05)
        watcher.start()
        started = time.monotonic()
        watcher.stop()
        assert time.monotonic() - started < 5.0
        assert not watcher._thread.is_alive()
