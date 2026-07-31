"""frob.mutate._journal: crash-safe backup journal for run_mutations
(T-0857) -- journal write/idempotency/collision, byte-exact restore
(CRLF fixture), the crash-simulation regression this ticket exists
for (a killed harness leaves a journal, the NEXT `run_mutations` call
restores the original byte-exact before doing anything else), and the
T-1327 stale-restore content-verification regression: a journal whose
last-known on-disk content no longer matches what's actually on disk
(a later legitimate run, or a live edit layered over a leftover mutant)
must never be blindly restored over."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import cast

import pytest

from frob.mutate import MutateError, run_mutations
from frob.mutate._journal import (
    JournalError,
    list_stale_journals,
    record_journal_progress,
    remove_journal,
    restore_stale_journals,
    write_journal,
)


def _dead_pid() -> int:
    """A PID guaranteed to be dead: spawn a trivial subprocess, wait for
    it to exit, then return its (now-vacated) PID -- deterministic, no
    race against a real running process."""
    proc = subprocess.Popen(["python3", "-c", "pass"])
    proc.wait()
    return proc.pid


def _journal_file_count(root: Path) -> int:
    """Every journal file present on disk under `root`, regardless of
    staleness -- `list_stale_journals` deliberately excludes a journal
    owned by a still-live PID, so a test only asserting "a journal file
    was written/removed" (not the staleness filter itself) checks the raw
    files, not that function."""
    journal_dir = root / ".frob" / "mutate-backup"
    if not journal_dir.exists():
        return 0
    return len(list(journal_dir.glob("*.json")))


def test_write_journal_is_idempotent_for_same_content(tmp_path):
    # frob:tests \
    # tests/test_mutate_journal.py::test_write_journal_is_idempotent_for_same_content
    target = tmp_path / "m.py"
    target.write_bytes(b"original bytes\n")
    assert write_journal(tmp_path, target, b"original bytes\n").is_ok
    # second call, same content -> no-op, still Ok
    assert write_journal(tmp_path, target, b"original bytes\n").is_ok
    assert _journal_file_count(tmp_path) == 1


def test_write_journal_refuses_on_content_collision(tmp_path):
    # frob:tests \
    # tests/test_mutate_journal.py::test_write_journal_refuses_on_content_collision
    target = tmp_path / "m.py"
    target.write_bytes(b"first run's original\n")
    assert write_journal(tmp_path, target, b"first run's original\n").is_ok
    # a second, concurrent run sees different "original" bytes for the same
    # target -- must refuse, not silently clobber the first run's backup.
    result = write_journal(tmp_path, target, b"second run's original\n")
    assert result.is_err
    assert result.danger_err == JournalError.Collision
    # the original (first run's) journal content must survive untouched
    assert _journal_file_count(tmp_path) == 1


def test_remove_journal_after_restore(tmp_path):
    # frob:tests tests/test_mutate_journal.py::test_remove_journal_after_restore
    target = tmp_path / "m.py"
    target.write_bytes(b"bytes\n")
    assert write_journal(tmp_path, target, b"bytes\n").is_ok
    assert _journal_file_count(tmp_path) == 1
    remove_journal(tmp_path, target)
    assert _journal_file_count(tmp_path) == 0
    # removing an already-removed journal is not an error
    remove_journal(tmp_path, target)


def test_list_stale_journals_reports_without_restoring(tmp_path):
    # frob:tests \
    # tests/test_mutate_journal.py::test_list_stale_journals_reports_without_restoring
    target = tmp_path / "m.py"
    target.write_bytes(b"MUTATED CONTENT")
    write_journal(tmp_path, target, b"ORIGINAL CONTENT", pid=_dead_pid())
    stale = list_stale_journals(tmp_path)
    assert len(stale) == 1
    assert stale[0].target == "m.py"
    # read-only: the target is untouched, still holding the "mutated" bytes
    assert target.read_bytes() == b"MUTATED CONTENT"
    # the journal itself is also untouched
    assert len(list_stale_journals(tmp_path)) == 1


def test_restore_stale_journals_is_byte_exact_crlf(tmp_path):
    # frob:tests \
    # tests/test_mutate_journal.py::test_restore_stale_journals_is_byte_exact_crlf
    # T-0441 lesson: a text-mode round trip silently rewrites CRLF to the
    # platform default. The journal must restore the exact original bytes.
    original = b"def f(a, b):\r\n    return a + b\r\n"
    target = tmp_path / "m.py"
    target.write_bytes(original)
    # pid=_dead_pid() simulates the WRITING process having crashed --
    # restore_stale_journals only acts on journals whose writer is dead.
    assert write_journal(tmp_path, target, original, pid=_dead_pid()).is_ok
    # simulate the crash: target now holds "mutant" content, and the
    # journal's own progress-tracking (T-1327) was kept in step with it,
    # exactly as `run_mutations`' write loop would have done.
    mutant = b"def f(a, b):\r\n    return a - b\r\n"
    target.write_bytes(mutant)
    record_journal_progress(tmp_path, target, mutant)
    restored = restore_stale_journals(tmp_path)
    assert restored == ("m.py",)
    assert target.read_bytes() == original
    # journal is cleaned up after a successful restore
    assert list_stale_journals(tmp_path) == ()


def test_restore_stale_journals_after_simulated_crash(tmp_path):
    # frob:tests \
    # tests/test_mutate_journal.py::test_restore_stale_journals_after_simulated_crash
    original = b"def add(a, b):\n    return a + b\n"
    target = tmp_path / "m.py"
    target.write_bytes(original)
    write_journal(tmp_path, target, original, pid=_dead_pid())
    # a crash leaves the mutant on disk with no ordinary restore ever run
    mutant = b"def add(a, b):\n    return a - b\n"
    target.write_bytes(mutant)
    record_journal_progress(tmp_path, target, mutant)
    assert list_stale_journals(tmp_path)
    restored = restore_stale_journals(tmp_path)
    assert restored == ("m.py",)
    assert target.read_bytes() == original


def test_restore_and_list_skip_a_journal_owned_by_a_live_pid(tmp_path):
    # frob:tests \
    # tests/test_mutate_journal.py::test_restore_and_list_skip_a_journal_owned_by_a_liv\
    # e_pid
    # A journal whose writer is STILL RUNNING is an in-progress mutation
    # run, not a crash -- restoring it would corrupt that live run. Using
    # this test's own (definitely alive) pid stands in for that case.
    import os

    original = b"original\n"
    target = tmp_path / "m.py"
    target.write_bytes(original)
    write_journal(tmp_path, target, original, pid=os.getpid())
    target.write_bytes(b"mutant in progress\n")
    assert list_stale_journals(tmp_path) == ()
    assert restore_stale_journals(tmp_path) == ()
    # untouched: neither the target nor the journal was disturbed
    assert target.read_bytes() == b"mutant in progress\n"


def test_recycled_pid_with_mismatched_starttime_is_treated_stale(tmp_path):
    # frob:tests \
    # tests/test_mutate_journal.py::test_recycled_pid_with_mismatched_starttime_is_trea\
    # ted_stale
    # T-0857 reviewer finding: a bare "is the PID alive" probe cannot tell
    # a crashed writer whose PID got recycled apart from a genuinely live
    # writer. Simulating recycling: a LIVE pid (this test process, so
    # _pid_alive is unambiguously True) with a deliberately WRONG recorded
    # starttime -- exactly what a recycled-PID journal would look like,
    # with no actual PID recycling required to test it.
    import os

    original = b"true original\n"
    target = tmp_path / "m.py"
    target.write_bytes(original)
    write_journal(tmp_path, target, original, pid=os.getpid(), starttime="0")
    # simulate the "crash left a mutant" state
    mutant = b"mutant left by the crashed (PID-recycled) writer\n"
    target.write_bytes(mutant)
    record_journal_progress(tmp_path, target, mutant)

    # UNLIKE the live-pid-with-correct-starttime case above, this must be
    # recognized as stale and restored -- a bare PID-liveness check would
    # wrongly leave this alone forever.
    stale = list_stale_journals(tmp_path)
    assert len(stale) == 1
    assert stale[0].target == "m.py"

    restored = restore_stale_journals(tmp_path)
    assert restored == ("m.py",)
    assert target.read_bytes() == original
    assert list_stale_journals(tmp_path) == ()


def test_write_journal_cleans_up_temp_file_on_replace_failure(tmp_path, monkeypatch):
    # frob:tests \
    # tests/test_mutate_journal.py::test_write_journal_cleans_up_temp_file_on_replace_f\
    # ailure
    # T-0857 reviewer nit: an IO error between the temp-file write and the
    # atomic rename must not leave a stray `.tmpNNN` file behind. The
    # underlying `os.replace` failure itself still propagates (write_journal
    # does not swallow it into a Result) -- only the leftover-temp-file
    # side effect is the bug this guards against.
    from frob.mutate import _journal as journal_mod

    target = tmp_path / "m.py"
    target.write_bytes(b"bytes\n")

    def _boom(*args, **kwargs):
        raise OSError("simulated failure between write and rename")

    monkeypatch.setattr(journal_mod.os, "replace", _boom)
    with pytest.raises(OSError, match="simulated failure"):
        write_journal(tmp_path, target, b"bytes\n")
    journal_dir = tmp_path / ".frob" / "mutate-backup"
    leftover = list(journal_dir.glob("*.tmp*")) if journal_dir.exists() else []
    assert leftover == []


def test_run_mutations_restores_stale_journal_from_prior_crash(tmp_path):
    # frob:tests src/frob/mutate/__init__.py::run_mutations
    # frob:tests \
    # tests/test_mutate_journal.py::test_run_mutations_restores_stale_journal_from_prio\
    # r_crash
    # The real incident this ticket fixes, minus the actual SIGKILL: a
    # "crashed" prior run left a journal and a mutated target on disk;
    # the NEXT run_mutations call must restore it before anything else,
    # and must still produce a correct mutation score of its own.
    original = "def add(a, b):\n    return a + b\n"
    (tmp_path / "m.py").write_text(original, encoding="utf-8")
    (tmp_path / "t.py").write_text(
        "import m\n"
        "def test_add():\n"
        "    assert m.add(2, 3) == 5\n"
        "    assert m.add(0, 0) == 0\n",
        encoding="utf-8",
    )
    target = tmp_path / "m.py"
    # simulate a prior crashed run: journal the true original under a now-
    # dead PID, then leave the target in mutant form (as a killed
    # run_mutations call would).
    write_journal(tmp_path, target, original.encode("utf-8"), pid=_dead_pid())
    mutant = b"def add(a, b):\n    return a - b\n"
    target.write_bytes(mutant)
    record_journal_progress(tmp_path, target, mutant)
    assert list_stale_journals(tmp_path)

    result = run_mutations(
        tmp_path, Path("m.py"), ("python", "-m", "pytest", "-q", "t.py")
    )

    assert result.is_ok, result.err
    report = result.danger_ok
    # a hand-verified mutant kill: the strong test set kills every
    # single-point mutation of `add`.
    assert report.total >= 1
    assert report.killed == report.total
    assert not report.survivors
    # the stale journal from the "crashed" run was restored and cleaned up
    assert list_stale_journals(tmp_path) == ()
    # and the file ends this run correctly restored to the true original
    assert target.read_text(encoding="utf-8") == original


def test_run_mutations_journals_and_cleans_up_on_success(tmp_path):
    # frob:tests src/frob/mutate/__init__.py::run_mutations
    # frob:tests \
    # tests/test_mutate_journal.py::test_run_mutations_journals_and_cleans_up_on_success
    original = "def add(a, b):\n    return a + b\n"
    (tmp_path / "m.py").write_text(original, encoding="utf-8")
    (tmp_path / "t.py").write_text(
        "import m\ndef test_add():\n    m.add(1, 2)\n", encoding="utf-8"
    )
    result = run_mutations(
        tmp_path, Path("m.py"), ("python", "-m", "pytest", "-q", "t.py")
    )
    assert result.is_ok, result.err
    # normal exit: no journal left behind
    assert list_stale_journals(tmp_path) == ()


def test_pytest_session_start_restores_leftover_journal(tmp_path, monkeypatch):
    # frob:ticket T-0885
    # frob:tests \
    # tests/test_mutate_journal.py::test_pytest_session_start_restores_leftover_journal
    # T-0885: generalize T-0857's crash-restore beyond `run_mutations`'
    # own call site. Simulates the exact incident this ticket describes --
    # an xdist worker crash / external SIGTERM leaves a stale journal and a
    # corrupted target on disk, with NO subsequent `frob mutate` call ever
    # made against that target -- and asserts `conftest.py`'s
    # `pytest_configure` hook (the generalized restore point) still
    # recovers it, standing in for the next pytest session's startup.
    import tests.conftest as repo_conftest

    original = b"true original bytes\n"
    target = tmp_path / "m.py"
    target.write_bytes(original)
    write_journal(tmp_path, target, original, pid=_dead_pid())
    # simulate the crash: the leftover mutant sits on disk, uncleaned
    mutant = b"MUTANT LEFT BY CRASHED WORKER\n"
    target.write_bytes(mutant)
    record_journal_progress(tmp_path, target, mutant)
    assert list_stale_journals(tmp_path)

    monkeypatch.setattr(repo_conftest, "_REPO_ROOT", tmp_path)

    class _FakeConfigNoWorker:
        """Stand-in for `pytest.Config` on the xdist CONTROLLER process --
        no `workerinput` attribute, matching real xdist's own contract."""

    repo_conftest.pytest_configure(cast("pytest.Config", _FakeConfigNoWorker()))

    assert target.read_bytes() == original
    assert list_stale_journals(tmp_path) == ()


