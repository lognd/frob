"""CLI wiring for `frob clean [--all|--deep] [-y]` (T-0457, docs/modules/clean.md)."""

from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.render import Renderer

_log = get_logger(__name__)


def _resolve_tier(cfg: AppConfig):  # noqa: ANN201
    """The `CleanTier` selected by `--all`/`--deep` (mutually additive, DEEP wins)."""
    from frob.clean import CleanTier

    if cfg.clean_deep:
        return CleanTier.DEEP
    if cfg.clean_all:
        return CleanTier.ALL
    return CleanTier.SAFE


def _print_report(r: Renderer, report, executed: bool) -> None:  # noqa: ANN001
    """Render a `CleanReport`: heading, per-entry path+size rows, and totals."""
    verb = "removed" if executed else "would remove"
    r.write.heading(f"frob clean (tier={report.tier.name.lower()})")
    r.blank()
    if not report.entries:
        r.write.good("nothing to clean")
    for entry in report.entries:
        kind = "dir " if entry.is_dir else "file"
        r.write.kv(f"  [{kind}] {entry.path}", f"{entry.size_bytes:,} bytes")
    if report.skipped_tracked:
        r.blank()
        r.write.warn("git-tracked matches skipped (never removed):")
        for path in report.skipped_tracked:
            r.write.kv("  skipped", str(path))
    r.blank()
    r.line(
        f"{verb} {report.count} artifact(s), {report.reclaimed_bytes:,} bytes reclaimed"
    )


# frob:ticket T-0457
# frob:ticket T-0563
# frob:ticket T-0875
# frob:doc docs/modules/clean.md#public-api
# frob:tests tests/unit/test_app_runners_t0875_leaf_collision.py::TestCleanRunnerRun.test_dry_run_reports_nothing_to_clean kind="unit"  # noqa: E501
def run(cfg: AppConfig) -> None:
    """`frob clean`: tiered, artifact-only workspace cleanup. Defaults to a
    dry-run preview (`--dry-run` is implicit); pass `-y`/`--yes` to execute."""
    from pathlib import Path

    from frob.clean import clean

    root = (cfg.clean_path or Path(".")).resolve()
    tier = _resolve_tier(cfg)

    result = clean(root, tier, dry_run=not cfg.clean_yes)
    if result.is_err:
        _log.error("frob clean: %s", result.danger_err)
        sys.exit(1)
    report = result.danger_ok

    if cfg.clean_json:
        _log.info(report.model_dump_json(indent=2))
        return

    r = Renderer.for_stream(
        sys.stdout, color_flag=cfg.color, no_color_flag=cfg.no_color
    )
    _print_report(r, report, executed=cfg.clean_yes)
    if not cfg.clean_yes and report.entries:
        r.blank()
        r.line("dry-run only -- pass -y/--yes to actually remove these")
