"""CLI wiring for `frob clean [--all|--deep] [-y]` (T-0457, docs/modules/clean.md)."""

from __future__ import annotations

import contextlib
import sys

from frob.app._json_guard import _guard_json_stdout_writes
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
# frob:ticket T-2492
# frob:ticket T-4437
def _print_disposable_sweep_report(r: Renderer, report, executed: bool) -> None:  # noqa: ANN001
    """Render a `DisposableSweepReport` (T-4437): one line per dead
    scratch dir (removed, or would-remove under a dry run) plus every
    live one it left alone and why."""
    verb = "removed" if executed else "would remove"
    r.write.heading("frob clean --sweep-disposable-worktrees")
    r.blank()
    if not report.removed and not report.kept:
        r.write.good("no leaked disposable worktrees found")
        return
    for entry in report.removed:
        r.write.kv(f"  [{verb}] {entry.scratch}", entry.reason)
    for entry in report.kept:
        r.write.kv(f"  [kept] {entry.scratch}", entry.reason)
    r.blank()
    r.line(f"{verb} {len(report.removed)} disposable worktree(s)")


def _run_sweep_disposable_worktrees(cfg: AppConfig) -> None:
    """`frob clean --sweep-disposable-worktrees` (T-4437): remove leaked
    BUG002-repro/land-squash `git worktree add` scratch dirs whose
    creator process is dead. Split out of `run` so the ordinary tiered-
    artifact path below stays exactly as it read before this ticket."""
    from pathlib import Path

    from frob.worktrees._disposable_sweep import sweep_disposable_worktrees

    root = (cfg.clean_path or Path(".")).resolve()
    report = sweep_disposable_worktrees(root, execute=cfg.clean_yes)

    if cfg.clean_json:
        _log.info(report.model_dump_json(indent=2))
        return

    r = Renderer.for_stream(
        sys.stdout, color_flag=cfg.color, no_color_flag=cfg.no_color
    )
    _print_disposable_sweep_report(r, report, executed=cfg.clean_yes)
    if not cfg.clean_yes and report.removed:
        r.blank()
        r.line("dry-run only -- pass -y/--yes to actually remove these")


def run(cfg: AppConfig) -> None:
    """`frob clean`: tiered, artifact-only workspace cleanup. Defaults to a
    dry-run preview (`--dry-run` is implicit); pass `-y`/`--yes` to execute.
    T-2492: `clean`'s own `gitio` DEBUG logging landed unguarded on stdout
    ahead of a `--json` payload (confirmed by execution -- corrupted the
    JSON), so the scan now runs under `_guard_json_stdout_writes()` when
    `--json` is set, matching `frob check`'s T-2486 precedent.

    T-4437: `--sweep-disposable-worktrees` is a DISTINCT sweep (leaked
    BUG002-repro/land-squash `git worktree add` scratch dirs) from the
    tiered artifact cleanup below, dispatched first and returning early --
    it shares this verb's `-y`/`--yes`/`--json` flags rather than
    duplicating them onto a new subcommand."""
    from pathlib import Path

    from frob.clean import clean

    if cfg.clean_sweep_worktrees:
        _run_sweep_disposable_worktrees(cfg)
        return

    root = (cfg.clean_path or Path(".")).resolve()
    tier = _resolve_tier(cfg)

    guard_ctx = (
        _guard_json_stdout_writes() if cfg.clean_json else contextlib.nullcontext()
    )
    with guard_ctx:
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