def test_pytest_session_start_skips_restore_on_xdist_worker(tmp_path, monkeypatch):
    # frob:ticket T-0885
    # frob:tests \
    # tests/test_mutate_journal.py::test_pytest_session_start_skips_restore_on_xdist_wo\
    # rker
    # Restoring from every xdist WORKER process (not just the controller)
    # would be redundant at best and a `write_journal`-style race at
    # worst -- the hook must no-op there and leave the journal untouched
    # for the controller to handle.
    import tests.conftest as repo_conftest

    original = b"true original bytes\n"
    target = tmp_path / "m.py"
    target.write_bytes(original)
    write_journal(tmp_path, target, original, pid=_dead_pid())
    target.write_bytes(b"MUTANT LEFT BY CRASHED WORKER\n")

    monkeypatch.setattr(repo_conftest, "_REPO_ROOT", tmp_path)

    class _FakeConfigWorker:
        """Stand-in for `pytest.Config` on an xdist WORKER process --
        `workerinput` is present there (real xdist sets it)."""

        workerinput = {}

    repo_conftest.pytest_configure(cast("pytest.Config", _FakeConfigWorker()))

    # untouched: the worker deliberately did not restore
    assert target.read_bytes() == b"MUTANT LEFT BY CRASHED WORKER\n"
    assert list_stale_journals(tmp_path)


