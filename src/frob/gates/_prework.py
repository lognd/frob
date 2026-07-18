"""Pre-work sweep storage (docs/modules/gates.md's PRE001 / `record_prework`).

**Deviation from docs/modules/gates.md**: the doc's prose suggested storing the
sweep digest "in the ticket body" via `frob.tickets`' record-style body
appender, but `frob.tickets` exposes only `record_failure` (a fixed
"## Failure log" section) -- no generic body-section appender, and
`frob.tickets` is explicitly out of scope for this phase (docs/rework.md's
cycle-avoidance: `frob.gates` may *read* tickets, but must not grow
`frob.tickets`'s public surface). The sweep is instead stored as JSON at
`.frob/prework/<ticket_id>.json`, one file per ticket, mirroring the
`.frob/coverage-stamp` posture used by TEST006. `prework_gate` reads it
back with `load_prework`.
"""

# frob:waive TEST005 reason="module line coverage 81.8%, debt T-0160"

from __future__ import annotations

import json
from pathlib import Path

from typani import Err, Ok
from typani.result import Result
from typani.unit import Unit

from frob.gates._models import GateError, PreworkSweep
from frob.logging import get_logger

_log = get_logger(__name__)


def _prework_path(root: Path, ticket_id: str) -> Path:
    """The `.frob/prework/<ticket_id>.json` path for `ticket_id`."""
    return root / ".frob" / "prework" / f"{ticket_id}.json"


# frob:doc docs/modules/gates.md#public-api
# frob:waive TEST005 reason="record_prework 66.7% branch cover, debt T-0160"
def record_prework(
    root: Path, ticket_id: str, sweep: PreworkSweep
) -> Result[Unit, GateError]:
    """Persist `sweep` for `ticket_id`; called by `frob ticket start`."""
    path = _prework_path(root, ticket_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(sweep.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        _log.error("record_prework: could not write %s: %s", path, exc)
        return Err(GateError.WriteFailed)
    _log.info(
        "record_prework: %s sweep recorded (dup=%d, xref=%d) at %s",
        ticket_id,
        sweep.dup_findings,
        len(sweep.xref_hits),
        path,
    )
    return Ok(Unit())


# frob:doc docs/modules/gates.md#public-api
# frob:waive TEST005 reason="load_prework 88.9% branch cover, debt T-0160"
def load_prework(root: Path, ticket_id: str) -> PreworkSweep | None:
    """The recorded sweep for `ticket_id`, or `None` if never recorded/unreadable."""
    path = _prework_path(root, ticket_id)
    if not path.exists():
        _log.debug("load_prework: no sweep recorded for %s", ticket_id)
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return PreworkSweep.model_validate(raw)
    except (OSError, ValueError) as exc:
        _log.warning("load_prework: %s unreadable: %s", path, exc)
        return None


__all__ = ["load_prework", "record_prework"]
