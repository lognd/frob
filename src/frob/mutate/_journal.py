# frob:waive INV006 reason="design-rationale/docstring prose describing \
# already-implemented internal behavior of this module ('only' used informally in \
# comments/docstrings, not a cross-module contract needing its own tracked invariant), \
# matching the T-0585 disposition already applied to src/frob/doctor.py's identical \
# INV006 hit"
"""frob.mutate._journal -- crash-safe backup journal for run_mutations
(T-0857).

`run_mutations` overwrites a REAL source file in place while it tests each
mutant, restoring the original on every normal exit. A killed/crashed
harness (a SIGKILL, an OOM kill, the T-0755 fork-bomb scenario) never
reaches that restore, which used to leave the mutant's `ast.unparse`
output on disk as the file's ONLY surviving copy -- the true content
existed nowhere until a human reconstructed it from git plus hand-
reapplied uncommitted edits (the T-0755 fork-bomb recovery). This module
journals each target's pre-mutation bytes to `.frob/mutate-backup/`
BEFORE the first mutant write, so a crash always leaves a recoverable
original on disk, and restores any stale journal found at the START of
the next `run_mutations` call (or reports it via `frob doctor`).

Design:
- One journal file per target, keyed by a hash of the target's RESOLVED
  path (not the raw path string) so two different files never collide on
  filename and the same file always maps to the same journal regardless
  of how its path was spelled by the caller.
- The journal itself is written atomically (temp file in the same
  directory + `os.replace`, which is atomic on both POSIX and Windows for
  same-filesystem renames) so a crash DURING the journal write never
  leaves a half-written journal that could be mistaken for a valid one.
- Journal content is base64-encoded RAW BYTES, never decoded text --
  restoring is byte-exact, no newline/encoding translation (the T-0441
  CRLF lesson: a naive text-mode round trip silently rewrites CRLF line
  endings to the platform default).
- A journal that already exists for a target is only a problem if its
  recorded content differs from what this run is about to write (a real
  collision -- e.g. two concurrent mutation runs against the same file,
  the exact fork-bomb shape T-0755 hit). The SAME content is idempotent
  and left alone; a DIFFERENT content refuses with `JournalError.Collision`
  rather than silently clobbering another run's backup.
- Every journal records the PID of the process that wrote it. "Stale"
  (eligible for automatic restore, or for `frob doctor` to flag) means the
  writing PID is no longer alive -- a journal whose writer is STILL alive
  is a currently-in-progress run, not a crash, and restoring it out from
  under that live run would itself corrupt the in-progress mutation (this
  was caught by this ticket's own crash-simulation test: an early version
  of `restore_stale_journals` restored unconditionally and would have
  silently destroyed a live concurrent run's target mid-mutation). PID
  liveness is checked with a signal-0 `os.kill` probe -- cheap, and
  correct in exactly the way a crash-recovery check needs: dead means
  gone, no lockfile or heartbeat protocol required.
- STALE-RESTORE CONTENT VERIFICATION (T-1327): a dead/reused-PID writer
  proves the journal's OWNING RUN is gone, but says nothing about whether
  the on-disk file is still what that run actually left there. A restore
  triggered by an unrelated LATER run (`run_mutations`' own startup sweep
  restores every stale journal under `root`, not just its own target)
  used to overwrite unconditionally -- observed clobbering two live,
  uncommitted edits to a file that had been mutated and crash-abandoned
  in an EARLIER, unrelated run, then further hand-edited by a developer
  who never noticed the leftover mutant underneath (T-1203 incident). Every
  journal entry now also records `current_sha256`: the sha256 of whatever
  content this module itself last WROTE to `target` (the original, at
  `write_journal` time; each mutant's bytes in turn, via
  `record_journal_progress`, as `run_mutations` writes it). Restoring
  first re-hashes the file CURRENTLY on disk and compares it against
  `current_sha256` -- a match proves nothing has touched the file since
  this module's own last write (the ordinary crash-recovery case: restore
  proceeds exactly as before); a mismatch proves something else (a later
  legitimate run, or -- the incident case -- a developer's live edit) has
  since written the file, and restoring over it would destroy that content.
  Fail CLOSED on a mismatch: skip the restore, log a WARNING naming the
  file, and drop the now-untrustworthy journal entry rather than either
  overwriting unverified content or leaving a phantom entry `frob doctor`
  would keep reporting forever.
- PID REUSE (a reviewer-caught gap in the first pass of this ticket): a
  signal-0 probe alone cannot tell "the original writer is still running"
  apart from "the OS recycled that PID number for an unrelated process
  after the writer crashed". A journal from a crashed writer whose PID
  got reused would probe as "alive" forever, so `list_stale_journals`
  would exclude it, `DoctorReport.mutate_journals` would stay empty, and
  `frob doctor` would report CLEAN while a real source file sat in mutant
  form -- silently, with no distinguishing signal. Every journal also
  records `starttime` (`/proc/<pid>/stat` field 22, the kernel's own
  process-start timestamp in clock ticks since boot) at write time;
  `_is_stale` treats a journal as stale (safe to restore) whenever the
  PID is dead OR the PID is alive but its CURRENT starttime no longer
  matches the journal's recorded one -- the exact signature of the
  original writer having exited and the PID having been handed to a
  different process. This is Linux-specific (`/proc` is not portable);
  where `/proc/<pid>/stat` cannot be read at all (`starttime` persisted as
  `None`), liveness falls back to PID-only -- the residual PID-reuse
  window this fallback still carries. Restoring the wrong file in that
  fallback window is prevented in practice by `write_journal`'s own
  content-hash collision check (the next legitimate run's own original
  bytes will very likely differ from whatever the recycled-PID journal
  recorded, in which case `write_journal` refuses rather than corrupts) --
  but that is a lucky side effect, not a guarantee: an operator whose
  `frob doctor` stays clean while a target keeps refusing with
  `JournalCollision` should inspect `.frob/mutate-backup/<hash>.json` by
  hand -- the recorded PID may have been reused.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path

from pydantic import BaseModel
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/modules/mutate.md#crash-safe-backup-journal-t-0857
#: Directory (relative to the mutation run's `root`) backup journals live
#: under -- derived, gitignored bookkeeping (`.frob/` is already
#: gitignored repo-wide), never committed.
JOURNAL_DIR = ".frob/mutate-backup"


class _Unset:
    """Sentinel type distinguishing "`starttime` not passed, compute it"
    from "`starttime=None` passed explicitly" (a genuine no-`/proc`
    result) in `write_journal`'s keyword-only `starttime` parameter."""


