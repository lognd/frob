"""Violation baseline stamp and `--delta` filtering (docs/modules/gates.md,
T-0095).

`frob check` prints every kept violation on every run, most of them
pre-existing legacy debt (ticketed, not new). An agent driving a single
ticket to green runs `frob check` several times per ticket and re-reads the
same ~100 warn-level lines each time -- pure token cost with no new signal.
`stamp_baseline` records the current violation set (rule + file + a digest
standing in for "symbol", since `Violation` messages already embed the
symref they concern) to `.frob/baseline`, alongside the same per-file
content-hash staleness check `frob.gates._coverage.stamp_coverage` uses for
`.frob/coverage-stamp`. `delta_violations` then reports only violations
absent from that baseline set. This is an agent-facing filter only: the
human-facing warn dial (every violation, always) is unchanged -- `--delta`
is opt-in.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from typani import Err, Ok
from typani.result import Result
from typani.unit import Unit

from frob.gates._filehash import _collect_file_hashes, _sha_of
from frob.gates._models import GateError, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

_BASELINE_REL = Path(".frob") / "baseline"


# frob:doc docs/modules/gates.md#public-api
def violation_fingerprint(violation: Violation) -> str:
    """A violation's baseline identity: sha256 over rule + file + message.

    Deliberately excludes `line` -- unrelated edits routinely shift line
    numbers without changing the violation itself, and a fingerprint that
    moves with every unrelated diff would make the baseline useless. The
    message already embeds the symref for most rules, standing in for a
    dedicated "symbol digest" column without widening `Violation`.
    """
    hasher = hashlib.sha256()
    hasher.update(f"{violation.rule}\n{violation.file}\n{violation.message}".encode())
    return hasher.hexdigest()


# frob:doc docs/modules/gates.md#public-api
# frob:waive TEST005 reason="stamp_baseline 75.0% branch cover, debt T-0160"
def stamp_baseline(
    root: Path, violations: tuple[Violation, ...]
) -> Result[Unit, GateError]:
    """Record `violations`' fingerprints plus current file hashes to `.frob/baseline`.

    The only writer of `.frob/baseline`; `is_baseline_stale` compares its
    file hashes against the live tree the same way `stamp_coverage`/TEST006
    already do, so a stale stamp is a detectable condition, not silent
    drift.
    """
    file_hashes = _collect_file_hashes(root)
    fingerprints = sorted({violation_fingerprint(v) for v in violations})
    stamp = {"file_hashes": file_hashes, "fingerprints": fingerprints}
    stamp_path = root / _BASELINE_REL
    try:
        stamp_path.parent.mkdir(parents=True, exist_ok=True)
        stamp_path.write_text(json.dumps(stamp, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        _log.error("stamp_baseline: could not write %s: %s", stamp_path, exc)
        return Err(GateError.WriteFailed)
    _log.info(
        "stamp_baseline: stamped %d violation(s) over %d file(s)",
        len(fingerprints),
        len(file_hashes),
    )
    return Ok(Unit())


# frob:doc docs/modules/gates.md#public-api
# frob:waive TEST005 reason="load_baseline 85.7% branch cover, debt T-0160"
def load_baseline(root: Path) -> dict | None:
    """The raw `.frob/baseline` document, or `None` if missing/unreadable."""
    stamp_path = root / _BASELINE_REL
    if not stamp_path.exists():
        return None
    try:
        return json.loads(stamp_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log.warning("load_baseline: %s unreadable: %s", stamp_path, exc)
        return None


# frob:doc docs/modules/gates.md#public-api
def is_baseline_stale(root: Path, baseline: dict) -> bool:
    """Whether any file hash in `baseline` no longer matches the live tree.

    Mirrors TEST006's coverage-stamp staleness check: a stale baseline
    silently hiding violations that moved back into the "new" set would be
    a worse failure mode than no baseline at all, so `--delta` callers must
    check this before trusting the filtered result.
    """
    stamped: dict[str, str] = baseline.get("file_hashes", {})
    for path, digest in stamped.items():
        live = _sha_of(root / path)
        if live != digest:
            _log.debug("is_baseline_stale: %s changed since stamp", path)
            return True
    return False


# frob:doc docs/modules/gates.md#public-api
def delta_violations(
    violations: tuple[Violation, ...], baseline: dict
) -> tuple[Violation, ...]:
    """Violations from `violations` whose fingerprint is absent from `baseline`.

    Pure filter, no IO -- callers load the baseline (and check staleness)
    themselves so this stays trivially testable.
    """
    known = frozenset(baseline.get("fingerprints", []))
    return tuple(v for v in violations if violation_fingerprint(v) not in known)


__all__ = [
    "delta_violations",
    "is_baseline_stale",
    "load_baseline",
    "stamp_baseline",
    "violation_fingerprint",
]
