# frob:waive TEST003 reason="pre-existing T-0319 debt, system kind only"
"""`frob doctor`: verify the native extensions (`frob_core`, `strata_core`)
are importable in the current environment and print exact remediation when
they are not.

Follow-up from T-0316: a plain `uv tool upgrade frob` (or `uv tool install
--force --reinstall frob` without `--with`) can silently strip the natives
`make install-tool` added, degrading `frob dup`'s R3+ rungs and every
`frob sys` command to the honest-but-easy-to-miss `SYS004` /
`DupError.CoreUnavailable` failure path. This module makes that same check a
first-class, explicit CLI surface instead of a paragraph in
docs/guides/install.md.

T-0570: `run_diagnosis` also fingerprints every derived artifact `frob`
writes under `.frob/` (plus the committed `frob-coverage.lock.json`) and
reports which ones are present-but-corrupt, BEFORE any gate consumes them.
Three real incidents motivate this: a stale fixture `dup.db` silently
flipping detector results (T-0517), `make coverage` clobbering the native
build mid-run and producing 44 phantom `frob check` errors, and a coverage
stamp lagging the source it claims to describe. Each of those used to
surface as a pile of confusing downstream `frob check`/`frob dup` findings
with no single "the derived state itself is stale" signal; `frob doctor`
is the first thing an agent runs, so this is the doctor-first choke point
that catches it before dozens of misleading findings follow. Wiring an
actual BLOCK into `frob check`/`frob gates` (rather than just reporting
here) is out of this ticket's scope -- `src/frob/check/**` and
`src/frob/gates/**` carry other agents' live leases at the time of this
ticket -- see T-0570's Done report for the follow-up ticket filed for that
(landed as T-0603).

T-0604: `run_diagnosis` also persists a `{artifact name: fingerprint}`
manifest under `.frob/derived-state-manifest.json` after every run and
compares against the manifest the PREVIOUS run left behind
(`_detect_derived_state_drift`), so a valid-format artifact that was
silently REWRITTEN out-of-band between two `frob doctor` invocations (not
just one that is malformed right now, T-0570's check) shows up as named
content drift with both fingerprints. This is deliberately informational
(`DoctorReport.drift`, does not affect `healthy`) -- see that function's
docstring for why treating ordinary cache churn between two doctor runs
as a hard failure would be wrong.

T-0857: `run_diagnosis` also reports every stale `frob mutate` backup
journal under `.frob/mutate-backup/` (`DoctorReport.mutate_journals`),
read-only, via `frob.mutate._journal.list_stale_journals`. A present
journal means a prior `frob mutate` run crashed before restoring its
target's original bytes -- UNLIKE `derived_state`'s corrupt-cache case,
this DOES feed into `healthy`/`remediation`: a stale journal names a real
source file currently sitting in mutant form on disk, not a disposable
cache. `frob doctor` itself never restores; it only reports and points at
the fix (re-running `frob mutate` against the same target, whose
`restore_stale_journals` startup check performs the actual restore).

Staleness itself is PID-reuse-aware (a reviewer-caught gap in this
ticket's first pass): a bare "is the writer's PID alive" probe cannot
tell a crashed writer whose PID number the OS later recycled apart from
the original writer still legitimately running, so a naive version of
this check would report CLEAN forever once that recycle happened, with a
real source file silently sitting in mutant form. `frob.mutate._journal`
also records the writer's `/proc/<pid>/stat` starttime and treats a live
PID with a MISMATCHED starttime as stale too -- see
`docs/modules/mutate.md#crash-safe-backup-journal-t-0857` for the full
mechanism. That check itself falls back to PID-only liveness wherever
`/proc` cannot be read (non-Linux, sandboxed environments) -- the
residual PID-reuse window in that fallback case is not detected by
`frob doctor`: if `frob doctor` stays clean but a target keeps refusing
with `JournalCollision`, inspect `.frob/mutate-backup/<hash>.json` by
hand -- the recorded PID may have been reused.
"""

# frob:waive LARGE001 reason="T-1651-grade: this module's own docstring states its one \
# job directly -- verify the native extensions are importable and print exact \
# remediation when they are not, plus (T-0570) fingerprint every derived artifact frob \
# writes under .frob/ for present-but-corrupt detection BEFORE any gate consumes them. \
# Both are the same 'is the installed environment actually usable' diagnostic concern \
# `frob doctor` exists to answer in one CLI surface, not two."

from __future__ import annotations

import importlib
import json
import os
import platform
import re
import shutil
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from enum import StrEnum
from importlib.metadata import version
from pathlib import Path

from pydantic import BaseModel
from typani import Err, Ok
from typani.error_set import ErrorSet
from typani.result import Result

import frob as _frob_pkg
from frob.derived_state import DerivedArtifactStatus, verify_derived_state
from frob.lang._project_detect import (
    UnityProjectDetectError,
    UnityProjectInfo,
    detect_unity_project,
)
from frob.logging import get_logger
from frob.mutate._journal import StaleJournal, list_stale_journals
from frob.process import net_enabled
from frob.process._guard import guarded_subprocess_run
from frob.process._lock import derived_state_lock
from frob.repo_meta import stale_binary_warning
from frob.scaffold._managed import ManagedBlockStatus, scaffold_conformance_status

_log = get_logger(__name__)

# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
#: the exact remediation command printed when a native extension is missing.
REMEDIATION_HINT = (
    "run 'make core' (build in-place) or 'make install-tool' "
    "(reinstall the frob CLI with natives bundled)"
)

# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
#: Native extension module names `frob doctor` checks for importability.
NATIVE_EXTENSIONS: tuple[str, ...] = ("frob_core", "strata_core")


# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
class NativeExtensionStatus(BaseModel):
    """Importability and version of one native extension, as observed by
    `frob doctor`."""

    model_config = {}

    name: str
    available: bool
    version: str | None = None


# frob:doc docs/guides/install.md#derived-state-integrity-manifest-t-0570
# frob:waive COV007 reason="T-0871: same -- see COV005 waiver above"
class _DerivedArtifactDrift(BaseModel):
    """Content drift detected for one derived artifact ACROSS TWO `frob
    doctor` runs (T-0604): its fingerprint from the manifest the previous
    run persisted no longer matches this run's live fingerprint, meaning
    something rewrote the artifact between the two invocations. This is
    orthogonal to `DerivedArtifactStatus.healthy` (T-0570's per-run
    format/corruption check) -- an artifact can drift while staying
    perfectly well-formed (a legitimate rewrite by a stale tool or a
    foreign process is still valid SQLite/JSON, just different content
    than last observed)."""

    model_config = {}

    name: str
    path: str
    previous_fingerprint: str
    current_fingerprint: str


# frob:ticket T-1132
# frob:doc docs/guides/install.md#malformed-ticket-edge-scan-t-1132
class MalformedTicketEdge(BaseModel):
    """One malformed `blocked_by`/`parent` entry found in the shared ledger
    (T-1132, the T-0380 incident: an empty-string `blocked_by` entry left
    a ticket silently undoable for days with nothing surfacing why)."""

    model_config = {}

    ticket_id: str
    field: str  # "blocked_by" or "parent"
    value: str
    ledger_file: str


def _malformed_edges_in_dict(
    ticket_id: str, data: dict, ledger_file: str
) -> list[MalformedTicketEdge]:
    """Every malformed `blocked_by`/`parent` entry in one raw ticket dict
    (T-1132) -- both fields tolerate being entirely absent (older/partial
    ledger rows), but a PRESENT value must satisfy `is_valid_ticket_ref`."""
    from frob.tickets import is_valid_ticket_ref

    found: list[MalformedTicketEdge] = []
    blocked_by = data.get("blocked_by") or ()
    if isinstance(blocked_by, (list, tuple)):
        for entry in blocked_by:
            if not isinstance(entry, str) or not is_valid_ticket_ref(entry):
                found.append(
                    MalformedTicketEdge(
                        ticket_id=ticket_id,
                        field="blocked_by",
                        value=str(entry),
                        ledger_file=ledger_file,
                    )
                )
    parent = data.get("parent")
    if parent is not None and (
        not isinstance(parent, str) or not is_valid_ticket_ref(parent)
    ):
        found.append(
            MalformedTicketEdge(
                ticket_id=ticket_id,
                field="parent",
                value=str(parent),
                ledger_file=ledger_file,
            )
        )
    return found


# frob:ticket T-1132
# frob:doc docs/guides/install.md#malformed-ticket-edge-scan-t-1132
# frob:tests tests/system/test_cli_doctor.py kind="integration"
def scan_malformed_ticket_edges(root: Path) -> list[MalformedTicketEdge]:
    """Every malformed `blocked_by`/`parent` entry across `tickets.md` AND
    `tickets-archive.md` (T-1132) -- an empty string, or anything not
    shaped like a real `T-####`/`T-draft-<hex>` id.

    Reads RAW frontmatter dicts (`frob.tickets._store.
    iter_raw_ledger_frontmatter`), never the strict `Ticket` loader --
    `Ticket.model_validate` deliberately does NOT reject a malformed edge
    (see that model's docstring), specifically so this scan can find one
    WITHOUT the rest of the toolchain (`load_all` and everything built on
    it) being at risk of a single bad edge hard-failing the entire shared
    ledger's load. Missing ledger file(s) (a fresh checkout with no
    `tickets-archive.md` yet) contribute zero findings, not an error."""
    from frob.tickets._store import (
        archive_path,
        iter_raw_ledger_frontmatter,
        ledger_path,
    )

    found: list[MalformedTicketEdge] = []
    for path in (ledger_path(root), archive_path(root)):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for ticket_id, data in iter_raw_ledger_frontmatter(text):
            found.extend(_malformed_edges_in_dict(ticket_id, data, path.name))
    return found


def _malformed_edges_remediation(edges: tuple[MalformedTicketEdge, ...]) -> str:
    """Remediation hint naming each malformed edge's ticket/field (T-1132)."""
    names = ", ".join(f"{e.ticket_id}.{e.field}={e.value!r}" for e in edges)
    return (
        f"malformed ticket edge(s) found: {names} -- fix by hand in tickets.md/"
        "tickets-archive.md (empty-string or non-T-#### blocked_by/parent "
        "entries are refused going forward at write time, but an existing "
        "one is not auto-repaired)"
    )


# frob:ticket T-1131
# frob:doc docs/guides/install.md#stale-ticket-lease-scan-t-1131
# frob:tests tests/system/test_cli_doctor.py kind="integration"
def scan_stale_ticket_leases(root: Path) -> tuple[str, ...]:
    """Every ticket id `frob.tickets._reconcile.reconcile`'s dry-run
    (`apply=False`) would requeue right now (T-1131, the T-1050 incident):
    an `IN_PROGRESS` ticket with no corresponding LIVE cross-worktree
    lease -- either the lease file's own worktree path no longer exists
    (T-0473's own liveness probe already judged it stale and pruned the
    file) or no lease was ever recorded for it at all. This is a pure
    READ, never a mutation: `reconcile(root, apply=False)` is the exact
    same detection `frob ticket reconcile --apply`/individual `frob
    ticket requeue <id>` perform, reused rather than reimplemented here
    -- `frob doctor` only ever reports, it never repairs. Degrades to an
    empty tuple on any load failure (a malformed ledger is `frob check`'s
    own gate to catch, not doctor's job to duplicate)."""
    from frob.tickets._reconcile import reconcile

    result = reconcile(root, apply=False)
    if result.is_err:
        _log.warning(
            "doctor: stale-ticket-lease scan could not load the ledger: %s",
            result.danger_err,
        )
        return ()
    return result.danger_ok.requeued_tickets