def test_run_mutations_journal_collision_aborts_with_journal_collision_error(
    tmp_path,
):
    # frob:tests src/frob/mutate/__init__.py::run_mutations
    # frob:tests \
    # tests/test_mutate_journal.py::test_run_mutations_journal_collision_aborts_with_jo\
    # urnal_collision_error
    original = "def add(a, b):\n    return a + b\n"
    target = tmp_path / "m.py"
    target.write_text(original, encoding="utf-8")
    (tmp_path / "t.py").write_text(
        "import m\ndef test_add():\n    m.add(1, 2)\n", encoding="utf-8"
    )
    # a "concurrent run" already journaled DIFFERENT original bytes for
    # this same target -- run_mutations must refuse, not clobber it.
    write_journal(tmp_path, target, b"a different concurrent run's original\n")
    result = run_mutations(
        tmp_path, Path("m.py"), ("python", "-m", "pytest", "-q", "t.py")
    )
    assert result.is_err
    assert result.danger_err == MutateError.JournalCollision
    # the target was never touched -- the concurrent run's journal and its
    # backing bytes are the ones that must survive, untouched.
    assert target.read_text(encoding="utf-8") == original


def test_record_journal_progress_tracks_last_written_content(tmp_path):
    # frob:tests \
    # tests/test_mutate_journal.py::test_record_journal_progress_tracks_last_written_co\
    # ntent
    # T-1327: `record_journal_progress` updates the journal's own
    # "last known on-disk content" hash, without touching the recorded
    # original bytes used for the eventual restore.
    import json

    original = b"original\n"
    target = tmp_path / "m.py"
    target.write_bytes(original)
    write_journal(tmp_path, target, original, pid=_dead_pid())
    journal_path = next((tmp_path / ".frob" / "mutate-backup").glob("*.json"))
    before = json.loads(journal_path.read_text(encoding="utf-8"))
    assert before["current_sha256"] == before["sha256"]

    mutant = b"mutant bytes\n"
    record_journal_progress(tmp_path, target, mutant)
    after = json.loads(journal_path.read_text(encoding="utf-8"))
    # the ORIGINAL backing bytes are untouched -- only the progress hash moved
    assert after["content_b64"] == before["content_b64"]
    assert after["sha256"] == before["sha256"]
    import hashlib

    assert after["current_sha256"] == hashlib.sha256(mutant).hexdigest()


