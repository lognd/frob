"""CLI wiring for `frob fmt [path] [--check] [--json]` (T-0441,
docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441)."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.render import Renderer

_log = get_logger(__name__)


# frob:ticket T-0441
# frob:ticket T-0875
# frob:doc docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441
# frob:tests tests/unit/test_app_runners_t0875_leaf_collision.py::TestFmtRunnerRun.test_check_mode_reports_all_canonical_on_empty_tree kind="unit"  # noqa: E501
def run(cfg: AppConfig) -> None:
    """`frob fmt`: canonicalize every `frob:` directive comment under
    `cfg.fmt_path` to the fewest physical lines that stay within the
    project's line-length limit. `--check` previews without writing and
    exits 1 if anything is non-canonical (CI-friendly); the default writes
    changes in place."""
    from frob.gates._fmt_directives import format_paths, read_line_length

    root = (cfg.fmt_path or Path(".")).resolve()
    project_root = root if root.is_dir() else root.parent
    limit = read_line_length(project_root)

    report = format_paths(root, check_only=cfg.fmt_check, limit=limit)

    if cfg.fmt_json:
        _log.info(report.model_dump_json(indent=2))
    else:
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

    if cfg.fmt_check and report.changes:
        sys.exit(1)
