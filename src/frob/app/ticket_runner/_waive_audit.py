"""T-2467: `frob ticket waive-audit` -- the periodic, watermark-scoped
successor to T-1614's one-shot `runs_last` waiver audit.

T-1614's audit was correct in INTENT (a waiver's honesty can only be
judged against finished code) but unreachable in SHAPE: `runs_last`
means "undispatchable while any other ticket is queued/in-progress",
and this repo files tickets faster than it drains them on most days, so
that precondition structurally never holds. This module keeps T-1614's
classification rubric (STILL NECESSARY AND HONEST / OBSOLETE / COP-OUT /
PERMANENT BY DESIGN) but changes what triggers a pass: instead of
"everything, once, after the queue empties", it is "whatever changed
since the last completed pass", tracked via
`frob.gates._waive_audit_watermark`.

Two subcommands:

  `frob ticket waive-audit scan`     -- read-only. Reports which
                                        `frob:waive` directives need
                                        classification since the last
                                        watermark (or, on a first-ever
                                        run, a BOUNDED catch-up set --
                                        see `_CATCHUP_BOUND`). Never
                                        mutates the watermark.

  `frob ticket waive-audit complete` -- records a completed pass's
                                        verdict (a human/agent finished
                                        classifying the scanned set per
                                        T-1614's rubric) and advances
                                        the watermark to current HEAD.
                                        Refuses if the reviewed count
                                        does not match the scanned
                                        count, and refuses on a
                                        catch-up pass to claim full
                                        coverage while
                                        `not_covered_count > 0`.

FAIL-LOUDLY (T-2391's doctrine, applied here per T-2467's own coordinator
brief): `AuditVerdict` distinguishes "the watermark could not be read"
from "nothing needed auditing" from "audited and clean" -- collapsing
those three into one "clean" report is exactly the failure this audit
exists to catch, one level up. A `scan` that finds nothing to review
and a `complete` that records a genuinely clean pass must never look
identical to a broken watermark read.
"""

from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path

from pydantic import BaseModel
from typani import Err, Ok, Result
from typani.error_set import ErrorSet

from frob.app.config import AppConfig
from frob.gates._waive_audit_watermark import (
    WaiveAuditWatermark,
    WaiveAuditWatermarkError,
    load_watermark,
    save_watermark,
    utc_now,
)
from frob.logging import get_logger

_log = get_logger(__name__)

#: First-ever run (no watermark exists): the catch-up pass is bounded to
#: this many waivers so a repo with a large pre-existing waiver corpus
#: does not hand the first pass an unreviewable pile -- the remainder is
#: reported (never silently dropped) as `not_covered_count`, and the
#: watermark's own `catchup_remaining` records that the NEXT pass must
#: keep catching up rather than treat the repo as fully audited.
_CATCHUP_BOUND = 100


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestRunScan.test_no_watermark_bounds_catchup \
# kind="unit"
class AuditVerdict(str, Enum):
    """The outcomes a `scan`/`complete` pair must keep visibly
    distinct -- see this module's own docstring for why collapsing any
    two of these is the exact failure T-1614 exists to prevent."""

    #: `.frob/waive-audit-watermark.json` exists but failed to parse --
    #: a real defect, never treated as "nothing to audit".
    WATERMARK_UNREADABLE = "watermark_unreadable"
    #: A watermark was read (or this is a legitimate first run) and ZERO
    #: `frob:waive` directives changed since it -- there was nothing to
    #: classify, which is a different, weaker claim than "audited and
    #: found no cop-outs".
    NO_NEW_WAIVERS = "no_new_waivers"
    #: One or more `frob:waive` directives need classification against
    #: T-1614's rubric before this pass can be marked complete.
    NEEDS_REVIEW = "needs_review"
    #: A `complete` call recorded that every scanned waiver was reviewed
    #: and none was a cop-out. Only reachable via `complete`, never
    #: `scan` -- `scan` cannot know a human/agent's judgment.
    CLEAN = "clean"
    #: T-2485: a `complete --partial` call banked a batch of a bounded
    #: catch-up pass -- every waiver IN THAT BATCH was reviewed, but
    #: `catchup_remaining` in the resulting watermark is still nonzero.
    #: Only reachable via `complete`, and deliberately never equal to
    #: `CLEAN` or `NO_NEW_WAIVERS` even when the batch itself had zero
    #: cop-outs -- collapsing "audited N of M, M-N remain" into "audited
    #: everything, found nothing" is exactly the T-2391 fail-loudly
    #: failure this state exists to keep visible.
    PARTIAL_PROGRESS_BANKED = "partial_progress_banked"


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestCompletePass.test_reviewed_count_mismatch_\
# refuses kind="unit"
class WaiveAuditError(ErrorSet):
    """Fallible outcomes of running a scan or recording completion."""

    GitUnavailable = "git could not be queried for the changed-file set"
    ReviewCountMismatch = "the recorded reviewed count does not match the scanned count"
    CatchupIncomplete = (
        "a bounded catch-up pass cannot be marked fully complete while "
        "waivers remain uncovered"
    )


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestRunScan.test_no_watermark_bounds_catchup \
# kind="unit"
class ScannedWaiver(BaseModel):
    """One `frob:waive` directive in the scan set, enough for a
    human/agent to locate and classify it without re-deriving the scan."""

    model_config = {}

    file: str
    line: int | None
    rule: str
    reason: str
    follow_up: str | None = None


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestRunScan.test_no_watermark_bounds_catchup \
# kind="unit"
class WaiveAuditScanReport(BaseModel):
    """The read-only output of `scan` -- never mutates the watermark."""

    model_config = {}

    verdict: AuditVerdict
    mode: str  # "incremental" | "catchup" | "unreadable"
    watermark_commit: str | None
    scanned: tuple[ScannedWaiver, ...]
    not_covered_count: int
    error: str | None = None


