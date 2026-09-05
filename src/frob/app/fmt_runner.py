"""CLI wiring for `frob fmt [path ...] [--check] [--json]` (T-0441,
docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441).

T-3906: `frob fmt` is now a DEPRECATED alias for `frob format --directives`
-- the two verbs were the same word for two different operations (`fmt`
canonicalized `frob:` directive comments, `format` ran ruff over Python
source), distinguishable only by reading the source. `run` below still does
the real work (unchanged behavior, T-3312's list-of-paths included) so every
existing `frob fmt` invocation -- CI, scripts, remedy strings -- keeps
working through the sunset window; it just also prints a deprecation notice
first."""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path

from frob.app._json_guard import _guard_json_stdout_writes
from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.render import Renderer

_log = get_logger(__name__)


# frob:ticket T-2492
# frob:ticket T-2761
# frob:ticket T-3906
# frob:deprecated 0.1.0 sunset="2026-12-01" ticket="T-3911" reason="T-3906: frob fmt \
# and frob format were the same word for two different operations, only one of which \
# had --check; consolidated under frob format --code/--directives (default both), fmt \
# kept as this working alias through the sunset window"
# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    """`frob fmt` (DEPRECATED, T-3906: use `frob format --directives`):
    canonicalize every `frob:` directive comment under each of
    `cfg.fmt_paths` (T-3312: a list, not one path) to the fewest physical
    lines that stay within the project's line-length limit. `--check`
    previews without writing and exits 1 if anything is non-canonical
    (CI-friendly); the default writes changes in place. T-2492:
    `format_paths`'s own `gitio`/file-walk DEBUG logging landed unguarded
    on stdout ahead of a `--json` payload (confirmed by execution --
    corrupted the JSON), so the scan now runs under
    `_guard_json_stdout_writes()` when `--json` is set, matching `frob
    check`'s T-2486 precedent."""
    from frob.gates._fmt_directives import FmtChange, FmtReport, format_paths

    # T-2492 precedent applied here too: the deprecation notice must go to
    # STDERR unconditionally, never stdout -- with `--json` set, stdout is
    # the JSON payload itself, and a leading human-readable line would
    # corrupt it exactly like the bug `_guard_json_stdout_writes()` below
    # was built to catch.
    Renderer.for_stream(
        sys.stderr, color_flag=cfg.color, no_color_flag=cfg.no_color
    ).write.warn(
        "frob fmt is DEPRECATED (T-3906, sunset 2026-12-01) -- use "
        "`frob format --directives` instead"
    )

    # T-2492: pre-existing bug, fixed incidentally because `ty` (correctly)
    # refuses this ticket's land on it otherwise -- `and` always discarded
    # a real `cfg.fmt_path` (returning the literal `Path(".")` instead) and
    # crashed on `.resolve()` when `cfg.fmt_path` was `None`; `or` is the
    # intended "explicit path, else cwd" fallback every sibling runner uses.
    paths = [Path(p) for p in (cfg.fmt_paths or ["."])]
    guard_ctx = (
        _guard_json_stdout_writes() if cfg.fmt_json else contextlib.nullcontext()
    )
    # T-2761: no `limit=` override here any more -- `format_paths`'s own
    # default (`None`) lets EACH FILE resolve its own width via T-1606's
    # `resolve_line_length` (rustfmt.toml/prettier config/.clang-format,
    # nearest-config-wins), instead of pre-resolving one ruff-derived
    # number via `read_line_length` and forcing every language to wrap
    # against it. That pre-resolution was exactly what made T-1606's
    # per-language resolver unreachable through the real `frob fmt`
    # entrypoint.
    all_changes: list[FmtChange] = []
    with guard_ctx:
        for path in paths:
            change_report = format_paths(
                path.resolve(),
                check_only=cfg.fmt_check,
                include_test_corpora=cfg.fmt_include_test_corpora,
            )
            all_changes.extend(change_report.changes)
    report = FmtReport(changes=tuple(all_changes))
    _render_fmt_report(cfg, report)
    if cfg.fmt_check and report.changes:
        sys.exit(1)


# frob:ticket T-3906
def _render_fmt_report(cfg: AppConfig, report) -> None:  # noqa: ANN001
    """The human/JSON `frob fmt` report, split out of `run` (T-3906,
    ARCH001) -- same JSON-vs-human branch `run` always had, unchanged."""
    if cfg.fmt_json:
        _log.info(report.model_dump_json(indent=2))
        return
    r = Renderer.for_stream(
        sys.stdout, color_flag=cfg.color, no_color_flag=cfg.no_color
    )
    r.write.heading("frob fmt")
    r.blank()
    if not report.changes:
        r.write.good("all frob: directive lines already canonical")
    for change in report.changes:
        verb = "would rewrite" if cfg.fmt_check else "rewrote"
        r.write.kv(f"  {verb}", change.path)
    r.blank()
    verb = "would change" if cfg.fmt_check else "changed"
    r.line(f"{len(report.changes)} file(s) {verb}")