# frob:doc docs/guides/install.md#live-land-process-report-t-1515
# frob:ticket T-1515
# frob:ticket T-1634
# frob:ticket T-1795
class LiveLandProcess(BaseModel):
    """One holder observed in `root`'s `.frob/land.lock` content (T-1515):
    who is (or, if `alive` is `False`, WAS -- an orphaned/crashed holder
    that never released the file) currently running `frob ticket land`
    against this repo. `alive` is a best-effort liveness probe
    (`frob.tickets._land._probe_land_lock_pid_liveness`, POSIX-only) --
    `None` when it could not be determined (a non-POSIX platform, or a
    `PermissionError` probing a pid this process does not own). T-1634:
    `alive is False` (CONFIRMED dead, never ambiguous) is informational,
    not a health failure -- see `_assemble_doctor_report`'s `healthy`
    computation. The dead holder's `flock` was already released by the
    kernel the instant that process exited, so nothing is actually
    blocked; the next real `_land_lock` acquisition self-heals the file's
    stale content and logs its own WARNING reclaim line (T-1634).

    `ticket_id` (T-1795): the ticket the holder is landing, read
    verbatim from the SAME lock-holder JSON `_land_lock` writes on
    acquisition (`_land_lock_holder_metadata`'s `ticket_id` key) --
    `None` for a lock file written before T-1795 (no key present) or an
    unparseable one, never a guess. This is what makes `frob doctor` a
    real substitute for `pgrep -f "frob ticket land T-XXXX"`: a coordinator
    checking "is MY ticket's land still running" no longer needs a
    process-table grep that can match its own polling loop's argv (the
    T-1795 incident: a `until ! pgrep -f "frob ticket land T-XXXX"` loop
    matched itself and hung 19 minutes past the land's actual exit) --
    one `frob doctor` read names the ticket directly."""

    model_config = {}

    pid: int
    session_id: str
    started_at: str
    alive: bool | None
    ticket_id: str | None = None


# frob:doc docs/guides/install.md#live-land-process-report-t-1515
# frob:ticket T-1515
# frob:ticket T-1634
def scan_live_land_processes(root: Path) -> LiveLandProcess | None:
    """T-1515: read `root`'s `.frob/land.lock` content (written by
    `frob.tickets._land._land_lock` on acquisition) and report who holds
    it, if anyone -- `None` if the file does not exist, is empty, or does
    not parse as the expected metadata shape (never raised: this is a
    diagnostic read, not a gate). This is what makes 'is a land process
    live against this repo right now' a single `frob doctor` command
    instead of a human having to `ps`/`lsof` the lock file by hand before
    starting a new session (the exact orphaned-driver blind spot T-1495's
    2026-08-04 incident hit). T-1634: the liveness probe itself now lives
    in `frob.tickets._land._probe_land_lock_pid_liveness` -- the SAME
    confirmed_absent/ambiguous three-state notion `_land_lock`'s own
    reclaim-logging (T-1634) and `frob.tickets._leases._probe_worktree_
    liveness` (T-0782) already use, so this repo has exactly one pid-
    liveness rule for a land.lock holder, not a second copy re-derived
    here."""
    from frob.tickets._land import (
        _LAND_LOCK_REL,
        _probe_land_lock_pid_liveness,
        _read_land_lock_holder,
    )

    path = root / _LAND_LOCK_REL
    holder = _read_land_lock_holder(path)
    if holder is None:
        return None
    pid = holder.get("pid")
    session_id = holder.get("session_id")
    started_at = holder.get("started_at")
    if (
        not isinstance(pid, int)
        or not isinstance(session_id, str)
        or not isinstance(started_at, str)
    ):
        return None
    # frob:ticket T-1795
    raw_ticket_id = holder.get("ticket_id")
    ticket_id = raw_ticket_id if isinstance(raw_ticket_id, str) else None
    alive = _probe_land_lock_pid_liveness(pid)
    return LiveLandProcess(
        pid=pid,
        session_id=session_id,
        started_at=started_at,
        alive=alive,
        ticket_id=ticket_id,
    )


# frob:ticket T-1515
# frob:ticket T-1634
def _live_land_process_remediation(proc: LiveLandProcess) -> str:
    """Remediation hint naming the observed land.lock holder (T-1515).
    T-1634: called for `alive in (False, None)` -- a CONFIRMED-dead holder
    (`False`) is disclosed but self-healing (the next `frob ticket land`
    reclaims and logs it automatically, and does not block `healthy`
    anymore); an AMBIGUOUS probe (`None`) is NOT self-healing (this repo
    cannot confirm the holder is actually gone, so it still blocks
    `healthy` exactly like before, per `_assemble_doctor_report`'s own
    confirmed_absent/ambiguous split). Never called for `alive is True`
    -- that is a normal, informational, in-flight land, not a finding."""
    # frob:ticket T-1795
    ticket_note = f" for {proc.ticket_id}" if proc.ticket_id else ""
    if proc.alive is False:
        return (
            f"land.lock names pid {proc.pid} (session {proc.session_id}, "
            f"started {proc.started_at}{ticket_note}) which is NOT running -- "
            "an orphaned lock file from a crashed/killed land; harmless (the "
            "OS already released the underlying lock) and self-healing: the "
            "next `frob ticket land` reclaims and overwrites it "
            "automatically, or run `rm .frob/land.lock` by hand to clear it "
            "immediately"
        )
    return (
        f"land.lock is held by pid {proc.pid} (session {proc.session_id}, "
        f"started {proc.started_at}{ticket_note}), "
        f"{'alive' if proc.alive else 'liveness unknown'} -- a `frob ticket "
        "land` is (or may be) mid-run against this repo right now"
    )


def _stale_ticket_leases_remediation(stale_ids: tuple[str, ...]) -> str:
    """Remediation hint naming each stuck ticket and the exact fix
    (T-1131)."""
    names = ", ".join(stale_ids)
    return (
        f"ticket(s) stuck in-progress with no live lease: {names} -- run "
        "`frob ticket requeue <id>` for each (or `frob ticket reconcile "
        "--apply` to requeue all of them at once)"
    )


# frob:ticket T-1161
# frob:doc docs/guides/install.md#venv-shim-shebang-scan-t-1161
class VenvShimDrift(BaseModel):
    """One `.venv/bin/` entrypoint script whose shebang points at a
    PYTHON INTERPRETER outside this checkout's own venv (T-1161, the
    2026-07-28 incident): a `uv` operation run from a sibling worktree
    rewrote the root venv's `pytest` shim to shebang at that worktree's
    own `.venv/bin/python`; once that worktree was removed, every `uv run
    pytest` in the root checkout broke with a dangling interpreter path,
    and `collect_python_tests` misattributed the resulting failure into a
    per-evidence COV003 flood instead of naming the real, single-cause
    fault."""

    model_config = {}

    script: str
    shebang_path: str
    expected_venv_bin: str


# frob:ticket T-1161
# frob:doc docs/guides/install.md#venv-shim-shebang-scan-t-1161
# tests/system/test_cli_doctor.py::TestDoctorVenvShims.test_flags_shebang_outside_venv
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to Path.iterdir/ \
# Path.resolve/bytes.decode, stdlib pathlib/bytes calls the resolver cannot statically \
# bound; every locally-visible fallible step (the two entry-level OSError sites, the \
# shebang-dir resolve) is already caught above"
def scan_venv_shims(root: Path) -> tuple[VenvShimDrift, ...]:
    """Every `.venv/bin/*` script under `root` whose `#!` shebang line
    resolves to a python interpreter OUTSIDE `root`'s own `.venv/bin/`
    (T-1161). A `uv sync`/`uv pip install --python <other venv>` run from
    the wrong cwd rewrites a shim's shebang absolute path in place with no
    other visible symptom until the target interpreter later vanishes
    (e.g. a sibling worktree is removed) -- this compares each shim's
    recorded shebang path against `root`'s own resolved `.venv/bin`
    directory rather than waiting for the interpreter to actually go
    missing, so a shim pointed at a STILL-EXISTING but wrong venv is also
    caught. A missing `.venv/bin` directory (no venv created yet)
    contributes zero findings, not an error -- that is an ordinary
    not-yet-set-up state, not drift."""
    venv_bin = root / ".venv" / "bin"
    if not venv_bin.is_dir():
        return ()
    try:
        expected_bin = venv_bin.resolve()
    except OSError:
        _log.warning("doctor: could not resolve %s", venv_bin)
        return ()
    found: list[VenvShimDrift] = []
    for entry in sorted(venv_bin.iterdir()):
        if not entry.is_file() or entry.is_symlink():
            continue
        try:
            with entry.open("rb") as fh:
                first_line = fh.readline(4096)
        except OSError:
            continue
        if not first_line.startswith(b"#!"):
            continue
        shebang_path = first_line[2:].decode("utf-8", errors="replace").strip()
        if not shebang_path or "python" not in Path(shebang_path).name:
            continue
        shebang_dir = Path(shebang_path).parent
        try:
            resolved_shebang_dir = shebang_dir.resolve()
        except OSError:
            resolved_shebang_dir = shebang_dir
        if resolved_shebang_dir != expected_bin:
            found.append(
                VenvShimDrift(
                    script=entry.name,
                    shebang_path=shebang_path,
                    expected_venv_bin=str(expected_bin),
                )
            )
    if found:
        _log.warning(
            "doctor: %d venv shim(s) shebang outside this venv: %s",
            len(found),
            [d.script for d in found],
        )
    return tuple(found)


def _venv_shim_remediation(drifted: tuple[VenvShimDrift, ...]) -> str:
    """Remediation hint naming each corrupted shim and the exact repair
    command (T-1161): `uv sync --reinstall-package <dist>` rewrites that
    script's shebang back to this venv's own interpreter, without
    reinstalling every other dependency."""
    names = ", ".join(f"{d.script} (-> {d.shebang_path})" for d in drifted)
    packages = " ".join(sorted({d.script for d in drifted}))
    return (
        f"venv shim(s) shebang outside this venv: {names} -- run "
        f"`uv sync --reinstall-package {packages}` (repeat per affected "
        "package name if the script name does not match its distribution) "
        "or `make install-tool` to rebuild the whole venv"
    )


# frob:ticket T-1719
# frob:doc docs/modules/cli.md#frob-doctor-global-vs-local-frob-binary-skew-t-1719
class GlobalBinarySkew(BaseModel):
    """`frob doctor`'s report of the on-PATH global `frob` versus this
    invocation's own version (T-1719): measured directly, `frob` on PATH
    sat at 0.184.0 while this repo's own `uv run frob` was 0.361.0 -- 177
    versions apart, with nothing surfacing the gap short of a human
    running both by hand. Every gate number and ledger splice the global
    binary produces against this tree is wrong while the two disagree
    (the same class of incident `stale_binary_warning`/T-1218 already
    covers for a `min_frob_version` floor violation -- this check instead
    reports ANY disagreement, floor or no floor, since even a NEWER global
    binary reading an older checkout can disagree on gate logic).

    `global_version`/`local_version` are the raw `frob --version` strings
    from each; `skewed` is True only when BOTH measured successfully and
    differ -- an unmeasurable side (no global `frob` on PATH, a spawn
    failure) is never itself read as evidence of skew. Mirrors
    `.claude/hooks/frob-suggest.py`'s own `_frob_version_skew` measurement
    (spawn, strip, compare) -- that hook is a standalone script with no
    `frob` package import available to it, so this is a parallel
    implementation of the same check rather than a shared function call;
    see this ticket's Done report for why full code-sharing across the
    two surfaces is a separate, larger change."""

    model_config = {}

    global_version: str | None
    local_version: str
    skewed: bool


