# frob:waive LARGE001 reason="T-2829 (T-1651-grade review): single feature, one CLI \
# subcommand (`frob ticket waive-audit`) with two phases this module's own docstring \
# already names -- scan (run_scan/_all_current_waivers/_waiver_identity/ \
# find_collision_suspects/classify_waiver_liveness) and complete (complete_pass/ \
# _complete_refusal_reason/_next_catchup_fields) -- both phases share the same \
# ScannedWaiver/WaiveAuditScanReport/CollisionSuspect/WaiverLiveness data model \
# (defined once, at the top, used throughout) and the complete phase's own docstring \
# frames it as literally 'the next pass over what scan already found', not an \
# independent concern. Same shape T-1651 already accepted for check_runner. \
# py/sys_runner.py: one subcommand's pipeline, no distinct consumer set to split along."
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
from collections.abc import Callable, Sequence
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel
from typani import Err, Ok, Result
from typani.error_set import ErrorSet

from frob.app.config import AppConfig
from frob.gates._models import GateReport, Violation
from frob.gates._waive_audit_watermark import (
    WaiveAuditWatermark,
    WaiveAuditWatermarkError,
    load_watermark,
    save_watermark,
    utc_now,
)
from frob.logging import get_logger

if TYPE_CHECKING:
    from frob.render import Renderer

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


# frob:waive DUP001 reason="coincidental short-function AST shape across 4 unrelated \
# domains (deprecated-baseline file#count codec, gtest name normalization, \
# next-ticket-id allocation, waiver identity key) -- no shared logic, independently \
# evolving"
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


# frob:ticket T-2496
def _run_scan_subcommand(root: Path, cfg: AppConfig) -> None:
    """Render `waive-audit scan`'s report and exit(1) on
    `WATERMARK_UNREADABLE` -- the only failure mode `scan` itself has,
    since it is otherwise read-only. T-2496: with `--check-collisions`,
    ALSO renders `find_collision_suspects`'s report as a second, clearly
    separate section -- see `_render_collision_suspects`'s own docstring
    for why this stays additive rather than folded into `scan`'s own
    verdict."""
    from frob.render import Renderer

    renderer = Renderer.for_stream(sys.stdout)
    report = run_scan(root)
    as_json = getattr(cfg, "ticket_json", False)
    if as_json:
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
    if getattr(cfg, "waive_audit_check_collisions", False):
        _render_collision_suspects(root, renderer, as_json=as_json)
    if getattr(cfg, "waive_audit_check_liveness", False):
        _render_waiver_liveness(root, renderer, as_json=as_json)
    if report.verdict == AuditVerdict.WATERMARK_UNREADABLE:
        sys.exit(1)


# frob:ticket T-2740
def _render_waiver_liveness(root: Path, renderer: Renderer, *, as_json: bool) -> None:
    """`--check-liveness`'s own report section: run a fresh, unscoped
    `frob check` gate pass, classify EVERY currently-live `frob:waive`
    directive in the repo (not only `scan`'s watermark-scoped subset --
    liveness is a property of the waiver's own rule/file, independent of
    when it was last audited) via `classify_waiver_liveness`, and render
    the necessary/inert/unverified counts plus every INERT site by name.

    Deliberately its own function and its own gate pass, matching
    `_render_collision_suspects`'s own precedent immediately above: a
    liveness verdict is a different question from `scan`'s watermark-
    scoped "what changed" verdict, and folding the two would let a
    liveness classification silently start counting toward `AuditVerdict.
    CLEAN`/`NEEDS_REVIEW` -- exactly the verdict-collapsing this module's
    own docstring says never to do. NEVER raises this command's exit
    status, NEVER mutates a waiver -- an INERT verdict is a lead for a
    human/agent to investigate (the waiver's site, AND the rule's own
    scan pathspec, per this module's T-2740 section docstring), never
    itself grounds for removal.

    A gate-run failure is reported and swallowed, not fatal -- same
    posture as `_render_collision_suspects`."""
    from frob.gates import GateConfig, run_gates

    gate_result = run_gates(GateConfig(root=str(root)))
    if gate_result.is_err:
        _log.warning(
            "waive-audit --check-liveness: gate run failed (%s) -- "
            "liveness report skipped, scan's own report above is "
            "unaffected",
            gate_result.danger_err,
        )
        if not as_json:
            renderer.line(f"check-liveness: gate run failed: {gate_result.danger_err}")
        return
    report = gate_result.danger_ok
    waivers = _all_current_waivers(root)
    classified = [(w, classify_waiver_liveness(w, report, root)) for w in waivers]
    counts: dict[str, int] = {}
    for _w, verdict in classified:
        counts[verdict.value] = counts.get(verdict.value, 0) + 1
    if as_json:
        payload = [
            {**w.model_dump(), "liveness": verdict.value} for w, verdict in classified
        ]
        renderer.line(f"check_liveness: {payload}")
        return
    renderer.line(
        f"check-liveness: {len(classified)} waiver(s) -- "
        f"necessary={counts.get('necessary', 0)} "
        f"inert={counts.get('inert', 0)} "
        f"unverified={counts.get('unverified', 0)}"
    )
    for w, verdict in classified:
        if verdict is WaiverLiveness.INERT:
            renderer.line(
                f"  INERT {w.file}:{w.line} frob:waive {w.rule} reason={w.reason!r} "
                "-- rule does not scan this path; treat as a lead on BOTH the "
                "waiver AND the rule's own scan pathspec, per T-2719"
            )


