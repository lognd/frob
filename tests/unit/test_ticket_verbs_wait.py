"""T-3614: `--wait [SECONDS]` on `new`/`drop`/`body`/`scope`/`fail`/
`reconcile`. Write verbs that hit a held `LandInProgress`/`tickets.lock`
window used to fail instantly (0.6s), forcing every caller (agents, the
coordinator, humans) to hand-roll a sleep loop around the retry. `--wait`
threads through `_add_ticket_wait_arg` (CLI) -> `AppConfig.ticket_wait_s`
-> `_refuse_if_land_in_progress_for_dispatch` -> `refuse_if_land_in_
progress`'s existing `wait_timeout_s` poll-with-backoff loop (T-1961/
T-2023), already fully built -- this ticket only had to reach it from
the CLI.

Two fixture classes: `TestAddWaitArg` (the argparse flag's own default/
bare/explicit shapes, no git/threads needed) and `TestDispatchWait` (the
end-to-end window-opens-mid-wait / budget-exhausted-names-holder pair
this ticket's own acceptance criteria name)."""

from __future__ import annotations

import argparse
import fcntl
import os
import subprocess
import threading
from pathlib import Path

import pytest

from frob._cli_parsers._ticket._new import (
    _TICKET_WAIT_DEFAULT_S,
    _add_ticket_wait_arg,
)
from frob.app.ticket_runner import _refuse_if_land_in_progress_for_dispatch
from frob.tickets._leases import TICKETS_LEDGER_LOCK_REL


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a subprocess quietly against `cwd`, raising on failure."""
    return subprocess.run(argv, cwd=cwd, check=True, capture_output=True, text=True)


def _git_init(root: Path) -> None:
    """A minimal initialized git repo -- test helper mirroring
    `tests/test_ticket_leases.py`'s own `_git_init`."""
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _run_with_bound(fn, *, bound_s: float) -> None:
    """Run `fn()` on a daemon thread and assert it returns within
    `bound_s` seconds -- a regression in the poll loop must fail this
    TEST rather than hang it forever (same T-2093 precedent `tests/
    test_ticket_leases.py::_run_with_bound` established)."""
    exc_box: list[BaseException] = []

    def _target() -> None:
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001 - re-raised below
            exc_box.append(exc)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=bound_s)
    assert not thread.is_alive(), (
        f"did not return within the asserted {bound_s}s bound -- the "
        "--wait poll loop is hanging"
    )
    if exc_box:
        raise exc_box[0]


def _expect_system_exit(fn) -> SystemExit:
    """The thread-safe equivalent of `pytest.raises(SystemExit)` for use
    inside `_run_with_bound`'s target."""
    try:
        fn()
    except SystemExit as exc:
        return exc
    raise AssertionError("expected SystemExit, but the call returned normally")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A bare initialized git repo -- `_refuse_if_land_in_progress_for_
    dispatch` only needs a real `.git` to find `tickets.lock` under, no
    ticket ledger content."""
    root = tmp_path / "repo"
    _git_init(root)
    return root


# frob:ticket T-3614
class TestAddWaitArg:
    """`_add_ticket_wait_arg`'s own default/bare/explicit argparse
    shapes, independent of the dispatch guard it feeds."""

    def _parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        _add_ticket_wait_arg(parser)
        return parser

    # frob:tests src/frob/_cli_parsers/_ticket/_new.py::_add_ticket_wait_arg
    def test_flag_absent_leaves_wait_none(self) -> None:
        """Omitted entirely: `ticket_wait_s` stays `None` -- today's
        unchanged instant-refusal behavior."""
        ns = self._parser().parse_args([])
        assert ns.ticket_wait_s is None

    # frob:tests src/frob/_cli_parsers/_ticket/_new.py::_add_ticket_wait_arg
    def test_bare_flag_uses_default_budget(self) -> None:
        """A bare `--wait` (no SECONDS) uses `_TICKET_WAIT_DEFAULT_S`."""
        ns = self._parser().parse_args(["--wait"])
        assert ns.ticket_wait_s == _TICKET_WAIT_DEFAULT_S

    # frob:tests src/frob/_cli_parsers/_ticket/_new.py::_add_ticket_wait_arg
    def test_explicit_seconds_is_used_verbatim(self) -> None:
        """`--wait N` sets `ticket_wait_s` to exactly `N`."""
        ns = self._parser().parse_args(["--wait", "12.5"])
        assert ns.ticket_wait_s == 12.5


# frob:ticket T-3614
class TestDispatchWait:
    """End to end: `_refuse_if_land_in_progress_for_dispatch`'s
    `wait_timeout_s` actually blocks on a held `tickets.lock` and either
    succeeds once the window opens, or refuses -- naming the holder --
    once its budget is exhausted (this ticket's own acceptance
    criteria)."""

    def test_window_opens_mid_wait_then_succeeds(self, repo: Path) -> None:
        """`tickets.lock` is released 0.3s into a 5s wait budget -- the
        dispatch guard must succeed (no `SystemExit`) rather than
        refusing on its very first probe."""
        if os.name == "nt":
            pytest.skip("POSIX-only (flock)")
        lock_path = repo / TICKETS_LEDGER_LOCK_REL
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        holder_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(holder_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        def _release_soon() -> None:
            import time

            time.sleep(0.3)
            fcntl.flock(holder_fd, fcntl.LOCK_UN)
            os.close(holder_fd)

        releaser = threading.Thread(target=_release_soon, daemon=True)
        releaser.start()
        try:
            _run_with_bound(
                lambda: _refuse_if_land_in_progress_for_dispatch(
                    repo, "priority", wait_timeout_s=5.0
                ),
                bound_s=10.0,
            )
        finally:
            releaser.join(timeout=5.0)

    def test_budget_exhausted_names_holder(self, repo: Path, caplog) -> None:  # noqa: ANN001
        """`tickets.lock` stays held for longer than a short `--wait`
        budget -- the dispatch guard refuses (`SystemExit(1)`) and the
        logged error names the verb, matching this ticket's "fail loudly
        with the holder's identity" acceptance criterion (the holder-
        identity computation itself is `_refuse_for_held_land_lock`'s,
        reused unchanged by this ticket, not re-derived here)."""
        if os.name == "nt":
            pytest.skip("POSIX-only (flock)")
        lock_path = repo / TICKETS_LEDGER_LOCK_REL
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        holder_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(holder_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            caplog.set_level("ERROR")
            captured: list[SystemExit] = []
            _run_with_bound(
                lambda: captured.append(
                    _expect_system_exit(
                        lambda: _refuse_if_land_in_progress_for_dispatch(
                            repo, "priority", wait_timeout_s=0.5
                        )
                    )
                ),
                bound_s=10.0,
            )
            assert captured[0].code == 1
            assert "priority" in caplog.text
        finally:
            fcntl.flock(holder_fd, fcntl.LOCK_UN)
            os.close(holder_fd)
