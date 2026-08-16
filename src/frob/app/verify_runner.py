"""CLI wiring for `frob verify status|now|explain|dispose` (T-1697): the
operable surface over the T-1686 unverified-window package (`frob.verify`).

Before this module, a raised quarantine (`frob.verify._quarantine`,
T-1693) could only be inspected or cleared by calling private Python
functions directly -- a safety mechanism operable only through a private
API is not operable. This module is the CLI that makes the whole T-1686
epic auditable and actionable from a shell: `status` for a human/CI-
readable snapshot of the unverified window (depth, age, quarantine,
attribution), `now` to force a synchronous drain, `explain` to print one
finding's attribution reachability path, and `dispose` to file or dismiss
every currently-quarantined finding and clear the quarantine.

PORCELAIN RULE: `frob verify status` exits non-zero while quarantine is
raised, so a shell or CI step can gate on "is this repo's verification
healthy" without parsing prose.

RENDER001: every human-facing line here routes through `frob.render.
Renderer` -- `--json` stays a separate channel (the pydantic model's own
`model_dump_json`), matching `frob doctor`'s T-0448 precedent.
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.render import Renderer

_log = get_logger(__name__)


# frob:doc docs/modules/tickets-verify-sweep.md#frob-verify-cli-t-1697
class VerifyQuarantineFindingView(BaseModel):
    """One quarantined finding, as `frob verify status` renders it --
    narrowed from `frob.verify._quarantine.QuarantinedFinding` to exactly
    what a human/CI reader needs, plus the `key` string `frob verify
    dispose --file-ticket`/`--dismiss` expect back (round-trip identity,
    not a second encoding)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    rule_id: str
    file: str
    line: int | None
    commit_sha: str | None
    ticket_id: str | None
    disposition: str