# frob:ticket T-2496
def _render_collision_suspects(
    root: Path, renderer: Renderer, *, as_json: bool
) -> None:
    """`--check-collisions`'s own report section: run a fresh, unscoped
    `frob check` gate pass, feed its `kept` (unsuppressed) violations plus
    the current waiver corpus into T-2493's `find_collision_suspects`, and
    render whatever it flags.

    Deliberately its own function, not folded into `run_scan`/
    `WaiveAuditScanReport`: `find_collision_suspects` answers a DIFFERENT
    question (does an active violation collide with a waiver's own
    rule+file) than `scan`'s watermark-scoped "what changed since last
    audit" question, and mixing the two into one verdict would let a
    collision-suspect silently start counting toward `AuditVerdict.
    CLEAN`/`NEEDS_REVIEW` -- exactly the kind of verdict-collapsing this
    module's own docstring says never to do. This function NEVER raises
    this command's exit status and NEVER mutates a waiver; a collision
    reported here is input for a human/agent's own T-1614 classification
    pass, same as `scan`'s own NEEDS_REVIEW list already is.

    A gate-run failure (`GateError`) is reported and swallowed, not
    fatal -- `--check-collisions` is additive to `scan`'s own report, so
    a gate-pass hiccup must not turn an otherwise-successful `scan` into
    a failed command."""
    from frob.gates import GateConfig, run_gates

    gate_result = run_gates(GateConfig(root=str(root)))
    if gate_result.is_err:
        _log.warning(
            "waive-audit --check-collisions: gate run failed (%s) -- "
            "collision report skipped, scan's own report above is "
            "unaffected",
            gate_result.danger_err,
        )
        if not as_json:
            renderer.line(
                f"check-collisions: gate run failed: {gate_result.danger_err}"
            )
        return
    waivers = _all_current_waivers(root)
    suspects = find_collision_suspects(
        waivers, gate_result.danger_ok.violations, root=root
    )
    if as_json:
        payload = [s.model_dump() for s in suspects]
        renderer.line(f"check_collisions: {payload}")
        return
    renderer.line(
        f"check-collisions: {len(suspects)} suspect(s) -- a waiver whose "
        "site has ZERO current violations anywhere is NOT detectable by "
        "this check (T-2493's disclosed blind spot); absence here is "
        "never proof of inertness"
    )
    for s in suspects:
        renderer.line(
            f"  {s.file}:{s.line} frob:waive {s.rule} reason={s.reason!r} "
            f"collides with kept violation at line {s.colliding_violation_line}: "
            f"{s.colliding_violation_message!r}"
        )


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


