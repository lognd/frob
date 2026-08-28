"""The artifact allowlist `frob.clean` walks (T-0457, docs/modules/clean.md).

Every pattern here is a `pathlib.Path.glob`-style pattern (relative to the
scan root, `**` allowed) naming things we KNOW are regenerable build/test
artifacts, not a blanket "everything gitignored" or "everything untracked"
sweep -- `frob.clean._core.scan` never enumerates untracked files and then
filters, it only ever walks these patterns.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from frob.clean._models import CleanTier
from frob.logging import get_logger

_log = get_logger(__name__)


_TIER1_PATTERNS: tuple[str, ...] = (
    # .coverage.<host>.<pid>.<random> parallel-run fragments (T-0464's
    # COVERAGE_PROCESS_START setup); the bare `.coverage` combined file is
    # tier 2 -- it is the thing `coverage combine` produces FROM these
    # fragments, not itself a throwaway fragment.
    ".coverage.*",
    "**/__pycache__",
    "**/*.pyc",
    ".pytest_cache",
    "**/.pytest_cache",
    ".playwright-mcp",
    "**/.playwright-mcp",
)

_TIER2_PATTERNS: tuple[str, ...] = (
    "build",
    "dist",
    "*.egg-info",
    "*/target",
    "cmake-build-*",
    "**/CMakeFiles",
    "**/CMakeCache.txt",
    ".ruff_cache",
    ".mypy_cache",
    "htmlcov",
    "coverage.xml",
    ".coverage",
)

_TIER3_PATTERNS: tuple[str, ...] = (
    ".frob",
    "FROBLEMS.md",
)

# frob:ticket T-3220
#: Paths (relative to the scan root) that `_TIER3_PATTERNS`' wholesale
#: `.frob` match must never carry into `clean`'s actual removal, even
#: though the glob itself matches the whole directory. T-2997 moved
#: `rapid-debt.jsonl` (a durable RECORD -- the T-1681 rapid-profile debt
#: ledger, not a regenerable measurement cache) from the tracked repo
#: root into `.frob/` specifically because `.frob/` used to be entirely
#: disposable per-checkout scratch state; `frob clean --deep` still
#: `shutil.rmtree`s that whole directory unconditionally, which now
#: means "regenerate `.frob/`'s caches" also silently destroys the one
#: piece of `.frob/` content that is NOT regenerable -- a real data-loss
#: mode T-2997's own acceptance bar ("do not silently discard it")
#: explicitly warned against. `frob.clean._core._protect_excluded_paths`
#: is what actually keeps this out of a DEEP clean's removal set; this
#: tuple is the single place that decides WHAT is protected.
# frob:doc docs/modules/clean.md#deep-clean-protects-rapid-debtjsonl-t-3220
TIER3_PROTECTED_PATHS: tuple[str, ...] = (".frob/rapid-debt.jsonl",)


# frob:doc docs/modules/clean.md#tiers
# frob:tests tests/test_clean.py::test_tier_patterns_cumulative
def tier_patterns(tier: CleanTier) -> tuple[str, ...]:
    """The full glob-pattern allowlist for `tier`, cumulative -- DEEP includes
    everything ALL includes, which includes everything SAFE includes."""
    patterns = list(_TIER1_PATTERNS)
    if tier >= CleanTier.ALL:
        patterns += _TIER2_PATTERNS
    if tier >= CleanTier.DEEP:
        patterns += _TIER3_PATTERNS
    return tuple(patterns)


# frob:doc docs/modules/clean.md#public-api
# frob:tests tests/test_clean.py::test_extra_patterns_from_config
# frob:tests tests/test_clean.py::test_extra_patterns_missing_toml
def extra_patterns_from_config(root: Path) -> tuple[str, ...]:
    """Project-specific extra allowlist patterns from `root/frob.toml`'s
    `[clean]` table (`extra_patterns = [...]`), same degrade-gracefully
    posture as `frob.app.config.load_arch_config`: a missing/malformed
    `frob.toml` or `[clean]` table is not an error, it just means "no
    extra patterns"."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return ()
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
        extra = data.get("clean", {}).get("extra_patterns", [])
        return tuple(str(p) for p in extra)
    except (OSError, tomllib.TOMLDecodeError, ValueError, TypeError) as exc:
        _log.warning("clean: frob.toml [clean] unreadable, ignoring: %s", exc)
        return ()
