"""frob.clean -- tiered, artifact-only workspace cleanup (T-0457).

See docs/modules/clean.md for the full design.

Three strictly artifact-only tiers -- never source, never a tracked file --
each a superset of the one before:

* `CleanTier.SAFE` (`frob clean`): fragments that are DEFINITELY never
  reused -- `.coverage.<host>.<pid>.*` parallel-run fragments, `__pycache__`
  directories, `.pytest_cache`, stray `.playwright-mcp` session dumps. Safe
  enough to wire as a post-step of routine make targets.
* `CleanTier.ALL` (`frob clean --all`): tier 1 plus rebuildable build/test/
  lint artifacts (`build/`, `dist/`, `*.egg-info/`, `target/` under each
  crate dir, `cmake-build-*/`, `.ruff_cache`, `.mypy_cache`, `htmlcov/`,
  `coverage.xml`, the combined `.coverage`).
* `CleanTier.DEEP` (`frob clean --deep`): tier 2 plus frob's own `.frob/`
  state (graph cache, prework, journal, collection caches) and
  `FROBLEMS.md` -- the "reset to a clean checkout" button.

Fail-safe by construction: every removal candidate must match a KNOWN
allowlist pattern (`_rules.tier_patterns`, extensible per-project via
`frob.toml`'s `[clean]` table) AND must not be `git`-tracked. A file that is
untracked but matches no allowlist pattern is never a candidate in the
first place -- `scan` only ever walks the allowlist, it never enumerates
"everything untracked" and then filters.
"""

from __future__ import annotations

from frob.clean._core import clean, scan
from frob.clean._models import ArtifactEntry, CleanError, CleanReport, CleanTier
from frob.clean._rules import extra_patterns_from_config, tier_patterns

__all__ = [
    "ArtifactEntry",
    "CleanError",
    "CleanReport",
    "CleanTier",
    "clean",
    "extra_patterns_from_config",
    "scan",
    "tier_patterns",
]