# ---------------------------------------------------------------------------
# T-2493: collision-based INERT-waiver detection.
#
# READ THIS BEFORE TOUCHING ANYTHING BELOW. T-1579 asked for exactly this
# shape of feature once already -- "let the audit tell us a waiver is
# doing nothing" -- and the version that shipped
# (`_rule_has_live_finding`, `frob.gates._fix_engine_sync`) reasoned "the
# rule fired somewhere in this run, so the detector is healthy, so a
# waiver of that rule matching nothing here is provably stale." That
# reasoning is UNSOUND: it proves the detector produced output
# SOMEWHERE, never that it re-examined the ONE site a given waiver
# covers. It shipped, and during a real land it deleted 55 LIVE waivers
# during a partially-degraded run that still found some instances of a
# rule while missing the exact sites those waivers covered. Reverted;
# `tests/test_gates.py::TestWaive004DegradedRunGuard::
# test_mass_invalidation_with_live_finding_elsewhere_still_refuses` locks
# against reintroducing it. T-1904 (successor) established that a SOUND
# escape needs per-site analysis-coverage proof, which is a materially
# larger capability than a guard tweak -- built later as T-1921/T-1943's
# `frob.gates._coverage_sites`, and even THAT substrate was deliberately
# shipped wired to nothing (its own module docstring: "NOT WIRED INTO
# WAIVE004 (or any other auto-fix/waiver-retirement path) by this
# ticket").
#
# `find_collision_suspects` below does NOT use an absence signal ("0
# findings for this waiver") at all -- that signal is exactly what
# failed. It uses the OPPOSITE, STRONGER signal: does an ACTIVE, PRESENT,
# UNSUPPRESSED (`GateReport.violations`, i.e. `kept` in
# `frob.gates._apply_waivers`'s own naming) violation of the SAME rule
# exist in the SAME repo-relative file as a `frob:waive` directive for
# that rule? If so, that waiver PROVABLY failed to suppress a violation
# it names -- not an inference from silence, a direct, present
# counter-example. This is the general form of the two REAL matching
# bugs this repo has actually found and fixed this way already: T-2314
# (`gate:PERF` emitted absolute file paths, so `_match_waiver`'s
# file-equality check silently never matched -- caught because a
# KNOWN-waived site's finding kept showing up unsuppressed) and T-2438
# (a hand-rolled C++ symref spelling differed from the DSL's own
# qualname join, so the symbol-exact match silently missed -- same
# shape: a violation persisted despite a waiver that should have covered
# it). Both were found by noticing presence, never absence.
#
# WHAT THIS DELIBERATELY DOES NOT CATCH, disclosed rather than hidden: a
# waiver whose site has ZERO current violations of its rule ANYWHERE in
# the tree -- the "hardened guard, currently quiet" case a real load-
# bearing waiver looks exactly like. `find_collision_suspects` cannot
# tell that case apart from a genuinely-inert waiver, and does not try
# to -- it reports NOTHING for either, by construction, because there is
# no active violation to collide with in either case. Closing that gap
# requires the per-site analysis-coverage proof T-1904 named as the
# missing capability (confirm the exact site was actually re-examined
# this run before treating its silence as meaningful), which
# `frob.gates._coverage_sites` (T-1921/T-1943) only provides for five
# gate families and was explicitly left unwired everywhere -- extending
# it into a general per-waiver inertness verdict is a materially larger,
# multi-file capability outside this ticket's single-file scope, not
# something safe to approximate here with a heuristic.
#
# REPORT-ONLY, on purpose: this returns data, never mutates a waiver,
# never gates `frob check`/`frob ticket land`, and is not wired to any
# CLI subcommand by this ticket -- a caller (a human, or a future ticket
# with its own scope and its own review) decides what to do with a
# reported collision. The `AuditVerdict.CLEAN` reachability rule
# elsewhere in this module (only `complete`, never `scan`, can claim
# CLEAN) applies here too, transitively: a collision-suspect report is
# evidence for a human/agent classifying per T-1614's rubric, not itself
# a verdict.


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestCollisionSuspects.test_active_unsuppressed\
# _violation_in_same_rule_and_file_is_flagged kind="unit"
class CollisionSuspect(BaseModel):
    """One `frob:waive` directive that, in a specific `GateReport`, coexists
    with an ACTIVE, UNSUPPRESSED violation of the same rule in the same
    repo-relative file -- see this module's own T-2493 section docstring
    for why this positive-collision signal is sound where an absence-based
    ("0 findings") signal is not."""

    model_config = {}

    file: str
    line: int | None
    rule: str
    reason: str
    colliding_violation_line: int
    colliding_violation_message: str


