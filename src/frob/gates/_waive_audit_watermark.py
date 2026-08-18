"""T-2467: persisted watermark state for the periodic `frob:waive` honesty
audit (T-1614's reshaped operating mode).

T-1614 used to be `runs_last` -- undispatchable while any other ticket in
the repo was queued/in-progress, which in a repo with continuous ticket
inflow is a condition that structurally never holds (T-2467's own filing:
48 open tickets, measured, at filing time). This module gives the audit a
PERSISTED PROGRESS MARKER instead of a one-shot terminal precondition: the
commit sha the last completed audit pass covered, so the NEXT pass only
has to look at `frob:waive` directives introduced since then, never the
whole repo, and never blocked on the queue being empty.

The watermark is deliberately dumb storage -- it records WHERE the last
completed audit stopped, not any judgment about the waivers found there.
The judgment (STILL NECESSARY AND HONEST / OBSOLETE / COP-OUT / PERMANENT
BY DESIGN, T-1614's own rubric) happens in `frob.app.ticket_runner.
_waive_audit`, which reads and advances this state only after an audit
pass is genuinely complete -- see that module's `AuditVerdict` for the
fail-loudly distinction between "audited and clean" and "nothing to
audit" this file's callers must not blur.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel
from typani import Err, Ok, Result
from typani.error_set import ErrorSet

from frob.logging import get_logger

_log = get_logger(__name__)

#: `.frob/waive-audit-watermark.json`, mirroring the shape of the existing
#: `.frob/baseline-chunks.json` / `.frob/check-budget-state.json` scratch
#: state files (`frob.app._check_chunking`) -- a per-checkout, gitignored
#: (`.frob/` is repo-gitignored) progress marker, not committed history.
_WATERMARK_REL = Path(".frob") / "waive-audit-watermark.json"


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_watermark.py::TestLoadWatermark.test_missing_file_is_not_\
# found kind="unit"
class WaiveAuditWatermarkError(ErrorSet):
    """Fallible outcomes of reading/writing the persisted watermark."""

    NotFound = "no watermark file exists yet at the expected path"
    Malformed = "the watermark file exists but does not parse as the expected shape"
    WriteFailed = "the watermark file could not be written"


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_watermark.py::TestSaveWatermark.test_round_trips_through_\
# load kind="unit"
class WaiveAuditWatermark(BaseModel):
    """One completed audit pass's stopping point.

    `commit_sha` is the repo HEAD the pass covered UP TO AND INCLUDING --
    the next incremental pass scans `frob:waive` directives introduced in
    `commit_sha..HEAD`. `catchup_remaining` is nonzero only when the most
    recent pass was a BOUNDED catch-up pass (T-2467's first-run mode) that
    did not cover the entire pre-watermark backlog in one go; a nonzero
    value here means the next pass must continue catch-up rather than
    treat the repo as fully audited-to-date.
    """

    model_config = {}

    commit_sha: str
    audited_at: datetime
    waivers_audited: int
    catchup_remaining: int = 0


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_watermark.py::TestSaveWatermark.test_creates_frob_dir_if_\
# missing kind="unit"
def watermark_path(root: Path) -> Path:
    """The watermark file's path for a checkout rooted at `root`."""
    return root / _WATERMARK_REL


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_watermark.py::TestLoadWatermark.test_missing_file_is_not_\
# found kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_watermark.py::TestLoadWatermark.test_malformed_json_is_ma\
# lformed kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_watermark.py::TestLoadWatermark.test_valid_file_round_tri\
# ps kind="unit"
def load_watermark(root: Path) -> Result[WaiveAuditWatermark, WaiveAuditWatermarkError]:
    """Read the persisted watermark, distinguishing "never audited"
    (`NotFound`) from "audited before, but the state is unreadable"
    (`Malformed`) -- callers must not collapse these into one silent
    catch-up decision (a malformed file is a real defect to surface, not
    a reason to quietly restart from zero)."""
    path = watermark_path(root)
    if not path.exists():
        _log.debug("load_watermark: no watermark at %s", path)
        return Err(WaiveAuditWatermarkError.NotFound)
    try:
        raw = path.read_text()
    except OSError as exc:
        _log.warning("load_watermark: could not read %s: %s", path, exc)
        return Err(WaiveAuditWatermarkError.Malformed)
    try:
        data = _json.loads(raw)
        watermark = WaiveAuditWatermark.model_validate(data)
    except Exception as exc:  # noqa: BLE001 -- any parse/validation failure is Malformed
        _log.warning("load_watermark: %s did not parse as a watermark: %s", path, exc)
        return Err(WaiveAuditWatermarkError.Malformed)
    return Ok(watermark)


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_watermark.py::TestSaveWatermark.test_round_trips_through_\
# load kind="unit"
def save_watermark(
    root: Path, watermark: WaiveAuditWatermark
) -> Result[None, WaiveAuditWatermarkError]:
    """Persist `watermark`, creating `.frob/` if this is the checkout's
    first ever state file. Overwrites any prior watermark wholesale --
    the watermark is a single current-position marker, not a log (the
    audit trail of PAST passes belongs to the tickets each pass files,
    not to this file)."""
    path = watermark_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(watermark.model_dump_json(indent=2) + "\n")
    except OSError as exc:
        _log.warning("save_watermark: could not write %s: %s", path, exc)
        return Err(WaiveAuditWatermarkError.WriteFailed)
    _log.info(
        "save_watermark: %s -> commit=%s waivers_audited=%d catchup_remaining=%d",
        path,
        watermark.commit_sha,
        watermark.waivers_audited,
        watermark.catchup_remaining,
    )
    return Ok(None)


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_watermark.py::TestSaveWatermark.test_round_trips_through_\
# load kind="unit"
def utc_now() -> datetime:
    """The current UTC time, as a single seam every caller uses instead of
    each calling `datetime.now(timezone.utc)` directly -- keeps
    `WaiveAuditWatermark.audited_at` monkeypatch-testable in one place."""
    return datetime.now(timezone.utc)