def _probe_global_frob_version() -> str | None:
    """The on-PATH `frob --version` output, or `None` when no `frob`
    binary is on PATH or the probe fails for any reason (never raises --
    an unmeasurable global binary is a normal outcome this reports, not an
    error)."""
    frob_path = shutil.which("frob")
    if frob_path is None:
        return None
    result = guarded_subprocess_run(
        [frob_path, "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.is_err:
        _log.debug("doctor: global frob version probe refused: %s", result.danger_err)
        return None
    proc = result.danger_ok
    if proc.returncode != 0:
        _log.warning("doctor: global frob --version exited %d", proc.returncode)
        return None
    out = (proc.stdout or proc.stderr).strip()
    return out or None


# frob:ticket T-1719
# frob:doc docs/modules/cli.md#frob-doctor-global-vs-local-frob-binary-skew-t-1719
# tests/test_doctor.py::test_global_binary_skew_not_skewed_when_versions_agree
def global_binary_skew(local_version: str) -> GlobalBinarySkew | None:
    """Compare the on-PATH `frob`'s `--version` output against
    `local_version` (this invocation's own `frob {_frob_version()}`
    string, T-1719), or `None` when there is no global `frob` on PATH at
    all to compare against -- nothing to reconcile in that case. Never
    raises; an unmeasurable global binary reports as `global_version=None,
    skewed=False`, not as a false skew."""
    global_v = _probe_global_frob_version()
    skewed = global_v is not None and global_v != local_version
    if skewed:
        _log.warning(
            "doctor: global frob version skew: PATH frob=%r, uv run frob=%r",
            global_v,
            local_version,
        )
    return GlobalBinarySkew(
        global_version=global_v, local_version=local_version, skewed=skewed
    )


# frob:waive DUP001 reason="coincidental structural resemblance only: \
# remediation/message-builder functions across 8 unrelated subsystems (doctor \
# version-skew, BUG002 repro-evidence messages, mutation evidence, strata waive, \
# deploy generate, scaffold managed, dup rules formatting, ticket close-cmd hints) -- \
# no shared domain, independently evolving, spot-checked per T-2966"
def _global_binary_skew_remediation(skew: GlobalBinarySkew) -> str:
    """Remediation hint naming both versions and the exact reconcile
    command (T-1719) -- mirrors `frob-suggest.py`'s own nudge text so an
    agent sees the same fix whether it hit the hook or ran `frob doctor`
    directly."""
    return (
        f"global `frob` on PATH ({skew.global_version!r}) disagrees with this "
        f"repo's own `uv run frob` ({skew.local_version!r}) -- use `uv run "
        "frob ...` here, or reconcile the installs with `uv tool upgrade frob`"
    )


#: `.frob/` cache dir this manifest lives under (T-0604) -- derived,
#: gitignored bookkeeping the same way every other entry in
#: `DERIVED_ARTIFACTS` is; deliberately NOT itself in `DERIVED_ARTIFACTS`
#: (a manifest fingerprinting its own drift would be circular).
_DRIFT_MANIFEST_REL_PATH = ".frob/derived-state-manifest.json"


def _load_drift_manifest(root: Path) -> dict[str, str]:
    """Best-effort load of the `{artifact name: fingerprint}` manifest the
    PREVIOUS `frob doctor` run persisted (T-0604). Missing, unreadable, or
    malformed manifest data is treated as "no prior run to compare
    against" (an empty dict) rather than raised -- the manifest is itself
    disposable derived-state bookkeeping, not a source of truth worth
    failing over."""
    path = root / _DRIFT_MANIFEST_REL_PATH
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        _log.warning(
            "doctor: derived-state manifest at %s unreadable/malformed (%s), "
            "treating as no prior run",
            path,
            exc,
        )
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}


def _write_drift_manifest(root: Path, fingerprints: dict[str, str]) -> None:
    """Persist this run's `{artifact name: fingerprint}` manifest (T-0604)
    for the NEXT `frob doctor` run's drift comparison. Best-effort: a write
    failure (read-only tree, missing `.frob/` permissions, ...) is logged
    and swallowed, never raised -- failing to record a manifest must never
    make `frob doctor` itself fail."""
    path = root / _DRIFT_MANIFEST_REL_PATH
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(fingerprints, indent=2, sort_keys=True), encoding="utf-8"
        )
    except OSError as exc:
        _log.warning(
            "doctor: failed to write derived-state manifest at %s: %s", path, exc
        )


# frob:doc docs/guides/install.md#derived-state-integrity-manifest-t-0570
# frob:tests tests/system/test_cli_doctor.py kind="integration"
# tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift.test_rewritten_artifact_\
# between_two_runs_reports_drift kind="unit"  # noqa: E501
# frob:waive COV007 reason="T-0871: same -- see COV005 waiver above"
def _detect_derived_state_drift(
    root: Path, current: tuple[DerivedArtifactStatus, ...]
) -> tuple[_DerivedArtifactDrift, ...]:
    """Compare `current`'s fingerprints against the manifest the PREVIOUS
    `frob doctor` run persisted (T-0604) and report every artifact whose
    content changed since then -- content drift, distinct from
    `verify_derived_state`'s per-run format/corruption check. An artifact
    missing from the prior manifest (first-ever run, or a newly added
    `DERIVED_ARTIFACTS` entry) or absent in `current` (deleted since, e.g.
    `frob clean`) has nothing to compare and never reports drift; only a
    present-in-both, fingerprint-mismatched pair does.

    Deliberately informational only -- this does NOT feed into
    `DoctorReport.healthy`/`remediation` the way T-0603's corrupt-artifact
    check does. `frob`'s OWN tools legitimately rewrite these same caches
    between two `frob doctor` invocations in normal use (running `frob
    check` updates `.frob/cache.db`, `frob dup` updates `.frob/dup.db`,
    ...); treating every such ordinary rewrite as a hard failure would make
    a session's second `frob doctor` call cry wolf on completely expected
    churn. Callers that want the raw signal (an audit trail, a "did
    anything touch my caches while I wasn't looking" check) read this
    return value or `DoctorReport.drift` directly."""
    previous = _load_drift_manifest(root)
    drift: list[_DerivedArtifactDrift] = []
    for d in current:
        if d.fingerprint is None:
            continue
        prev_fingerprint = previous.get(d.name)
        if prev_fingerprint is not None and prev_fingerprint != d.fingerprint:
            drift.append(
                _DerivedArtifactDrift(
                    name=d.name,
                    path=d.path,
                    previous_fingerprint=prev_fingerprint,
                    current_fingerprint=d.fingerprint,
                )
            )
    if drift:
        _log.info(
            "doctor: derived-state drift detected for %s since last frob doctor run",
            [d.name for d in drift],
        )
    return tuple(drift)


def _derived_state_remediation(corrupt: tuple[DerivedArtifactStatus, ...]) -> str:
    """One clear remediation line naming every corrupt derived artifact and
    the exact command to clear each, instead of dozens of misleading
    findings downstream that never say the cache itself is the problem."""
    names = ", ".join(f"{d.name} ({d.path})" for d in corrupt)
    commands = " ; ".join(f"rm -f {d.path}" for d in corrupt)
    return f"corrupt derived state: {names} -- {commands}"


def _scaffold_remediation(missing_or_stale: tuple[ManagedBlockStatus, ...]) -> str:
    """One clear remediation line naming every missing/stale managed block
    (T-0736) -- the fix is always the same single command."""
    names = ", ".join(f"{s.block_id} ({s.target})" for s in missing_or_stale)
    return (
        f"managed boilerplate blocks missing/stale: {names} -- "
        "run `frob scaffold apply`"
    )


# tests/system/test_cli_doctor.py::TestDoctorMutateJournal.test_run_diagnosis_unhealthy\
# _with_stale_mutate_journal kind="unit"  # noqa: E501
def _mutate_journal_remediation(stale: tuple[StaleJournal, ...]) -> str:
    """One clear remediation line naming every target still in mutant form
    on disk (T-0857) -- a stale `frob mutate` backup journal, from a run
    that crashed before restoring."""
    names = ", ".join(s.target for s in stale)
    return (
        f"mutate-backup journal(s) needing restore: {names} -- "
        "re-run `frob mutate <target>` (its startup check restores "
        "automatically) or restore by hand from the journal file"
    )


