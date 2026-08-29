"""CLI wiring for `frob status` (T-2911): a delta-first movement summary
so a large absolute finding count does not read as "no progress" to a
newcomer.

Measured motivation: this repo's own `frob check` reports several
thousand warnings; a foreign repo can report over four thousand. Nothing
in that absolute count conveys that the number is MOVING. The user's own
words: a newcomer who sees a four-figure wall concludes the codebase is
hopeless and stops. `frob status` answers a narrower question instead --
"is this getting better" -- using the DELTA, never the absolute.

REUSE, NOT A PARALLEL COUNTER (the standing anti-duplication rule). Every
number here comes from a store this repo already maintains as the single
source of truth for it:

- Findings movement: `.frob/baseline` (`frob.gates.load_baseline`/
  `is_baseline_stale`/`violation_fingerprint`), the exact same store and
  fingerprint identity `frob check --delta` already reads. The current
  violation set is collected via `frob.gates.run_gates` with a
  `GateConfig`, the SAME call shape `frob check --stamp-baseline` itself
  uses (`frob.app._check_chunking_baseline._run_baseline_chunks`) -- not a
  second gate-running code path.
- Verification lag: `frob.app.verify_runner.build_status`, the exact
  function `frob verify status` calls.
- Ticket movement: `frob.tickets.ticket_flow`, the exact function
  `frob ticket flow` calls.

This module adds exactly one new computation: the healed/introduced/net
delta between a stamped baseline's fingerprints and a fresh gate run's
fingerprints. Everything else is assembly.

SPEED (T-2950): the ticket-movement section (`frob.tickets.ticket_flow`)
mines the WHOLE ledger's git history -- one `git log` subprocess pair per
ticket id, active AND archived -- and measured at 5m41s wall clock on this
repo's own ~1000-ticket archive, blowing past the 200s foreground budget a
newcomer-facing surface must fit inside. The findings-movement and
verification-lag sections are both reused-artifact reads and measure
under half a second each; they were never the bottleneck. Rather than
force everyone to pay the ticket-flow cost (or silently drop the section),
T-2950 makes it opt-in via `--tickets` (default OFF) -- the default
`frob status` reports the ticket-movement section as an honest "not
measured", in the same voice the stale-baseline refusal already uses,
never a fabricated zero.

HONEST ZERO, NEVER A FABRICATED DELTA (T-2911's own hard requirement,
motivated by a real incident this same session: a 53-commit-stale
watermark caused the post-land sweep to file three phantom regression
tickets). `FindingsMovement.measured=False` means exactly that -- this
report makes NO claim about movement, not "zero movement measured". A
missing or STALE baseline (`is_baseline_stale`) both take this path,
refusing to even run the gate scan, rather than compute a number nobody
should trust."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from frob.app.config import AppConfig
from frob.gates._lock_producer import LockProducerStatus
from frob.logging import get_logger
from frob.render import Renderer

_log = get_logger(__name__)

if TYPE_CHECKING:
    from frob.gates import Violation

#: Default gate selection for the findings-movement scan: the SAME
#: "gates-fast" stage group `frob check --only gates-fast` already
#: defines (`frob.check._STAGE_GROUPS`) -- no second gate list invented.
_DEFAULT_STATUS_GATES = "gates-fast"


# frob:doc docs/modules/cli.md#frob-status-t-2911
# frob:tests tests/test_status.py::TestFindingsMovementModel.test_defaults_are_unmeasured_shaped kind="unit"  # noqa: E501
# frob:ticket T-2911
class FindingsMovement(BaseModel):
    """The `.frob/baseline`-vs-current-run delta -- the one genuinely new
    computation `frob status` performs, everything else in `StatusReport`
    is reused from an existing report builder verbatim.

    `measured=False` is a first-class outcome, not an edge case: it means
    this section makes NO claim about movement (see this module's own
    docstring for why an absent/stale baseline must never be silently
    read as "no movement" -- that is a different, false claim)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    measured: bool
    #: Always present -- explains either the honest non-measurement, or
    #: which gates a real measurement covered.
    note: str
    stale: bool = False
    #: Findings present in the baseline but absent from the current run
    #: (fixed since the baseline was stamped). `None` iff `measured` is
    #: `False` -- a real "0" (measured, nothing healed) must render
    #: differently from "not measured", so this is never coerced to 0.
    healed: int | None = None
    #: Findings present in the current run but absent from the baseline
    #: (introduced since the baseline was stamped).
    introduced: int | None = None
    #: `healed - introduced`. Positive means net improvement.
    net: int | None = None
    gates_covered: tuple[str, ...] = ()


