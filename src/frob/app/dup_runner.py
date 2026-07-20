from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.dup import find_duplicates
from frob.logging import get_logger

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"

# AppConfig fields used by this runner (add to AppConfig when wiring CLI):
#   dup_path: Path | None      -- directory to scan (required)
#   dup_min_lines: int         -- minimum function body size (default 6)
#   dup_json: bool             -- emit JSON instead of human-readable text


# frob:ticket T-0041
# frob:ticket T-0192
def _probe(cfg: AppConfig, dup_path: Path) -> None:
    """`frob dup --probe A B`: R6 observational-equivalence of two symbols.

    WARNING (see docs/modules/dup.md's probe safety/workload contract):
    resolving each symref loads its whole source FILE via
    `importlib.util.spec_from_file_location` + `exec_module`, which runs
    every top-level statement in that file, not just the probed function
    -- there is no sandbox. Only point this at trees you already trust.
    """
    from frob.dup import probe_equivalence
    from frob.graph import build_graph, load_graph

    a, b = cfg.dup_probe[0], cfg.dup_probe[1]
    root = dup_path if dup_path.is_dir() else dup_path.parent
    cache = root / _CACHE_REL
    loaded = load_graph(cache)
    snapshot = (loaded if loaded.is_ok else build_graph(root, cache)).danger_ok
    result = probe_equivalence(a, b, snapshot, budget_s=30.0)
    if result.is_err:
        _log.error("probe %s <-> %s: %s", a, b, result.danger_err)
        sys.exit(1)
    verdict = result.danger_ok
    print(f"probe {a} <-> {b}: {'EQUIVALENT' if verdict.equivalent else 'DIFFER'}")
    sys.exit(0 if verdict.equivalent else 1)


# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    dup_path: Path | None = getattr(cfg, "dup_path", None)
    if dup_path is None:
        _log.error("frob dup requires <path>")
        sys.exit(1)

    if cfg.dup_probe:
        if len(cfg.dup_probe) != 2:
            _log.error("frob dup --probe needs exactly two symrefs")
            sys.exit(1)
        _probe(cfg, dup_path)
        return

    if not dup_path.exists():
        _log.error("path does not exist: %s", dup_path)
        sys.exit(1)

    min_lines: int = getattr(cfg, "dup_min_lines", 6) or 6
    dup_json: bool = getattr(cfg, "dup_json", False)

    result = find_duplicates(dup_path, min_lines=min_lines)

    if dup_json:
        _log.info("%s", result.as_json())
    else:
        _log.info("%s", result.as_text())