_UNSET = _Unset()


# frob:doc docs/modules/mutate.md#crash-safe-backup-journal-t-0857
class JournalError(ErrorSet):
    """Fallible outcomes of journal operations."""

    Collision = (
        "a journal already exists for this target with DIFFERENT content -- "
        "refusing to overwrite (a concurrent mutation run may be active)"
    )


# frob:doc docs/modules/mutate.md#crash-safe-backup-journal-t-0857
# frob:waive COV007 reason="T-0871: same -- see COV005 waiver above"
class _MutationJournalEntry(BaseModel):
    """One target file's pre-mutation bytes, persisted so `run_mutations`
    can recover it after a crash (T-0857). `target` is `target`'s path
    relative to the run's `root` when possible (absolute otherwise, e.g.
    a target outside `root`) -- used only for display/restore, never for
    the journal's own filename (see `_journal_key`). `sha256` fingerprints
    `content_b64`'s DECODED bytes so a same-content journal write can be
    told apart from a real collision without decoding twice. `starttime`
    (T-0857 reviewer fix) is the writing PID's `/proc/<pid>/stat` field-22
    process-start timestamp at write time, `None` when `/proc` could not
    be read (non-Linux, or a sandboxed/restricted environment) -- see the
    module docstring's PID-reuse section for why this exists and what its
    absence costs. `current_sha256` (T-1327) is the sha256 of whatever
    content this module itself last WROTE to the target -- `sha256` at
    `write_journal` time, then each mutant's own bytes as
    `record_journal_progress` is called in step with `run_mutations`'
    write loop. A restore compares the file's CURRENT on-disk hash against
    this field, not against `sha256`, since by the time a restore is
    warranted the file legitimately holds mutant bytes, not the original
    -- see the module docstring's stale-restore verification section."""

    model_config = {}

    target: str
    sha256: str
    content_b64: str
    pid: int
    starttime: str | None = None
    current_sha256: str | None = None