# frob:ticket T-3276
# frob:doc docs/guides/install.md#external-tool-inventory-and-preflight-t-3276
class ToolCategory(StrEnum):
    """T-3276: the three ways `frob doctor` treats a missing external
    tool, per the owner's own stated rule -- REQUIRED (frob cannot
    perform the operation at all without it: a loud, typed, install-
    command-naming failure), OPTIONAL (frob never uses it unless the
    repo opts in, e.g. a language toolchain for a language this repo
    does not contain: silent when absent), and OPTIONAL_FOR_GATE (a
    `frob check` gate needs it to MEASURE something: absence must report
    that gate UNMEASURED, loudly, distinguishable from CLEAN, never
    silently skipped or folded into a passing result)."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    OPTIONAL_FOR_GATE = "optional_for_gate"


# frob:ticket T-3276
# frob:doc docs/guides/install.md#external-tool-inventory-and-preflight-t-3276
class ExternalToolStatus(BaseModel):
    """One `_EXTERNAL_TOOLS` entry's measured presence (T-3276): `present`
    is `shutil.which(name) is not None` for a binary, or the package
    being importable/its distribution version resolvable for a Python
    plugin (`kind="package"` entries in `_EXTERNAL_TOOLS`); `version` is
    best-effort (`None` when unmeasurable, never itself a failure).
    `frob doctor` reports one of these per inventory entry so "what tools
    does frob spawn, and is each one here" is a single command's answer,
    not tribal knowledge scattered across call sites (T-3276's own
    measured finding: `shutil.which` in only 10 of `src/frob/`'s files,
    `frob doctor` checking exactly one binary before this)."""

    model_config = {}

    name: str
    category: ToolCategory
    present: bool
    version: str | None = None
    install_hint: str


# see T-3276 for the history behind this
_EXTERNAL_TOOLS: tuple[tuple[str, str, ToolCategory, str], ...] = (
    ("python", "binary", ToolCategory.REQUIRED, "install a Python 3.11+ interpreter"),
    ("git", "binary", ToolCategory.REQUIRED, "install git (https://git-scm.com)"),
    ("uv", "binary", ToolCategory.REQUIRED, "install uv: https://docs.astral.sh/uv/"),
    (
        "ruff",
        "binary",
        ToolCategory.REQUIRED,
        "pip install ruff (or: uv pip install ruff)",
    ),
    ("ty", "binary", ToolCategory.REQUIRED, "pip install ty (or: uv pip install ty)"),
    (
        "pytest",
        "binary",
        ToolCategory.OPTIONAL_FOR_GATE,
        "pip install pytest (or: uv pip install pytest)",
    ),
    (
        "pytest-xdist",
        "package",
        ToolCategory.OPTIONAL_FOR_GATE,
        "pip install pytest-xdist (or: uv pip install pytest-xdist) -- "
        "without it, pytest addopts' `-n auto` fails with a usage error "
        "(pytest exits 4) rather than running serially",
    ),
    (
        "pytest-cov",
        "package",
        ToolCategory.OPTIONAL_FOR_GATE,
        "pip install pytest-cov (or: uv pip install pytest-cov) -- "
        "without it, `frob coverage` cannot produce coverage.xml and "
        "TEST006 can never be measured",
    ),
    ("cargo", "binary", ToolCategory.OPTIONAL, "install rustup (https://rustup.rs)"),
    ("npm", "binary", ToolCategory.OPTIONAL, "install Node.js (https://nodejs.org)"),
    ("ctest", "binary", ToolCategory.OPTIONAL, "install CMake (https://cmake.org)"),
    (
        "dotnet",
        "binary",
        ToolCategory.OPTIONAL,
        "install the .NET SDK (https://dotnet.microsoft.com/download)",
    ),
)


# frob:ticket T-3276
def _probe_binary_version(binary: str) -> str | None:
    """Best-effort `<binary> --version`'s first output line, or `None` on
    any failure (missing binary, non-zero exit, no output, exec disabled
    via `guarded_subprocess_run`) -- never raises, matching every other
    doctor probe's fail-soft discipline; a version string is a diagnostic
    nicety, never itself a presence/absence verdict."""
    spawned = guarded_subprocess_run(
        [binary, "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if spawned.is_err:
        return None
    completed = spawned.danger_ok
    if completed.returncode != 0:
        return None
    first_line = (completed.stdout or completed.stderr or "").strip().splitlines()
    return first_line[0] if first_line else None


# frob:ticket T-3276
# frob:doc docs/guides/install.md#external-tool-inventory-and-preflight-t-3276
def scan_external_tools() -> list[ExternalToolStatus]:
    """Probe every `_EXTERNAL_TOOLS` entry and return its
    `ExternalToolStatus` (T-3276) -- the MUST-STAY-QUIET fixture's
    counterpart: when every tool is present this only measures (a
    `shutil.which`/`importlib.metadata.version` call per entry, no
    subprocess spawn beyond the cheap `--version` probe), it never warns
    or slows the caller down; `run_diagnosis`/`_assemble_doctor_report`
    decide what `healthy`/`remediation` do with a REQUIRED absence."""
    statuses: list[ExternalToolStatus] = []
    for name, kind, category, install_hint in _EXTERNAL_TOOLS:
        if kind == "package":
            try:
                pkg_version = version(name)
                present = True
            except Exception:
                pkg_version = None
                present = False
            statuses.append(
                ExternalToolStatus(
                    name=name,
                    category=category,
                    present=present,
                    version=pkg_version,
                    install_hint=install_hint,
                )
            )
            continue
        which = shutil.which(name)
        present = which is not None
        probed_version = _probe_binary_version(name) if present else None
        statuses.append(
            ExternalToolStatus(
                name=name,
                category=category,
                present=present,
                version=probed_version,
                install_hint=install_hint,
            )
        )
    return statuses


# frob:ticket T-3276
def _external_tools_remediation(statuses: list[ExternalToolStatus]) -> str | None:
    """One clear remediation line per missing REQUIRED tool (T-3276) --
    joined if more than one -- naming the tool and its install command;
    `None` if every REQUIRED tool is present (a missing OPTIONAL or
    OPTIONAL_FOR_GATE tool is never itself unhealthy, per `ToolCategory`'s
    own docstring -- OPTIONAL_FOR_GATE's absence is a gate-level UNMEASURED
    concern, not a `frob doctor` health failure)."""
    missing_required = [
        s for s in statuses if s.category == ToolCategory.REQUIRED and not s.present
    ]
    if not missing_required:
        return None
    lines = [f"{s.name} not found -- {s.install_hint}" for s in missing_required]
    return "required tool(s) missing: " + "; ".join(lines)


# frob:ticket T-5139
# frob:doc docs/guides/install.md#external-tool-inventory-and-preflight-t-3276
class RelevantToolFailureKind(StrEnum):
    """T-5139 DESIGN item 2: why a gate-serving tool's `RelevantToolEntry`
    could not measure what it serves -- Result-typed instead of a bare
    presence bool, so a REACHED-but-broken tool (`NonZeroExit`,
    `UnparseableOutput`, `Timeout`) is never folded into the same "absent"
    bucket as `Missing`: each is a differently actionable remedy."""

    MISSING = "missing"
    VERSION_TOO_OLD = "version_too_old"
    SPAWN_FAILED = "spawn_failed"
    NON_ZERO_EXIT = "non_zero_exit"
    TIMEOUT = "timeout"
    UNPARSEABLE_OUTPUT = "unparseable_output"
    NETWORK_UNAVAILABLE = "network_unavailable"


# frob:ticket T-5139
# frob:doc docs/guides/install.md#external-tool-inventory-and-preflight-t-3276
class RelevantToolEntry(BaseModel):
    """One `_RELEVANT_TOOLS` registry row (T-5139 DESIGN item 1): `name` +
    `rules_it_serves` (the gate rule ids left UNMEASURED when this tool is
    relevant-and-missing/failed) + `install_remedy` (the command a human
    or `frob doctor --install` runs). `relevant_when` is NOT stored on the
    model (a `Path -> bool` repo predicate is not pydantic-serializable);
    it lives in the paired `_RELEVANT_TOOLS` tuple entry instead, keyed by
    `name`, and `tool_is_relevant`/`relevant_tool_findings` below join the
    two back together."""

    model_config = {}

    name: str
    rules_it_serves: tuple[str, ...]
    install_remedy: str


# frob:ticket T-5139
# frob:doc docs/guides/install.md#external-tool-inventory-and-preflight-t-3276
class RelevantToolFinding(BaseModel):
    """One gate-serving tool that IS relevant to `root` and is missing or
    failed (T-5139 DESIGN item 3): the rules it serves are UNMEASURED, and
    a relevant finding makes the caller's run exit non-zero UNLESS
    overridden (`--allow-missing-tool NAME --reason ...`, T-5139 DESIGN
    item 3) -- wiring that override and the non-zero exit itself into
    `frob check`/`frob ticket land` is a follow-up (`src/frob/check/**`/
    `src/frob/gates/**` carried other agents' live leases at the time of
    this ticket, same class of cut T-0570 made for the derived-state
    drift check this module already reports -- see this module's own
    docstring)."""

    model_config = {}

    entry: RelevantToolEntry
    kind: RelevantToolFailureKind
    detail: str = ""


# frob:ticket T-5139
# frob:doc docs/guides/install.md#external-tool-inventory-and-preflight-t-3276
_RELEVANT_TOOLS: tuple[tuple[RelevantToolEntry, Callable[[Path], bool]], ...] = (
    (
        RelevantToolEntry(
            name="cargo-audit",
            rules_it_serves=("VET005",),
            install_remedy="cargo install cargo-audit",
        ),
        lambda root: (root / "Cargo.lock").exists(),
    ),
)


# frob:ticket T-5139
def _relevant_tool_status(
    entry: RelevantToolEntry,
) -> tuple[bool, RelevantToolFailureKind | None, str]:
    """Whether `entry`'s binary is present and, if not, which
    `RelevantToolFailureKind` explains the absence -- `shutil.which` is
    the whole probe for MVP (VersionTooOld/NonZeroExit/Timeout/
    UnparseableOutput/NetworkUnavailable are real adapter-failure kinds a
    real spawn-and-parse adapter can report; this registry-level presence
    check can only ever observe MISSING, so it is the only kind returned
    here)."""
    if shutil.which(entry.name) is None:
        return False, RelevantToolFailureKind.MISSING, f"{entry.name} not on PATH"
    return True, None, ""


# frob:ticket T-5139
# frob:doc docs/guides/install.md#external-tool-inventory-and-preflight-t-3276
def relevant_tool_findings(root: Path) -> list[RelevantToolFinding]:
    """Every `_RELEVANT_TOOLS` entry whose `relevant_when(root)` predicate
    is true AND which is missing/failed (T-5139 DESIGN item 3) -- a tool
    that is not relevant here (no `Cargo.lock`, no `*.sql`, ...) is never
    reported, even if absent: "not needed here" is not a finding. An
    empty return means every relevant tool measured cleanly, never "no
    tools exist to check" (the registry always has entries)."""
    findings: list[RelevantToolFinding] = []
    for entry, relevant_when in _RELEVANT_TOOLS:
        if not relevant_when(root):
            continue
        present, kind, detail = _relevant_tool_status(entry)
        if not present and kind is not None:
            findings.append(RelevantToolFinding(entry=entry, kind=kind, detail=detail))
    return findings


# frob:ticket T-5204
# frob:doc docs/guides/install.md#external-tool-inventory-and-preflight-t-3276
class LintToolLagError(ErrorSet):
    """Fallible outcomes of `_latest_release_version`'s registry query
    (T-5204 DESIGN item 7, T-5138's own follow-up): distinct kinds so a
    caller can tell "no cache and network disabled/unreachable" apart
    from "the registry answered but its response did not parse" -- same
    T-5139-acceptance-[2] posture `frob.vet._osv.OsvQueryError` already
    established for exactly this shape."""

    Unavailable = "registry query unavailable: no cache and no network"
    UnparseableResponse = (
        "registry query reached the server but its response did not parse"
    )


# frob:ticket T-5204
# frob:doc docs/guides/install.md#external-tool-inventory-and-preflight-t-3276
class LintToolVersionLag(BaseModel):
    """One lint tool whose installed version is behind its latest
    published release (T-5204, T-5138 DESIGN item 7): `installed`/
    `latest` are raw version strings (never parsed to a `Version` object
    here -- `_minor_versions_behind` does the one comparison this module
    needs), `registry` names which of PyPI/npm/crates answered."""

    model_config = {}

    name: str
    installed: str
    latest: str
    registry: str
    minor_versions_behind: int


#: T-5204 DESIGN item 7: which registry (module:callable resolving a
#: `Result[str, LintToolLagError]` of the latest published version) each
#: lint tool's version lag is measured against. `clippy` is deliberately
#: absent -- it ships as a rustup component, not a standalone PyPI/npm/
#: crates.io release, so there is no single "latest version" registry
#: query for it; T-5204's own scope (`src/frob/doctor.py` only) does not
#: extend to a rustup-component-specific probe, filed as disclosed
#: residue rather than silently guessed at.
_LINT_TOOL_REGISTRIES: tuple[tuple[str, str], ...] = (
    ("ruff", "pypi"),
    ("ty", "pypi"),
    ("mypy", "pypi"),
    ("eslint", "npm"),
)

#: T-5204: a cache entry younger than this serves with no network call at
#: all -- same 24h freshness target `frob.vet._osv`'s OSV.dev cache uses,
#: named directly in this ticket's own DESIGN item 7 text ("cached 24h").
_LINT_LAG_CACHE_TTL_S = 24 * 60 * 60

#: T-5204 DESIGN item 7: warn once a tool is this many minor releases (or
#: more) behind its registry's latest -- configurable via frob.toml is
#: named in the design but `frob.toml`/`frob.gates` parsing is out of
#: this ticket's own declared scope (`src/frob/doctor.py` only); this
#: constant is the hardcoded default until a follow-up wires a
#: `[doctor]` config table.
_LINT_LAG_WARN_THRESHOLD = 2


def _lint_lag_cache_path(root: Path) -> Path:
    """`.frob/tool-version-lag-cache.json` under `root` -- a small,
    self-contained JSON cache (not `frob.vet._cache`'s sqlite table: this
    ticket's own scope is `src/frob/doctor.py` only, not `src/frob/
    vet/**`) keyed by tool name, `{version, checked_at}` per entry."""
    return Path(root) / ".frob" / "tool-version-lag-cache.json"


def _load_lint_lag_cache(root: Path) -> dict[str, dict]:
    """The whole `_lint_lag_cache_path` JSON blob, or `{}` on any read/
    parse failure -- a corrupt or missing cache is a cold cache, never a
    crash (same fail-soft discipline every other doctor probe follows)."""
    path = _lint_lag_cache_path(root)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _store_lint_lag_cache(root: Path, cache: dict[str, dict]) -> None:
    """Persist `cache` to `_lint_lag_cache_path`, best-effort -- a write
    failure is logged, never raised (the caller already has its answer
    in memory for this run)."""
    path = _lint_lag_cache_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache), encoding="utf-8")
    except OSError as exc:
        _log.warning("doctor: could not write %s: %s", path, exc)


