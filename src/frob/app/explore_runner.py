from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/app.md#runners
# frob:ticket T-1238
# frob:tests tests/unit/test_app_runners.py::TestExploreRunner.test_map_subcommand_delegates_to_map_runner  # noqa: E501
# frob:tests tests/unit/test_app_runners.py::TestExploreRunner.test_outline_subcommand_delegates_to_outline_runner  # noqa: E501
# frob:tests tests/unit/test_app_runners.py::TestExploreRunner.test_xref_subcommand_missing_symbol_exits_1  # noqa: E501
# frob:tests tests/unit/test_app_runners.py::TestExploreRunner.test_docs_search_subcommand_missing_path_exits_1  # noqa: E501
# frob:tests tests/unit/test_app_runners.py::TestExploreRunner.test_unknown_subcommand_exits_1  # noqa: E501
def run(cfg: AppConfig) -> None:
    """`frob explore <map|outline|xref|docs-search>`: the T-1238 verb-group
    front door onto the navigation porcelain -- delegates straight into the
    existing per-command runner logic (same `AppConfig` dests each
    subcommand's parser populates), so behavior is identical to invoking
    the standalone top-level command directly."""
    if cfg.explore_command == "map":
        from frob.app.map_runner import run as map_run

        map_run(cfg)
    elif cfg.explore_command == "outline":
        from frob.app.outline_runner import run as outline_run

        outline_run(cfg)
    elif cfg.explore_command == "xref":
        from frob.app.xref_runner import run as xref_run

        xref_run(cfg)
    elif cfg.explore_command == "docs-search":
        _run_docs_search(cfg)
    else:
        _log.error(
            "frob explore requires a subcommand: map, outline, xref, or "
            "docs-search"
        )
        sys.exit(1)


# frob:ticket T-1238
def _run_docs_search(cfg: AppConfig) -> None:
    """`frob explore docs-search <path> <query>`: same lookup as `frob docs
    --search`, reusing `docs_runner._run_search` directly (T-1238) instead
    of duplicating its docs/ directory resolution and match-printing
    logic -- `_run_search` itself reports "no docs/ directory found"."""
    from frob.app.docs_runner import _run_search

    path = cfg.docs_path
    if path is None:
        _log.error("frob explore docs-search requires <path> <query>")
        sys.exit(1)
    if not path.exists():
        _log.error(f"error: {path} does not exist")
        sys.exit(1)
    _run_search(cfg, path)