def _current_head(root: Path) -> Result[str, WaiveAuditError]:
    """`git rev-parse HEAD` for `root`, the sha a completed pass's new
    watermark advances to."""
    from frob import gitio

    result = gitio.run_argv(("git", "-C", str(root), "rev-parse", "HEAD"))
    if result.is_err or result.danger_ok.returncode != 0:
        _log.warning("waive_audit: could not resolve HEAD for %s", root)
        return Err(WaiveAuditError.GitUnavailable)
    return Ok(result.danger_ok.stdout.strip())


def _files_changed_since(
    root: Path, since_sha: str
) -> Result[frozenset[str], WaiveAuditError]:
    """Repo-relative paths that differ between `since_sha` and HEAD --
    the incremental scan's candidate set, narrowed further below to
    files whose diff actually touches a `frob:waive` line."""
    from frob import gitio

    result = gitio.run_argv(
        ("git", "-C", str(root), "diff", "--name-only", f"{since_sha}..HEAD")
    )
    if result.is_err or result.danger_ok.returncode != 0:
        _log.warning(
            "waive_audit: git diff --name-only %s..HEAD failed for %s",
            since_sha,
            root,
        )
        return Err(WaiveAuditError.GitUnavailable)
    return Ok(
        frozenset(
            line.strip()
            for line in result.danger_ok.stdout.splitlines()
            if line.strip()
        )
    )


def _waive_touched_since(
    root: Path, since_sha: str
) -> Result[frozenset[str], WaiveAuditError]:
    """Of the files changed since `since_sha`, the subset whose diff
    actually added/modified a `frob:waive` line (`git log -S`) -- a file
    that changed for an unrelated reason must not pull every waiver it
    happens to also contain into the scan set."""
    from frob import gitio

    changed = _files_changed_since(root, since_sha)
    if changed.is_err:
        return changed
    touched: set[str] = set()
    for file in sorted(changed.danger_ok):
        result = gitio.run_argv(
            (
                "git",
                "-C",
                str(root),
                "log",
                f"{since_sha}..HEAD",
                "-S",
                "frob:waive",
                "--oneline",
                "--",
                file,
            )
        )
        if result.is_err or result.danger_ok.returncode != 0:
            continue
        if result.danger_ok.stdout.strip():
            touched.add(file)
    return Ok(frozenset(touched))


def _all_current_waivers(root: Path) -> tuple[ScannedWaiver, ...]:
    """Every live `frob:waive` edge in the current snapshot, as
    `ScannedWaiver` records -- the full corpus a catch-up pass draws
    its bounded sample from, and the pool an incremental pass filters
    down to its touched-file subset."""
    from frob.app._snapshot import load_or_build_snapshot
    from frob.gates import _site_from_edge_origin
    from frob.gates._waive import _waive_edges

    snapshot = load_or_build_snapshot(root, log_context="waive-audit")
    out: list[ScannedWaiver] = []
    for edge in _waive_edges(snapshot):
        file, line = _site_from_edge_origin(edge.origin)
        out.append(
            ScannedWaiver(
                file=file,
                line=line,
                rule=edge.target,
                reason=edge.attrs.get("reason", ""),
                follow_up=edge.attrs.get("follow_up"),
            )
        )
    return tuple(out)