def _repo_relative(path: str, root: Path) -> str:
    """Best-effort normalize `path` to a repo-relative, forward-slash form
    comparable to a `ScannedWaiver.file`/`Violation.file` value -- T-2314's
    own root cause was exactly an absolute-vs-relative mismatch silently
    voiding a match, so this comparison deliberately does NOT trust either
    side's shape as-is."""
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(root)
        except ValueError:
            # Absolute but outside root: leave as-is -- an exotic case
            # (a violation naming a path outside the checkout at all)
            # that no repo-relative normalization can meaningfully fix;
            # falling through lets the equality check below just fail to
            # match, same as an honest "these are different files" would.
            return str(p)
    return p.as_posix()


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestCollisionSuspects.test_active_unsuppressed\
# _violation_in_same_rule_and_file_is_flagged kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestCollisionSuspects.test_a_correctly_matchin\
# g_live_waiver_is_not_flagged kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestCollisionSuspects.test_a_quiet_hardened_si\
# te_with_zero_violations_anywhere_is_not_flagged kind="unit"
# frob:ticket T-2496
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestCheckCollisionsWiring.test_check_collision\
# s_renders_suspects kind="unit"
def find_collision_suspects(
    waivers: Sequence[ScannedWaiver],
    kept_violations: Sequence[Violation],
    *,
    root: Path,
) -> tuple[CollisionSuspect, ...]:
    """The sound half of T-2493: for each of `waivers`, report it as a
    `CollisionSuspect` only when `kept_violations` (a `GateReport.
    violations` -- the UNSUPPRESSED set `frob.gates._apply_waivers`
    already computed for whatever run produced them) contains a violation
    of the SAME rule in the SAME repo-relative file. Pure and
    side-effect-free: takes data, returns data, calls neither `run_gates`
    nor anything that mutates a waiver -- see this module's T-2493 section
    docstring for what this signal does and does not prove, and why a
    caller must not treat an empty result as "these waivers are all
    live"."""
    kept_by_rule_file: dict[tuple[str, str], list[Violation]] = {}
    for violation in kept_violations:
        key = (violation.rule, _repo_relative(violation.file, root))
        kept_by_rule_file.setdefault(key, []).append(violation)

    suspects: list[CollisionSuspect] = []
    for waiver in waivers:
        candidates = kept_by_rule_file.get(
            (waiver.rule, _repo_relative(waiver.file, root))
        )
        if not candidates:
            continue
        first = candidates[0]
        suspects.append(
            CollisionSuspect(
                file=waiver.file,
                line=waiver.line,
                rule=waiver.rule,
                reason=waiver.reason,
                colliding_violation_line=first.line,
                colliding_violation_message=first.message,
            )
        )
    return tuple(suspects)


# ---------------------------------------------------------------------------
# T-2740: waiver LIVENESS, distinct from T-2493's collision-suspect honesty
# signal above.
#
# WHY THIS IS A DIFFERENT QUESTION. T-1614's audit (and T-2493's collision
# check) both judge a waiver's REASON or its collision with an ACTIVE
# violation -- neither establishes that the waiver's own RULE ever looks at
# the FILE the waiver sits in at all. T-2719 found 11 `frob:waive RENDER001`
# directives in `.claude/hooks/` and `scripts/fleet_status.py` that were
# individually honest AND collision-free (nothing to collide with, because
# RENDER001's scan pathspec was hardcoded to `src/frob` and never reached
# those files) -- T-1614's audit classified all 100 directives it reviewed
# as "still necessary and honest", 11 of which were provably doing nothing.
#
# THE SOUNDNESS LINE, drawn deliberately narrow (same posture as T-2493's
# own docstring above, and the same lesson the reverted T-1579
# `_rule_has_live_finding` incident taught this repo once already):
#
#   NECESSARY -- the CURRENT run's `GateReport.waived` (the exact set
#     `_apply_waivers` computed THIS run, a direct observation, never an
#     inference from absence) contains a violation this waiver actually
#     suppressed. Sound: this is not "the rule fired somewhere", it is
#     "this exact waiver suppressed this exact violation just now".
#
#   INERT -- the waiver's rule has a REGISTERED, structural scan-membership
#     predicate (`_LIVENESS_SCAN_CHECKERS`, e.g. RENDER001's own
#     `render001_scans`, itself derived from the gate's real pathspec/
#     exemption logic, never a second hardcoded copy) and that predicate
#     says the waiver's file falls OUTSIDE the rule's scan set. This is a
#     structural fact about what the rule enumerates, not an inference
#     from a run finding nothing -- sound for the same reason
#     `frob.gates._coverage_sites.site_examined`'s POSITIVE membership
#     claims are sound, applied here to a NEGATIVE (not-in-scope) claim
#     instead.
#
#   UNVERIFIED -- neither of the above could be established: the rule has
#     no registered checker, or the checker says the file IS in scope but
#     this run's `waived` set does not confirm active suppression. This is
#     the HONEST default. It is deliberately NOT "OBSOLETE" -- claiming a
#     finding "no longer reproduces" from one run's absence is exactly the
#     T-1579 reasoning that deleted 55 live waivers, and this module does
#     not repeat it. A caller wanting a real OBSOLETE verdict must do what
#     T-2739 did: construct an actual synthetic diff/measurement for that
#     specific rule and site, by hand, per this repo's own waiver-removal
#     discipline -- this classifier reports a LEAD, never a verdict
#     strong enough to justify removal on its own.
#
# REPORT-ONLY, same as T-2493: never mutates a waiver, never gates
# `frob check`/`frob ticket land`, not wired to any auto-removal path.
# An INERT verdict is ALSO evidence about the GATE, not only the waiver --
# see `_run_scan_subcommand`'s own liveness section render for the prompt
# this is meant to leave a human/agent with: an unscanned path someone is
# writing waivers for is exactly how T-2719 found RENDER001's own pathspec
# bug, one level up from any individual waiver.


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness.test_necessary_when\
# _waived_this_run kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness.test_inert_when_rul\
# e_does_not_scan_the_file kind="unit"
class WaiverLiveness(str, Enum):
    """T-2740: the three-way answer `classify_waiver_liveness` gives for a
    single scanned waiver -- see this module's own T-2740 section docstring
    above for why each state is reachable only by the specific sound
    signal it names, and why a fourth ("obsolete") state is deliberately
    not claimed automatically anywhere in this file."""

    #: This run's own `GateReport.waived` shows the waiver actively
    #: suppressing a real violation -- direct observation, not inference.
    NECESSARY = "necessary"
    #: The waiver's rule has a registered scan-membership predicate, and
    #: the waiver's file structurally falls outside that rule's scan set.
    INERT = "inert"
    #: Neither NECESSARY nor INERT could be established this run. The
    #: honest default -- never "obsolete", see this module's own T-2740
    #: docstring for why that claim is never made from this signal alone.
    UNVERIFIED = "unverified"


