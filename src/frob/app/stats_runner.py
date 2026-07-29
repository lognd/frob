"""CLI wiring for `frob stats` -- delivery measurement (T-0009)."""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/app/stats_runner.py's exclusivity-vocabulary hits are source-level \
# design-rationale prose (a header string and docstring describing already-implemented \
# proxy behavior added by T-1127, verifiable by reading the code they annotate) rather \
# than a separate cross-module contract needing its own tracked invariant; disposed as \
# a calibration batch, not claim-by-claim"

from __future__ import annotations

import os
import sys
from pathlib import Path

from frob.app._style import style_header, style_warn
from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.render import Renderer

_log = get_logger(__name__)

# frob:ticket T-0178
_AGENTIC_ENV = "FROB_STATS_AGENTIC"
"""Set (any non-empty, non-0/false value) to render `--agentic` output from
`frob stats` -- an env-var trigger rather than an argparse flag because
T-0178's declared scope excludes `src/frob/__main__.py`, where the stats
subparser's `add_argument` calls live; wiring a real `--agentic` CLI flag
is filed separately (see the ticket's Done report)."""


def _agentic_requested(cfg: AppConfig) -> bool:
    """Whether the agentic report was requested for this `frob stats` run."""
    value = os.environ.get(
        _AGENTIC_ENV, ""
    )  # frob:waive SEC110 reason="behavior flag, not a secret"
    return value.strip().lower() not in ("", "0", "false")


def _agentic_time_lines(report) -> list[str]:  # noqa: ANN001
    """The category-time and top-sinks sections of the `--agentic` report."""
    lines = ["command time by category:"]
    if not report.category_time:
        lines.append("  (no telemetry recorded yet -- .frob/telemetry.jsonl is empty)")
    for c in report.category_time:
        lines.append(f"  {c.category}: {c.total_ms:.0f}ms over {c.count} run(s)")
    lines += ["", "top wall-clock sinks:"]
    for s in report.top_time_sinks:
        lines.append(f"  {s.duration_ms:.0f}ms  frob {s.args_head}")
    return lines


def _agentic_retread_lines(report) -> list[str]:  # noqa: ANN001
    """The retread-candidates section of the `--agentic` report."""
    lines = ["", "retread candidates (identical command+tree re-run):"]
    if not report.retread_candidates:
        lines.append("  (none observed)")
    for r in report.retread_candidates:
        lines.append(
            f"  frob {r.args_head} @ {r.tree_hash}: "
            f"{r.run_count}x, {r.total_ms:.0f}ms total"
        )
    return lines


def _agentic_ticket_and_token_lines(report) -> list[str]:  # noqa: ANN001
    """The per-ticket cycle-time and per-tool token sections of the
    `--agentic` report."""
    lines = ["", "per-ticket cycle time:"]
    if not report.ticket_cycle_times:
        lines.append("  (no ticket transitions recorded yet)")
    for t in report.ticket_cycle_times:
        cycle = f"{t.cycle_time_s:.0f}s" if t.cycle_time_s is not None else "n/a"
        lead = f"{t.lead_time_s:.0f}s" if t.lead_time_s is not None else "n/a"
        lines.append(f"  {t.ticket_id}: cycle={cycle} lead={lead}")
    lines += ["", "tool output tokens (estimated, len/4 heuristic):"]
    if not report.tool_tokens:
        lines.append("  (no PostToolUse hook events recorded yet)")
    for tt in report.tool_tokens:
        lines.append(
            f"  {tt.tool}: ~{tt.total_tokens} tokens over {tt.call_count} call(s)"
        )
    return lines


