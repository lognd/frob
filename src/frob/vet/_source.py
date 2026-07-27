"""Locates a locked dependency's SOURCE in local caches (docs/modules/vet.md
"Mechanics":
"fetch/locate the package source (local caches first: uv/pip cache, cargo
registry cache, node_modules; network fetch only with consent)").

MVP-plus note: this is best-effort local-cache discovery only; no network
fetch is implemented (`--fetch` in the CLI controls the quarantine/typosquat
registry lookups, not source download). A dependency whose source is not
found locally scans with an empty capability set and a "source-unavailable"
signal, never a crash (docs/modules/vet.md "Honest limits").
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/vet/_source.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

# frob:waive TEST005 reason="module line coverage 78.3%, debt T-0160"

from __future__ import annotations

import os
from pathlib import Path

from frob.logging import get_logger

_log = get_logger(__name__)


def _candidate_uv_cache_dirs() -> tuple[Path, ...]:
    """Plausible uv/pip wheel-cache roots, cheapest-first."""
    dirs = []
    # frob:waive SEC110 reason="UV_CACHE_DIR is a local cache dir path, not a secret"
    uv_cache = os.environ.get("UV_CACHE_DIR")
    if uv_cache:
        dirs.append(Path(uv_cache))
    dirs.append(Path.home() / ".cache" / "uv")
    dirs.append(Path.home() / ".cache" / "pip")
    return tuple(dirs)


def _normalize_py_name(name: str) -> str:
    return name.replace("-", "_").lower()


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
# frob:waive TEST005 reason="_locate_pypi_source 73.3% branch cover, debt T-0160"
def _locate_pypi_source(root: Path, name: str, version: str) -> Path | None:
    """A directory containing `name`'s Python source, or `None`.

    Checked in order: any `.venv/lib/*/site-packages/<name>` under `root`,
    then uv/pip wheel-extraction caches under the user's home.
    """
    normalized = _normalize_py_name(name)
    for venv_glob in root.glob(".venv/lib/*/site-packages"):
        for candidate_name in (normalized, name):
            candidate = venv_glob / candidate_name
            if candidate.is_dir():
                _log.debug("vet: located pypi source for %s at %s", name, candidate)
                return candidate
    for cache_root in _candidate_uv_cache_dirs():
        if not cache_root.is_dir():
            continue
        # frob:waive WALK001 reason="uv/pip wheel-extraction cache under the user's home, not the repo tree; frob.excludes' BUILTIN_SKIP_DIRS is irrelevant outside a project checkout"  # noqa: E501
        for hit in cache_root.glob(f"**/{normalized}"):
            if hit.is_dir():
                _log.debug("vet: located pypi source for %s at %s", name, hit)
                return hit
    _log.info("vet: no local source found for pypi/%s@%s", name, version)
    return None


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
def _locate_npm_source(root: Path, name: str) -> Path | None:
    """A directory containing `name`'s JS/TS source under `node_modules/`."""
    candidate = root / "node_modules" / name
    if candidate.is_dir():
        _log.debug("vet: located npm source for %s at %s", name, candidate)
        return candidate
    _log.info("vet: no local node_modules entry for npm/%s", name)
    return None


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
# frob:waive TEST005 reason="_locate_cargo_source 55.6% branch cover, debt T-0160"
def _locate_cargo_source(name: str, version: str) -> Path | None:
    """A directory containing `name`'s Rust source under `~/.cargo/registry/src`."""
    registry_root = Path.home() / ".cargo" / "registry" / "src"
    if not registry_root.is_dir():
        _log.info("vet: no ~/.cargo/registry/src; skipping cargo source lookup")
        return None
    # frob:waive WALK001 reason="~/.cargo/registry/src cache, not the repo tree; single-level glob for a specific name-version, frob.excludes is irrelevant here"  # noqa: E501
    for hit in registry_root.glob(f"*/{name}-{version}"):
        if hit.is_dir():
            _log.debug("vet: located cargo source for %s at %s", name, hit)
            return hit
    _log.info("vet: no local source found for cargo/%s@%s", name, version)
    return None


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
# frob:waive TEST005 reason="_locate_source 71.4% branch cover, debt T-0160"
def _locate_source(root: Path, ecosystem: str, name: str, version: str) -> Path | None:
    """Dispatch to the ecosystem-appropriate local-cache source locator."""
    if ecosystem == "pypi":
        return _locate_pypi_source(root, name, version)
    if ecosystem == "npm":
        return _locate_npm_source(root, name)
    if ecosystem == "cargo":
        return _locate_cargo_source(name, version)
    _log.debug("vet: no source locator for ecosystem=%s", ecosystem)
    return None


__all__ = [
    "_locate_cargo_source",
    "_locate_npm_source",
    "_locate_pypi_source",
    "_locate_source",
]
