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
    from frob.gates._fmt_directives import format_paths, read_line_length

    # T-2492: pre-existing bug, fixed incidentally because `ty` (correctly)
    # refuses this ticket's land on it otherwise -- `and` always discarded
    # a real `cfg.fmt_path` (returning the literal `Path(".")` instead) and
    # crashed on `.resolve()` when `cfg.fmt_path` was `None`; `or` is the
    # intended "explicit path, else cwd" fallback every sibling runner uses.
    root = (cfg.fmt_path or Path(".")).resolve()
    project_root = root if root.is_dir() else root.parent
    guard_ctx = (
        _guard_json_stdout_writes() if cfg.fmt_json else contextlib.nullcontext()
    )
    # T-2492: `read_line_length`'s own DEBUG log (an unreadable/missing
    # pyproject.toml) landed unguarded on stdout ahead of a `--json`
    # payload -- confirmed by execution once the `cfg.fmt_path or Path(".")`
    # fix above started honoring a real `fmt_path` again. Moved inside the
    # same guarded span as `format_paths`.
    with guard_ctx:
        limit = read_line_length(project_root)
        report = format_paths(
            root,
            check_only=cfg.fmt_check,
            limit=limit,
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