# frob:doc docs/modules/tickets-verify-sweep.md#frob-verify-cli-t-1697
class VerifyStatus(BaseModel):
    """`frob verify status`'s whole payload -- the unverified window in
    one snapshot: watermark age, queue depth/age, and quarantine state
    including every undisposed finding. `--json` serializes this model
    directly (`model_dump_json`), so the schema IS the contract, not a
    hand-maintained parallel dict."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    watermark_commit: str | None
    watermark_age_s: float | None
    depth: int
    oldest_unverified_age_s: float | None
    oldest_unverified_commit: str | None
    oldest_unverified_ticket: str | None
    quarantine_raised: bool
    quarantine_batch_commit_shas: tuple[str, ...]
    quarantine_findings: tuple[VerifyQuarantineFindingView, ...]


def _resolve_root(cfg: AppConfig) -> Path:
    """`cfg.verify_path` if given, else the current directory, resolved."""
    return (cfg.verify_path or Path(".")).resolve()


def _renderer(cfg: AppConfig) -> Renderer:
    """The one `Renderer` every human-facing `frob verify` subcommand
    prints through (RENDER001, T-0448's `frob doctor` precedent)."""
    return Renderer.for_stream(
        sys.stdout, color_flag=cfg.color, no_color_flag=cfg.no_color
    )


def _finding_view(finding) -> VerifyQuarantineFindingView:  # noqa: ANN001
    """One `QuarantinedFinding` (`frob.verify._quarantine`) rendered as a
    `VerifyQuarantineFindingView`, including its `key`."""
    line_part = finding.line if finding.line is not None else ""
    key = f"{finding.rule_id}:{finding.file}:{line_part}"
    return VerifyQuarantineFindingView(
        key=key,
        rule_id=finding.rule_id,
        file=finding.file,
        line=finding.line,
        commit_sha=finding.commit_sha,
        ticket_id=finding.ticket_id,
        disposition=finding.disposition,
    )


def _load_status_inputs(root: Path):  # noqa: ANN201
    """Read the three stores `build_status` assembles from, or `None` on
    any unreadable store -- split out of `build_status` (ARCH001) so that
    function's own body stays the assembly step, not the fallible loads."""
    from frob.verify import load_watermark, queue_status
    from frob.verify._quarantine import load_quarantine

    queue = queue_status(root)
    if queue.is_err:
        _log.error("verify status: queue unreadable: %s", queue.danger_err)
        return None
    watermark = load_watermark(root)
    if watermark.is_err:
        _log.error("verify status: watermark unreadable: %s", watermark.danger_err)
        return None
    quarantine = load_quarantine(root)
    if quarantine.is_err:
        _log.error("verify status: quarantine unreadable: %s", quarantine.danger_err)
        return None
    return queue.danger_ok, watermark.danger_ok, quarantine.danger_ok


# frob:doc docs/modules/tickets-verify-sweep.md#frob-verify-cli-t-1697
# frob:tests tests/unit/verify/test_verify_runner.py::TestBuildStatus.test_reports_depth_age_and_quarantine kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_verify_runner.py::TestBuildStatus.test_clean_when_nothing_queued_and_no_quarantine kind="unit"  # noqa: E501
def build_status(root: Path) -> VerifyStatus | None:
    """Assemble one `VerifyStatus` snapshot for `root`, or `None` on an
    unreadable queue/quarantine store -- "cannot verify is never verified"
    (T-1686's standing invariant) applies to reading this state too: an
    unreadable store must never render as an empty, healthy-looking
    status."""
    import time

    loaded = _load_status_inputs(root)
    if loaded is None:
        return None
    entries, wm, record = loaded

    now = time.time()
    watermark_age_s = None
    if wm is not None:
        parsed = _parse_iso(wm.verified_at)
        if parsed is not None:
            watermark_age_s = max(0.0, now - parsed)

    oldest_age_s = None
    oldest_commit = None
    oldest_ticket = None
    if entries:
        oldest = entries[0]
        oldest_commit = oldest.commit_sha
        oldest_ticket = oldest.ticket_id
        parsed = _parse_iso(oldest.enqueued_at)
        if parsed is not None:
            oldest_age_s = max(0.0, now - parsed)

    raised = record is not None and record.cleared_at is None
    batch_shas: tuple[str, ...] = record.batch_commit_shas if raised and record else ()
    findings = (
        tuple(_finding_view(f) for f in record.findings) if raised and record else ()
    )

    return VerifyStatus(
        watermark_commit=wm.commit_sha if wm else None,
        watermark_age_s=watermark_age_s,
        depth=len(entries),
        oldest_unverified_age_s=oldest_age_s,
        oldest_unverified_commit=oldest_commit,
        oldest_unverified_ticket=oldest_ticket,
        quarantine_raised=raised,
        quarantine_batch_commit_shas=batch_shas,
        quarantine_findings=findings,
    )


def _parse_iso(value: str) -> float | None:
    """`value` (an ISO-8601 UTC timestamp, this package's own convention)
    as a Unix epoch float, or `None` on any parse failure -- a corrupt/
    unparseable timestamp degrades an AGE reading to unknown rather than
    crashing the whole status call."""
    from datetime import datetime

    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return None


def _print_status_human(r: Renderer, status: VerifyStatus) -> None:
    """Render `status` as the default human-readable `frob verify status`
    text, through `r`."""
    r.line(f"watermark:        {status.watermark_commit or '(none yet)'}")
    if status.watermark_age_s is not None:
        r.line(f"watermark age:    {status.watermark_age_s:.0f}s")
    r.line(f"unverified depth: {status.depth}")
    if status.oldest_unverified_age_s is not None:
        r.line(
            f"oldest unverified: {status.oldest_unverified_commit} "
            f"(ticket {status.oldest_unverified_ticket}, "
            f"{status.oldest_unverified_age_s:.0f}s old)"
        )
    if status.quarantine_raised:
        n = len(status.quarantine_findings)
        r.line(f"quarantine:       RAISED ({n} finding(s))")
        r.line(f"  batch:          {list(status.quarantine_batch_commit_shas)}")
        for f in status.quarantine_findings:
            disp = f.disposition or "UNDISPOSED"
            r.line(
                f"  - [{disp}] {f.key} (commit={f.commit_sha}, ticket={f.ticket_id})"
            )
    else:
        r.line("quarantine:       clear")


def _run_status(cfg: AppConfig) -> None:
    """`frob verify status`: print the unverified window and exit
    non-zero while quarantine is raised (the porcelain rule this
    subcommand exists to provide)."""
    root = _resolve_root(cfg)
    status = build_status(root)
    if status is None:
        sys.exit(1)
    r = _renderer(cfg)
    if cfg.verify_json:
        r.line(status.model_dump_json(indent=2))
    else:
        _print_status_human(r, status)
    if status.quarantine_raised:
        sys.exit(1)


def _run_now(cfg: AppConfig) -> None:
    """`frob verify now`: drain and verify the queue synchronously, right
    now, for a human who wants the unverified window closed before
    walking away."""
    from frob.verify import run_coalesced_verification

    root = _resolve_root(cfg)
    result = run_coalesced_verification(root)
    if result.is_err:
        _log.error("verify now: %s", result.danger_err)
        sys.exit(1)
    outcome = result.danger_ok
    r = _renderer(cfg)
    if cfg.verify_json:
        r.line(outcome.model_dump_json(indent=2))
    else:
        r.line(f"status: {outcome.status}")
        if outcome.commit_sha:
            r.line(f"commit: {outcome.commit_sha}")
        r.line(f"advanced watermark: {outcome.advanced_watermark}")
        if outcome.filed_ticket:
            r.line(f"filed ticket: {outcome.filed_ticket}")
    if outcome.status == "red":
        sys.exit(1)


def _parse_finding_arg(raw: str) -> tuple[str, str, int | None] | None:
    """Parse `RULE:FILE[:LINE]` into `(rule_id, file, line)`, or `None` on
    a malformed argument."""
    parts = raw.split(":")
    if len(parts) < 2:
        return None
    rule_id = parts[0]
    line: int | None = None
    if len(parts) >= 3 and parts[-1]:
        try:
            line = int(parts[-1])
        except ValueError:
            return None
        file = ":".join(parts[1:-1])
    else:
        file = ":".join(parts[1:]) if len(parts) == 2 else ":".join(parts[1:-1])
    if not file:
        return None
    return rule_id, file, line


def _print_attribution_human(r: Renderer, attribution) -> None:  # noqa: ANN001
    """Render one `Attribution` result as `frob verify explain`'s default
    human-readable text, through `r`. Exits 1 for an unattributed result."""
    if attribution.status == "attributed":
        r.line(
            f"attributed to commit {attribution.commit_sha} "
            f"(ticket {attribution.ticket_id})"
        )
        r.line("reachability path:")
        for step in attribution.reachability_path:
            r.line(f"  -> {step}")
    else:
        r.line("UNATTRIBUTED")
        r.line(f"candidate commits: {list(attribution.candidate_commits)}")
        sys.exit(1)


# frob:ticket T-2018
def _explain_batch(root: Path, snapshot) -> tuple:  # noqa: ANN001, ANN201 -- (VerifyQueueEntry, ...), deferred-import types
    """T-2018: `_run_explain`'s candidate-commit batch, no longer just
    the persisted verify queue (which is empty whenever a sweep has not
    happened to enqueue the RIGHT commit, or has already compacted past
    it once the watermark advanced -- the exact "queue is empty, nothing
    to attribute against" refusal this ticket measured and fixed).
    Merges the persisted queue (`queue_status`, real recorded land
    intents, given priority on a duplicate commit sha) with an ad-hoc
    batch built from real git history (`build_ad_hoc_batch`, anchored at
    the current watermark's commit sha when one exists, else a bounded
    recent-commit window for a cold start) -- so `frob verify explain`
    can attribute a finding whether or not a sweep ever enqueued the
    commit that caused it. A `queue_status` failure is logged and
    degrades to ad-hoc-only, never a hard refusal -- the ad-hoc half
    alone is still real, useful data."""
    from frob.verify import build_ad_hoc_batch, load_watermark, queue_status

    queue = queue_status(root)
    persisted = queue.danger_ok if queue.is_ok else ()
    if queue.is_err:
        _log.warning(
            "verify explain: queue unreadable (%s), falling back to ad-hoc "
            "attribution only",
            queue.danger_err,
        )

    watermark = load_watermark(root)
    since = (
        watermark.danger_ok.commit_sha
        if watermark.is_ok and watermark.danger_ok is not None
        else None
    )
    ad_hoc = build_ad_hoc_batch(root, snapshot=snapshot, since=since)

    seen_shas = {entry.commit_sha for entry in persisted}
    return tuple(persisted) + tuple(
        entry for entry in ad_hoc if entry.commit_sha not in seen_shas
    )


def _run_explain(cfg: AppConfig) -> None:
    """`frob verify explain RULE:FILE[:LINE]`: print the attribution
    reachability path -- the chain of symbol references that let
    `attribute_batch` assign this finding to a commit -- so an
    attribution is auditable evidence, not a bare assertion. T-2018: no
    longer refuses just because the persisted verify queue is empty --
    `_explain_batch` widens the candidate set with real git history so
    an operator holding a single `frob check` finding (rule id + file[:
    line]) can get it attributed, or an honest `unattributed` with named
    candidates, without a sweep having enqueued anything first."""
    from frob.verify import attribute_batch, load_attribution_context

    root = _resolve_root(cfg)
    parsed = _parse_finding_arg(cfg.verify_finding or "")
    if parsed is None:
        _log.error("verify explain: %r is not RULE:FILE[:LINE]", cfg.verify_finding)
        sys.exit(1)
    rule_id, file, line = parsed

    context = load_attribution_context(root)
    if context.is_err:
        _log.error("verify explain: %s", context.danger_err)
        sys.exit(1)
    snapshot, call_graph = context.danger_ok

    batch = _explain_batch(root, snapshot)
    if not batch:
        _log.error(
            "verify explain: no candidate commit(s) found -- persisted "
            "queue and ad-hoc git history both yielded nothing to "
            "attribute against"
        )
        sys.exit(1)

    finding = (rule_id, file, line) if line is not None else (rule_id, file)
    result = attribute_batch(
        root, [finding], batch, graph_and_calls=(snapshot, call_graph)
    )
    if result.is_err:
        _log.error("verify explain: %s", result.danger_err)
        sys.exit(1)
    (attribution,) = result.danger_ok

    r = _renderer(cfg)
    if cfg.verify_json:
        r.line(attribution.model_dump_json(indent=2))
        if attribution.status != "attributed":
            sys.exit(1)
        return
    _print_attribution_human(r, attribution)


def _parse_dispose_entry(raw: str) -> tuple[tuple[str, str, int | None], str] | None:
    """Parse one `--file-ticket`/`--dismiss` argument
    (`RULE:FILE:LINE=VALUE`) into `((rule_id, file, line), value)`, or
    `None` on a malformed argument."""
    if "=" not in raw:
        return None
    key_part, value = raw.split("=", 1)
    parsed = _parse_finding_arg(key_part)
    if parsed is None or not value:
        return None
    return parsed, value


def _collect_dispositions(
    cfg: AppConfig,
) -> dict[tuple[str, str, int | None], tuple[str, str]] | None:
    """Parse `cfg.verify_dispose_filed`/`verify_dispose_dismissed` into
    `clear_quarantine`'s own `dispositions` mapping, or `None` (having
    already logged and exited) on a malformed entry -- split out of
    `_run_dispose` (ARCH001) so that function's own body stays the
    validate-then-call sequence."""
    dispositions: dict[tuple[str, str, int | None], tuple[str, str]] = {}
    for raw in cfg.verify_dispose_filed:
        parsed = _parse_dispose_entry(raw)
        if parsed is None:
            _log.error("verify dispose: malformed --file-ticket %r", raw)
            return None
        key, ticket_id = parsed
        dispositions[key] = ("filed", ticket_id)
    for raw in cfg.verify_dispose_dismissed:
        parsed = _parse_dispose_entry(raw)
        if parsed is None:
            _log.error("verify dispose: malformed --dismiss %r", raw)
            return None
        key, reason = parsed
        dispositions[key] = ("dismissed", reason)
    return dispositions


def _run_dispose(cfg: AppConfig) -> None:
    """`frob verify dispose`: apply every `--file-ticket`/`--dismiss`
    disposition given and, once every currently-quarantined finding is
    disposed, clear the quarantine -- the only path that ever clears one
    (`frob.verify._quarantine.clear_quarantine`'s own contract)."""
    from frob.verify._quarantine import clear_quarantine

    root = _resolve_root(cfg)
    if not cfg.verify_dispose_reason:
        _log.error("verify dispose: --reason is required")
        sys.exit(1)

    dispositions = _collect_dispositions(cfg)
    if dispositions is None:
        sys.exit(1)
    if not dispositions:
        _log.error(
            "verify dispose: at least one --file-ticket or --dismiss is required"
        )
        sys.exit(1)

    actor = cfg.verify_dispose_actor or getpass.getuser()
    result = clear_quarantine(
        root, dispositions=dispositions, reason=cfg.verify_dispose_reason, actor=actor
    )
    if result.is_err:
        _log.error("verify dispose: %s", result.danger_err)
        sys.exit(1)
    cleared = result.danger_ok
    r = _renderer(cfg)
    if cfg.verify_json:
        r.line(cleared.model_dump_json(indent=2))
    else:
        r.line(f"quarantine cleared by {actor}: {cfg.verify_dispose_reason}")


# frob:doc docs/modules/tickets-verify-sweep.md#frob-verify-cli-t-1697
# frob:ticket T-1697
def run(cfg: AppConfig) -> None:
    """`frob verify status|now|explain|dispose` dispatch -- see this
    module's own docstring for what each subcommand does."""
    if cfg.verify_command == "status":
        _run_status(cfg)
    elif cfg.verify_command == "now":
        _run_now(cfg)
    elif cfg.verify_command == "explain":
        _run_explain(cfg)
    elif cfg.verify_command == "dispose":
        _run_dispose(cfg)
    else:
        _log.error("frob verify requires a subcommand: status|now|explain|dispose")
        sys.exit(1)
