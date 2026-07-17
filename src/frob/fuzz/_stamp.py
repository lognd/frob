"""`.frob/fuzz-stamp.json`: per-target body digest at the last fuzz run (docs/fuzz.md).

Mirrors `frob.gates._coverage`'s stamp posture: the stamp is a plain JSON
map keyed by `ref` (a `path::qualname` symref) to the body digest recorded
at the last completed budgeted run. FUZZ003 compares digests, never
wall-clock age, so an untouched function never re-obligates.
"""

from __future__ import annotations

import json
from pathlib import Path

from typani import Err, Ok
from typani.result import Result
from typani.unit import Unit

from frob.fuzz._models import FuzzError, FuzzResult
from frob.logging import get_logger

_log = get_logger(__name__)

_STAMP_REL = Path(".frob") / "fuzz-stamp.json"


# frob:doc docs/fuzz.md#public-api
def stamp_fuzz(root: Path, results: tuple[FuzzResult, ...]) -> Result[Unit, FuzzError]:
    """Record `results`' body digests, merged over any prior stamp at `root`."""
    stamp_path = root / _STAMP_REL
    recorded = dict(load_fuzz_stamp(root) or {})
    for result in results:
        recorded[result.ref] = result.body_digest

    try:
        stamp_path.parent.mkdir(parents=True, exist_ok=True)
        stamp_path.write_text(json.dumps(recorded, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        _log.error("stamp_fuzz: could not write %s: %s", stamp_path, exc)
        return Err(FuzzError.StampFailed)

    _log.info("stamp_fuzz: recorded %d target(s) at %s", len(results), stamp_path)
    return Ok(Unit())


# frob:doc docs/fuzz.md#public-api
def load_fuzz_stamp(root: Path) -> dict[str, str] | None:
    """The raw `{ref: body_digest}` map from `.frob/fuzz-stamp.json`, or `None`."""
    stamp_path = root / _STAMP_REL
    if not stamp_path.exists():
        return None
    try:
        raw = json.loads(stamp_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log.warning("load_fuzz_stamp: %s unreadable: %s", stamp_path, exc)
        return None
    if not isinstance(raw, dict):
        _log.warning("load_fuzz_stamp: %s is not a JSON object", stamp_path)
        return None
    return {str(k): str(v) for k, v in raw.items()}


__all__ = ["load_fuzz_stamp", "stamp_fuzz"]
