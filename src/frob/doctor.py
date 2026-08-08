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

from __future__ import annotations

import hashlib
import importlib
import json
import shutil
from importlib.metadata import version
from pathlib import Path

from pydantic import BaseModel

from frob.app._config_meta import stale_binary_warning
from frob.logging import get_logger
from frob.mutate._journal import StaleJournal, list_stale_journals
from frob.process._guard import guarded_subprocess_run
from frob.process._lock import derived_state_lock
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
#: `(manifest name, path relative to root, byte-format kind)` for every
#: derived artifact `frob` writes that `run_diagnosis` fingerprints.
#: `"sqlite"` entries are validated by header magic bytes (see
#: `_SQLITE_MAGIC`); `"json"` entries by `json.loads`. Deliberately excludes
#: `.frob/telemetry.jsonl` (append-only event log, not a cache another gate
#: trusts for correctness) and native build output (already covered by
#: `NATIVE_EXTENSIONS` above via direct import, a stronger check than a
#: fingerprint could give).
DERIVED_ARTIFACTS: tuple[tuple[str, str, str], ...] = (
    ("graph-cache", ".frob/cache.db", "sqlite"),
    ("dup-cache", ".frob/dup.db", "sqlite"),
    ("vet-cache", ".frob/vet.db", "sqlite"),
    ("coverage-stamp", ".frob/coverage-stamp", "json"),
    ("baseline", ".frob/baseline", "json"),
    ("coverage-lock", "frob-coverage.lock.json", "json"),
)

#: The first 16 bytes of any valid SQLite database file (the format's own
#: fixed magic header) -- a `"sqlite"`-kind artifact whose bytes don't start
#: with this is corrupt/truncated/not-actually-sqlite, not merely "old".
_SQLITE_MAGIC = b"SQLite format 3\x00"


# frob:doc docs/guides/install.md#derived-state-integrity-manifest-t-0570
class DerivedArtifactStatus(BaseModel):
    """One derived artifact's presence, content fingerprint, and validity,
    as observed by `frob doctor` (T-0570)."""

    model_config = {}

    name: str
    path: str
    present: bool
    healthy: bool
    fingerprint: str | None = None
    detail: str | None = None


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
# frob:tests \
# tests/system/test_cli_doctor.py::TestDoctorVenvShims.test_flags_shebang_outside_venv
# frob:tests tests/system/test_cli_doctor.py::TestDoctorVenvShims.test_clean_shebang_reports_nothing  # noqa: E501
# frob:tests tests/system/test_cli_doctor.py::TestDoctorVenvShims.test_no_venv_directory_reports_nothing  # noqa: E501
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to Path.iterdir/ \
# Path.resolve/bytes.decode, stdlib pathlib/bytes calls the resolver cannot statically \
# bound; every locally-visible fallible step (the two entry-level OSError sites, the \
# shebang-dir resolve) is already caught above"
# frob:waive EXHAUST002 reason="T-1062: same resolver artifact as EXHAUST001 above -- \
# the flagged KeyError trace has no locally-visible source; every fallible step here \
# is already narrowly caught"
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
# frob:tests tests/test_doctor.py::test_global_binary_skew_reports_disagreement
# frob:tests tests/test_doctor.py::test_global_binary_skew_none_when_no_global_frob
# frob:tests \
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


def _sqlite_validity(data: bytes) -> str | None:
    """`None` if `data` starts with the SQLite magic header, else a short
    corruption detail string -- never raises on garbage bytes."""
    if data.startswith(_SQLITE_MAGIC):
        return None
    return "not a valid SQLite file (bad or missing header)"


def _json_validity(data: bytes) -> str | None:
    """`None` if `data` parses as JSON, else a short corruption detail
    string -- never raises on malformed bytes."""
    try:
        json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return f"malformed JSON ({exc})"
    return None


_VALIDATORS = {"sqlite": _sqlite_validity, "json": _json_validity}


# frob:waive OPAQUE001 reason="T-1038: kind is always a literal 'sqlite'/'json' string \
# passed by this module's own internal derived-artifact manifest (every call site is \
# in this file, never user/CLI input) -- the dict-key lookup can only ever resolve to \
# one of the two _VALIDATORS entries declared right above"
def _artifact_status(
    root: Path, name: str, rel_path: str, kind: str
) -> DerivedArtifactStatus:
    """One `DerivedArtifactStatus` for `root/rel_path` -- absent is reported
    as healthy (nothing written yet is not corruption); present-but-unreadable
    or present-but-invalid-for-`kind` is reported unhealthy with `detail`
    explaining why. Never raises: an artifact this function cannot even
    read is itself a diagnosis, not an exception to propagate."""
    path = root / rel_path
    if not path.exists():
        return DerivedArtifactStatus(
            name=name, path=rel_path, present=False, healthy=True
        )
    try:
        data = path.read_bytes()
    except OSError as exc:
        _log.warning("doctor: derived artifact %s (%s) unreadable: %s", name, path, exc)
        return DerivedArtifactStatus(
            name=name,
            path=rel_path,
            present=True,
            healthy=False,
            detail=f"unreadable: {exc}",
        )
    fingerprint = hashlib.sha256(data).hexdigest()
    detail = _VALIDATORS[kind](data)
    healthy = detail is None
    if not healthy:
        _log.warning(
            "doctor: derived artifact %s (%s) failed integrity check: %s",
            name,
            path,
            detail,
        )
    return DerivedArtifactStatus(
        name=name,
        path=rel_path,
        present=True,
        healthy=healthy,
        fingerprint=fingerprint,
        detail=detail,
    )