def _waiver_identity(waiver: ScannedWaiver) -> str:
    """T-2485: a `ScannedWaiver`'s stable identity across passes
    (`"file:line:rule"`) -- what `WaiveAuditWatermark.catchup_covered`
    persists so a banked partial catch-up pass's NEXT scan can skip
    waivers already reviewed instead of re-offering the same bounded
    window forever (the bug T-2485 was filed against: a catch-up pass
    that could never advance past its own first `_CATCHUP_BOUND`
    items)."""
    return f"{waiver.file}:{waiver.line}:{waiver.rule}"


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestRunScan.test_no_watermark_bounds_catchup \
# kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestRunScan.test_watermark_malformed_is_unread\
# able kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestRunScan.test_no_new_waivers_when_nothing_c\
# hanged_since_watermark kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestPartialCatchup.test_next_scan_skips_alread\
# y_banked_waivers kind="unit"
def run_scan(root: Path) -> WaiveAuditScanReport:
    """The `scan` subcommand's core logic -- read-only, safe to run as
    often as wanted. See the module docstring for the outcomes this
    must keep distinguishable."""
    watermark_result = load_watermark(root)
    all_waivers = _all_current_waivers(root)

    if watermark_result.is_err:
        err = watermark_result.danger_err
        if err is WaiveAuditWatermarkError.NotFound:
            # Legitimate first run: bounded catch-up over the WHOLE
            # current corpus, never the "since sha" incremental path
            # (there is no prior sha to diff against).
            bounded = all_waivers[:_CATCHUP_BOUND]
            not_covered = max(0, len(all_waivers) - len(bounded))
            verdict = (
                AuditVerdict.NO_NEW_WAIVERS
                if not bounded
                else AuditVerdict.NEEDS_REVIEW
            )
            return WaiveAuditScanReport(
                verdict=verdict,
                mode="catchup",
                watermark_commit=None,
                scanned=bounded,
                not_covered_count=not_covered,
            )
        # Malformed / unreadable: a real defect, distinct from both
        # "nothing to audit" and "audited clean" -- never silently
        # treated as either.
        return WaiveAuditScanReport(
            verdict=AuditVerdict.WATERMARK_UNREADABLE,
            mode="unreadable",
            watermark_commit=None,
            scanned=(),
            not_covered_count=0,
            error=str(err),
        )

    watermark = watermark_result.danger_ok
    if watermark.catchup_remaining > 0:
        # A prior pass's catch-up was itself bounded; continue it before
        # switching to incremental-since-watermark mode, same posture as
        # the first-run branch above. T-2485: skip waivers a PRIOR banked
        # partial pass already reviewed (`catchup_covered`) rather than
        # re-offering the same leading window every scan -- that
        # re-offering was the exact bug T-2485 was filed against, since
        # nothing ever advanced past the first `_CATCHUP_BOUND` items.
        covered = set(watermark.catchup_covered)
        remaining = [w for w in all_waivers if _waiver_identity(w) not in covered]
        bounded = tuple(remaining[:_CATCHUP_BOUND])
        not_covered = max(0, len(remaining) - len(bounded))
        verdict = (
            AuditVerdict.NO_NEW_WAIVERS if not bounded else AuditVerdict.NEEDS_REVIEW
        )
        return WaiveAuditScanReport(
            verdict=verdict,
            mode="catchup",
            watermark_commit=watermark.commit_sha,
            scanned=bounded,
            not_covered_count=not_covered,
        )

    touched = _waive_touched_since(root, watermark.commit_sha)
    if touched.is_err:
        return WaiveAuditScanReport(
            verdict=AuditVerdict.WATERMARK_UNREADABLE,
            mode="unreadable",
            watermark_commit=watermark.commit_sha,
            scanned=(),
            not_covered_count=0,
            error=str(touched.danger_err),
        )
    touched_files = touched.danger_ok
    scanned = tuple(w for w in all_waivers if w.file in touched_files)
    verdict = AuditVerdict.NEEDS_REVIEW if scanned else AuditVerdict.NO_NEW_WAIVERS
    return WaiveAuditScanReport(
        verdict=verdict,
        mode="incremental",
        watermark_commit=watermark.commit_sha,
        scanned=scanned,
        not_covered_count=0,
    )


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestCompletePass.test_reviewed_count_mismatch_\
# refuses kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestCompletePass.test_catchup_incomplete_refus\
# es_full_completion kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestCompletePass.test_matching_reviewed_count_\
# advances_watermark kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestPartialCatchup.test_partial_without_flag_s\
# till_refuses kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestPartialCatchup.test_partial_banks_batch_an\
# d_advances_watermark kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestPartialCatchup.test_banking_the_final_batc\
# h_clears_catchup_state kind="unit"
def complete_pass(
    root: Path, *, reviewed_count: int, cop_outs_found: int, partial: bool = False
) -> Result[WaiveAuditWatermark, WaiveAuditError]:
    """Record that a scan's exact set was reviewed against T-1614's
    rubric and advance the watermark. Refuses (writes nothing) if
    `reviewed_count` does not match the just-rescanned set.

    T-2485: a bounded catch-up pass with waivers still uncovered used to
    refuse UNCONDITIONALLY here -- correct in that it could never claim
    full coverage, but it also gave a genuinely-reviewed batch nowhere
    to go, so `_CATCHUP_BOUND`'s whole point (do not hand a large
    pre-existing corpus to one unreviewable sitting) was defeated: the
    only way to ever advance the watermark was to review the entire
    backlog in one pass. `partial=True` is the caller's explicit
    acknowledgement that this batch does NOT cover the whole backlog --
    it banks exactly the scanned batch (`catchup_remaining` records what
    is still outstanding, `catchup_covered` records this batch's
    identities so the next scan's bounded window advances past them)
    without ever writing a state a later reader could mistake for
    "fully audited, found nothing" (T-2391 fail-loudly: see
    `AuditVerdict.PARTIAL_PROGRESS_BANKED`). Omitting `partial` keeps the
    original refusal for an incomplete catch-up -- `partial` must be
    passed on purpose, never inferred, so a caller cannot bank a partial
    pass by accident while believing they completed the audit."""
    report = run_scan(root)
    refusal = _complete_refusal_reason(report, reviewed_count, partial)
    if refusal is not None:
        return Err(refusal)

    head = _current_head(root)
    if head.is_err:
        return Err(head.danger_err)

    still_remaining, catchup_remaining, new_covered = _next_catchup_fields(root, report)

    new_watermark = WaiveAuditWatermark(
        commit_sha=head.danger_ok,
        audited_at=utc_now(),
        waivers_audited=reviewed_count,
        catchup_remaining=catchup_remaining,
        catchup_covered=new_covered,
    )
    saved = save_watermark(root, new_watermark)
    if saved.is_err:
        return Err(WaiveAuditError.GitUnavailable)
    _log.info(
        "waive_audit: pass %s -- reviewed=%d cop_outs=%d catchup_remaining=%d "
        "new_watermark=%s",
        "banked (partial)" if still_remaining else "complete",
        reviewed_count,
        cop_outs_found,
        catchup_remaining,
        new_watermark.commit_sha,
    )
    return Ok(new_watermark)


