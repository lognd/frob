"""T-3526: the Tier-A auto-fix journal (`frob.gates._fix_engine_shared`)
and its wiring into `frob.check`'s pre-dispatch precheck
(`_abandoned_autofix_result`).

Covers the incident this ticket fixes: a killed `frob check --fix` (or
`frob ticket land` pre-land Tier-A phase) used to leave an arbitrary,
unmarked prefix of a rewrite applied on disk. `write_autofix_manifest`
now runs BEFORE the first handler mutates anything (not only after each
one completes), records the writing process's pid, and
`read_abandoned_autofix_manifest`/`_abandoned_autofix_result` detect and
loudly refuse a journal left behind by a process that is no longer
alive -- distinguishing that from a journal a still-live, concurrently
running `--fix` process legitimately owns.

MUST-FIRE: a journal written by a process that is then SIGKILLed (a real
subprocess, not a mocked pid) is detected as abandoned and fails
`frob check` loudly with AUTOFIX001.
MUST-STAY-QUIET: a completed `apply_tier_a_fixes` run leaves no journal,
and `frob check` against a tree with no journal at all is unaffected."""

from __future__ import annotations

import multiprocessing
import os
import time
from pathlib import Path

import pytest

from frob.check import _abandoned_autofix_result, run_check
from frob.gates._fix_engine import apply_tier_a_fixes
from frob.gates._fix_engine_shared import (
    _autofix_manifest_path,
    read_abandoned_autofix_manifest,
    write_autofix_manifest,
)
from frob.tickets import TicketQueue


# frob:waive WIRE001 reason="genuinely wired -- passed as multiprocessing.Process's \
# own target= in \
# TestAbandonedAutofixJournalSigkillSubprocess.test_sigkilled_journal_writer_ \
# is_detected_and_refused below; the analyzer's call-graph does not resolve a target= \
# reference the way it resolves a direct call" follow_up="T-3558"
def _write_journal_and_block(root: str, ready: "multiprocessing.synchronize.Event") -> None:
    """Child-process target (module-level so it is picklable on every
    start method): writes the T-1348 journal with THIS process's own
    pid, signals `ready`, then blocks forever so the parent can SIGKILL
    it mid-"fix" -- the real-subprocess-kill shape the ticket's MUST-FIRE
    fixture calls for, rather than a monkeypatched/faked pid."""
    write_autofix_manifest(Path(root), [])
    ready.set()
    while True:
        time.sleep(1)


