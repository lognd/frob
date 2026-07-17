"""Locates a locked dependency's SOURCE in local caches (docs/vet.md "Mechanics":
"fetch/locate the package source (local caches first: uv/pip cache, cargo
registry cache, node_modules; network fetch only with consent)").

MVP-plus note: this is best-effort local-cache discovery only; no network
fetch is implemented (`--fetch` in the CLI controls the quarantine/typosquat
registry lookups, not source download). A dependency whose source is not
found locally scans with an empty capability set and a "source-unavailable"
signal, never a crash (docs/vet.md "Honest limits").
"""

from __future__ import annotations

import os
from pathlib import Path

from frob.logging import get_logger

_log = get_logger(__name__)


def _candidate_uv_cache_dirs() -> tuple[Path, ...]:
    """Plausible uv/pip wheel-cache roots, cheapest-first."""
    dirs = []
    uv_cache = os.environ.get("UV_CACHE_DIR")
    if uv_cache:
        dirs.append(Path(uv_cache))
    dirs.append(Path.home() / ".cache" / "uv")
    dirs.append(Path.home() / ".cache" / "pip")
    return tuple(dirs)


def _normalize_py_name(name: str) -> str:
    return name.replace("-", "_").lower()


# frob:doc docs/vet.md#public-api
def locate_pypi_source(root: Path, name: str, version: str) -> Path | None:
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
        for hit in cache_root.glob(f"**/{normalized}"):
            if hit.is_dir():
                _log.debug("vet: located pypi source for %s at %s", name, hit)
                return hit
    _log.info("vet: no local source found for pypi/%s@%s", name, version)
    return None


# frob:doc docs/vet.md#public-api
def locate_npm_source(root: Path, name: str) -> Path | None:
    """A directory containing `name`'s JS/TS source under `node_modules/`."""
    candidate = root / "node_modules" / name
    if candidate.is_dir():
        _log.debug("vet: located npm source for %s at %s", name, candidate)
        return candidate
    _log.info("vet: no local node_modules entry for npm/%s", name)
    return None


# frob:doc docs/vet.md#public-api
def locate_cargo_source(name: str, version: str) -> Path | None:
    """A directory containing `name`'s Rust source under `~/.cargo/registry/src`."""
    registry_root = Path.home() / ".cargo" / "registry" / "src"
    if not registry_root.is_dir():
        _log.info("vet: no ~/.cargo/registry/src; skipping cargo source lookup")
        return None
    for hit in registry_root.glob(f"*/{name}-{version}"):
        if hit.is_dir():
            _log.debug("vet: located cargo source for %s at %s", name, hit)
            return hit
    _log.info("vet: no local source found for cargo/%s@%s", name, version)
    return None


# frob:doc docs/vet.md#public-api
def locate_source(root: Path, ecosystem: str, name: str, version: str) -> Path | None:
    """Dispatch to the ecosystem-appropriate local-cache source locator."""
    if ecosystem == "pypi":
        return locate_pypi_source(root, name, version)
    if ecosystem == "npm":
        return locate_npm_source(root, name)
    if ecosystem == "cargo":
        return locate_cargo_source(name, version)
    _log.debug("vet: no source locator for ecosystem=%s", ecosystem)
    return None


__all__ = [
    "locate_cargo_source",
    "locate_npm_source",
    "locate_pypi_source",
    "locate_source",
]