def _complete_refusal_reason(
    report: WaiveAuditScanReport, reviewed_count: int, partial: bool
) -> WaiveAuditError | None:
    """The three reasons `complete_pass` refuses to write anything --
    split out so `complete_pass` itself stays the orchestration
    (validate, then persist) rather than growing this checklist inline.
    Returns `None` when nothing refuses."""
    if report.verdict == AuditVerdict.WATERMARK_UNREADABLE:
        _log.error(
            "waive_audit: complete refused -- watermark unreadable: %s", report.error
        )
        return WaiveAuditError.GitUnavailable
    if reviewed_count != len(report.scanned):
        _log.error(
            "waive_audit: complete refused -- reviewed_count=%d but scan found %d "
            "waiver(s)",
            reviewed_count,
            len(report.scanned),
        )
        return WaiveAuditError.ReviewCountMismatch
    if report.mode == "catchup" and report.not_covered_count > 0 and not partial:
        _log.error(
            "waive_audit: complete refused -- catch-up pass still has %d waiver(s) "
            "not covered (pass --partial to bank this batch's progress instead of "
            "claiming full coverage)",
            report.not_covered_count,
        )
        return WaiveAuditError.CatchupIncomplete
    return None


def _next_catchup_fields(
    root: Path, report: WaiveAuditScanReport
) -> tuple[bool, int, tuple[str, ...]]:
    """T-2485: the pure "what does the NEXT watermark's catch-up state
    look like" computation `complete_pass` builds a new
    `WaiveAuditWatermark` from -- split out so `complete_pass` itself
    stays the orchestration (refuse-or-proceed, then persist) rather
    than growing this decision inline. Returns `(still_remaining,
    catchup_remaining, catchup_covered)`: `still_remaining` is True only
    for a BANKED partial catch-up pass (this batch reviewed, but the
    backlog is not exhausted) -- in that case `catchup_covered`
    accumulates this batch's identities onto whatever a prior banked
    pass already covered, so the next scan's bounded window advances
    past them instead of re-offering the same leading slice forever.
    Any other case (plain incremental, or a catch-up pass that just
    covered the last of its backlog) resets both fields to empty/zero --
    the covered-set stops meaning anything once catch-up mode ends."""
    still_remaining = report.mode == "catchup" and report.not_covered_count > 0
    if not still_remaining:
        return False, 0, ()
    prior_watermark = load_watermark(root)
    prior_covered = (
        prior_watermark.danger_ok.catchup_covered if prior_watermark.is_ok else ()
    )
    new_covered = tuple(
        sorted(set(prior_covered) | {_waiver_identity(w) for w in report.scanned})
    )
    return True, report.not_covered_count, new_covered