# frob:doc docs/modules/cli.md#frob-status-t-2911
# frob:tests tests/test_status.py::TestBuildStatusReportIntegration.test_no_baseline_reports_unmeasured_findings kind="unit"  # noqa: E501
# frob:ticket T-2911
class StatusReport(BaseModel):
    """`frob status`'s whole payload. `--json` serializes this model
    directly, matching `VerifyStatus`'s own T-1697 precedent -- the schema
    IS the contract, not a hand-maintained parallel dict."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    findings: FindingsMovement
    #: `None` only when the verify store itself is unreadable (mirrors
    #: `build_status`'s own "cannot verify is never verified" contract) --
    #: never fabricated as a healthy-looking default.
    verify_watermark_commit: str | None
    verify_commits_since_watermark: int | None
    verify_quarantine_raised: bool | None
    #: `None` when `--no-tickets` was passed -- the ticket-flow section
    #: was not measured this run, not "zero tickets landed".
    tickets_open: int | None
    tickets_landed_today: int | None
    trailing_net_rate: float | None
    #: T-2999: one entry per `frob.gates._lock_producer.KNOWN_LOCKS`,
    #: always populated (this section has no opt-out and no expensive
    #: git-history mining -- three `git log`/`git rev-list` calls,
    #: unlike the ticket-flow section above) -- so an abandoned baseline
    #: producer is visible on every `frob status`, not behind a flag a
    #: reader has to know to pass.
    baseline_locks: tuple[LockProducerStatus, ...] = ()


# frob:doc docs/modules/cli.md#frob-status-t-2911
# frob:tests tests/test_status.py::TestComputeFindingsMovement.test_must_show_healed_and_introduced kind="unit"  # noqa: E501
# frob:ticket T-2911
def compute_findings_movement(
    baseline: dict | None,
    *,
    stale: bool,
    current_violations: "tuple[Violation, ...] | None",
    gates_covered: tuple[str, ...],
) -> FindingsMovement:
    """Pure delta computation -- no IO, so this is trivially testable
    against a fixture baseline dict and a fixture `Violation` tuple,
    independent of a real gate run or a real `.frob/baseline` file.

    Refuses to compute anything (returns `measured=False`) for every
    condition that would make the result untrustworthy: no baseline yet,
    a stale baseline, or no current violation set to diff against. See
    this module's own docstring for why that refusal is the point, not a
    gap to fill in later."""
    from frob.gates import violation_fingerprint

    if baseline is None:
        return FindingsMovement(
            measured=False,
            note="no baseline stamped yet -- run "
            "`frob check --stamp-baseline` to start tracking movement",
        )
    if stale:
        return FindingsMovement(
            measured=False,
            stale=True,
            note="baseline is STALE (the tree changed since it was "
            "stamped) -- re-stamp with `frob check --stamp-baseline` "
            "before trusting a delta",
        )
    if current_violations is None:
        return FindingsMovement(
            measured=False,
            note="findings not measured this run",
        )
    baseline_fps = frozenset(baseline.get("fingerprints", []))
    current_fps = frozenset(violation_fingerprint(v) for v in current_violations)
    healed = len(baseline_fps - current_fps)
    introduced = len(current_fps - baseline_fps)
    return FindingsMovement(
        measured=True,
        note=f"measured against {len(gates_covered)} gate famil(ies)",
        healed=healed,
        introduced=introduced,
        net=healed - introduced,
        gates_covered=gates_covered,
    )


# frob:ticket T-2911
def _collect_current_violations(
    root: Path, gates: frozenset[str]
) -> "tuple[Violation, ...] | None":
    """`gates`' current violation set via `frob.gates.run_gates`, the SAME
    call shape `frob check --stamp-baseline` itself uses
    (`_run_baseline_chunks`) -- `None` on any gate-run failure (never a
    fabricated empty result)."""
    from frob.gates import GateConfig, run_gates

    result = run_gates(GateConfig(root=str(root), gates=gates))
    if result.is_err:
        _log.error("frob status: gate scan failed: %s", result.danger_err.value)
        return None
    return result.danger_ok.violations


# frob:ticket T-2911
def _findings_section(root: Path, only: list[str]) -> FindingsMovement:
    """Assemble `FindingsMovement` for `root`: load the baseline, check
    staleness, and only then (never otherwise) run the bounded gate scan
    `only` selects."""
    from frob.check import _expand_stage_groups
    from frob.gates import is_baseline_stale, load_baseline

    baseline = load_baseline(root)
    if baseline is None:
        return compute_findings_movement(
            None, stale=False, current_violations=None, gates_covered=()
        )
    stale = is_baseline_stale(root, baseline)
    if stale:
        return compute_findings_movement(
            baseline, stale=True, current_violations=None, gates_covered=()
        )
    requested = frozenset(only) if only else frozenset({_DEFAULT_STATUS_GATES})
    gates = _expand_stage_groups(requested)
    violations = _collect_current_violations(root, gates)
    if violations is None:
        return compute_findings_movement(
            baseline,
            stale=False,
            current_violations=None,
            gates_covered=tuple(sorted(gates)),
        )
    return compute_findings_movement(
        baseline,
        stale=False,
        current_violations=violations,
        gates_covered=tuple(sorted(gates)),
    )


# frob:ticket T-2911
def _verify_section(root: Path) -> tuple[str | None, int | None, bool | None]:
    """`(watermark_commit, commits_since_watermark, quarantine_raised)`
    from `frob.app.verify_runner.build_status` -- the exact function
    `frob verify status` calls. All `None` when the verify store itself
    is unreadable."""
    from frob.app.verify_runner import build_status

    status = build_status(root)
    if status is None:
        return None, None, None
    return (
        status.watermark_commit,
        status.commits_since_watermark,
        status.quarantine_raised,
    )


# frob:ticket T-2911
def _flow_section(root: Path) -> tuple[int | None, int | None, float | None]:
    """`(open_count, landed_today, trailing_net_rate)` from
    `frob.tickets.ticket_flow` -- the exact function `frob ticket flow`
    calls. Mines the whole ledger's git history, so this is the single
    most expensive section; callers pass `--no-tickets` to skip it."""
    from datetime import date

    from frob.tickets import load_active, ticket_flow

    result = load_active(root)
    if result.is_err:
        _log.error("frob status: ticket ledger unreadable: %s", result.danger_err)
        return None, None, None
    report = ticket_flow(root, result.danger_ok)
    today = date.today()
    landed_today = next((r.landed for r in report.rows if r.day == today), 0)
    return report.open_count, landed_today, report.trailing_net_rate


# frob:ticket T-2999
# frob:tests tests/test_status.py::TestBuildStatusReportIntegration.test_baseline_locks_section_is_always_populated kind="unit"  # noqa: E501
def _baseline_locks_section(root: Path) -> tuple[LockProducerStatus, ...]:
    """`frob.gates._lock_producer.all_producer_statuses` for `root` --
    three `git log`/`git rev-list` calls, cheap enough (T-2999 measured:
    well under a second) to run unconditionally on every `frob status`,
    unlike the opt-in ticket-flow section above."""
    from frob.gates._lock_producer import all_producer_statuses

    return all_producer_statuses(root)


# frob:doc docs/modules/cli.md#frob-status-t-2911
# frob:tests tests/test_status.py::TestBuildStatusReportIntegration.test_no_baseline_reports_unmeasured_findings kind="unit"  # noqa: E501
# frob:ticket T-2911
def build_status_report(
    root: Path, *, only: list[str], include_tickets: bool
) -> StatusReport:
    """Assemble one `StatusReport` for `root` -- the composition of the
    three reused sections above, plus the one new findings-delta
    computation. Split out of `run` (ARCH001) so it is testable without
    an `AppConfig`/argparse round-trip."""
    findings = _findings_section(root, only)
    watermark_commit, commits_since_watermark, quarantine_raised = _verify_section(root)
    if include_tickets:
        open_count, landed_today, trailing_net_rate = _flow_section(root)
    else:
        open_count, landed_today, trailing_net_rate = None, None, None
    return StatusReport(
        findings=findings,
        verify_watermark_commit=watermark_commit,
        verify_commits_since_watermark=commits_since_watermark,
        verify_quarantine_raised=quarantine_raised,
        tickets_open=open_count,
        tickets_landed_today=landed_today,
        trailing_net_rate=trailing_net_rate,
        baseline_locks=_baseline_locks_section(root),
    )


# frob:ticket T-2911
def _print_status_human(r: Renderer, report: StatusReport) -> None:
    """Render `report` as the default human-readable `frob status` text."""
    f = report.findings
    r.line("== findings movement ==")
    if not f.measured:
        r.line(f"  not measured: {f.note}")
    else:
        r.line(f"  healed:     {f.healed}")
        r.line(f"  introduced: {f.introduced}")
        sign = "+" if (f.net or 0) >= 0 else ""
        r.line(f"  net:        {sign}{f.net}")
        r.line(f"  ({f.note})")
    r.line("")
    r.line("== verification lag ==")
    if report.verify_watermark_commit is None and (
        report.verify_commits_since_watermark is None
    ):
        r.line("  watermark: (none yet)")
    else:
        r.line(f"  watermark: {report.verify_watermark_commit or '(none yet)'}")
        if report.verify_commits_since_watermark is not None:
            r.line(
                f"  commits since watermark: {report.verify_commits_since_watermark}"
            )
    if report.verify_quarantine_raised:
        r.line("  quarantine: RAISED")
    r.line("")
    r.line("== ticket movement ==")
    if report.tickets_open is None:
        r.line(
            "  not measured: ticket-flow mining is off by default (it "
            "mines the whole ledger's git history, active and archived "
            "tickets alike, and can take minutes on a large repo) -- "
            "pass --tickets to include it"
        )
    else:
        r.line(f"  open: {report.tickets_open}")
        r.line(f"  landed today: {report.tickets_landed_today}")
        r.line(f"  trailing net rate: {report.trailing_net_rate:+.1f}/day")
    r.line("")
    r.line("== baseline locks ==")
    for lock in report.baseline_locks:
        if lock.verdict == "ABANDONED":
            tail = (
                f"ABANDONED -- {lock.code_commits_since} commit(s) touched "
                "its own code since last stamp with no pin; producer "
                "looks stopped"
            )
        elif lock.verdict == "PINNED":
            reason = lock.pin.reason if lock.pin is not None else "(no reason)"
            tail = f"PINNED -- {reason}"
        elif lock.verdict == "UNMEASURED":
            tail = (
                "UNMEASURED -- no committed lock, or its git history could not be read"
            )
        else:
            tail = f"fresh ({lock.code_commits_since} commit(s) since last stamp)"
        r.line(f"  {lock.name} ({lock.path_rel}): {tail}")


# frob:ticket T-2911
def _resolve_root(cfg: AppConfig) -> Path:
    """`cfg.status_path` if given, else the current directory, resolved."""
    return (cfg.status_path or Path(".")).resolve()


# frob:doc docs/modules/cli.md#frob-status-t-2911
# frob:tests tests/test_status.py::TestRunEndToEnd.test_run_prints_human_text_by_default kind="unit"  # noqa: E501
# frob:tests tests/test_status.py::TestRunEndToEnd.test_run_prints_json_when_requested kind="unit"  # noqa: E501
# frob:ticket T-2911
def run(cfg: AppConfig) -> None:
    """`frob status`: print the delta-first movement summary. Never exits
    non-zero on its own account (unlike `frob verify status`'s quarantine
    porcelain rule) -- this is a report, not a gate."""
    root = _resolve_root(cfg)
    # T-2950: ticket-flow mining is opt-IN (default off) -- it measured
    # over 5 minutes on this repo's own ticket archive (one git-log
    # subprocess pair per ticket id, active AND archived). `--no-tickets`
    # is kept as a deprecated no-op for scripts that already pass it.
    report = build_status_report(
        root, only=cfg.status_only, include_tickets=cfg.status_tickets
    )
    r = Renderer.for_stream(
        sys.stdout, color_flag=cfg.color, no_color_flag=cfg.no_color
    )
    if cfg.status_json:
        r.line(report.model_dump_json(indent=2))
    else:
        _print_status_human(r, report)