def _fetch_pypi_latest_version(name: str) -> Result[str, LintToolLagError]:
    """`https://pypi.org/pypi/<name>/json`'s `info.version` -- gated by
    `net_enabled()` (the `FROB_DISABLE_NET` kill switch, same T-0822
    posture `frob.vet._osv` already uses) before the socket ever opens."""
    if not net_enabled():
        return Err(LintToolLagError.Unavailable)
    url = f"https://pypi.org/pypi/{name}/json"
    try:
        with urllib.request.urlopen(url, timeout=10.0) as resp:  # noqa: S310
            body = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return Err(LintToolLagError.Unavailable)
    try:
        data = json.loads(body)
        latest = data["info"]["version"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return Err(LintToolLagError.UnparseableResponse)
    if not isinstance(latest, str) or not latest:
        return Err(LintToolLagError.UnparseableResponse)
    return Ok(latest)


def _fetch_npm_latest_version(name: str) -> Result[str, LintToolLagError]:
    """`https://registry.npmjs.org/<name>/latest`'s `version` -- same
    net-kill-switch gating as `_fetch_pypi_latest_version`."""
    if not net_enabled():
        return Err(LintToolLagError.Unavailable)
    url = f"https://registry.npmjs.org/{name}/latest"
    try:
        with urllib.request.urlopen(url, timeout=10.0) as resp:  # noqa: S310
            body = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return Err(LintToolLagError.Unavailable)
    try:
        data = json.loads(body)
        latest = data["version"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return Err(LintToolLagError.UnparseableResponse)
    if not isinstance(latest, str) or not latest:
        return Err(LintToolLagError.UnparseableResponse)
    return Ok(latest)


_LINT_LAG_FETCHERS: dict[str, Callable[[str], "Result[str, LintToolLagError]"]] = {
    "pypi": _fetch_pypi_latest_version,
    "npm": _fetch_npm_latest_version,
}


#: `_probe_binary_version`'s raw `<tool> --version` first line (e.g.
#: `"ruff 0.1.0"`) needs its bare `MAJOR.MINOR...` number pulled out
#: before `_minor_versions_behind` can compare it against a registry's
#: already-bare version string.
_VERSION_NUMBER_RE = re.compile(r"\d+(?:\.\d+)+")


def _minor_versions_behind(installed: str, latest: str) -> int | None:
    """`latest`'s minor component minus `installed`'s, when both parse as
    `MAJOR.MINOR...` and share the same major version; `None` when either
    fails to parse, or the major versions differ (a major bump is a
    different kind of gap than DESIGN item 7's "N minor versions behind"
    -- reported honestly as unmeasurable here rather than guessed at).
    `installed` is `_probe_binary_version`'s raw first line (e.g. `"ruff
    0.1.0"`) -- `_VERSION_NUMBER_RE` extracts the bare version number
    before comparing."""
    inst_match = _VERSION_NUMBER_RE.search(installed)
    if inst_match is None:
        return None
    inst_parts = inst_match.group().split(".")
    latest_parts = latest.split(".")
    if len(inst_parts) < 2 or len(latest_parts) < 2:
        return None
    try:
        inst_major, inst_minor = int(inst_parts[0]), int(inst_parts[1])
        latest_major, latest_minor = int(latest_parts[0]), int(latest_parts[1])
    except ValueError:
        return None
    if inst_major != latest_major:
        return None
    return latest_minor - inst_minor


# frob:ticket T-5204
# frob:doc docs/guides/install.md#external-tool-inventory-and-preflight-t-3276
def lint_tool_version_lag(
    root: Path, *, fetch: bool = True
) -> list[LintToolVersionLag]:
    """T-5204 (T-5138 DESIGN item 7): every `_LINT_TOOL_REGISTRIES` entry
    whose installed version (`_probe_binary_version`) is
    `_LINT_LAG_WARN_THRESHOLD` or more minor releases behind its
    registry's latest published version. Cache-first in
    `_lint_lag_cache_path` (24h TTL): a fresh cached `latest` serves with
    zero network calls; an expired/missing entry triggers one fetch
    attempt UNLESS `fetch=False` (tests always pass `fetch=False` or
    monkeypatch the fetcher directly -- this never hits the real network
    in a test run, matching every other network-adjacent probe in this
    codebase). A tool that is not installed, or whose registry query
    fails outright, is silently skipped -- this is an informational lag
    report, never itself an unhealthy-doctor verdict."""
    root = Path(root)
    cache = _load_lint_lag_cache(root)
    now = time.time()
    findings: list[LintToolVersionLag] = []
    dirty = False
    for name, registry in _LINT_TOOL_REGISTRIES:
        installed = _probe_binary_version(name)
        if installed is None:
            continue
        cached = cache.get(name)
        latest: str | None = None
        if isinstance(cached, dict):
            checked_at = cached.get("checked_at")
            fresh = (
                isinstance(checked_at, (int, float))
                and now - checked_at < _LINT_LAG_CACHE_TTL_S
            )
            if fresh:
                cached_version = cached.get("version")
                if isinstance(cached_version, str):
                    latest = cached_version
        if latest is None and fetch:
            fetcher = _LINT_LAG_FETCHERS.get(registry)
            if fetcher is None:
                continue
            result = fetcher(name)
            if result.is_err:
                continue
            latest = result.danger_ok
            cache[name] = {"version": latest, "checked_at": now}
            dirty = True
        if latest is None:
            continue
        behind = _minor_versions_behind(installed, latest)
        if behind is None or behind < _LINT_LAG_WARN_THRESHOLD:
            continue
        findings.append(
            LintToolVersionLag(
                name=name,
                installed=installed,
                latest=latest,
                registry=registry,
                minor_versions_behind=behind,
            )
        )
    if dirty:
        _store_lint_lag_cache(root, cache)
    return findings


# frob:ticket T-4459
# frob:doc docs/modules/agent-worktree.md#pythonpath-import-source-t-4459
# tests/test_worktree_pythonpath.py::TestImportSourceStatus.test_matching_worktree_reports_clean  # noqa: E501
# tests/test_worktree_pythonpath.py::TestImportSourceStatus.test_mismatched_worktree_reports_loudly  # noqa: E501
# tests/test_worktree_pythonpath.py::TestImportSourceStatus.test_no_worktree_src_never_mismatches  # noqa: E501
class ImportSourceStatus(BaseModel):
    """Where `import frob` actually resolved from vs. where `resolved_root`'s
    own checkout would put it (T-4459). A worktree test run using the
    root checkout's editable-install `.pth` (rather than a PYTHONPATH
    pointed at the worktree's own `src/`) silently imports and measures
    ANOTHER checkout's code, not the branch checked out at `resolved_root`
    -- this is the diagnostic surface for that, distinct from every other
    `DoctorReport` field in that it reports on `frob`'s OWN identity, not
    a scan of repo state. `worktree_src` is `None` when `resolved_root`
    has no `src/frob/__init__.py` of its own (a non-source checkout, e.g.
    an installed tool with no worktree layout) -- there is nothing to
    mismatch against, so `mismatched` is always `False` in that case."""

    model_config = {}

    resolved_module_path: str
    worktree_src: str | None
    mismatched: bool


def _import_source_status(resolved_root: Path) -> ImportSourceStatus:
    """Compare the currently-imported `frob` package's file location
    against `resolved_root`'s own `src/frob/__init__.py` (T-4459): a
    worktree whose own `src/` exists but whose imported `frob.__file__`
    resolves elsewhere means THIS process is silently measuring another
    checkout (typically the root checkout's editable-install `.pth`
    winning over an unset `PYTHONPATH`), not the branch checked out at
    `resolved_root`. Logs a WARNING (loud, not silent) the moment a
    mismatch is detected, since this is exactly the class of bug that
    otherwise produces a passing-but-meaningless test run."""
    resolved_module = Path(_frob_pkg.__file__).resolve()
    candidate_src = (resolved_root / "src" / "frob" / "__init__.py").resolve()
    worktree_src = str(candidate_src) if candidate_src.is_file() else None
    mismatched = worktree_src is not None and resolved_module != candidate_src
    if mismatched:
        _log.warning(
            "doctor: import frob resolves to %s, not this checkout's own %s "
            "-- PYTHONPATH is not pointed at this worktree's src/",
            resolved_module,
            candidate_src,
        )
    else:
        _log.debug(
            "doctor: import frob resolves to %s (worktree_src=%s)",
            resolved_module,
            worktree_src,
        )
    return ImportSourceStatus(
        resolved_module_path=str(resolved_module),
        worktree_src=worktree_src,
        mismatched=mismatched,
    )


# frob:doc docs/guides/install.md#unity-toolchain-detection-t-4501
# frob:ticket T-4501
class UnityEditorStatus(BaseModel):
    """Whether a Unity Editor binary was located on this machine (T-4501),
    plus its version and the path it was found at. Distinct from
    `_EXTERNAL_TOOLS`/`ExternalToolStatus`'s simple `shutil.which(name)`
    check -- the Unity Editor has no single stable PATH-discoverable
    binary name across OSes and install methods (Unity Hub installs each
    editor version into its own versioned directory), so locating it
    needs the multi-source search `_locate_unity_editor` performs. Always
    OPTIONAL (`ToolCategory.OPTIONAL`'s rule): absence is reported here
    for visibility when the caller is already inside a detected Unity
    project (see `_collect_doctor_scans`'s Unity-project gating), never a
    `frob doctor` health failure."""

    model_config = {}

    present: bool
    path: str | None = None
    version: str | None = None


# frob:doc docs/guides/install.md#unity-toolchain-detection-t-4501
# frob:ticket T-4501
def _unity_hub_default_roots() -> tuple[Path, ...]:
    """The default Unity Hub editor-install root(s) for the current OS
    (T-4501): each editor version Unity Hub installs lives in its own
    subdirectory under one of these roots (e.g. `<root>/2022.3.5f1/`),
    which is what makes a plain `shutil.which("unity")` insufficient --
    there is no single binary on PATH by default, only a per-version
    install tree a Hub user never adds to PATH themselves. Returns
    whichever root(s) apply to `platform.system()`; a root that does not
    exist on this machine is filtered out by the caller
    (`_locate_unity_editor`), not here -- this function only states the
    convention, never touches the filesystem."""
    system = platform.system()
    if system == "Windows":
        # frob:waive SEC110 reason="PROGRAMFILES is a well-known filesystem-location \
        # env var, not a secret"
        program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        return (Path(program_files) / "Unity" / "Hub" / "Editor",)
    if system == "Darwin":
        return (Path("/Applications/Unity/Hub/Editor"),)
    return (Path.home() / "Unity" / "Hub" / "Editor",)


def _unity_editor_binary_for_version_dir(version_dir: Path) -> Path:
    """The Unity Editor executable path inside one Unity Hub versioned
    install directory (T-4501), per-OS layout: Windows nests
    `Editor/Unity.exe`, macOS nests `Unity.app/Contents/MacOS/Unity`, and
    Linux nests `Editor/Unity` directly under the version directory."""
    system = platform.system()
    if system == "Windows":
        return version_dir / "Editor" / "Unity.exe"
    if system == "Darwin":
        return version_dir / "Unity.app" / "Contents" / "MacOS" / "Unity"
    return version_dir / "Editor" / "Unity"


# frob:doc docs/guides/install.md#unity-toolchain-detection-t-4501
# frob:ticket T-4501
def _locate_unity_editor() -> UnityEditorStatus:
    """Locate a Unity Editor binary (T-4501), in precedence order: the
    `UNITY_PATH`/`UNITY_EDITOR` environment variables (an explicit path
    to the editor binary, checked first so a pinned CI/dev override always
    wins), Unity Hub's own default per-OS install root
    (`_unity_hub_default_roots`, one subdirectory per installed editor
    version -- the newest version directory by name is reported when
    more than one is installed), then a plain PATH lookup for `Unity`
    (Linux tarball installs and some manual installs put it there,
    unlike the Hub layout). Never raises and never logs above DEBUG on
    absence -- this is an OPTIONAL tool (`ToolCategory.OPTIONAL`'s rule:
    absence is informational, never a `frob doctor` health failure) that
    is only even consulted when the caller has already confirmed it is
    inside a Unity project (see `_collect_doctor_scans`)."""
    # frob:waive SEC110 reason="UNITY_PATH/UNITY_EDITOR are filesystem-path overrides \
    # for the editor binary location, not secrets"
    for env_name in ("UNITY_PATH", "UNITY_EDITOR"):
        env_path = os.environ.get(env_name)
        if env_path and Path(env_path).is_file():
            _log.info("doctor: Unity editor located via $%s at %s", env_name, env_path)
            return UnityEditorStatus(present=True, path=env_path, version=None)

    for hub_root in _unity_hub_default_roots():
        if not hub_root.is_dir():
            continue
        version_dirs = sorted(
            (d for d in hub_root.iterdir() if d.is_dir()),
            key=lambda d: d.name,
            reverse=True,
        )
        for version_dir in version_dirs:
            binary = _unity_editor_binary_for_version_dir(version_dir)
            if binary.is_file():
                _log.info(
                    "doctor: Unity editor located via Unity Hub at %s (version %s)",
                    binary,
                    version_dir.name,
                )
                return UnityEditorStatus(
                    present=True, path=str(binary), version=version_dir.name
                )

    which = shutil.which("Unity") or shutil.which("unity")
    if which is not None:
        _log.info("doctor: Unity editor located on PATH at %s", which)
        return UnityEditorStatus(present=True, path=which, version=None)

    _log.debug("doctor: no Unity editor located (env/Hub-default-roots/PATH)")
    return UnityEditorStatus(present=False)


# frob:doc docs/guides/install.md#unity-toolchain-detection-t-4501
# frob:ticket T-4501
def _diagnose_unity_toolchain(
    resolved_root: Path,
) -> tuple[UnityProjectInfo | None, UnityEditorStatus | None]:
    """Report the Unity project and installed editor (T-4501) -- but ONLY
    when `resolved_root` is a Unity project (`detect_unity_project`);
    outside a Unity project this returns `(None, None)` and does NOT call
    `_locate_unity_editor` at all, deliberately: a non-Unity repo must
    never see a spurious 'Unity not found' line (the story's own third
    acceptance criterion), and every other project on this machine using
    `frob doctor` should not pay a Unity Hub filesystem probe it has no
    use for. `_project_detect.detect_unity_project`'s own `Err
    (NotUnityProject)` case is deliberately quiet (not logged) for the
    same reason its docstring states -- this is the common case for
    every non-Unity root. A detected Unity project with no editor located
    is reported (`UnityEditorStatus(present=False)`), never a `frob
    doctor` failure -- see `UnityEditorStatus`'s own docstring."""
    detected = detect_unity_project(resolved_root)
    if detected.is_err:
        if detected.danger_err != UnityProjectDetectError.NotUnityProject:
            _log.warning(
                "doctor: Unity project detection at %s failed: %s",
                resolved_root,
                detected.danger_err,
            )
        return None, None
    project = detected.danger_ok
    editor = _locate_unity_editor()
    _log.info(
        "doctor: Unity project detected at %s (editor %s); Unity editor %s",
        resolved_root,
        project.editor_version,
        f"found at {editor.path}" if editor.present else "not found",
    )
    return project, editor


# frob:ticket T-4416
#: T-4416: repo-scale threshold at which `frob doctor`/`frob scaffold new`
#: RECOMMEND (never force -- see `profile_recommendation`'s own docstring)
#: `[profile] profile = "rapid"` in `frob.toml`. Measured on this repo
#: (T-4416's own ticket body): an unscoped `standard`-profile `frob check`
#: takes 25-45 minutes at ~4200 tickets / ~1400 tracked source files, and
#: T-4408's land (a comparable scale) measured 50+ minutes single-thread --
#: `rapid`'s post-T-4413 scoped-synchronous check (diff-touched files plus
#: direct dependents, unscoped sweep deferred to the batched post-land
#: pass, CI the unscoped authority) is the profile that scales, so a repo
#: past this size is told so. Deliberately DISTINCT from `frob.tickets.
#: _profile`'s `_THRESHOLD_FILE_COUNT`/`_THRESHOLD_TICKET_COUNT` (300/200)
#: -- that pair drives the one-way DOWNWARD auto-ratchet off of `rapid`'s
#: PRE-T-4413 meaning (small-repo-only, ceremony-light, risky at scale);
#: this pair drives an advisory recommendation TOWARD `rapid`'s POST-T-4413
#: meaning (scoped-synchronous, the profile that scales). Both live because
#: they answer different questions about the same enum member post-rename;
#: reconciling the two is out of this ticket's scope (see T-4416's Done
#: report for the filed follow-up).
class _ProfileRecommendationThreshold(BaseModel):
    """One named threshold pair for `profile_recommendation`'s OR check --
    a `BaseModel` (not a bare tuple) so the measured numbers stay
    self-documenting at every call site, per this repo's `model_config = {}`
    convention."""

    model_config = {}

    ticket_count: int
    file_count: int


# frob:ticket T-4416
#: The module-level `_ProfileRecommendationThreshold` instance
#: `profile_recommendation` checks against; a distinct symbol from the
#: class above it, so it carries its own frob:ticket edge.
_PROFILE_RECOMMEND_THRESHOLD = _ProfileRecommendationThreshold(
    ticket_count=4200,
    file_count=1400,
)


# frob:ticket T-4416
# frob:doc docs/modules/land-profiles.md#land-profiles-rapid-vs-standard-t-4416
def profile_recommendation(root: Path) -> str | None:
    """`None` when `root` is at or below `_PROFILE_RECOMMEND_THRESHOLD` on
    both axes (an OR check -- either axis alone is enough to recommend,
    matching `frob.tickets._profile`'s own "any ONE threshold" precedent);
    otherwise a human-readable recommendation string naming which axis
    tripped and citing the measured numbers, for `frob doctor` and `frob
    scaffold new`'s frob.toml-writing path to surface. This is ADVISORY
    ONLY -- it never writes `frob.toml`, never flips `DoctorReport.healthy`,
    and a repo below threshold is never told to relax anything: `standard`
    (this repo's existing unscoped-synchronous default, T-4415 declared CI
    the unscoped authority regardless of profile) stays a reasonable
    default for a small project, matching this ticket's acceptance
    criterion 3. Measures via the same two primitives `frob.tickets.
    _profile` already uses for its own (differently-thresholded, see
    `_PROFILE_RECOMMEND_THRESHOLD`'s docstring) ratchet check --
    `frob.excludes.iter_files` for file count and `frob.tickets.load_queue`
    for open+archived ticket count -- rather than importing that module's
    private helpers across a package boundary."""
    from frob.excludes import iter_files
    from frob.tickets import load_queue

    file_count = len(iter_files(root))
    loaded = load_queue(root)
    if loaded.is_err:
        _log.warning(
            "doctor: profile_recommendation: load_queue failed (%s), "
            "ticket-count axis treated as 0",
            loaded.danger_err,
        )
        ticket_count = 0
    else:
        ticket_count = len(loaded.danger_ok.tickets)

    if ticket_count > _PROFILE_RECOMMEND_THRESHOLD.ticket_count:
        return (
            f"repo ticket count {ticket_count} > "
            f"{_PROFILE_RECOMMEND_THRESHOLD.ticket_count} -- consider "
            '`[profile] profile = "rapid"` in frob.toml: standard\'s '
            "unscoped synchronous check measures 25-45 minutes at this "
            "scale (T-4416), rapid's scoped-synchronous check (diff plus "
            "dependents, unscoped sweep deferred to the batched post-land "
            "pass, CI authoritative) does not"
        )
    if file_count > _PROFILE_RECOMMEND_THRESHOLD.file_count:
        return (
            f"repo file count {file_count} > "
            f"{_PROFILE_RECOMMEND_THRESHOLD.file_count} -- consider "
            '`[profile] profile = "rapid"` in frob.toml: standard\'s '
            "unscoped synchronous check measures 25-45 minutes at this "
            "scale (T-4416), rapid's scoped-synchronous check (diff plus "
            "dependents, unscoped sweep deferred to the batched post-land "
            "pass, CI authoritative) does not"
        )
    _log.debug(
        "doctor: profile_recommendation: %s below threshold "
        "(tickets=%d/%d files=%d/%d), no recommendation",
        root,
        ticket_count,
        _PROFILE_RECOMMEND_THRESHOLD.ticket_count,
        file_count,
        _PROFILE_RECOMMEND_THRESHOLD.file_count,
    )
    return None


# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
# frob:ticket T-1501
# frob:ticket T-1515
# frob:ticket T-4416
class DoctorReport(BaseModel):
    """Full `frob doctor` diagnosis: per-extension status, derived-artifact
    integrity manifest (T-0570), cross-run content drift (T-0604),
    managed-boilerplate-block conformance (T-0736), stale mutate-backup
    journals needing restore (T-0857), the overall verdict, and
    remediation hint (empty when everything is healthy).

    `drift` is informational only -- see `_detect_derived_state_drift`'s
    docstring for why it does not feed into `healthy`/`remediation` the
    way a corrupt (`derived_state`) artifact does. `scaffold_blocks`
    (T-0736) is ALSO informational only as of T-3725: a missing/stale
    LOCAL managed git hook (`.git/hooks/pre-commit` and friends) is a
    dev-ergonomics nudge a CI checkout structurally never satisfies (CI
    never runs `frob scaffold apply`), not a build-correctness failure --
    see `_doctor_healthy`'s docstring for the motivating incident (CI run
    33715737237). Still surfaced in `remediation` and the plain renderer
    whenever present; never counts against `healthy`. `mutate_journals` is
    the opposite: any entry DOES make `healthy` False -- it names a real
    source file currently sitting in mutant form on disk, not disposable
    cache churn. `malformed_ticket_edges` (T-1132) is the same class as
    `mutate_journals`: any entry DOES make `healthy` False -- an empty-
    string or malformed `blocked_by`/`parent` entry is a real, silently
    wrong ledger row (the T-0380 incident), not disposable state.
    `stale_ticket_leases` (T-1131) is the same class again: a ticket id
    stuck `IN_PROGRESS` with no live lease (its worktree gone, the T-1050
    incident) is a real stuck ticket, not disposable state. `venv_shims`
    (T-1161) is the same class once more: a `.venv/bin/` entrypoint
    shebang pointing outside this venv is a real, silently broken
    interpreter binding, not disposable cache churn. `stale_binary`
    (T-1218) is the same class again: the invoked `frob` reading BELOW
    this repo's own `frob.toml` `min_frob_version` floor means every gate
    number and ledger splice this run produced may already be wrong --
    see `stale_binary_warning`'s docstring for the motivating incident.
    `global_binary` (T-1719) is a related but distinct check: it compares
    the on-PATH global `frob` against THIS run's own version regardless of
    any declared `min_frob_version` floor -- see `GlobalBinarySkew`'s
    docstring. Only its `skewed=True` case makes `healthy` False; an
    unmeasurable comparison (no global `frob` on PATH) reports
    `global_binary` with `global_version=None, skewed=False` and never
    counts against `healthy`. `external_tools` (T-3276) is the stated
    inventory of every external tool frob spawns or depends on for a gate
    to measure something (`_EXTERNAL_TOOLS`/`ExternalToolStatus`); only a
    missing `ToolCategory.REQUIRED` entry makes `healthy` False -- a
    missing OPTIONAL entry is silent by design, and a missing
    OPTIONAL_FOR_GATE entry is the affected gate's own UNMEASURED concern,
    never a `frob doctor` health failure (`ToolCategory`'s own docstring
    states the rule). `unity_project`/`unity_editor` (T-4501) are `None`
    unless `resolved_root` is a detected Unity project
    (`_diagnose_unity_toolchain`) -- a non-Unity repo never populates
    either field, matching the story's own "no spurious noise" acceptance
    criterion. Neither ever makes `healthy` False: a Unity project with
    no editor located is reported via `unity_editor.present=False`,
    informational only, per `UnityEditorStatus`'s own docstring.
    `profile_recommendation` (T-4416) is `None` below `profile_
    recommendation`'s own `_PROFILE_RECOMMEND_THRESHOLD` on both axes,
    else a human-readable nudge toward `[profile] profile = "rapid"` --
    ADVISORY ONLY, like `scaffold_blocks`: never affects `healthy`, and a
    repo below threshold gets no recommendation at all (a small project's
    `standard` default is left alone, matching T-4416's acceptance
    criterion 3)."""

    model_config = {}

    frob_version: str
    extensions: list[NativeExtensionStatus]
    derived_state: list[DerivedArtifactStatus] = []
    drift: list[_DerivedArtifactDrift] = []
    scaffold_blocks: list[ManagedBlockStatus] = []
    mutate_journals: list[StaleJournal] = []
    malformed_ticket_edges: list[MalformedTicketEdge] = []
    stale_ticket_leases: list[str] = []
    venv_shims: list[VenvShimDrift] = []
    external_tools: list[ExternalToolStatus] = []
    stale_binary: str | None = None
    global_binary: GlobalBinarySkew | None = None
    live_land_process: LiveLandProcess | None = None
    import_source: ImportSourceStatus | None = None
    unity_project: UnityProjectInfo | None = None
    unity_editor: UnityEditorStatus | None = None
    profile_recommendation: str | None = None
    healthy: bool
    remediation: str | None = None


# frob:waive OPAQUE001 reason="T-1038: name is always one of the fixed \
# NATIVE_EXTENSIONS module-level constant's entries (this function's one call site) -- \
# not attacker/config-controlled input; a closed, statically-declared native extension \
# name list"
def _extension_status(name: str) -> NativeExtensionStatus:
    """Import `name` and report whether it succeeded, plus its version if
    the module exposes one -- never raises, a missing extension is a normal
    (not exceptional) outcome this function reports rather than propagates."""
    try:
        mod = importlib.import_module(name)
    except Exception:
        _log.warning("doctor: native extension %s not importable", name)
        return NativeExtensionStatus(name=name, available=False, version=None)
    mod_version = getattr(mod, "__version__", None)
    _log.debug("doctor: native extension %s available (version=%s)", name, mod_version)
    return NativeExtensionStatus(name=name, available=True, version=mod_version)


# frob:doc docs/guides/release.md#native-acceleration-degrade-doctrine-t-3011
# frob:ticket T-3011
def native_degrade_warning(repo_root: Path | None = None) -> str | None:
    """PLATFORM001 applied to distribution (T-3011): a loud, one-line, by-
    name stderr warning when any of `NATIVE_EXTENSIONS` is not importable,
    printed automatically ahead of every subcommand
    (`__main__._print_startup_warnings`) rather than only surfaced on an
    explicit `frob doctor` run -- the boundary between accelerated and
    pure-Python operation must be declared, never crossed silently (the
    sdist-fallback alternative this replaces would instead attempt a
    silent Rust build, a miserable first run for exactly the adopter this
    exists to serve). Returns None the instant every declared extension
    imports cleanly -- the common, fully-accelerated case, and the only
    case this must NEVER fire for. The remediation half distinguishes a
    source checkout (`repo_root/frob-core/Cargo.toml` present: `make
    core` applies) from an installed package (no such checkout: the PyPI
    `frob[native]` extra applies) -- never raises, matching
    `_extension_status`'s fail-soft discipline."""
    missing = [
        name for name in NATIVE_EXTENSIONS if not _extension_status(name).available
    ]
    if not missing:
        return None
    names = ", ".join(missing)
    if repo_root is not None and (repo_root / "frob-core" / "Cargo.toml").exists():
        fix = REMEDIATION_HINT
    else:
        fix = (
            "install with: pip install 'frob[native]' "
            "(or: uv pip install 'frob[native]')"
        )
    message = (
        f"frob: native acceleration unavailable ({names} not importable) -- "
        f"running in pure-Python mode; {fix}"
    )
    _log.warning("native_degrade_warning: %s", message)
    return message


def _frob_version() -> str:
    """Resolve the installed `frob` distribution version, or 'unknown' when
    run from a source checkout with no registered distribution metadata."""
    try:
        return version("frob")
    except Exception:
        return "unknown"


# frob:ticket T-1501
# frob:ticket T-1515
def _combined_remediation(
    natives_healthy: bool,
    corrupt: tuple[DerivedArtifactStatus, ...],
    scaffold_needs_apply: tuple[ManagedBlockStatus, ...] = (),
    stale_mutate_journals: tuple[StaleJournal, ...] = (),
    malformed_ticket_edges: tuple[MalformedTicketEdge, ...] = (),
    stale_ticket_leases: tuple[str, ...] = (),
    venv_shims: tuple[VenvShimDrift, ...] = (),
    stale_binary: str | None = None,
    global_binary: GlobalBinarySkew | None = None,
    live_land_process: LiveLandProcess | None = None,
    external_tools: tuple[ExternalToolStatus, ...] = (),
    import_source: ImportSourceStatus | None = None,
) -> str | None:
    """The full remediation text for a `DoctorReport`: natives hint,
    derived-state hint, scaffold-conformance hint (T-0736), stale mutate-
    journal hint (T-0857), malformed-ticket-edge hint (T-1132), stale-
    ticket-lease hint (T-1131), venv-shim hint (T-1161), stale-binary-
    floor hint (T-1218), global-binary-skew hint (T-1719), live-land-process
    hint (T-1515), external-tools hint (T-3276, REQUIRED absences only --
    `_external_tools_remediation`'s own docstring states why OPTIONAL/
    OPTIONAL_FOR_GATE absences never appear here), or all joined -- `None`
    only when every part is clean.
    T-1515: an ALIVE land process is
    informational, not unhealthy (a real, in-flight `land()` is normal).
    T-1634: a CONFIRMED-dead (orphaned) holder still contributes a
    disclosure line here (so it is never silently dropped from the
    report), but no longer makes the OVERALL report unhealthy -- see
    `_assemble_doctor_report`'s `healthy` computation, which now treats
    only an AMBIGUOUS liveness probe as blocking, matching the
    confirmed_absent/ambiguous split `frob.tickets._leases.
    _probe_worktree_liveness` already draws."""
    parts = []
    if not natives_healthy:
        parts.append(REMEDIATION_HINT)
    if corrupt:
        parts.append(_derived_state_remediation(corrupt))
    if scaffold_needs_apply:
        parts.append(_scaffold_remediation(scaffold_needs_apply))
    if stale_mutate_journals:
        parts.append(_mutate_journal_remediation(stale_mutate_journals))
    if malformed_ticket_edges:
        parts.append(_malformed_edges_remediation(malformed_ticket_edges))
    if stale_ticket_leases:
        parts.append(_stale_ticket_leases_remediation(stale_ticket_leases))
    if venv_shims:
        parts.append(_venv_shim_remediation(venv_shims))
    if stale_binary:
        parts.append(stale_binary)
    if global_binary is not None and global_binary.skewed:
        parts.append(_global_binary_skew_remediation(global_binary))
    if live_land_process is not None and live_land_process.alive is not True:
        parts.append(_live_land_process_remediation(live_land_process))
    external_tools_hint = _external_tools_remediation(list(external_tools))
    if external_tools_hint is not None:
        parts.append(external_tools_hint)
    if import_source is not None and import_source.mismatched:
        parts.append(
            f"import frob resolves to {import_source.resolved_module_path}, "
            f"not this checkout's own {import_source.worktree_src} -- set "
            "PYTHONPATH=<worktree>/src (T-4459)"
        )
    return " | ".join(parts) if parts else None


# frob:ticket T-1162
def _diagnose_derived_state(resolved_root: Path):
    """T-1162: pure I/O -- under `derived_state_lock(resolved_root,
    exclusive=True)`, verify every `DERIVED_ARTIFACTS` fingerprint, detect
    drift against the previous run's manifest, and stamp a fresh manifest
    for the next run. Returns `(derived_state, corrupt, drift)`. See
    `run_diagnosis`'s docstring (T-0879) for why the exclusive acquisition
    here cannot self-deadlock."""
    with derived_state_lock(resolved_root, exclusive=True):
        derived_state = verify_derived_state(resolved_root)
        corrupt = tuple(d for d in derived_state if d.present and not d.healthy)
        drift = _detect_derived_state_drift(resolved_root, derived_state)
        _write_drift_manifest(
            resolved_root,
            {d.name: d.fingerprint for d in derived_state if d.fingerprint is not None},
        )
    return derived_state, corrupt, drift


# frob:ticket T-1162
# frob:ticket T-1515
def _collect_doctor_scans(resolved_root: Path):
    """T-1162: pure I/O -- run the five unlocked doctor scans (scaffold
    conformance, stale mutate-backup journals (T-0857), malformed ticket
    edges (T-1132), stale ticket leases (T-1131), venv-shim shebang drift
    (T-1161)) and return `(scaffold_blocks, scaffold_needs_apply,
    stale_mutate_journals, malformed_ticket_edges, stale_ticket_leases,
    venv_shims)`."""
    scaffold_blocks = scaffold_conformance_status(resolved_root)
    scaffold_needs_apply = tuple(s for s in scaffold_blocks if not s.present or s.stale)
    stale_mutate_journals = list_stale_journals(resolved_root)
    malformed_ticket_edges = tuple(scan_malformed_ticket_edges(resolved_root))
    stale_ticket_leases = scan_stale_ticket_leases(resolved_root)
    venv_shims = scan_venv_shims(resolved_root)
    live_land_process = scan_live_land_processes(resolved_root)
    return (
        scaffold_blocks,
        scaffold_needs_apply,
        stale_mutate_journals,
        malformed_ticket_edges,
        stale_ticket_leases,
        venv_shims,
        live_land_process,
    )


# frob:ticket T-1162
# frob:ticket T-1501
# frob:waive PII012 reason="'diagnosis' here is repository-health machinery (frob \
# doctor's own DoctorReport summary log), not a medical/health record about a person \
# -- a name-signature false positive, same class as run_diagnosis's own existing PII \
# surface"
# frob:ticket T-1515
def _log_doctor_diagnosis(
    healthy,
    extensions,
    corrupt,
    drift,
    scaffold_needs_apply,
    stale_mutate_journals,
    malformed_ticket_edges,
    stale_ticket_leases,
    venv_shims=(),
    stale_binary=None,
    live_land_process=None,
    global_binary=None,
    external_tools=(),
) -> None:
    """T-1162: pure I/O -- emit `run_diagnosis`'s single summary log line.
    Extracted verbatim so the report-building logic above it stays
    decision/formatting only. `venv_shims` (T-1161) defaults to `()` so
    existing positional callers are unaffected. `stale_binary` (T-1218),
    `live_land_process` (T-1515), and `global_binary` (T-1719) default to
    `None` for the same reason. `external_tools` (T-3276) defaults to
    `()` and logs only the REQUIRED entries that are missing -- the same
    "only what matters" posture the rest of this line already has."""
    _log.info(
        "doctor: healthy=%s extensions=%s derived_state_corrupt=%s drift=%s "
        "scaffold_needs_apply=%s stale_mutate_journals=%s "
        "malformed_ticket_edges=%s stale_ticket_leases=%s venv_shims=%s "
        "stale_binary=%s global_binary_skewed=%s live_land_process=%s "
        "missing_required_tools=%s",
        healthy,
        extensions,
        [d.name for d in corrupt],
        [d.name for d in drift],
        [s.block_id for s in scaffold_needs_apply],
        [s.target for s in stale_mutate_journals],
        [f"{e.ticket_id}.{e.field}" for e in malformed_ticket_edges],
        stale_ticket_leases,
        [d.script for d in venv_shims],
        bool(stale_binary),
        global_binary.skewed if global_binary is not None else None,
        live_land_process.model_dump() if live_land_process is not None else None,
        [
            t.name
            for t in external_tools
            if t.category == ToolCategory.REQUIRED and not t.present
        ],
    )


# frob:ticket T-1501
# frob:ticket T-1515
# frob:ticket T-3276
# frob:ticket T-3725
def _doctor_healthy(
    natives_healthy: bool,
    corrupt,
    scaffold_needs_apply,
    stale_mutate_journals,
    malformed_ticket_edges,
    stale_ticket_leases,
    venv_shims,
    stale_binary,
    global_binary,
    live_land_process,
    missing_required_tools: list[ExternalToolStatus],
    import_source: ImportSourceStatus | None = None,
) -> bool:
    """`_assemble_doctor_report`'s own `healthy` boolean, split out
    (T-3276) to keep that function under the ARCH001 threshold -- pure
    decision logic, no I/O, matching every other doctor helper's split
    shape (T-1501/T-1162 already established this pattern).

    T-3725: `scaffold_needs_apply` (missing/stale LOCAL managed git hooks,
    e.g. `.git/hooks/pre-commit`) is deliberately NOT one of the
    conditions below -- see CI run 33715737237, where a fresh checkout
    with a clean suite and a clean self-gate still failed a later `frob
    doctor` preflight step solely because CI never runs `frob scaffold
    apply` (there is no local git working tree convenience to protect in
    a CI runner). Hooks-missing is a dev-ergonomics nudge, not a build-
    correctness failure -- it stays visible (see `DoctorReport.
    scaffold_blocks` and `_combined_remediation`'s scaffold hint) but no
    longer flips `healthy`/exits 1, matching how `drift` and a
    CONFIRMED-dead `live_land_process` are already informational-only."""
    return (
        natives_healthy
        and not corrupt
        and not stale_mutate_journals
        and not malformed_ticket_edges
        and not stale_ticket_leases
        and not venv_shims
        and not stale_binary
        and not (global_binary is not None and global_binary.skewed)
        and not (live_land_process is not None and live_land_process.alive is None)
        and not missing_required_tools
        and not (import_source is not None and import_source.mismatched)
    )


# frob:ticket T-4416
def _assemble_doctor_report(
    resolved_root: Path,
    extensions: list,
    natives_healthy: bool,
    derived_state,
    corrupt,
    drift,
    scaffold_blocks,
    scaffold_needs_apply,
    stale_mutate_journals,
    malformed_ticket_edges,
    stale_ticket_leases,
    venv_shims,
    stale_binary,
    live_land_process=None,
    global_binary=None,
    external_tools: list[ExternalToolStatus] | None = None,
    import_source: ImportSourceStatus | None = None,
    unity_project: UnityProjectInfo | None = None,
    unity_editor: UnityEditorStatus | None = None,
    profile_recommendation: str | None = None,
) -> DoctorReport:
    """`run_diagnosis`'s own `healthy`/`DoctorReport` decision and build,
    extracted (T-1501) to keep `run_diagnosis` itself under the ARCH001
    60-line threshold now that its docstring has grown with each health
    check it documents. `healthy` is False if natives fail to import, the
    derived-state manifest is corrupt, or any of the mutate-
    journal/ticket-edge/ticket-lease/venv-shim/stale-binary/global-binary-
    skew/external-tools scans found something -- see `DoctorReport`'s own
    docstring for the per-field contract each of those checks documents.
    `scaffold_needs_apply` (T-0736) is DELIBERATELY excluded from that
    list as of T-3725 -- see `_doctor_healthy`'s docstring; it stays
    informational (surfaced in `remediation`) but never flips `healthy`.
    `live_land_process` (T-1515)
    only affects `healthy` when its holder's liveness is AMBIGUOUS
    (`alive is None`) -- this repo genuinely cannot confirm the holder is
    gone, so it stays a human-actionable finding. T-1634: a CONFIRMED-dead
    holder (`alive is False`) no longer counts against `healthy` -- the
    OS already released its `flock` the instant that process exited, so
    nothing is actually blocked, and the next real `_land_lock`
    acquisition self-heals the file's stale content on its own (logging a
    WARNING when it does). A genuinely live `land()` in flight
    (`alive is True`) was already, and remains, informational, not
    unhealthy. `external_tools` (T-3276) only affects `healthy` via a
    missing `ToolCategory.REQUIRED` entry -- see `ToolCategory`'s own
    docstring for why OPTIONAL/OPTIONAL_FOR_GATE absences never do.
    `unity_project`/`unity_editor` (T-4501) never affect `healthy` --
    see `DoctorReport`'s own docstring for why. `profile_recommendation`
    (T-4416) never affects `healthy` either -- same reasoning."""
    tools = external_tools or []
    missing_required_tools = [
        t for t in tools if t.category == ToolCategory.REQUIRED and not t.present
    ]
    healthy = _doctor_healthy(
        natives_healthy,
        corrupt,
        scaffold_needs_apply,
        stale_mutate_journals,
        malformed_ticket_edges,
        stale_ticket_leases,
        venv_shims,
        stale_binary,
        global_binary,
        live_land_process,
        missing_required_tools,
        import_source,
    )
    return DoctorReport(
        frob_version=_frob_version(),
        extensions=extensions,
        derived_state=list(derived_state),
        drift=list(drift),
        scaffold_blocks=list(scaffold_blocks),
        mutate_journals=list(stale_mutate_journals),
        malformed_ticket_edges=list(malformed_ticket_edges),
        stale_ticket_leases=list(stale_ticket_leases),
        venv_shims=list(venv_shims),
        external_tools=tools,
        stale_binary=stale_binary,
        global_binary=global_binary,
        live_land_process=live_land_process,
        import_source=import_source,
        unity_project=unity_project,
        unity_editor=unity_editor,
        profile_recommendation=profile_recommendation,
        healthy=healthy,
        remediation=_combined_remediation(
            natives_healthy,
            corrupt,
            scaffold_needs_apply,
            stale_mutate_journals,
            malformed_ticket_edges,
            stale_ticket_leases,
            venv_shims,
            stale_binary,
            global_binary,
            live_land_process,
            tuple(tools),
        ),
    )


# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
# frob:tests tests/system/test_cli_doctor.py kind="integration"
# frob:ticket T-1501
# frob:waive AFFECT001 reason="T-1162/T-1501 are pure internal extractions \
# (I/O/scan/log/assembly helpers pulled out to cut the function under the 60-line ARCH \
# threshold); behavior, inputs, outputs, and the documented contract are all \
# unchanged, so docs/guides/install.md's own content needs no edit"
# frob:ticket T-1515
# frob:ticket T-4416
def run_diagnosis(root: Path | None = None) -> DoctorReport:
    """Check every entry in `NATIVE_EXTENSIONS` for importability and
    fingerprint every entry in `DERIVED_ARTIFACTS` under `root`, building
    the full `DoctorReport`. `healthy` is True only when every native
    extension imports cleanly, no present derived artifact fails its
    integrity check, and none of the scan-based checks below found
    anything; `remediation` names whichever failed. `root` defaults to the
    current working directory, matching every other `frob` command's
    implicit-root convention -- passing it explicitly is for tests and
    non-CLI callers.

    Beyond the native/derived-state check, this also: compares fingerprints
    against the previous run's manifest (`drift`, informational only, does
    not affect `healthy`); reports stale `frob mutate` backup journals;
    scans `tickets.md`/`tickets-archive.md` for malformed `blocked_by`/
    `parent` entries and for tickets stuck `IN_PROGRESS` with no live
    lease; scans `.venv/bin/` for shebangs pointing outside this venv; and
    checks the invoked `frob`'s own version against `frob.toml`'s
    `min_frob_version` floor. Each of these DOES make `healthy` False when
    it finds something -- see `_assemble_doctor_report` and the individual
    scan functions' own docstrings for the per-check detail and originating
    incidents (T-0570/T-0604/T-0857/T-1132/T-1131/T-1161/T-1218).

    T-0879: the fingerprint-read + manifest-write sequence
    (`verify_derived_state` through `_write_drift_manifest`) holds
    `derived_state_lock(resolved_root, exclusive=True)` for its whole
    span; `frob doctor` is always a standalone invocation (never nested
    inside an already-locked `frob check` run), so this cannot self-
    deadlock against a SHARED holder in the same process.

    T-1162 split the locked derived-state pass into `_diagnose_derived_state`,
    the unlocked scans into `_collect_doctor_scans`, and the summary log
    line into `_log_doctor_diagnosis`; T-1501 further split the report
    assembly into `_assemble_doctor_report` -- this function is now just
    their composition.

    T-4501: also reports the Unity project and its editor version when
    `resolved_root` is a detected Unity project, plus whether a Unity
    Editor binary and `dotnet` were located on this machine -- see
    `_diagnose_unity_toolchain`'s own docstring for the project-detection
    gating (a non-Unity repo never attempts Unity detection at all).

    T-4416: also computes `profile_recommendation` -- a nudge toward
    `[profile] profile = "rapid"` in `frob.toml` once `resolved_root`
    crosses `_PROFILE_RECOMMEND_THRESHOLD` on ticket or file count, never
    affecting `healthy` -- see `profile_recommendation`'s own docstring.
    """
    resolved_root = root or Path.cwd()
    extensions = [_extension_status(name) for name in NATIVE_EXTENSIONS]
    natives_healthy = all(ext.available for ext in extensions)

    derived_state, corrupt, drift = _diagnose_derived_state(resolved_root)
    (
        scaffold_blocks,
        scaffold_needs_apply,
        stale_mutate_journals,
        malformed_ticket_edges,
        stale_ticket_leases,
        venv_shims,
        live_land_process,
    ) = _collect_doctor_scans(resolved_root)
    stale_binary = stale_binary_warning(resolved_root)
    global_binary = global_binary_skew(f"frob {_frob_version()}")
    external_tools = scan_external_tools()
    import_source = _import_source_status(resolved_root)
    unity_project, unity_editor = _diagnose_unity_toolchain(resolved_root)
    recommendation = profile_recommendation(resolved_root)

    report = _assemble_doctor_report(
        resolved_root,
        extensions,
        natives_healthy,
        derived_state,
        corrupt,
        drift,
        scaffold_blocks,
        scaffold_needs_apply,
        stale_mutate_journals,
        malformed_ticket_edges,
        stale_ticket_leases,
        venv_shims,
        stale_binary,
        live_land_process,
        global_binary,
        external_tools,
        import_source,
        unity_project,
        unity_editor,
        recommendation,
    )
    _log_doctor_diagnosis(
        report.healthy,
        extensions,
        corrupt,
        drift,
        scaffold_needs_apply,
        stale_mutate_journals,
        malformed_ticket_edges,
        stale_ticket_leases,
        venv_shims,
        stale_binary,
        live_land_process,
        global_binary,
        external_tools,
    )
    return report