# frob:ticket T-2467
# frob:doc docs/modules/app.md#runners
# frob:tests \
# tests/integration/test_interfaces.py::TestInterfaces.test_main_cli_dispatches \
# kind="unit"
def run(root: Path, cfg: AppConfig) -> None:
    """`frob ticket waive-audit {scan,complete}` CLI entrypoint -- resolves
    the subcommand and delegates; the report-rendering job for each
    subcommand lives in its own small helper below (T-2485 split, keeping
    this dispatcher itself under ARCH001's line threshold)."""
    subcommand = getattr(cfg, "waive_audit_subcommand", "scan") or "scan"

    if subcommand == "scan":
        _run_scan_subcommand(root, cfg)
        return
    if subcommand == "complete":
        _run_complete_subcommand(root, cfg)
        return

    _log.error("waive-audit: unknown subcommand %r", subcommand)
    sys.exit(1)


def _run_scan_subcommand(root: Path, cfg: AppConfig) -> None:
    """Render `waive-audit scan`'s report and exit(1) on
    `WATERMARK_UNREADABLE` -- the only failure mode `scan` itself has,
    since it is otherwise read-only."""
    from frob.render import Renderer

    renderer = Renderer.for_stream(sys.stdout)
    report = run_scan(root)
    if getattr(cfg, "ticket_json", False):
        renderer.line(report.model_dump_json(indent=2))
    else:
        renderer.line(f"verdict={report.verdict.value} mode={report.mode}")
        if report.error:
            renderer.line(f"error: {report.error}")
        renderer.line(
            f"scanned={len(report.scanned)} not_covered={report.not_covered_count}"
        )
        for w in report.scanned:
            renderer.line(
                f"  {w.file}:{w.line} frob:waive {w.rule} reason={w.reason!r}"
            )
    if report.verdict == AuditVerdict.WATERMARK_UNREADABLE:
        sys.exit(1)


def _run_complete_subcommand(root: Path, cfg: AppConfig) -> None:
    """Render `waive-audit complete`'s report and exit(1) on any
    `complete_pass` refusal. T-2485: computes the DISPLAYED verdict from
    the resulting watermark's own `catchup_remaining`, not just
    `cop_outs` -- a banked partial pass (`catchup_remaining > 0`) must
    always render as `PARTIAL_PROGRESS_BANKED`, never `CLEAN`, even when
    the reviewed batch itself had zero cop-outs (T-2391 fail-loudly:
    collapsing those two into one render is the exact failure this
    module's own docstring says to keep visibly distinct)."""
    import json as _json

    from frob.render import Renderer

    renderer = Renderer.for_stream(sys.stdout)
    reviewed = int(getattr(cfg, "waive_audit_reviewed_count", 0) or 0)
    cop_outs = int(getattr(cfg, "waive_audit_cop_outs", 0) or 0)
    partial = bool(getattr(cfg, "waive_audit_partial", False))
    result = complete_pass(
        root, reviewed_count=reviewed, cop_outs_found=cop_outs, partial=partial
    )
    if result.is_err:
        _log.error("waive-audit complete failed: %s", result.danger_err)
        renderer.line(f"error: {result.danger_err}")
        sys.exit(1)
    watermark = result.danger_ok
    if watermark.catchup_remaining > 0:
        verdict = AuditVerdict.PARTIAL_PROGRESS_BANKED
    elif cop_outs == 0:
        verdict = AuditVerdict.CLEAN
    else:
        verdict = AuditVerdict.NEEDS_REVIEW
    payload = {
        "verdict": verdict.value,
        "watermark_commit": watermark.commit_sha,
        "waivers_audited": watermark.waivers_audited,
        "catchup_remaining": watermark.catchup_remaining,
    }
    if getattr(cfg, "ticket_json", False):
        renderer.line(_json.dumps(payload, indent=2))
    else:
        renderer.line(
            f"verdict={payload['verdict']} watermark={watermark.commit_sha} "
            f"audited={watermark.waivers_audited} "
            f"catchup_remaining={watermark.catchup_remaining}"
        )
