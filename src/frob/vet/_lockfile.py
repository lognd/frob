"""Lockfile parsers: uv.lock, package-lock.json, pnpm-lock.yaml, Cargo.lock ->
`Dependency` tuples (docs/vet.md "Input"; 0.2.x adds poetry.lock/yarn.lock/bun.lockb).
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


# frob:doc docs/vet.md#public-api
def find_lockfile(root: Path) -> Path | None:
    """The first supported lockfile found directly under `root`, or `None`."""
    for name in _LOCKFILE_NAMES:
        candidate = root / name
        if candidate.exists():
            _log.debug("vet: found lockfile %s", candidate)
            return candidate
    return None


# frob:doc docs/vet.md#public-api
def parse_lockfile(path: Path) -> Result[tuple[Dependency, ...], VetError]:
    """Dispatch to the parser matching `path`'s filename; Err on unsupported."""
    name = path.name
    if name == "uv.lock":
        return _parse_uv_lock(path)
    if name == "package-lock.json":
        return _parse_package_lock_json(path)
    if name == "pnpm-lock.yaml":
        return _parse_pnpm_lock(path)
    if name == "Cargo.lock":
        return _parse_cargo_lock(path)
    _log.warning(
        "vet: no parser for %s; supported: %s", path, ", ".join(_LOCKFILE_NAMES)
    )
    return Err(VetError.LockfileUnsupported)


def _parse_uv_lock(path: Path) -> Result[tuple[Dependency, ...], VetError]:
    """`uv.lock` -> pypi dependencies via `[[package]]` TOML tables."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("vet: could not parse %s: %s", path, exc)
        return Err(VetError.LockfileUnsupported)
    deps = tuple(
        Dependency(ecosystem="pypi", name=pkg["name"], version=pkg["version"])
        for pkg in data.get("package", [])
        if "name" in pkg and "version" in pkg
    )
    _log.info("vet: parsed %d package(s) from %s", len(deps), path)
    return Ok(deps)


def _parse_package_lock_json(path: Path) -> Result[tuple[Dependency, ...], VetError]:
    """`package-lock.json` -> npm dependencies. Handles v1 `dependencies` and
    v2/v3 `packages` (node_modules/<name>) shapes."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _log.warning("vet: could not parse %s: %s", path, exc)
        return Err(VetError.LockfileUnsupported)

    deps: list[Dependency] = []
    packages = data.get("packages")
    if isinstance(packages, dict):
        for key, meta in packages.items():
            if not key or not isinstance(meta, dict):
                continue
            version = meta.get("version")
            if version is None:
                continue
            # key looks like "node_modules/foo" or "node_modules/@scope/foo"
            name = key.rsplit("node_modules/", 1)[-1]
            resolved = meta.get("resolved", "")
            resolved = resolved if isinstance(resolved, str) else ""
            deps.append(
                Dependency(
                    ecosystem="npm", name=name, version=version, resolved=resolved
                )
            )
    else:
        for name, meta in data.get("dependencies", {}).items():
            if not isinstance(meta, dict):
                continue
            version = meta.get("version")
            if version is None:
                continue
            resolved = meta.get("resolved", "")
            resolved = resolved if isinstance(resolved, str) else ""
            deps.append(
                Dependency(
                    ecosystem="npm", name=name, version=version, resolved=resolved
                )
            )

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


def _parse_cargo_lock(path: Path) -> Result[tuple[Dependency, ...], VetError]:
    """`Cargo.lock` -> crates.io dependencies via `[[package]]` TOML tables."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("vet: could not parse %s: %s", path, exc)
        return Err(VetError.LockfileUnsupported)
    deps = tuple(
        Dependency(ecosystem="cargo", name=pkg["name"], version=pkg["version"])
        for pkg in data.get("package", [])
        if "name" in pkg and "version" in pkg
    )
    _log.info("vet: parsed %d package(s) from %s", len(deps), path)
    return Ok(deps)


__all__ = ["find_lockfile", "parse_lockfile"]