# frob:ticket T-0562
def _run_agentic(cfg: AppConfig) -> None:
    """Render `frob stats`'s non-gated agentic time/token breakdown."""
    from frob.stats import agentic_report

    root = (cfg.stats_path or Path(".")).resolve()
    report = agentic_report(root)

    if cfg.stats_json:
        Renderer.for_stream(sys.stdout).line(report.model_dump_json(indent=2))
        return

    from frob.logging.color import should_color

    color = should_color(sys.stdout)
    lines = [
        style_header("frob stats --agentic (diagnostics only, non-gated)", color),
        "",
        f"telemetry events: {report.event_count}",
        "",
    ]
    lines += _agentic_time_lines(report)
    lines += _agentic_retread_lines(report)
    lines += _agentic_ticket_and_token_lines(report)
    Renderer.for_stream(sys.stdout).line("\n".join(lines))


# frob:tests tests/test_app_daemon_proxy.py::TestDifferentialParity.test_stats_json_daemon_matches_in_process kind="unit"  # noqa: E501
def _try_stats_via_daemon(root: Path, cfg: AppConfig) -> bool:
    """T-1127: for a plain `frob stats --json` (non-`--agentic` -- the RPC
    (`frob_stats`) answers the default `StatsReport` shape only, never
    the separate `AgenticReport` `--agentic` reads), try the daemon's RPC
    via `frob.app._daemon_proxy.query` before computing it in-process.
    Returns `True` on a daemon hit (already rendered); `False` falls
    through unchanged, same contract every other `_try_*_via_daemon`
    helper uses. The RPC returns `StatsReport.model_dump(mode='json')`
    verbatim (T-1127), field-for-field identical to this CLI's own
    `--json` output (both sides dump the identical pydantic model)."""
    if not cfg.stats_json:
        return False
    from frob.app._daemon_proxy import query

    days = cfg.stats_days or 30
    proxied = query(root, "frob_stats", {"window_days": days})
    if proxied.is_err:
        return False
    import json

    _log.info(json.dumps(proxied.danger_ok, indent=2))
    return True


# frob:ticket T-0009
# frob:ticket T-0562
# frob:doc docs/modules/app.md#runners
# frob:ticket T-0588
# frob:tests tests/unit/test_app_style.py::test_stats_plain_stdout_has_no_ansi
# frob:waive ARCH103 reason="T-0977: `frob stats` CLI entrypoint -- routes between the \
# agentic and gated report modes and renders each; the mode-branch-then-render shape \
# IS the runner's job, same as this module's sibling `frob.app.*_runner`s"
def run(cfg: AppConfig) -> None:
    """Render the delivery snapshot (queue health + commit cadence), or
    the non-gated agentic time/token breakdown when `FROB_STATS_AGENTIC`
    is set (T-0178)."""
    if _agentic_requested(cfg):
        _run_agentic(cfg)
        return

    root = (cfg.stats_path or Path(".")).resolve()

    if _try_stats_via_daemon(root, cfg):
        return

    from frob.stats import collect

    days = cfg.stats_days or 30
    result = collect(root, window_days=days)
    if result.is_err:
        _log.error("frob stats: %s", result.danger_err)
        sys.exit(1)
    report = result.danger_ok

    if cfg.stats_json:
        Renderer.for_stream(sys.stdout).line(report.model_dump_json(indent=2))
        return

    from frob.logging.color import should_color

    color = should_color(sys.stdout)
    t = report.tickets
    c = report.commits
    blocked = style_warn(str(t.blocked), color) if t.blocked else str(t.blocked)
    lines = [
        style_header("frob stats", color),
        "",
        f"tickets: {t.total} total  ({t.doable} doable, {blocked} blocked)",
        f"  by state: {_fmt(t.by_state)}",
        f"  by kind:  {_fmt(t.by_kind)}",
        f"  failure-log entries: {t.failure_entries}",
        "",
        f"commits (last {c.window_days}d): {c.total} total  ~{c.per_week}/week",
        f"  by type: {_fmt(c.by_type)}",
    ]
    Renderer.for_stream(sys.stdout).line("\n".join(lines))


def _fmt(counts: dict[str, int]) -> str:
    """Render a count map as `k=v` pairs ordered by descending count."""
    if not counts:
        return "(none)"
    ordered = sorted(counts.items(), key=lambda kv: -kv[1])
    return "  ".join(f"{k}={v}" for k, v in ordered)
