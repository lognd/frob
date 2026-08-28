"""Tests for `frob.gates._lock_producer` (T-2999): a baseline lock's
producer-staleness verdict, distinguishing PINNED/ABANDONED/FRESH/
UNMEASURED against a real (small, fixture) git history."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from frob.gates._lock_producer import (
    KNOWN_LOCKS,
    TrackedLock,
    all_producer_statuses,
    producer_status,
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "PATH": "/usr/bin:/bin",
        },
    )


def _init_repo(root: Path) -> None:
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")


class TestProducerStatusVerdicts:
    """`producer_status`'s four verdicts, against a real small git repo."""

    # frob:tests src/frob/gates/_lock_producer.py::producer_status kind="unit"
    def test_no_lock_file_is_unmeasured(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        (tmp_path / "README.md").write_text("x")
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-q", "-m", "init")
        lock = TrackedLock(name="x", path_rel="missing.lock.json", code_glob="src/**/*.py")
        status = producer_status(tmp_path, lock)
        assert status.verdict == "UNMEASURED"
        assert status.exists is False

    # frob:tests src/frob/gates/_lock_producer.py::producer_status kind="unit"
    def test_must_fire_abandoned_when_code_moved_and_no_pin(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-FIRE fixture: a lock stamped once, then the code it
        baselines keeps changing with no re-stamp and no pin -- the
        exact shape T-2999 measured on this repo's own three real
        locks (thousands of commits since last stamp)."""
        monkeypatch.setattr(
            "frob.gates._lock_producer.ABANDONED_CODE_COMMIT_THRESHOLD", 2
        )
        _init_repo(tmp_path)
        (tmp_path / "x.lock.json").write_text(json.dumps({"v": 1}))
        (tmp_path / "src" / "pkg").mkdir(parents=True)
        (tmp_path / "src" / "pkg" / "a.py").write_text("x = 1\n")
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-q", "-m", "stamp")
        for i in range(3):
            (tmp_path / "src" / "pkg" / "a.py").write_text(f"x = {i}\n")
            _git(tmp_path, "add", "-A")
            _git(tmp_path, "commit", "-q", "-m", f"code change {i}")
        lock = TrackedLock(name="x", path_rel="x.lock.json", code_glob="src/**/*.py")
        status = producer_status(tmp_path, lock)
        assert status.verdict == "ABANDONED"
        assert status.code_commits_since == 3

    # frob:tests src/frob/gates/_lock_producer.py::producer_status kind="unit"
    def test_must_stay_quiet_when_pinned(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-STAY-QUIET fixture: the identical code-churn shape as the
        must-fire case above, but the lock carries a `pin` -- a
        deliberate freeze must never read as abandonment."""
        monkeypatch.setattr(
            "frob.gates._lock_producer.ABANDONED_CODE_COMMIT_THRESHOLD", 2
        )
        _init_repo(tmp_path)
        (tmp_path / "x.lock.json").write_text(
            json.dumps({"v": 1, "pin": {"reason": "frozen on purpose", "ticket": "T-1"}})
        )
        (tmp_path / "src" / "pkg").mkdir(parents=True)
        (tmp_path / "src" / "pkg" / "a.py").write_text("x = 1\n")
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-q", "-m", "stamp")
        for i in range(3):
            (tmp_path / "src" / "pkg" / "a.py").write_text(f"x = {i}\n")
            _git(tmp_path, "add", "-A")
            _git(tmp_path, "commit", "-q", "-m", f"code change {i}")
        lock = TrackedLock(name="x", path_rel="x.lock.json", code_glob="src/**/*.py")
        status = producer_status(tmp_path, lock)
        assert status.verdict == "PINNED"
        assert status.pin is not None
        assert status.pin.reason == "frozen on purpose"

    # frob:tests src/frob/gates/_lock_producer.py::producer_status kind="unit"
    def test_fresh_when_unpinned_and_below_threshold(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "frob.gates._lock_producer.ABANDONED_CODE_COMMIT_THRESHOLD", 100
        )
        _init_repo(tmp_path)
        (tmp_path / "x.lock.json").write_text(json.dumps({"v": 1}))
        (tmp_path / "src" / "pkg").mkdir(parents=True)
        (tmp_path / "src" / "pkg" / "a.py").write_text("x = 1\n")
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-q", "-m", "stamp")
        (tmp_path / "src" / "pkg" / "a.py").write_text("x = 2\n")
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-q", "-m", "one code change")
        lock = TrackedLock(name="x", path_rel="x.lock.json", code_glob="src/**/*.py")
        status = producer_status(tmp_path, lock)
        assert status.verdict == "FRESH"

    # frob:tests src/frob/gates/_lock_producer.py::all_producer_statuses kind="unit"
    def test_all_producer_statuses_covers_the_three_known_locks(self) -> None:
        assert {lock.name for lock in KNOWN_LOCKS} == {
            "coverage",
            "deprecated-baseline",
            "ratchet",
        }


class TestAgainstThisRepo:
    """Sanity check against the real repo (not a synthetic fixture) --
    the module must be able to run against a real, large history
    without crashing."""

    # frob:tests src/frob/gates/_lock_producer.py::all_producer_statuses kind="unit"
    def test_runs_clean_against_this_repo(self) -> None:
        root = Path(__file__).resolve().parents[3]
        statuses = all_producer_statuses(root)
        assert len(statuses) == 3
        for status in statuses:
            assert status.verdict in ("UNMEASURED", "PINNED", "ABANDONED", "FRESH")
