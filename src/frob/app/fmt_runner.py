"""CLI wiring for `frob fmt [path] [--check] [--json]` (T-0441,
docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441)."""

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
# frob:doc docs/modules/app.md#runners
# frob:waive AFFECT001 reason="T-2492: docs/modules/app.md#runners one-line summary is \
# still accurate -- this change only adds an internal --json stdout-corruption guard, \
# no user-visible contract change; filed T-2491 to sync the doc note once its own \
# lease clears, same precedent as T-2486"
def run(cfg: AppConfig) -> None:
    """`frob fmt`: canonicalize every `frob:` directive comment under
    `cfg.fmt_path` to the fewest physical lines that stay within the
    project's line-length limit. `--check` previews without writing and
    exits 1 if anything is non-canonical (CI-friendly); the default writes
    changes in place. T-2492: `format_paths`'s own `gitio`/file-walk
    DEBUG logging landed unguarded on stdout ahead of a `--json` payload
    (confirmed by execution -- corrupted the JSON), so the scan now runs
    under `_guard_json_stdout_writes()` when `--json` is set, matching
    `frob check`'s T-2486 precedent."""
    from frob.gates._fmt_directives import format_paths

    # T-2492: pre-existing bug, fixed incidentally because `ty` (correctly)
    # refuses this ticket's land on it otherwise -- `and` always discarded
    # a real `cfg.fmt_path` (returning the literal `Path(".")` instead) and
    # crashed on `.resolve()` when `cfg.fmt_path` was `None`; `or` is the
    # intended "explicit path, else cwd" fallback every sibling runner uses.
    root = (cfg.fmt_path or Path(".")).resolve()
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
    with guard_ctx:
        report = format_paths(
            root,
            check_only=cfg.fmt_check,
            include_test_corpora=cfg.fmt_include_test_corpora,
        )
    if cfg.fmt_json:
        _log.info(report.model_dump_json(indent=2))
    else:
        r = Renderer.for_stream(
            sys.stdout, color_flag=cfg.color, no_color_flag=cfg.no_color
        )
        r.write.heading('frob fmt')
        r.blank()
        if not report.changes:
            r.write.good('all frob: directive lines already canonical')
        for change in report.changes:
            verb = 'would rewrite' if cfg.fmt_check else 'rewrote'
            r.write.kv(f'  {verb}', change.path)
        r.blank()
        verb = 'would change' if cfg.fmt_check else 'changed'
        r.line(f'{len(report.changes)} file(s) {verb}')
    if cfg.fmt_check and report.changes:
        sys.exit(1)
