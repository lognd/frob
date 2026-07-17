"""frob.stats: delivery measurement (T-0009)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.stats import collect, commit_stats, ticket_stats
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    transition,
)


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    return tmp_path


def _commit(root: Path, subject: str) -> None:
    (root / "f.txt").write_text(subject, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", subject], cwd=root, check=True)


def test_ticket_stats_counts_states_and_doable(tmp_path):
    # frob:tests src/frob/stats/__init__.py::ticket_stats
    from frob.tickets import load_queue

    a = new_ticket(tmp_path, TicketSpec(title="a", kind=TicketKind.FEATURE, origin=Origin.AGENT)).danger_ok
    new_ticket(tmp_path, TicketSpec(title="b", kind=TicketKind.BUG, origin=Origin.AGENT))
    transition(tmp_path, a.id, TicketState.PLANNED)
    stats = ticket_stats(load_queue(tmp_path).danger_ok)
    assert stats.total == 2
    assert stats.doable == 2
    assert stats.by_kind == {"feature": 1, "bug": 1}


def test_commit_stats_classifies_conventional_types(tmp_path):
    # frob:tests src/frob/stats/__init__.py::commit_stats
    root = _repo(tmp_path)
    _commit(root, "feat: a")
    _commit(root, "fix: b")
    _commit(root, "feat(x): c")
    _commit(root, "random subject")
    stats = commit_stats(root, window_days=30).danger_ok
    assert stats.total == 4
    assert stats.by_type["feat"] == 2
    assert stats.by_type["fix"] == 1
    assert stats.by_type["other"] == 1


def test_collect_combines_both(tmp_path):
    # frob:tests src/frob/stats/__init__.py::collect
    root = _repo(tmp_path)
    _commit(root, "chore: init")
    new_ticket(root, TicketSpec(title="t", kind=TicketKind.FEATURE, origin=Origin.HUMAN))
    report = collect(root, window_days=7).danger_ok
    assert report.tickets.total == 1
    assert report.commits.total == 1
