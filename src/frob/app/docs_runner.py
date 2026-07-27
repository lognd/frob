from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.docs import extract_docstrings, find_docs_dir, overview, search
from frob.excludes import iter_files
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:deprecated 2026-07-23 sunset="2026-10-01" ticket="T-0802" reason="zero organic use; navigation owned by Serena/native tools"  # noqa: E501
def _run_search(cfg: AppConfig, path: Path) -> None:
    """Handle `frob docs --search`: print heading/excerpt matches or JSON.
    T-0580: DEPRECATED, sunset 2026-10-01 -- navigation is owned by
    Serena/native tools in agentic use; zero organic invocation observed."""
    _log.warning(
        "frob docs --search is deprecated, sunset 2026-10-01, use "
        "Serena/native navigation; see T-0580"
    )
    docs_dir = find_docs_dir(path)
    if not docs_dir:
        _log.error("error: no docs/ directory found")
        sys.exit(1)
    matches = search(cfg.docs_search or "", docs_dir)
    if cfg.docs_json:
        import json

        _log.info(json.dumps([m.model_dump() for m in matches], indent=2))
        return
    if not matches:
        _log.info("no matches found")
    for m in matches:
        _log.info(f"{m.file}:{m.line}  [{m.heading}]")
        _log.info(f"  {m.excerpt}")


def _run_overview(cfg: AppConfig, path: Path) -> None:
    """Handle `frob docs --overview`: print per-heading summaries or JSON."""
    docs_dir = find_docs_dir(path)
    if not docs_dir:
        _log.info("no docs/ directory found")
        return
    entries = overview(path, cfg.docs_symbol)
    if cfg.docs_json:
        import json

        _log.info(json.dumps([e.model_dump() for e in entries], indent=2))
        return
    for e in entries:
        _log.info(f"## {e.heading}  ({e.file}:{e.line})")
        if e.summary:
            _log.info(f"   {e.summary}")


def _collect_docstrings(path: Path, symbol: str | None) -> list:
    """Docstrings for a single file, or every `.py` file under a directory."""
    if not path.is_dir():
        return extract_docstrings(path, symbol)
    results: list = []
    for f in iter_files(path, suffix=".py"):
        results.extend(extract_docstrings(f, symbol))
    return results


def _run_extract(cfg: AppConfig, path: Path) -> None:
    """Handle bare `frob docs <path>`: print extracted docstrings or JSON."""
    results = _collect_docstrings(path, cfg.docs_symbol)
    if cfg.docs_json:
        import json

        _log.info(json.dumps([d.model_dump() for d in results], indent=2))
        return
    if not results:
        _log.info("no docstrings found")
        return
    for d in results:
        _log.info(f"[L{d.line}] {d.symbol} ({d.kind})")
        for line in d.text.splitlines():
            _log.info(f"  {line}")
        _log.info("")


# frob:ticket T-1011
# frob:tests tests/unit/test_app_runners_batch5.py::TestDocsRunner.test_sync_commands_writes  # noqa: E501
def _run_sync_commands(cfg: AppConfig) -> None:
    """Handle `frob docs --sync-commands` (T-1011): regenerate
    `docs/modules/cli.md`'s generated command-table block from the live
    argparse registry via `frob.gates._docblocks.sync_cli_command_table`
    -- the write half of DOC005's freshness check
    (`_doc005_cli_table_freshness_violations`)."""
    from frob.gates._docblocks import sync_cli_command_table

    root = (cfg.docs_path or Path(".")).resolve()
    wrote = sync_cli_command_table(root)
    if not wrote:
        _log.warning(
            "docs sync-commands: nothing synced at %s -- no "
            "[[docblocks.commands]] source configured, or docs/modules/"
            "cli.md has no generated-block markers to replace",
            root,
        )
        return
    _log.info("docs sync-commands: docs/modules/cli.md's generated block synced")


# frob:doc docs/modules/app.md#runners
# frob:ticket T-0588
# frob:tests tests/unit/test_app_runners_batch5.py::TestDocsRunner.test_search_json_mode
def run(cfg: AppConfig) -> None:
    if cfg.docs_sync_commands:
        _run_sync_commands(cfg)
        return

    path = cfg.docs_path
    if path is None:
        _log.error("frob docs requires <path>")
        sys.exit(1)
    if not path.exists():
        _log.error(f"error: {path} does not exist")
        sys.exit(1)

    if cfg.docs_search:
        _run_search(cfg, path)
    elif cfg.docs_overview:
        _run_overview(cfg, path)
    else:
        _run_extract(cfg, path)
