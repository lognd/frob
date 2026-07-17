"""VET-JS lifecycle-script scan: preinstall/install/postinstall/prepare in any
package.json under node_modules/ (docs/vet.md "Lifecycle scripts are the
headline capability")."""

from __future__ import annotations

import json
from pathlib import Path

from frob.logging import get_logger

_log = get_logger(__name__)

_LIFECYCLE_SCRIPTS = ("preinstall", "install", "postinstall", "prepare")


# frob:doc docs/vet.md#public-api
def scan_lifecycle_scripts(root: Path) -> dict[str, tuple[str, ...]]:
    """`{package_name: (script_name, ...)}` for every node_modules package.json
    declaring a lifecycle script. Empty dict (with a log note) if no node_modules."""
    node_modules = root / "node_modules"
    if not node_modules.is_dir():
        _log.info("vet: no node_modules under %s; skipping lifecycle scan", root)
        return {}

    found: dict[str, tuple[str, ...]] = {}
    for pkg_json in node_modules.glob("**/package.json"):
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _log.warning("vet: could not parse %s: %s", pkg_json, exc)
            continue
        scripts = data.get("scripts")
        if not isinstance(scripts, dict):
            continue
        hits = tuple(s for s in _LIFECYCLE_SCRIPTS if s in scripts)
        if hits:
            name = data.get("name", pkg_json.parent.name)
            found[name] = hits
            _log.info("vet: %s declares lifecycle script(s): %s", name, hits)
    _log.info("vet: lifecycle scan found %d package(s) with hooks", len(found))
    return found


__all__ = ["scan_lifecycle_scripts"]
