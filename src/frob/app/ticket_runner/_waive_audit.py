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
    """The four outcomes a `scan`/`complete` pair must keep visibly
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
def run_scan(root: Path) -> WaiveAuditScanReport:
    """The `scan` subcommand's core logic -- read-only, safe to run as
    often as wanted. See the module docstring for the four-way verdict
    this must keep distinguishable."""
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
        # the first-run branch above.
        bounded = all_waivers[:_CATCHUP_BOUND]
        not_covered = max(0, watermark.catchup_remaining - len(bounded))
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
def complete_pass(
    root: Path, *, reviewed_count: int, cop_outs_found: int
) -> Result[WaiveAuditWatermark, WaiveAuditError]:
    """Record that a scan's exact set was reviewed against T-1614's
    rubric and advance the watermark to current HEAD. Refuses (writes
    nothing) if `reviewed_count` does not match the just-rescanned set,
    or if the pass was a bounded catch-up that still has uncovered
    waivers -- a partial catch-up must not be recorded as "fully
    audited to date", or the next pass would silently skip the
    remainder forever."""
    report = run_scan(root)
    if report.verdict == AuditVerdict.WATERMARK_UNREADABLE:
        _log.error(
            "waive_audit: complete refused -- watermark unreadable: %s", report.error
        )
        return Err(WaiveAuditError.GitUnavailable)
    if reviewed_count != len(report.scanned):
        _log.error(
            "waive_audit: complete refused -- reviewed_count=%d but scan found %d waiver(s)",
            reviewed_count,
            len(report.scanned),
        )
        return Err(WaiveAuditError.ReviewCountMismatch)
    if report.mode == "catchup" and report.not_covered_count > 0:
        _log.error(
            "waive_audit: complete refused -- catch-up pass still has %d waiver(s) not covered",
            report.not_covered_count,
        )
        return Err(WaiveAuditError.CatchupIncomplete)

    head = _current_head(root)
    if head.is_err:
        return Err(head.danger_err)
    new_watermark = WaiveAuditWatermark(
        commit_sha=head.danger_ok,
        audited_at=utc_now(),
        waivers_audited=reviewed_count,
        catchup_remaining=0,
    )
    saved = save_watermark(root, new_watermark)
    if saved.is_err:
        return Err(WaiveAuditError.GitUnavailable)
    _log.info(
        "waive_audit: pass complete -- reviewed=%d cop_outs=%d new_watermark=%s",
        reviewed_count,
        cop_outs_found,
        new_watermark.commit_sha,
    )
    return Ok(new_watermark)


# frob:ticket T-2467
# frob:doc docs/modules/app.md#runners
# frob:tests \
# tests/integration/test_interfaces.py::TestInterfaces.test_main_cli_dispatches \
# kind="unit"
def run(root: Path, cfg: AppConfig) -> None:
    """`frob ticket waive-audit {scan,complete}` CLI entrypoint."""
    import json as _json

    from frob.render import Renderer

    renderer = Renderer.for_stream(sys.stdout)
    subcommand = getattr(cfg, "waive_audit_subcommand", "scan") or "scan"

    if subcommand == "scan":
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
        return

    if subcommand == "complete":
        reviewed = int(getattr(cfg, "waive_audit_reviewed_count", 0) or 0)
        cop_outs = int(getattr(cfg, "waive_audit_cop_outs", 0) or 0)
        result = complete_pass(root, reviewed_count=reviewed, cop_outs_found=cop_outs)
        if result.is_err:
            _log.error("waive-audit complete failed: %s", result.danger_err)
            renderer.line(f"error: {result.danger_err}")
            sys.exit(1)
        watermark = result.danger_ok
        verdict = AuditVerdict.CLEAN if cop_outs == 0 else AuditVerdict.NEEDS_REVIEW
        payload = {
            "verdict": verdict.value,
            "watermark_commit": watermark.commit_sha,
            "waivers_audited": watermark.waivers_audited,
        }
        if getattr(cfg, "ticket_json", False):
            renderer.line(_json.dumps(payload, indent=2))
        else:
            renderer.line(
                f"verdict={payload['verdict']} watermark={watermark.commit_sha} audited={watermark.waivers_audited}"
            )
        return

    _log.error("waive-audit: unknown subcommand %r", subcommand)
    sys.exit(1)
