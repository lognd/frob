from __future__ import annotations

import os
import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:ticket T-5201
def _stamp_read_only_parse_artifact_cache_env() -> None:
    """Stamp `frob.lang.PARSE_ARTIFACT_CACHE_ENV` for THIS single process
    (T-5201), read-only: `frob.lang._parse_file_with_artifact_cache` is a
    transparent uncached passthrough whenever the env var is unset --
    which is every single-process command including `frob explore`, so
    1643 uncached parses were measured on `frob explore xref` alone
    (found while working T-5135).

    Deliberately does NOT call `_stamp_worker_parse_artifact_cache_env`
    (`frob.gates`'s own gate-worker stamp): that helper also CREATES/
    migrates the db via `frob.graph.cache.connect(...).close()` before
    stamping, because a `ProcessPoolExecutor` gate run legitimately wants
    a fresh, populated cache. `frob explore` is a single, short-lived,
    read-oriented process with no sibling workers to share a freshly
    built cache with -- creating one here would just leave an empty db
    file behind on a repo that has never run `frob check`. Only stamps
    the env var (making `_artifact_cache_connection` open it) when the
    `.frob/parse-artifacts.db` file ALREADY exists -- i.e. a previous
    `frob check`/`frob land` already built and populated it -- so explore
    opportunistically reuses that cache and never writes to a repo that
    has none. Root is resolved the same explicit-path-then-`FROB_ROOT`-
    then-cwd precedence `frob.app.config._pyproject_file_for_args` uses
    (T-4502), since `AppConfig` carries no single unified `root` field
    for `run()` to read directly here."""
    from frob.lang import PARSE_ARTIFACT_CACHE_ENV

    # frob:waive SEC110 reason="FROB_ROOT is a worktree-root path marker (T-4502), not a secret -- same posture as _pyproject_file_for_args's existing waiver"  # noqa: E501
    root = Path(os.environ.get("FROB_ROOT") or ".")
    cache_path = (root / ".frob" / "parse-artifacts.db").resolve()
    if not cache_path.is_file():
        return
    # frob:waive SEC110 reason="a resolved .frob/parse-artifacts.db filesystem path, not a secret -- same posture as frob.lang._artifact_cache_connection's own waiver"  # noqa: E501
    os.environ[PARSE_ARTIFACT_CACHE_ENV] = str(cache_path)


# frob:doc docs/modules/app.md#runners
# frob:ticket T-1238
# frob:tests tests/unit/test_app_runners.py::TestExploreRunner.test_map_subcommand_delegates_to_map_runner  # noqa: E501
# frob:tests tests/unit/test_app_runners.py::TestExploreRunner.test_outline_subcommand_delegates_to_outline_runner  # noqa: E501
# frob:tests tests/unit/test_app_runners.py::TestExploreRunner.test_xref_subcommand_missing_symbol_exits_1  # noqa: E501
# frob:tests tests/unit/test_app_runners.py::TestExploreRunner.test_docs_search_subcommand_missing_path_exits_1  # noqa: E501
# frob:tests tests/unit/test_app_runners.py::TestExploreRunner.test_unknown_subcommand_exits_1  # noqa: E501
# frob:tests tests/unit/test_explore_runner_parse_artifact_cache.py::TestStampReadOnlyParseArtifactCacheEnv.test_stamps_env_when_cache_db_exists  # noqa: E501
def run(cfg: AppConfig) -> None:
    """`frob explore <map|outline|xref|docs-search>`: the T-1238 verb-group
    front door onto the navigation porcelain -- delegates straight into the
    existing per-command runner logic (same `AppConfig` dests each
    subcommand's parser populates), so behavior is identical to invoking
    the standalone top-level command directly.

    T-5201: stamps the parse-artifact cache read-only
    (`_stamp_read_only_parse_artifact_cache_env`) before dispatching to
    any subcommand, so a repo with an already-populated
    `.frob/parse-artifacts.db` (from a prior `frob check`) gets its
    parses served from cache instead of every subcommand's own
    `frob.lang.parse_file` call re-parsing from scratch."""
    _stamp_read_only_parse_artifact_cache_env()
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
    elif cfg.explore_command == "gitlog":
        from frob.app.gitlog_runner import run as gitlog_run

        gitlog_run(cfg)
    elif cfg.explore_command == "stats":
        from frob.app.stats_runner import run as stats_run

        stats_run(cfg)
    elif cfg.explore_command in ("graph-query", "graph-why", "graph-affects"):
        _run_graph_leaf(cfg)
    elif cfg.explore_command == "debt":
        from frob.app.debt_runner import run as debt_run

        debt_run(cfg)
    elif cfg.explore_command == "deprecated":
        from frob.app.deprecated_runner import run as deprecated_run

        deprecated_run(cfg)
    else:
        _log.error(
            "frob explore requires a subcommand: map, outline, xref, docs-search, "
            "gitlog, stats, graph-query, graph-why, graph-affects, debt, or deprecated"
        )
        sys.exit(1)


# frob:ticket T-4695
def _run_graph_leaf(cfg: AppConfig) -> None:
    """`frob explore graph-query|graph-why|graph-affects` (T-4695): the
    read-only third of `frob graph`'s four subverbs, reached here under
    their hyphenated `explore` spelling -- `graph_runner.run` itself
    still dispatches by `cfg.graph_command` (`query`/`why`/`affects`,
    the SAME dest `frob graph`'s own subparser already populates), so
    this just maps `explore_command`'s hyphenated leaf name back onto
    that dest before delegating; `build` (the write side) has no
    `explore` leaf and is unreachable from here, per the ticket's own
    "graph's non-read-only half stays on flat frob graph" instruction."""
    from frob.app.graph_runner import run as graph_run

    assert cfg.explore_command is not None  # guarded by run()'s caller check
    cfg.graph_command = cfg.explore_command.removeprefix("graph-")
    graph_run(cfg)


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