class TestAbandonedAutofixJournal:
    """Direct (non-CLI) coverage of `read_abandoned_autofix_manifest` and
    `_abandoned_autofix_result`."""

    def test_absent_manifest_is_not_abandoned(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_shared.py::read_abandoned_autofix_manifest kind="unit"  # noqa: E501
        assert read_abandoned_autofix_manifest(tmp_path) is None

    def test_live_pid_manifest_is_not_abandoned(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_shared.py::read_abandoned_autofix_manifest kind="unit"  # noqa: E501
        (tmp_path / ".frob").mkdir()
        write_autofix_manifest(tmp_path, [])
        # T-3526: write_autofix_manifest always records os.getpid() --
        # THIS test process is itself still alive by construction.
        assert read_abandoned_autofix_manifest(tmp_path) is None

    def test_dead_pid_manifest_is_abandoned(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_shared.py::read_abandoned_autofix_manifest kind="unit"  # noqa: E501
        (tmp_path / ".frob").mkdir()
        path = _autofix_manifest_path(tmp_path)
        path.write_text(
            '{"rewritten_paths": ["src/a.py"], "fix_count": 1, "pid": 999999999}\n'
        )
        result = read_abandoned_autofix_manifest(tmp_path)
        assert result is not None
        assert result.rewritten_paths == ("src/a.py",)
        assert result.pid == 999999999

    def test_malformed_journal_is_abandoned(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine_shared.py::read_abandoned_autofix_manifest kind="unit"  # noqa: E501
        (tmp_path / ".frob").mkdir()
        _autofix_manifest_path(tmp_path).write_text("{not json")
        result = read_abandoned_autofix_manifest(tmp_path)
        assert result is not None
        assert result.rewritten_paths == ()

    def test_no_journal_is_not_a_violation(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::_abandoned_autofix_result kind="unit"
        assert _abandoned_autofix_result(tmp_path) is None

    def test_abandoned_journal_fails_check_loudly(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::_abandoned_autofix_result kind="unit"
        (tmp_path / ".frob").mkdir()
        path = _autofix_manifest_path(tmp_path)
        path.write_text('{"rewritten_paths": ["x.py"], "fix_count": 1, "pid": 999999999}\n')
        result = _abandoned_autofix_result(tmp_path)
        assert result is not None
        assert result.exit_code != 0
        assert any(d.code == "AUTOFIX001" for d in result.diagnostics)
        assert "x.py" in result.summary or any("x.py" in d.message for d in result.diagnostics)

    def test_completed_apply_tier_a_fixes_leaves_no_journal(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_fix_engine.py::apply_tier_a_fixes kind="unit"
        (tmp_path / ".frob").mkdir()
        (tmp_path / "tickets.md").write_text("# Tickets\n")
        from frob.graph import GraphSnapshot

        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        apply_tier_a_fixes(tmp_path, snapshot, TicketQueue(tickets={}))
        assert read_abandoned_autofix_manifest(tmp_path) is None
        assert not _autofix_manifest_path(tmp_path).exists()

    def test_run_check_is_unaffected_with_no_journal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::run_check kind="unit"
        (tmp_path / "tickets.md").write_text("# Tickets\n")
        monkeypatch.setattr(
            "frob.check._native_staleness_result", lambda root: None
        )
        # A precheck-only smoke check: the abandoned-journal precheck
        # must not itself flag a perfectly ordinary tree with no journal
        # at all -- downstream stage failures (missing native builds
        # etc. in a bare tmp_path) are out of scope for this assertion.
        result = run_check(tmp_path, only=frozenset({"gates"}))
        assert not any(
            r.tool == "autofix-journal" for r in result.results
        )


class TestAbandonedAutofixJournalSigkillSubprocess:
    """MUST-FIRE fixture (T-3526 ticket body): kill the process that
    wrote the journal via a REAL SIGKILL in a REAL subprocess (not a
    faked pid) -- the journal must still be detected as abandoned and
    `frob check` must refuse loudly."""

    def test_sigkilled_journal_writer_is_detected_and_refused(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_fix_engine_shared.py::read_abandoned_autofix_manifest kind="unit"  # noqa: E501
        (tmp_path / ".frob").mkdir()
        ctx = multiprocessing.get_context("fork" if os.name != "nt" else "spawn")
        ready = ctx.Event()
        proc = ctx.Process(
            target=_write_journal_and_block, args=(str(tmp_path), ready)
        )
        proc.start()
        try:
            assert ready.wait(timeout=30), "child never wrote its journal"
            child_pid = proc.pid
            assert child_pid is not None
            # T-3526: multiprocessing.Process.kill() is the portable
            # SIGKILL-equivalent (SIGKILL on POSIX, TerminateProcess on
            # Windows, where `signal.SIGKILL` does not exist) -- avoids a
            # raw `os.kill(pid, signal.SIGKILL)` call ty flags as
            # platform-unsound on win32/darwin.
            proc.kill()
            proc.join(timeout=10)
            assert not proc.is_alive()

            manifest = read_abandoned_autofix_manifest(tmp_path)
            assert manifest is not None
            assert manifest.pid == child_pid

            check_result = _abandoned_autofix_result(tmp_path)
            assert check_result is not None
            assert check_result.exit_code != 0
            assert any(d.code == "AUTOFIX001" for d in check_result.diagnostics)
        finally:
            if proc.is_alive():
                proc.kill()
                proc.join(timeout=10)
