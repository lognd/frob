"""CLI wiring for `frob release stamp|check` (T-0003)."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"


# frob:ticket T-0003
def run(cfg: AppConfig) -> None:
    """Dispatch to the release subcommand named by `cfg.release_command`."""
    root = (cfg.release_path or Path(".")).resolve()

    match cfg.release_command:
        case "stamp":
            _stamp(root)
        case "check":
            _check(root)
        case _:
            _log.error("usage: frob release <stamp|check>")
            sys.exit(1)


def _snapshot(root: Path):  # noqa: ANN202
    from frob.graph import build_graph, load_graph

    cache = root / _CACHE_REL
    loaded = load_graph(cache)
    if loaded.is_ok:
        return loaded.danger_ok
    built = build_graph(root, cache)
    if built.is_err:
        _log.error("release: graph build failed: %s", built.danger_err)
        sys.exit(1)
    return built.danger_ok


def _version(root: Path) -> str:
    import tomllib

    toml_path = root / "pyproject.toml"
    if not toml_path.exists():
        _log.error("release: no pyproject.toml at %s", root)
        sys.exit(1)
    with toml_path.open("rb") as fh:
        version = tomllib.load(fh).get("project", {}).get("version")
    if not isinstance(version, str):
        _log.error("release: no [project].version in pyproject.toml")
        sys.exit(1)
    return version


def _stamp(root: Path) -> None:
    from frob.release import stamp

    version = _version(root)
    result = stamp(root, _snapshot(root), version)
    if result.is_err:
        _log.error("release stamp failed: %s", result.danger_err)
        sys.exit(1)
    print(f"stamped public API at {version} -> .frob-release.json")


def _check(root: Path) -> None:
    from frob.release import diff_class, load_manifest, required_version, satisfies

    manifest_result = load_manifest(root)
    if manifest_result.is_err:
        _log.error("release check: %s", manifest_result.danger_err)
        sys.exit(1)
    manifest = manifest_result.danger_ok
    version = _version(root)
    bump = diff_class(manifest, _snapshot(root))
    need = required_version(manifest.version, bump)
    ok = need.is_ok and satisfies(version, need.danger_ok)
    target = need.danger_ok if need.is_ok else "?"
    print(
        f"since {manifest.version}: {bump.name.lower()} change -> "
        f"need >= {target} (current {version}): {'OK' if ok else 'BUMP REQUIRED'}"
    )
    if not ok:
        sys.exit(1)
