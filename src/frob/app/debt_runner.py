"""CLI wiring for `frob debt` (T-0412): list outstanding `frob:debt` entries.

`frob:debt` is the TEMPORARY, ticket-bound counterpart to `frob:waive`'s
PERMANENT exception -- this command is the honest "what is owed right now"
listing `docs/guides/extending/comment-dsl-directives.md` and
`docs/modules/gates.md#debt-gate-t-0412` describe: rule, site, owning
ticket, expiry, and whether it has already expired. It never mutates
anything (no `--apply`, unlike `frob ticket reconcile`) -- resolving a debt
means fixing the underlying gap and removing the directive, not running a
command over it.
"""

from __future__ import annotations

import contextlib
import sys
import tomllib
from datetime import date
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"


def _current_version(root: Path) -> str:
    """`[project].version` from `root`'s `pyproject.toml`, or `"0.0.0"` if
    unresolvable -- mirrors `frob.gates`' own `_current_version` degrade so
    a repo with no declared version still gets the date-based expiry check."""
    toml_path = root / "pyproject.toml"
    if not toml_path.exists():
        return "0.0.0"
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return "0.0.0"
    version = data.get("project", {}).get("version")
    return version if isinstance(version, str) else "0.0.0"


def _load_snapshot(root: Path):  # noqa: ANN201
    """Load (building if stale) the graph snapshot `debt` lists entries from."""
    from frob.graph import build_graph, load_graph

    cache = root / _CACHE_REL
    loaded = load_graph(cache)
    if loaded.is_ok:
        return loaded.danger_ok
    built = build_graph(root, cache)
    if built.is_err:
        _log.error("debt: graph build failed: %s", built.danger_err)
        sys.exit(1)
    return built.danger_ok


# frob:ticket T-0563
# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    """List every outstanding `frob:debt` entry under `cfg.debt_path`."""
    from frob.gates import list_debt
    from frob.logging import quiet_stdout_logs

    root = (cfg.debt_path or Path(".")).resolve()
    # T-0563: `--json` wraps snapshot-loading in `quiet_stdout_logs`,
    # matching `frob map`/`frob dup` -- the graph-build INFO/DEBUG chatter
    # must not land ahead of the JSON payload on the same stdout-bound
    # `_log.info` channel now that both go through the logger.
    ctx = quiet_stdout_logs() if cfg.debt_json else contextlib.nullcontext()
    with ctx:
        snapshot = _load_snapshot(root)
        entries = list_debt(
            snapshot,
            current_date=date.today().isoformat(),
            current_version=_current_version(root),
        )

    if cfg.debt_json:
        import json

        _log.info(
            json.dumps([e.model_dump() for e in entries], indent=2, sort_keys=True)
        )
        return

    if not entries:
        _log.info("debt: no outstanding frob:debt entries")
        return

    for entry in sorted(entries, key=lambda e: (e.expired is False, e.rule, e.site)):
        flag = "EXPIRED" if entry.expired else "open"
        until = entry.until or "(no expiry)"
        _log.info(
            "debt: [%s] %s at %s -- ticket=%s until=%s",
            flag,
            entry.rule,
            entry.site,
            entry.ticket,
            until,
        )
