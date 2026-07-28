# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: src/frob/doctor.py's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim"
# frob:waive SCOPE001 reason="T-0319 scope comma-joined, matches nothing (T-0241 bug)"
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
(`detect_derived_state_drift`), so a valid-format artifact that was
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
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from pydantic import BaseModel

from frob.logging import get_logger
from frob.mutate._journal import StaleJournal, list_stale_journals
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
class DerivedArtifactDrift(BaseModel):
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
def detect_derived_state_drift(
    root: Path, current: tuple[DerivedArtifactStatus, ...]
) -> tuple[DerivedArtifactDrift, ...]:
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
    drift: list[DerivedArtifactDrift] = []
    for d in current:
        if d.fingerprint is None:
            continue
        prev_fingerprint = previous.get(d.name)
        if prev_fingerprint is not None and prev_fingerprint != d.fingerprint:
            drift.append(
                DerivedArtifactDrift(
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
class DoctorReport(BaseModel):
    """Full `frob doctor` diagnosis: per-extension status, derived-artifact
    integrity manifest (T-0570), cross-run content drift (T-0604),
    managed-boilerplate-block conformance (T-0736), stale mutate-backup
    journals needing restore (T-0857), the overall verdict, and
    remediation hint (empty when everything is healthy).

    `drift` is informational only -- see `detect_derived_state_drift`'s
    docstring for why it does not feed into `healthy`/`remediation` the
    way a corrupt (`derived_state`) artifact does. `mutate_journals` is
    the opposite: any entry DOES make `healthy` False -- it names a real
    source file currently sitting in mutant form on disk, not disposable
    cache churn."""

    model_config = {}

    frob_version: str
    extensions: list[NativeExtensionStatus]
    derived_state: list[DerivedArtifactStatus] = []
    drift: list[DerivedArtifactDrift] = []
    scaffold_blocks: list[ManagedBlockStatus] = []
    mutate_journals: list[StaleJournal] = []
    healthy: bool
    remediation: str | None = None


def _extension_status(name: str) -> NativeExtensionStatus:
    """Import `name` and report whether it succeeded, plus its version if
    the module exposes one -- never raises, a missing extension is a normal
    (not exceptional) outcome this function reports rather than propagates."""
    try:
        mod = importlib.import_module(name)
    except ImportError:
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
    except PackageNotFoundError:
        return "unknown"


def _combined_remediation(
    natives_healthy: bool,
    corrupt: tuple[DerivedArtifactStatus, ...],
    scaffold_needs_apply: tuple[ManagedBlockStatus, ...] = (),
    stale_mutate_journals: tuple[StaleJournal, ...] = (),
) -> str | None:
    """The full remediation text for a `DoctorReport`: natives hint,
    derived-state hint, scaffold-conformance hint (T-0736), stale mutate-
    journal hint (T-0857), or all joined -- `None` only when every part is
    clean."""
    parts = []
    if not natives_healthy:
        parts.append(REMEDIATION_HINT)
    if corrupt:
        parts.append(_derived_state_remediation(corrupt))
    if scaffold_needs_apply:
        parts.append(_scaffold_remediation(scaffold_needs_apply))
    if stale_mutate_journals:
        parts.append(_mutate_journal_remediation(stale_mutate_journals))
    return " | ".join(parts) if parts else None


# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
# frob:tests tests/system/test_cli_doctor.py kind="integration"
def run_diagnosis(root: Path | None = None) -> DoctorReport:
    """Check every entry in `NATIVE_EXTENSIONS` for importability and
    fingerprint every entry in `DERIVED_ARTIFACTS` under `root` (T-0570),
    building the full `DoctorReport`. `healthy` is True only when every
    native extension imports cleanly AND no present derived artifact fails
    its integrity check; `remediation` names whichever failed. `root`
    defaults to the current working directory, matching every other
    `frob` command's implicit-root convention -- passing it explicitly is
    for tests and non-CLI callers.

    T-0604: also compares this run's fingerprints against the manifest the
    PREVIOUS `frob doctor` run persisted (`detect_derived_state_drift`)
    and stamps a fresh manifest for the NEXT run before returning --
    `report.drift` is informational only and does not affect `healthy`,
    see that function's docstring for why.

    T-0857: also reports every stale `frob mutate` backup journal under
    `.frob/mutate-backup/` (`list_stale_journals`) -- UNLIKE `drift`, a
    present journal DOES make `healthy` False (see `DoctorReport`'s
    docstring).

    T-0879: the fingerprint-read + manifest-write sequence
    (`verify_derived_state` through `_write_drift_manifest`) holds
    `derived_state_lock(resolved_root, exclusive=True)` for its whole
    span -- this is `run_diagnosis`'s own rebuild/write path over
    `.frob`'s derived-state manifest, and `frob doctor` is always a
    standalone invocation (never nested inside an already-locked `frob
    check` run), so the EXCLUSIVE acquisition here cannot self-deadlock
    against a SHARED holder in the same process. See
    `derived_state_lock`'s docstring for the shared/exclusive contract.
    """
    resolved_root = root or Path.cwd()
    extensions = [_extension_status(name) for name in NATIVE_EXTENSIONS]
    natives_healthy = all(ext.available for ext in extensions)

    with derived_state_lock(resolved_root, exclusive=True):
        derived_state = verify_derived_state(resolved_root)
        corrupt = tuple(d for d in derived_state if d.present and not d.healthy)
        drift = detect_derived_state_drift(resolved_root, derived_state)
        _write_drift_manifest(
            resolved_root,
            {d.name: d.fingerprint for d in derived_state if d.fingerprint is not None},
        )

    scaffold_blocks = scaffold_conformance_status(resolved_root)
    scaffold_needs_apply = tuple(s for s in scaffold_blocks if not s.present or s.stale)

    stale_mutate_journals = list_stale_journals(resolved_root)

    healthy = (
        natives_healthy
        and not corrupt
        and not scaffold_needs_apply
        and not stale_mutate_journals
    )
    report = DoctorReport(
        frob_version=_frob_version(),
        extensions=extensions,
        derived_state=list(derived_state),
        drift=list(drift),
        scaffold_blocks=list(scaffold_blocks),
        mutate_journals=list(stale_mutate_journals),
        healthy=healthy,
        remediation=_combined_remediation(
            natives_healthy, corrupt, scaffold_needs_apply, stale_mutate_journals
        ),
    )
    _log.info(
        "doctor: healthy=%s extensions=%s derived_state_corrupt=%s drift=%s "
        "scaffold_needs_apply=%s stale_mutate_journals=%s",
        healthy,
        extensions,
        [d.name for d in corrupt],
        [d.name for d in drift],
        [s.block_id for s in scaffold_needs_apply],
        [s.target for s in stale_mutate_journals],
    )
    return report
