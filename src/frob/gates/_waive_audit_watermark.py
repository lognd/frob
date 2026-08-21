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

T-2721: THE WATERMARK IS COMMITTED, GIT-TRACKED STATE, NOT A GITIGNORED
SCRATCH FILE. It used to live at `.frob/waive-audit-watermark.json` --
`.frob/` is repo-gitignored, so that state was per-checkout only. Agents
run this audit from DISPOSABLE worktrees (`.claude/worktrees/<id>`), so a
completed pass's progress lived only inside a directory that gets deleted
on cleanup -- measured directly: T-1614's pass classified 100 waiver
directives, and afterward `.claude/worktrees/t-1614/.frob/waive-audit-
watermark.json` existed while the primary checkout's own copy was ABSENT.
`waive-audit scan` from the primary checkout reported `not_covered=967`
before manually copying the worktree's file across, `not_covered=867`
after -- proof the 100 classifications were genuinely gone from
everywhere the fleet actually looks, and silently so (nothing warns that
progress is about to be discarded; the next scan just re-reports the old
denominator). This defeats T-2467's entire point: a PERIODIC, incremental
audit over a large backlog only works if progress accumulates across
passes, and every agent-run pass was silently resetting to zero.

Fixed by moving the watermark out of `.frob/` to a plain, GIT-TRACKED file
at the repo root (`waive-audit-watermark.json`, `.gitignore`'s `!`-negated
the same way `rapid-debt.jsonl` already is) and having `save_watermark`
commit it -- in `root` itself, AND, when `root` is a worktree of some
other primary checkout, mirrored and committed onto that primary checkout
too (reusing `frob.tickets._land._resolve_primary_checkout`/`frob.
tickets._leases.refuse_if_land_in_progress`, the same primitives `frob.
app.ticket_runner._ledger_mirror`'s T-2563 worktree-ledger-mirror already
established for exactly this "an edit made in a worktree must be visible
to the whole fleet immediately, not only once this ticket lands" shape).
`waive-audit` is `NOT_TICKET_SCOPED` in `LEDGER_VERB_STRATEGY` -- its
write is not part of any ticket's own pathspecs, so without this mirror a
worktree's watermark commit would never reach `main` on its own at all,
even after that worktree's ticket eventually lands. Both halves (commit
in `root`, mirror onto `primary`) are best-effort and never raise: a
`git`/lock failure degrades to a loud `_log.error` (matching `frob.app.
ticket_runner._ledger_mirror._log_mirror_unavailable`'s posture) rather
than failing the audit pass itself -- the watermark write to disk already
succeeded by that point, and refusing the whole call would throw away
real, already-computed audit progress over a git plumbing hiccup.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel
from typani import Err, Ok, Result
from typani.error_set import ErrorSet

from frob import gitio
from frob.logging import get_logger

_log = get_logger(__name__)

#: `waive-audit-watermark.json` at the repo ROOT (T-2721) -- deliberately
#: OUTSIDE `.frob/` and `.gitignore`-negated (`!waive-audit-watermark.
#: json`, matching `!rapid-debt.jsonl`'s existing precedent) so this
#: state is git-tracked, committed history rather than per-checkout
#: scratch. See this module's own docstring, "THE WATERMARK IS COMMITTED,
#: GIT-TRACKED STATE", for the incident this fixes.
_WATERMARK_REL = Path("waive-audit-watermark.json")


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
    """One completed (or partially banked) audit pass's stopping point.

    `commit_sha` is the repo HEAD the pass covered UP TO AND INCLUDING --
    the next incremental pass scans `frob:waive` directives introduced in
    `commit_sha..HEAD`. `catchup_remaining` is nonzero only when the most
    recent pass was a BOUNDED catch-up pass (T-2467's first-run mode) that
    did not cover the entire pre-watermark backlog in one go; a nonzero
    value here means the next pass must continue catch-up rather than
    treat the repo as fully audited-to-date.

    T-2485: `catchup_remaining > 0` is a BANKED PARTIAL PASS, never a
    completed one -- a caller reading this watermark must be able to tell
    "audited N of M so far, M-N remain" from "audited everything, found
    nothing" without cross-referencing anything else (T-2391's
    fail-loudly doctrine: those two must never render the same way).
    `catchup_covered` is the set of already-reviewed waiver identities
    (`"file:line:rule"`, see `frob.app.ticket_runner._waive_audit.
    _waiver_identity`) accumulated across banked partial passes so the
    NEXT catch-up scan's bounded window advances past what was already
    reviewed instead of re-offering the same waivers forever. Both fields
    reset to their zero/empty defaults the moment a catch-up run finally
    covers the whole backlog (`catchup_remaining` hits 0) -- at that
    point the watermark reverts to plain incremental-since-`commit_sha`
    mode and the covered-set no longer means anything.
    """

    model_config = {}

    commit_sha: str
    audited_at: datetime
    waivers_audited: int
    catchup_remaining: int = 0
    catchup_covered: tuple[str, ...] = ()


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_watermark.py::TestSaveWatermark.test_creates_parent_dir_i\
# f_missing kind="unit"
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


# frob:ticket T-2721
def _git_commit_watermark(root: Path, message: str) -> bool:
    """`git add waive-audit-watermark.json && git commit -m message --
    waive-audit-watermark.json` in `root` -- pathspec-limited on both
    halves (T-1403's own lesson: a bare `git commit` sweeps the whole
    index, not just what this call staged) so nothing else uncommitted in
    `root` can ride along as a passenger. Returns whether a commit was
    actually made; `False` (never raises) on any git failure, including
    "nothing to commit" (the watermark's content happened to be
    byte-identical to what is already committed) and a genuinely
    non-git `root` (the unit-test-fixture case, `tmp_path`)."""
    from frob.tickets._leases import _without_agent_commit_guard

    added = gitio.run_argv(["git", "-C", str(root), "add", str(_WATERMARK_REL)])
    if added.is_err or added.danger_ok.returncode != 0:
        return False
    with _without_agent_commit_guard():
        committed = gitio.run_argv(
            [
                "git",
                "-C",
                str(root),
                "commit",
                "-m",
                message,
                "--",
                str(_WATERMARK_REL),
            ]
        )
    return committed.is_ok and committed.danger_ok.returncode == 0


# frob:ticket T-2721
def _mirror_watermark_to_primary(root: Path, message: str) -> None:
    """T-2721: when `root` is a linked worktree of some other primary
    checkout, copy the just-written watermark file across and commit it
    there too -- the same shape `frob.app.ticket_runner._ledger_mirror.
    mirror_ledger_change_to_primary` already established for a
    worktree-local ledger edit the whole fleet must see immediately.
    `waive-audit` carries no ticket id and is `NOT_TICKET_SCOPED` in
    `LEDGER_VERB_STRATEGY`, so it cannot reuse that mirror directly (it is
    keyed on a ticket's own pathspecs) -- this is the same primitives
    (`_resolve_primary_checkout`, `refuse_if_land_in_progress`),
    purpose-built for this one file instead. A no-op, loudly logged
    rather than silently skipped, whenever: `root` IS the primary
    checkout already (nothing to mirror); the primary cannot be resolved
    (a non-git `root`, e.g. a unit-test `tmp_path` fixture); a land is
    currently in progress on the primary (retry later, matching `frob.
    app.ticket_runner._ledger_mirror._log_mirror_unavailable`'s posture
    exactly); or the git add/commit on the primary itself fails."""
    from frob.tickets._land import _resolve_primary_checkout
    from frob.tickets._leases import refuse_if_land_in_progress

    primary = _resolve_primary_checkout(root)
    if primary is None or primary.resolve() == root.resolve():
        return
    land_check = refuse_if_land_in_progress(primary)
    if land_check.is_err:
        _log.error(
            "save_watermark: %s's watermark commit is WORKTREE-LOCAL and NOT "
            "visible on the primary checkout %s -- a land is in progress there "
            "(%s). Re-run the audit, or wait for the land to finish, to make "
            "this progress visible to the fleet.",
            root,
            primary,
            land_check.danger_err,
        )
        return
    try:
        primary_path = watermark_path(primary)
        primary_path.parent.mkdir(parents=True, exist_ok=True)
        primary_path.write_text(watermark_path(root).read_text())
    except OSError as exc:
        _log.error(
            "save_watermark: could not copy the watermark from %s onto the "
            "primary checkout %s: %s -- this pass's progress stays "
            "worktree-local until the ticket lands or the audit is re-run "
            "from %s",
            root,
            primary,
            exc,
            primary,
        )
        return
    if _git_commit_watermark(primary, message):
        _log.info(
            "save_watermark: mirrored onto the primary checkout %s -- visible "
            "to the fleet now, not only after this worktree's ticket lands",
            primary,
        )
    else:
        _log.error(
            "save_watermark: wrote the watermark onto the primary checkout %s "
            "but could not commit it there (git add/commit failed) -- the "
            "file is present but uncommitted; re-run the audit from %s to "
            "retry, or commit it by hand",
            primary,
            primary,
        )


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:ticket T-2721
# frob:ticket T-2735
# T-2735: the AFFECT001 waiver this docstring used to carry (`docs/
# modules/app.md was held by a LIVE cross-worktree lease (T-2694) for
# T-2721's entire duration ...`) is resolved -- T-2694 landed, freeing
# the lease, and T-2735 wrote the git-tracked/mirrored watermark section
# into `docs/modules/app.md#waive-audit-t-2467` in the same change that
# removes this waiver, so AFFECT001 no longer has anything to excuse here.
# frob:tests \
# tests/unit/test_waive_audit_watermark.py::TestSaveWatermark.test_round_trips_through_\
# load kind="unit"
def save_watermark(
    root: Path, watermark: WaiveAuditWatermark
) -> Result[None, WaiveAuditWatermarkError]:
    """Persist `watermark`, creating any missing parent directory if this
    is the checkout's first ever state file. Overwrites any prior
    watermark wholesale -- the watermark is a single current-position
    marker, not a log (the audit trail of PAST passes belongs to the
    tickets each pass files, not to this file).

    T-2721: also COMMITS the write in `root` (git-tracked, see this
    module's own docstring), and, when `root` is a worktree, mirrors and
    commits it onto the primary checkout too -- both steps are
    best-effort and never turn a successful on-disk write into an
    `Err`: see `_git_commit_watermark`/`_mirror_watermark_to_primary`
    for exactly what degrades, and how loudly, on a git failure."""
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
    message = (
        f"chore(waive-audit): advance watermark to {watermark.commit_sha} "
        f"({watermark.waivers_audited} waiver(s) audited)"
    )
    _git_commit_watermark(root, message)
    _mirror_watermark_to_primary(root, message)
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