# frob:doc docs/guides/install.md#derived-state-integrity-manifest-t-0570
# frob:tests tests/system/test_cli_doctor.py kind="integration"
def verify_derived_state(root: Path) -> tuple[DerivedArtifactStatus, ...]:
    """Fingerprint every entry in `DERIVED_ARTIFACTS` under `root` and report
    its presence/validity -- the one doctor-first pass `run_diagnosis` folds
    into `DoctorReport.derived_state`, so stale/corrupt cache state is a
    named finding instead of a pile of confusing downstream `frob check`/
    `frob dup` errors (T-0570)."""
    return tuple(
        _artifact_status(root, name, rel_path, kind)
        for name, rel_path, kind in DERIVED_ARTIFACTS
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
# frob:tests \
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


# frob:tests \
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


# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
# frob:ticket T-1501
# frob:ticket T-1515
class DoctorReport(BaseModel):
    """Full `frob doctor` diagnosis: per-extension status, derived-artifact
    integrity manifest (T-0570), cross-run content drift (T-0604),
    managed-boilerplate-block conformance (T-0736), stale mutate-backup
    journals needing restore (T-0857), the overall verdict, and
    remediation hint (empty when everything is healthy).

    `drift` is informational only -- see `_detect_derived_state_drift`'s
    docstring for why it does not feed into `healthy`/`remediation` the
    way a corrupt (`derived_state`) artifact does. `mutate_journals` is
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
    counts against `healthy`."""

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
    stale_binary: str | None = None
    global_binary: GlobalBinarySkew | None = None
    live_land_process: LiveLandProcess | None = None
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
) -> str | None:
    """The full remediation text for a `DoctorReport`: natives hint,
    derived-state hint, scaffold-conformance hint (T-0736), stale mutate-
    journal hint (T-0857), malformed-ticket-edge hint (T-1132), stale-
    ticket-lease hint (T-1131), venv-shim hint (T-1161), stale-binary-
    floor hint (T-1218), global-binary-skew hint (T-1719), live-land-process
    hint (T-1515), or all joined -- `None` only when every part is clean.
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
) -> None:
    """T-1162: pure I/O -- emit `run_diagnosis`'s single summary log line.
    Extracted verbatim so the report-building logic above it stays
    decision/formatting only. `venv_shims` (T-1161) defaults to `()` so
    existing positional callers are unaffected. `stale_binary` (T-1218),
    `live_land_process` (T-1515), and `global_binary` (T-1719) default to
    `None` for the same reason."""
    _log.info(
        "doctor: healthy=%s extensions=%s derived_state_corrupt=%s drift=%s "
        "scaffold_needs_apply=%s stale_mutate_journals=%s "
        "malformed_ticket_edges=%s stale_ticket_leases=%s venv_shims=%s "
        "stale_binary=%s global_binary_skewed=%s live_land_process=%s",
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
    )


# frob:ticket T-1501
# frob:ticket T-1515
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
) -> DoctorReport:
    """`run_diagnosis`'s own `healthy`/`DoctorReport` decision and build,
    extracted (T-1501) to keep `run_diagnosis` itself under the ARCH001
    60-line threshold now that its docstring has grown with each health
    check it documents. `healthy` is False if natives fail to import, the
    derived-state manifest is corrupt, or any of the scaffold/mutate-
    journal/ticket-edge/ticket-lease/venv-shim/stale-binary/global-binary-
    skew scans found something -- see `DoctorReport`'s own docstring for
    the per-field contract each of those checks documents. `live_land_process` (T-1515)
    only affects `healthy` when its holder's liveness is AMBIGUOUS
    (`alive is None`) -- this repo genuinely cannot confirm the holder is
    gone, so it stays a human-actionable finding. T-1634: a CONFIRMED-dead
    holder (`alive is False`) no longer counts against `healthy` -- the
    OS already released its `flock` the instant that process exited, so
    nothing is actually blocked, and the next real `_land_lock`
    acquisition self-heals the file's stale content on its own (logging a
    WARNING when it does). A genuinely live `land()` in flight
    (`alive is True`) was already, and remains, informational, not
    unhealthy."""
    healthy = (
        natives_healthy
        and not corrupt
        and not scaffold_needs_apply
        and not stale_mutate_journals
        and not malformed_ticket_edges
        and not stale_ticket_leases
        and not venv_shims
        and not stale_binary
        and not (global_binary is not None and global_binary.skewed)
        and not (live_land_process is not None and live_land_process.alive is None)
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
        stale_binary=stale_binary,
        global_binary=global_binary,
        live_land_process=live_land_process,
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
    )
    return report