def test_restore_refuses_when_stale_journal_no_longer_matches_on_disk_content(
    tmp_path,
):
    # frob:tests \
    # tests/test_mutate_journal.py::test_restore_refuses_when_stale_journal_no_longer_m\
    # atches_on_disk_content
    # frob:tests src/frob/mutate/_journal.py::restore_stale_journals
    # The T-1203 incident, reproduced directly: an earlier, unrelated
    # mutation run crashed and left a stale journal for this file plus its
    # mutant content on disk; a developer then made a LIVE, uncommitted
    # edit on top of it (never noticing the leftover mutant underneath).
    # A later, unrelated `restore_stale_journals` sweep (as
    # `run_mutations`' own startup call performs, across every stale
    # journal under root, not just its own target) must NOT clobber that
    # live edit -- it must fail closed: skip the restore, drop the now-
    # untrustworthy journal entry, and leave the live edit exactly as the
    # developer left it.
    original = b"def add(a, b):\n    return a + b\n"
    target = tmp_path / "m.py"
    target.write_bytes(original)
    write_journal(tmp_path, target, original, pid=_dead_pid())
    # the crash: the crashed run's mutant is what's actually on disk, and
    # its journal progress is tracked accurately, matching a real crash.
    mutant = b"def add(a, b):\n    return a - b\n"
    target.write_bytes(mutant)
    record_journal_progress(tmp_path, target, mutant)
    assert list_stale_journals(tmp_path)

    # the developer's live, uncommitted edit -- layered on top of the
    # leftover mutant, never restored, never noticed.
    live_edit = b"def add(a, b):\n    return a + b  # developer's live fix\n"
    target.write_bytes(live_edit)

    restored = restore_stale_journals(tmp_path)

    # nothing was restored -- the live edit survives untouched.
    assert restored == ()
    assert target.read_bytes() == live_edit
    # the stale, now-untrustworthy journal entry was dropped, not left
    # behind to be silently retried (and silently fail the same way)
    # forever.
    assert list_stale_journals(tmp_path) == ()


def test_restore_refuses_and_drops_a_legacy_journal_missing_current_sha256(tmp_path):
    # frob:tests \
    # tests/test_mutate_journal.py::test_restore_refuses_and_drops_a_legacy_journal_mis\
    # sing_current_sha256
    # A pre-T-1327 journal on disk (no `current_sha256` field at all) is
    # just as unverifiable as a genuine mismatch -- fail closed the same
    # way rather than trust it.
    import json

    original = b"original\n"
    target = tmp_path / "m.py"
    target.write_bytes(original)
    write_journal(tmp_path, target, original, pid=_dead_pid())
    journal_path = next((tmp_path / ".frob" / "mutate-backup").glob("*.json"))
    data = json.loads(journal_path.read_text(encoding="utf-8"))
    del data["current_sha256"]
    journal_path.write_text(json.dumps(data), encoding="utf-8")

    live_edit = b"whatever is here now\n"
    target.write_bytes(live_edit)

    restored = restore_stale_journals(tmp_path)

    assert restored == ()
    assert target.read_bytes() == live_edit
    assert list_stale_journals(tmp_path) == ()
