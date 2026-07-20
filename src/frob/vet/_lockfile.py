"""Lockfile parsers: uv.lock, package-lock.json, pnpm-lock.yaml, Cargo.lock ->
`Dependency` tuples
(docs/modules/vet.md "Input"; 0.2.x adds poetry.lock/yarn.lock/bun.lockb).
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import yaml
from typani import Err, Ok
from typani.result import Result

from frob.logging import get_logger
from frob.vet._models import Dependency, VetError

_log = get_logger(__name__)

# Filename -> (ecosystem, parser). Checked in this order.
_LOCKFILE_NAMES = (
    "uv.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "Cargo.lock",
)


# frob:doc docs/modules/vet.md#public-api
# frob:tests tests/test_vet.py::TestLockfileParsers.test_find_lockfile_direct
# frob:tests tests/test_vet.py::TestLockfileParsers.test_find_lockfile_bad_name
def _find_lockfile(root: Path) -> Path | None:
    """`root` itself if it is already a supported lockfile path (T-0221 --
    `frob vet uv.lock` must not be misread as "look for uv.lock under
    ./uv.lock/"), else the first supported lockfile found directly under
    `root` as a directory, or `None` if neither resolves."""
    if root.is_file() and root.name in _LOCKFILE_NAMES:
        _log.debug("vet: using lockfile path directly %s", root)
        return root
    for name in _LOCKFILE_NAMES:
        candidate = root / name
        if candidate.exists():
            _log.debug("vet: found lockfile %s", candidate)
            return candidate
    return None


# frob:doc docs/modules/vet.md#public-api
def _parse_lockfile(path: Path) -> Result[tuple[Dependency, ...], VetError]:
    """Dispatch to the parser matching `path`'s filename; Err on unsupported."""
    name = path.name
    if name == "uv.lock":
        return _parse_toml_packages(path, "pypi")
    if name == "package-lock.json":
        return _parse_package_lock_json(path)
    if name == "pnpm-lock.yaml":
        return _parse_pnpm_lock(path)
    if name == "Cargo.lock":
        return _parse_toml_packages(path, "cargo")
    _log.warning(
        "vet: no parser for %s; supported: %s", path, ", ".join(_LOCKFILE_NAMES)
    )
    return Err(VetError.LockfileUnsupported)


def _parse_toml_packages(
    path: Path, ecosystem: str
) -> Result[tuple[Dependency, ...], VetError]:
    """`[[package]]` TOML tables (uv.lock, Cargo.lock) -> `Dependency` tuples."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("vet: could not parse %s: %s", path, exc)
        return Err(VetError.LockfileUnsupported)
    deps = tuple(
        Dependency(ecosystem=ecosystem, name=pkg["name"], version=pkg["version"])
        for pkg in data.get("package", [])
        if "name" in pkg and "version" in pkg
    )
    _log.info("vet: parsed %d package(s) from %s", len(deps), path)
    return Ok(deps)


def _npm_dep(name: str, meta: dict) -> Dependency | None:
    """One npm `Dependency` from a lockfile metadata table, or `None` if it
    carries no version."""
    version = meta.get("version")
    if version is None:
        return None
    resolved = meta.get("resolved", "")
    resolved = resolved if isinstance(resolved, str) else ""
    return Dependency(ecosystem="npm", name=name, version=version, resolved=resolved)


def _npm_deps_from_packages(packages: dict) -> list[Dependency]:
    """v2/v3 `packages` map (keys like `node_modules/@scope/foo`) -> deps."""
    deps: list[Dependency] = []
    for key, meta in packages.items():
        if not key or not isinstance(meta, dict):
            continue
        name = key.rsplit("node_modules/", 1)[-1]
        dep = _npm_dep(name, meta)
        if dep is not None:
            deps.append(dep)
    return deps


def _npm_deps_from_dependencies(dependencies: dict) -> list[Dependency]:
    """v1 `dependencies` map (name -> meta) -> deps."""
    deps: list[Dependency] = []
    for name, meta in dependencies.items():
        if not isinstance(meta, dict):
            continue
        dep = _npm_dep(name, meta)
        if dep is not None:
            deps.append(dep)
    return deps


def _parse_package_lock_json(path: Path) -> Result[tuple[Dependency, ...], VetError]:
    """`package-lock.json` -> npm dependencies. Handles v1 `dependencies` and
    v2/v3 `packages` (node_modules/<name>) shapes."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _log.warning("vet: could not parse %s: %s", path, exc)
        return Err(VetError.LockfileUnsupported)

    packages = data.get("packages")
    if isinstance(packages, dict):
        deps = _npm_deps_from_packages(packages)
    else:
        deps = _npm_deps_from_dependencies(data.get("dependencies", {}))

    _log.info("vet: parsed %d package(s) from %s", len(deps), path)
    return Ok(tuple(deps))


_PNPM_KEY_RE = re.compile(r"^/?(?P<name>@?[^@()]+(?:/[^@()]+)?)@(?P<version>[^()]+)")


def _parse_pnpm_lock(path: Path) -> Result[tuple[Dependency, ...], VetError]:
    """`pnpm-lock.yaml` -> npm dependencies from the top-level `packages:` map."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        _log.warning("vet: could not parse %s: %s", path, exc)
        return Err(VetError.LockfileUnsupported)
    if not isinstance(data, dict):
        return Err(VetError.LockfileUnsupported)

    packages = data.get("packages") or {}
    deps: list[Dependency] = []
    for key in packages:
        match = _PNPM_KEY_RE.match(key)
        if match is None:
            continue
        deps.append(
            Dependency(
                ecosystem="npm",
                name=match.group("name"),
                version=match.group("version"),
            )
        )
    _log.info("vet: parsed %d package(s) from %s", len(deps), path)
    return Ok(tuple(deps))


__all__ = ["_find_lockfile", "_parse_lockfile"]