# frob:doc docs/modules/mutate.md#crash-safe-backup-journal-t-0857
class StaleJournal(BaseModel):
    """One journal `list_stale_journals` (read-only, `frob doctor`'s view)
    or `restore_stale_journals` (restoring, `run_mutations`' own startup
    check) found on disk -- the crash-recovery signal T-0857 exists to
    surface. Presence of ANY `StaleJournal` means a previous mutation run
    did not exit normally."""

    model_config = {}

    target: str
    journal_path: str


def _journal_key(target: Path) -> str:
    """Stable, filesystem-safe key for `target`'s resolved path: hashing
    (rather than the raw path) sidesteps filesystem-illegal characters and
    keeps every journal filename a fixed, predictable length."""
    return hashlib.sha256(str(target.resolve()).encode("utf-8")).hexdigest()


def _journal_file(root: Path, target: Path) -> Path:
    """The journal path for `target` under `root`'s `JOURNAL_DIR`."""
    return root / JOURNAL_DIR / f"{_journal_key(target)}.json"


def _target_display(root: Path, target: Path) -> str:
    """`target` rendered relative to `root` when possible, absolute
    otherwise -- for a human-readable journal entry and restore lookup."""
    try:
        resolved = target.resolve()
        return str(resolved.relative_to(root.resolve()))
    except Exception:
        return str(target)


# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to os.kill itself; every exception \
# os.kill can raise is an OSError subclass, and ProcessLookupError/ \
# PermissionError/OSError together already cover the full hierarchy"
def _pid_alive(pid: int) -> bool:
    """Whether `pid` names a currently-running process, via a signal-0
    probe (`os.kill(pid, 0)`, which sends no actual signal). A
    `ProcessLookupError` means the PID is gone (dead -- eligible for
    crash-recovery restore); a `PermissionError` means the PID exists but
    is owned by someone else (still alive, just not ours to signal) --
    treated as alive, the conservative choice (never restore out from
    under a process we merely lack permission to probe fully)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _pid_starttime(pid: int) -> str | None:
    """`pid`'s process-start timestamp (field 22 of `/proc/<pid>/stat`,
    clock ticks since boot -- stable for the lifetime of that PID number,
    and different for whatever process the kernel hands the PID to next),
    or `None` when `/proc` is unavailable (non-Linux) or the file cannot
    be read/parsed right now (the process just exited, a sandboxed
    environment, ...). Comm (`(name)`) can itself contain spaces or
    parentheses, so this splits on the LAST `)` rather than tokenizing
    naively -- everything after it is `state ppid ... starttime ...`,
    space-separated, with `starttime` at (0-based) offset 19 in that
    remainder (field 22 overall, minus the 3 fields -- pid, comm, state --
    consumed before the remainder starts)."""
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
        after_comm = raw.rsplit(")", 1)[1]
        return after_comm.split()[19]
    except Exception:
        return None


def _is_stale(entry: _MutationJournalEntry) -> bool:
    """Whether `entry`'s journal is eligible for crash-recovery restore
    (T-0857): its writing PID is dead, OR the PID is alive but its CURRENT
    `/proc` starttime no longer matches `entry.starttime` -- the PID-reuse
    case (a reviewer-caught gap in this ticket's first pass, see the
    module docstring): the ORIGINAL writer crashed and the OS has since
    handed that same PID number to an unrelated process, which a bare
    signal-0 liveness probe cannot tell apart from the original writer
    still legitimately running. When `entry.starttime` is `None` (`/proc`
    was unavailable at write time) this falls back to PID-only liveness --
    the documented residual PID-reuse window on platforms/environments
    without `/proc`. A journal whose writer is STILL alive (same PID, same
    starttime) belongs to an in-progress run, not a crash -- treating it
    as stale and restoring it would corrupt that live run's mutation
    mid-flight."""
    if not _pid_alive(entry.pid):
        return True
    if entry.starttime is None:
        return False
    current = _pid_starttime(entry.pid)
    if current is None:
        # /proc unreadable right now (a narrow race: the process exited
        # between _pid_alive's probe and this read) -- conservatively NOT
        # stale rather than risk restoring out from under a process that
        # may still be alive; the next call re-checks from scratch.
        return False
    return current != entry.starttime


def _entry_target_path(root: Path, entry: _MutationJournalEntry) -> Path:
    """Resolve a persisted `_MutationJournalEntry.target` back to a real
    `Path`: relative entries are joined onto `root` (mirroring
    `_target_display`'s relative branch), absolute entries are used as-is."""
    recorded = Path(entry.target)
    return recorded if recorded.is_absolute() else root / recorded


def _read_journal_file(path: Path) -> _MutationJournalEntry | None:
    """Best-effort load of a journal file -- `None` if absent, unreadable,
    or malformed (treated as "no journal", never raised): the journal is
    disposable crash-recovery bookkeeping, not a source of truth worth
    failing a whole run over if it is itself corrupt)."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return _MutationJournalEntry.model_validate(data)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        _log.warning("mutate: journal at %s unreadable/malformed: %s", path, exc)
        return None


# frob:doc docs/modules/mutate.md#crash-safe-backup-journal-t-0857
# frob:tests \
# tests/test_mutate_journal.py::test_write_journal_is_idempotent_for_same_content \
# kind="unit"  # noqa: E501
# frob:tests \
# tests/test_mutate_journal.py::test_write_journal_refuses_on_content_collision \
# kind="unit"  # noqa: E501
def write_journal(
    root: Path,
    target: Path,
    original: bytes,
    *,
    pid: int | None = None,
    starttime: str | None | _Unset = _UNSET,
) -> Result[None, JournalError]:
    """Persist `original` (the target's pre-mutation bytes) to its journal
    file BEFORE the first mutant write, atomically (temp file in the same
    directory + `os.replace`) so a crash mid-write never leaves a half-
    written journal. Idempotent when a journal already exists for `target`
    with the SAME content; `Err(JournalError.Collision)` when an existing
    journal's content differs -- a genuine sign of a second, concurrent
    mutation run against the same file (the T-0755 fork-bomb scenario),
    never silently overwritten. `pid` defaults to `os.getpid()` (the real
    caller in every production path); a test simulating a crashed OTHER
    process passes an explicit dead PID instead. `starttime` defaults to
    `_pid_starttime(pid)` (the real caller's own path, T-0857 reviewer
    fix); a test simulating a PID-REUSE false-liveness (a live PID whose
    recorded starttime no longer matches -- the recycled-PID case, see the
    module docstring) passes an explicit mismatched value instead."""
    path = _journal_file(root, target)
    sha256 = hashlib.sha256(original).hexdigest()
    existing = _read_journal_file(path)
    if existing is not None:
        if existing.sha256 == sha256:
            _log.debug(
                "mutate: journal for %s already present with matching content, no-op",
                target,
            )
            return Ok(None)
        _log.error(
            "mutate: journal collision for %s -- existing journal content "
            "differs from this run's original bytes, refusing to overwrite "
            "(possible concurrent mutation run against the same file)",
            target,
        )
        return Err(JournalError.Collision)
    resolved_pid = pid if pid is not None else os.getpid()
    resolved_starttime: str | None
    if isinstance(starttime, _Unset):
        resolved_starttime = _pid_starttime(resolved_pid)
    else:
        resolved_starttime = starttime
    entry = _MutationJournalEntry(
        target=_target_display(root, target),
        sha256=sha256,
        content_b64=base64.b64encode(original).decode("ascii"),
        pid=resolved_pid,
        starttime=resolved_starttime,
        # T-1327: at write time the file on disk IS still the original
        # (no mutant has been written yet), so the "last known on-disk"
        # hash starts out identical to `sha256`; `record_journal_progress`
        # advances it as each mutant is subsequently written.
        current_sha256=sha256,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp{os.getpid()}")
    try:
        tmp_path.write_text(entry.model_dump_json(), encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        # T-0857 reviewer nit: an IO error between the write and the
        # rename must not leave a stray `.tmpNNN` file behind -- best
        # effort, `missing_ok` covers the normal (already-renamed) case.
        tmp_path.unlink(missing_ok=True)
    _log.info("mutate: journaled pre-mutation bytes for %s to %s", target, path)
    return Ok(None)


# frob:doc docs/modules/mutate.md#crash-safe-backup-journal-t-0857
# frob:tests \
# tests/test_mutate_journal.py::test_record_journal_progress_tracks_last_written_conten\
# t \
# kind="unit"  # noqa: E501
def record_journal_progress(root: Path, target: Path, current: bytes) -> None:
    """Update `target`'s journal entry's `current_sha256` (T-1327) to the
    hash of `current` -- called by `run_mutations`' write loop immediately
    after each mutant's bytes are written to disk, so the journal always
    reflects exactly what this module itself last wrote there. Best-effort
    and silent on any failure (missing/malformed journal, IO error): this
    is bookkeeping for a LATER restore's verification, never something a
    mutation run should abort over. A missing/unreadable journal here
    simply means a subsequent restore falls back to its own
    unverifiable-content handling (skip and drop, fail closed) rather than
    silently trusting stale state."""
    path = _journal_file(root, target)
    entry = _read_journal_file(path)
    if entry is None:
        return
    updated = entry.model_copy(
        update={"current_sha256": hashlib.sha256(current).hexdigest()}
    )
    tmp_path = path.with_name(f"{path.name}.tmp{os.getpid()}")
    try:
        tmp_path.write_text(updated.model_dump_json(), encoding="utf-8")
        os.replace(tmp_path, path)
    except OSError as exc:
        _log.warning(
            "mutate: failed to record journal progress for %s: %s", target, exc
        )
    finally:
        tmp_path.unlink(missing_ok=True)


# frob:doc docs/modules/mutate.md#crash-safe-backup-journal-t-0857
# frob:tests tests/test_mutate_journal.py::test_remove_journal_after_restore \
# kind="unit"  # noqa: E501
def remove_journal(root: Path, target: Path) -> None:
    """Delete `target`'s journal file after a successful restore -- called
    on every normal `run_mutations` exit. Best-effort: a missing/already-
    removed journal is not an error."""
    path = _journal_file(root, target)
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        _log.warning("mutate: failed to remove journal at %s: %s", path, exc)


def _iter_journal_files(root: Path) -> tuple[Path, ...]:
    """Every journal file currently on disk under `root`'s `JOURNAL_DIR`,
    sorted for deterministic iteration order."""
    journal_dir = root / JOURNAL_DIR
    if not journal_dir.exists():
        return ()
    return tuple(sorted(journal_dir.glob("*.json")))


# frob:doc docs/modules/mutate.md#crash-safe-backup-journal-t-0857
# frob:tests \
# tests/test_mutate_journal.py::test_list_stale_journals_reports_without_restoring \
# kind="unit"  # noqa: E501
def list_stale_journals(root: Path) -> tuple[StaleJournal, ...]:
    """Read-only report of every STALE journal on disk under `root`
    (T-0857) -- `frob doctor`'s view. "Stale" means the writing PID is no
    longer alive (`_is_stale`); a journal whose writer is still running is
    a normal in-progress mutation run, not a crash, and is deliberately
    excluded here (surfacing it would make `frob doctor` cry wolf on an
    ordinary concurrent `frob mutate` invocation). Presence of any
    returned entry means a previous mutation run did NOT exit normally and
    a target still needs restoring; this function never restores anything
    itself (doctor is a diagnostic, not a repair tool)."""
    stale: list[StaleJournal] = []
    for path in _iter_journal_files(root):
        entry = _read_journal_file(path)
        if entry is None or not _is_stale(entry):
            continue
        stale.append(StaleJournal(target=entry.target, journal_path=str(path)))
    return tuple(stale)


# frob:doc docs/modules/mutate.md#crash-safe-backup-journal-t-0857
# frob:tests \
# tests/test_mutate_journal.py::test_restore_stale_journals_is_byte_exact_crlf \
# kind="unit"  # noqa: E501
# frob:tests \
# tests/test_mutate_journal.py::test_restore_stale_journals_after_simulated_crash \
# kind="unit"  # noqa: E501
def restore_stale_journals(root: Path) -> tuple[str, ...]:
    """Restore every STALE journal found under `root`'s `JOURNAL_DIR`
    (T-0857): called at the START of `run_mutations`, before any new
    mutation begins, so a crash-left mutant from a PRIOR run is put back
    before this run touches anything. "Stale" means the writing PID is no
    longer alive (`_is_stale`) -- a journal whose writer is STILL running
    belongs to another in-progress mutation run against the same file and
    is deliberately left untouched (restoring it would corrupt that live
    run's mutation mid-flight; its own `write_journal` collision check is
    what protects it, not this function). Restoring writes the journaled
    RAW BYTES back verbatim (`Path.write_bytes`, no text-mode decoding) --
    byte-exact, honoring the T-0441 CRLF lesson. Returns the display path
    of every target actually restored; each restore is logged at WARNING
    (not INFO), since a stale journal existing at all means a previous run
    crashed and this is a mid-recovery finding, not routine bookkeeping."""
    restored: list[str] = []
    for path in _iter_journal_files(root):
        entry = _read_journal_file(path)
        if entry is None:
            continue
        if not _is_stale(entry):
            _log.debug(
                "mutate: journal for %s owned by live pid %d, not restoring "
                "(in-progress run, not a crash)",
                entry.target,
                entry.pid,
            )
            continue
        target_path = _entry_target_path(root, entry)
        # T-1327: the writer being dead only proves the OWNING RUN is
        # gone -- it says nothing about whether the file it left behind
        # is still that exact content. Verify the on-disk bytes still
        # match what this module itself last wrote (`current_sha256`)
        # before overwriting; a mismatch (a later legitimate run, or a
        # developer's live edit layered on top of the leftover mutant --
        # the T-1203 incident) means restoring would destroy content that
        # is not this journal's to clobber. Fail CLOSED: skip, warn, and
        # drop the now-untrustworthy entry rather than overwrite or leave
        # a phantom entry `frob doctor` would keep reporting forever. A
        # journal with no `current_sha256` at all (pre-T-1327 format) is
        # equally unverifiable and handled the same way.
        if entry.current_sha256 is None or (
            target_path.exists()
            and hashlib.sha256(target_path.read_bytes()).hexdigest()
            != entry.current_sha256
        ):
            _log.warning(
                "mutate: stale journal for %s no longer matches its last known "
                "on-disk content -- the file was modified since this journal "
                "was written (a later run, or a live edit); leaving it "
                "untouched and dropping the stale entry (%s)",
                entry.target,
                path,
            )
            path.unlink(missing_ok=True)
            continue
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(base64.b64decode(entry.content_b64))
        except (OSError, ValueError) as exc:
            _log.error(
                "mutate: failed to restore stale journal for %s from %s: %s -- "
                "journal left in place, manual recovery required",
                entry.target,
                path,
                exc,
            )
            continue
        _log.warning(
            "mutate: restored stale mutation-backup journal for %s (a prior "
            "mutation run did not exit normally)",
            entry.target,
        )
        path.unlink(missing_ok=True)
        restored.append(entry.target)
    return tuple(restored)


__all__ = [
    "JOURNAL_DIR",
    "JournalError",
    "StaleJournal",
    "list_stale_journals",
    "record_journal_progress",
    "remove_journal",
    "restore_stale_journals",
    "write_journal",
]
