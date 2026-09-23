"""T-4660: the post-publish sweep must never hold `.frob/derived.lock`
across a full check.

Covers `frob.app.ticket_runner._rapid_sweep._snapshot_worktree` and
`_run_full_check_in_snapshot`. The second measured T-4660 incident (an
orphaned check child surviving its dead sweep worker) is filed as a
follow-up, T-4686 -- see `_run_full_check_in_snapshot`'s own
docstring."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from frob.app.ticket_runner._rapid_sweep import _snapshot_worktree
from frob.process._derived_lock import derived_state_lock
from tests.conftest import _git_commit, _init_git_repo

#: The `src/` directory this repo's own tests run against -- forwarded
#: into every helper subprocess script below (`sys.path.insert`) since a
#: plain `python -c` child does not inherit pytest's own import setup.
_SRC_DIR = str(Path(__file__).resolve().parents[2] / "src")

#: Generous relative to a real `git worktree add`/`remove` on an empty
#: fixture repo (milliseconds), but bounded so a genuinely wedged git
#: process fails the test loudly instead of hanging the suite.
_WORKTREE_OP_TIMEOUT_S = 30

#: T-4660's own bounded ceiling for a land-side derived.lock acquire
#: while a (simulated) sweep check is in flight -- generous relative to
#: the sub-second work a lock acquire/release actually is, but far below
#: the multi-minute holds the measured incident exhibited.
_LAND_ACQUIRE_CEILING_S = 3.0


class TestSnapshotWorktree:
    """`_snapshot_worktree` -- the isolation primitive the rest of this
    ticket's fix depends on: a full check must run against a path that is
    NOT `root`, so its own `derived_state_lock` acquisition cannot be the
    thing a land's lock acquire on `root` waits on."""

    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_snapshot_worktree
    def test_yields_a_detached_checkout_of_the_commit(self, tmp_path: Path) -> None:
        """The yielded path is a real, separate checkout of `commit_sha`
        -- not `root` itself, and it contains the committed content."""
        # frob:tests tests/unit/test_post_publish_lock_window.py::TestSnapshotWorktree.test_yields_a_detached_checkout_of_the_commit  # noqa: E501
        _init_git_repo(tmp_path)
        (tmp_path / "marker.txt").write_text("hello\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(tmp_path), "add", "marker.txt"], check=True)
        sha = _git_commit(tmp_path, "chore: add marker")

        with _snapshot_worktree(tmp_path, sha) as snapshot_root:
            assert snapshot_root is not None
            assert snapshot_root != tmp_path
            assert snapshot_root.resolve() != tmp_path.resolve()
            assert (snapshot_root / "marker.txt").read_text(
                encoding="utf-8"
            ) == "hello\n"
            # T-4660: the whole point -- the snapshot's own lock file is
            # NOT root's.
            assert (snapshot_root / ".frob" / "derived.lock").resolve() != (
                tmp_path / ".frob" / "derived.lock"
            ).resolve()

    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_snapshot_worktree
    def test_removes_the_worktree_on_exit(self, tmp_path: Path) -> None:
        """After the context manager exits, the snapshot directory is
        gone and git no longer lists it as a registered worktree."""
        # frob:tests tests/unit/test_post_publish_lock_window.py::TestSnapshotWorktree.test_removes_the_worktree_on_exit  # noqa: E501
        _init_git_repo(tmp_path)
        sha = _git_commit(tmp_path, "chore: init")

        with _snapshot_worktree(tmp_path, sha) as snapshot_root:
            assert snapshot_root is not None
            captured = snapshot_root

        assert not captured.exists()
        listing = subprocess.run(
            ["git", "-C", str(tmp_path), "worktree", "list"],
            check=True,
            capture_output=True,
            text=True,
            timeout=_WORKTREE_OP_TIMEOUT_S,
        ).stdout
        assert str(captured) not in listing

    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_snapshot_worktree
    def test_yields_none_when_the_commit_does_not_resolve(self, tmp_path: Path) -> None:
        """A `commit_sha` git cannot resolve is a clean `None`, not a
        raised exception -- the caller degrades to its own unmeasurable-
        this-round handling."""
        # frob:tests tests/unit/test_post_publish_lock_window.py::TestSnapshotWorktree.test_yields_none_when_the_commit_does_not_resolve  # noqa: E501
        _init_git_repo(tmp_path)
        _git_commit(tmp_path, "chore: init")

        with _snapshot_worktree(tmp_path, "deadbeef" * 5) as snapshot_root:
            assert snapshot_root is None


def _spawn_sweep_subprocess(
    root: Path,
    ticket_id: str,
    commit_sha: str,
    hold_seconds: float,
    captured_file: Path,
) -> subprocess.Popen:
    """Run `run_deferred_post_land_sweep(root, ticket_id, commit_sha)` in
    a REAL child process, with `_land_cmd._unscoped_error_findings`
    monkeypatched (in that child, before the call) to a fake that records
    the `root` it was actually called with to `captured_file` and holds
    THAT root's own `derived_state_lock` (SHARED) for `hold_seconds` --
    i.e. it behaves exactly like a real `frob check` subprocess's own
    lock discipline would. A real (sub)process rather than a plain
    monkeypatch in this test process, so the land-side lock acquire below
    genuinely races a SEPARATE process's held lock, the same shape the
    measured incident had."""
    script = f"""
import sys
sys.path.insert(0, {_SRC_DIR!r})
import time
from pathlib import Path

from frob.app.ticket_runner import _land_cmd
from frob.app.ticket_runner._rapid_sweep import run_deferred_post_land_sweep
from frob.process._derived_lock import derived_state_lock


def _fake(root, ticket_id, *, full=False, **kwargs):
    root = Path(root)
    with open({str(captured_file)!r}, "w", encoding="utf-8") as fh:
        fh.write(str(root))
    with derived_state_lock(root, exclusive=False):
        time.sleep({hold_seconds!r})
    return frozenset()


_land_cmd._unscoped_error_findings = _fake
run_deferred_post_land_sweep(Path({str(root)!r}), {ticket_id!r}, {commit_sha!r})
"""
    return subprocess.Popen([sys.executable, "-c", script])


# frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_run_full_check_in_snapshot
def test_post_publish_never_holds_derived_lock_across_a_check(
    tmp_path: Path,
) -> None:
    """POSITIVE CONTROL (T-4660 acceptance criterion 1/2): instrument the
    lock the sweep's full check would take, and assert (a) the check
    never receives `root` itself -- it runs against the snapshot, so its
    lock hold can never be root's -- and (b) a land-side EXCLUSIVE
    acquire on root's OWN `.frob/derived.lock`, attempted WHILE the
    (simulated) check is still holding its own lock, completes within a
    bounded ceiling instead of waiting on it.

    Fails on the pre-T-4660 code (a direct `_unscoped_error_findings(root,
    ..., full=True)` call): `captured_roots[0]` would equal `root`, and
    the land-side acquire below would block for the full `hold_seconds`
    instead of returning immediately."""
    # frob:tests tests/unit/test_post_publish_lock_window.py::test_post_publish_never_holds_derived_lock_across_a_check  # noqa: E501
    _init_git_repo(tmp_path)
    _git_commit(tmp_path, "chore: init")
    sha = _git_commit(tmp_path, "fix(tickets): land T-4660 test commit")
    captured_file = tmp_path.parent / f"{tmp_path.name}-captured-root.txt"

    proc = _spawn_sweep_subprocess(tmp_path, "T-4660", sha, 1.5, captured_file)
    try:
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline and not captured_file.exists():
            time.sleep(0.02)
        assert captured_file.exists(), "the check spawn seam was never reached"

        started = time.monotonic()
        with derived_state_lock(tmp_path, exclusive=True):
            pass
        elapsed = time.monotonic() - started

        proc.wait(timeout=10.0)

        captured_root = Path(captured_file.read_text(encoding="utf-8").strip())
        assert captured_root != tmp_path, (
            "the sweep's full check received the LIVE root -- the T-4660 "
            "fix requires it to run against a snapshot instead"
        )
        assert elapsed < _LAND_ACQUIRE_CEILING_S, (
            f"land-side derived.lock acquire took {elapsed:.2f}s while a "
            "sweep check was in flight -- it must never wait on a sweep"
        )
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10.0)


# frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::_run_full_check_in_snapshot
def test_next_land_not_blocked_by_previous_sweep(tmp_path: Path) -> None:
    """POSITIVE CONTROL (T-4660 acceptance criterion 3): once one
    deferred sweep has started (and is still "running" its full check),
    the NEXT land's own `derived_state_lock` acquire must not wait on
    it -- proven the same way as above, but framed as the sequential
    "next land" scenario the ticket names explicitly."""
    # frob:tests tests/unit/test_post_publish_lock_window.py::test_next_land_not_blocked_by_previous_sweep  # noqa: E501
    _init_git_repo(tmp_path)
    _git_commit(tmp_path, "chore: init")
    sha = _git_commit(tmp_path, "fix(tickets): land T-4660 first land")
    captured_file = tmp_path.parent / f"{tmp_path.name}-captured-root.txt"

    proc = _spawn_sweep_subprocess(tmp_path, "T-4660", sha, 2.0, captured_file)
    try:
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline and not captured_file.exists():
            time.sleep(0.02)
        assert captured_file.exists(), "the check spawn seam was never reached"

        # The "next land": a fresh EXCLUSIVE acquire on the SAME
        # checkout's lock, while the previous land's sweep is still
        # mid-check.
        started = time.monotonic()
        with derived_state_lock(tmp_path, exclusive=True):
            pass
        elapsed = time.monotonic() - started

        proc.wait(timeout=10.0)
        assert elapsed < _LAND_ACQUIRE_CEILING_S, (
            f"next land waited {elapsed:.2f}s on the previous sweep's check"
        )
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10.0)