#: rule id -> `(root, repo_relative_file) -> bool` structural scan-
#: membership predicate, the INERT half of `classify_waiver_liveness`.
#: T-2740: starts with RENDER001 (the rule T-2719 found the hardcoded-
#: pathspec bug in); add a new rule here, and ONLY here, to extend
#: coverage -- matching `frob.gates._coverage_sites._FAMILY_REPORTERS`'s
#: own one-line-addition shape.
_LIVENESS_SCAN_CHECKERS: dict[str, "Callable[[Path, str], bool]"] = {}


def _load_liveness_scan_checkers() -> "dict[str, Callable[[Path, str], bool]]":
    """Lazily builds `_LIVENESS_SCAN_CHECKERS`'s real contents on first
    use -- same deferred-import posture as `_load_family_reporters` in
    `frob.gates._coverage_sites` (T-1921), for the identical reason: a
    module-level import of a gate module here risks the same import-cycle
    shape `frob.gates.__init__` already sits in."""
    if not _LIVENESS_SCAN_CHECKERS:
        from frob.gates._render_lint import render001_scans

        _LIVENESS_SCAN_CHECKERS["RENDER001"] = render001_scans
    return _LIVENESS_SCAN_CHECKERS


# frob:doc docs/modules/app.md#waive-audit-t-2467
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness.test_necessary_when\
# _waived_this_run kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness.test_inert_when_rul\
# e_does_not_scan_the_file kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness.test_unverified_whe\
# n_no_checker_registered kind="unit"
# frob:tests \
# tests/unit/test_waive_audit_runner.py::TestClassifyWaiverLiveness.test_necessary_neve\
# r_inert_even_with_a_registered_checker kind="unit"
def classify_waiver_liveness(
    waiver: ScannedWaiver, report: GateReport, root: Path
) -> WaiverLiveness:
    """T-2740: classify one `ScannedWaiver` against `report` (a `GateReport`
    from a fresh, unscoped `run_gates` call against `root`) -- see this
    module's own T-2740 section docstring for exactly what each of the
    three states proves and why. NECESSARY is checked FIRST and always
    wins over INERT: a waiver that actively suppressed a violation this
    run is, by construction, in the rule's scan set, so the two verdicts
    can never legitimately disagree -- checking order only matters if a
    registered checker were ever wrong, and NECESSARY's direct-observation
    signal is strictly stronger evidence than INERT's structural one."""
    file = _repo_relative(waiver.file, root)
    for violation in report.waived:
        if violation.rule == waiver.rule and _repo_relative(violation.file, root) == (
            file
        ):
            return WaiverLiveness.NECESSARY
    checkers = _load_liveness_scan_checkers()
    checker = checkers.get(waiver.rule)
    if checker is not None and not checker(root, file):
        return WaiverLiveness.INERT
    return WaiverLiveness.UNVERIFIED
