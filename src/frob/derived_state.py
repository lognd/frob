# frob:waive TEST003 reason="pre-existing T-0319-class doctor debt, system kind only \
# -- same posture as doctor.py's own module-level waiver, unchanged by this T-2407 \
# relocation"
"""Derived-artifact integrity fingerprinting (T-0570), split out of
`frob.doctor` by T-2407's SYS003 calibration pass.

`verify_derived_state` fingerprints every entry in `DERIVED_ARTIFACTS`
under a repo root and reports presence/validity -- `frob doctor`'s own
`run_diagnosis` was its only in-repo caller until `frob.check` also
started consuming it directly (T-0570's own follow-up) to fail the
build BEFORE a stale/corrupt cache produces a pile of confusing
downstream `frob check`/`frob dup` findings (docs/guides/install.md
#derived-state-integrity-manifest-t-0570).

That second caller is what T-2407 measured as an undeclared SYS003
`checker -> cli` edge: `frob.check` needing this fingerprint pass is
architecturally sound, but `frob.doctor` (this repo's `cli`-node home
for the `frob doctor` subcommand, T-0500) is the wrong place for a
general derived-state health check to live -- this module has no
argparse/CLI-dispatch surface of its own, exactly the misplaced-leaf-
utility shape T-2380/T-2403 already relocated `excludes.py`/`yamlio.py`
/`tomlio.py`/`repo_meta.py` for. `frob.doctor` keeps its own drift-
manifest tracking (`_detect_derived_state_drift` et al, doctor-only, no
external caller) and imports `DerivedArtifactStatus`/`verify_derived_
state` back from here, same shape those four prior moves left behind."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel

from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/guides/install.md#derived-state-integrity-manifest-t-0570
# frob:ticket T-2407
# frob:waive PII012 reason="'diagnosis' here is repository-health machinery (frob \
# doctor's own DoctorReport summary log), not a medical/health record about a person \
# -- a name-signature false positive, same class as doctor.py's own pre-existing \
# PII012 waiver on this identical token"
#: `(manifest name, path relative to root, byte-format kind)` for every
#: derived artifact `frob` writes that `run_diagnosis`/`frob.check` both
#: fingerprint. `"sqlite"` entries are validated by header magic bytes
#: (see `_SQLITE_MAGIC`); `"json"` entries by `json.loads`. Deliberately
#: excludes `.frob/telemetry.jsonl` (append-only event log, not a cache
#: another gate trusts for correctness) and native build output (already
#: covered by `frob.doctor.NATIVE_EXTENSIONS` via direct import, a
#: stronger check than a fingerprint could give).
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
# frob:ticket T-2407
_SQLITE_MAGIC = b"SQLite format 3\x00"


# frob:doc docs/guides/install.md#derived-state-integrity-manifest-t-0570
# frob:tests tests/system/test_cli_doctor.py kind="integration"
# frob:ticket T-2407
class DerivedArtifactStatus(BaseModel):
    """One derived artifact's presence, content fingerprint, and validity,
    as observed by `verify_derived_state` (T-0570)."""

    model_config = {}

    name: str
    path: str
    present: bool
    healthy: bool
    fingerprint: str | None = None
    detail: str | None = None


# frob:ticket T-2407
def _sqlite_validity(data: bytes) -> str | None:
    """`None` if `data` starts with the SQLite magic header, else a short
    corruption detail string -- never raises on garbage bytes."""
    if data.startswith(_SQLITE_MAGIC):
        return None
    return "not a valid SQLite file (bad or missing header)"


# frob:ticket T-2407
def _json_validity(data: bytes) -> str | None:
    """`None` if `data` parses as JSON, else a short corruption detail
    string -- never raises on malformed bytes."""
    try:
        json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return f"malformed JSON ({exc})"
    return None


# frob:ticket T-2407
_VALIDATORS = {"sqlite": _sqlite_validity, "json": _json_validity}


# frob:waive OPAQUE001 reason="T-1038: kind is always a literal 'sqlite'/'json' string \
# passed by this module's own internal derived-artifact manifest (every call site is \
# in this file, never user/CLI input) -- the dict-key lookup can only ever resolve to \
# one of the two _VALIDATORS entries declared right above"
# frob:ticket T-2407
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
# frob:ticket T-2407
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
