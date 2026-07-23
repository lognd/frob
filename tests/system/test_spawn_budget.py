"""Spawn-budget regression lock (T-0776 seed, T-0773 target): one
`frob ticket list` invocation must never spawn the same argv twice.

The 2026-07-22 rev-parse incident: every ticket row's state display
re-derived the git common dir through an uncached subprocess spawn
(`read_all_leases` -> `leases_dir` -> `git_common_dir`), so one listing
spawned dozens of identical `git rev-parse --git-common-dir` processes.
This test pins the budget NOW as a strict xfail: it fails today
(documented debt), and the moment T-0773 lands its memoization the
unexpected pass becomes a hard error demanding the marker's removal --
converting this lock into a live regression gate with no window where
the behavior is silently unprotected. T-0776 then generalizes the
recorder to every hot CLI path.
"""

from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import _list
from frob.tickets import TicketKind, TicketSpec, new_ticket
from frob.tickets._models import Origin


def _make_repo_with_tickets(tmp_path: Path, count: int) -> None:
    """A minimal frob-enabled git repo with `count` queued tickets."""
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    for i in range(count):
        spec = TicketSpec(
            title=f"budget fixture ticket {i}",
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
        )
        result = new_ticket(tmp_path, spec)
        assert result.is_ok, result


# frob:ticket T-0773
@pytest.mark.xfail(
    strict=True,
    reason=(
        "T-0773 not yet landed: the lease layer re-derives the git common "
        "dir per ticket row instead of once per invocation. When T-0773 "
        "lands its memoization this xpasses; remove the marker then."
    ),
)
def test_ticket_list_spawns_each_argv_at_most_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # frob:tests src/frob/tickets/_leases.py::git_common_dir kind="system"
    _make_repo_with_tickets(tmp_path, count=3)

    counts: Counter[tuple[str, ...]] = Counter()
    real_run = subprocess.run

    def counting_run(argv, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
        if isinstance(argv, (list, tuple)) and argv and argv[0] == "git":
            counts[tuple(str(a) for a in argv)] += 1
        return real_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", counting_run)

    cfg = AppConfig(ticket_command="list", ticket_path=tmp_path)
    _list(tmp_path, cfg)

    duplicated = {argv: n for argv, n in counts.items() if n > 1}
    assert duplicated == {}, (
        f"identical argv spawned more than once in a single `frob ticket "
        f"list` invocation: {duplicated}"
    )
