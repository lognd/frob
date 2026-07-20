"""CLI wiring for `frob stats` -- delivery measurement (T-0009)."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app._style import style_header, style_warn
from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:ticket T-0009
# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    """Render the delivery snapshot (queue health + commit cadence)."""
    from frob.stats import collect

    root = (cfg.stats_path or Path(".")).resolve()
    days = cfg.stats_days or 30
    result = collect(root, window_days=days)
    if result.is_err:
        _log.error("frob stats: %s", result.danger_err)
        sys.exit(1)
    report = result.danger_ok

    if cfg.stats_json:
        print(report.model_dump_json(indent=2))
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
    print("\n".join(lines))


def _fmt(counts: dict[str, int]) -> str:
    """Render a count map as `k=v` pairs ordered by descending count."""
    if not counts:
        return "(none)"
    ordered = sorted(counts.items(), key=lambda kv: -kv[1])
    return "  ".join(f"{k}={v}" for k, v in ordered)
