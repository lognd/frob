"""Spawn-budget litmus for CLI hot paths (T-0776): every hot `frob ticket`/
`frob check` entry point below must not spawn an identical git argv more
than its declared budget (default 1, "spawned at most once") in a single
invocation, measured via `frob.gitio.spawn_recorder` -- the exact-count
complement to the static loop-invariant-effect detector. Heuristic-free:
no code-shape pattern matching, just counting real spawns.

`test_ticket_list_spawns_each_argv_at_most_once` is the seed case
(T-0776's precursor). The 2026-07-22 rev-parse incident: every ticket
row's state display re-derived the git common dir through an uncached
subprocess spawn (`read_all_leases` -> `leases_dir` -> `_git_common_dir`),
so one listing spawned dozens of identical `git rev-parse
--git-common-dir` processes. T-0773 fixed this by memoizing
`_git_common_dir`/`read_all_leases` per resolved path for the process's
lifetime (`frob.tickets._leases`) and threading one `_all_leases`
snapshot through `doable`/`doable_blocked`'s per-candidate loop -- this
test (and `test_ticket_doable_spawns_each_argv_at_most_once` below) is
now a plain, non-xfail regression lock: a future change that reintroduces
per-row/per-candidate re-derivation fails it immediately, no window where
the behavior is silently unprotected.

Every test in this file is a budget the path ALREADY meets -- non-xfail,
so a future regression is a hard, immediate failure rather than a
documented one.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.app.config import AppConfig
from frob.app.ticket_runner import _doable, _list, _show
from frob.gates._exclude_hazard import exclude_hazard_gate
from frob.gitio import spawn_recorder
from frob.tickets import TicketKind, TicketSpec, new_ticket
from frob.tickets._models import Origin


def _make_repo_with_tickets(tmp_path: Path, count: int) -> list[str]:
    """A minimal frob-enabled git repo with `count` queued tickets; returns
    the created ticket ids in creation order."""
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    ids: list[str] = []
    for i in range(count):
        spec = TicketSpec(
            title=f"budget fixture ticket {i}",
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
        )
        result = new_ticket(tmp_path, spec)
        assert result.is_ok, result
        ids.append(result.danger_ok.id)
    return ids


# frob:ticket T-0773
def test_ticket_list_spawns_each_argv_at_most_once(tmp_path: Path) -> None:
    # frob:tests src/frob/tickets/_leases.py::_git_common_dir kind="e2e"
    _make_repo_with_tickets(tmp_path, count=3)

    cfg = AppConfig(ticket_command="list", ticket_path=tmp_path)
    with spawn_recorder() as recorder:
        _list(tmp_path, cfg)

    duplicated = recorder.duplicates()
    assert duplicated == {}, (
        f"identical argv spawned more than once in a single `frob ticket "
        f"list` invocation: {duplicated}"
    )


# frob:ticket T-0776
def test_ticket_show_spawns_each_argv_at_most_once(tmp_path: Path) -> None:
    # frob:tests src/frob/app/ticket_runner.py::_show kind="e2e"
    ids = _make_repo_with_tickets(tmp_path, count=1)

    cfg = AppConfig(ticket_command="show", ticket_path=tmp_path, ticket_id=ids[0])
    with spawn_recorder() as recorder:
        _show(tmp_path, cfg)

    duplicated = recorder.duplicates()
    assert duplicated == {}, (
        f"identical argv spawned more than once in a single `frob ticket "
        f"show` invocation: {duplicated}"
    )


# frob:ticket T-0773
def test_ticket_doable_spawns_each_argv_at_most_once(tmp_path: Path) -> None:
    # frob:tests src/frob/tickets/_leases.py::_git_common_dir kind="e2e"
    _make_repo_with_tickets(tmp_path, count=3)

    cfg = AppConfig(ticket_command="doable", ticket_path=tmp_path)
    with spawn_recorder() as recorder:
        _doable(tmp_path, cfg)

    duplicated = recorder.duplicates()
    assert duplicated == {}, (
        f"identical argv spawned more than once in a single `frob ticket "
        f"doable` invocation: {duplicated}"
    )


# frob:ticket T-0776
def test_exclude_hazard_gate_spawns_each_argv_at_most_once(tmp_path: Path) -> None:
    # frob:tests src/frob/gates/_exclude_hazard.py::exclude_hazard_gate kind="e2e"
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=a@b.c",
            "-c",
            "user.name=a",
            "commit",
            "-q",
            "-m",
            "init",
        ],
        cwd=tmp_path,
        check=True,
    )

    with spawn_recorder() as recorder:
        exclude_hazard_gate(tmp_path)

    duplicated = recorder.duplicates()
    assert duplicated == {}, (
        f"identical argv spawned more than once in a single "
        f"`exclude_hazard_gate` invocation: {duplicated}"
    )
