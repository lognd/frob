"""Aggregated top-package lists per ecosystem, used by the typosquat distance
check (docs/modules/vet.md VET-JS003 generalized). The per-ecosystem data lives in
`_popular_pypi`/`_popular_npm`/`_popular_cargo` submodules to keep each file
under the large-file threshold; this module just re-exports and indexes them.
0.2.x note: refresh via a `--sync-advisories`-style command instead of hand-
maintaining these lists.
"""

from __future__ import annotations

from frob.vet._popular_cargo import CARGO_TOP
from frob.vet._popular_npm import NPM_TOP
from frob.vet._popular_pypi import PYPI_TOP

# frob:doc docs/modules/vet.md#public-api
ECOSYSTEM_POPULAR = {
    "pypi": PYPI_TOP,
    "npm": NPM_TOP,
    "cargo": CARGO_TOP,
}

__all__ = ["CARGO_TOP", "ECOSYSTEM_POPULAR", "NPM_TOP", "PYPI_TOP"]
