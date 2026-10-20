"""Reversible, idempotent install/uninstall of the frob-suggest hook entry in
a Claude Code settings.json (T-5101).

Every function takes the settings path, so tests never touch ~/.claude.
Frob-owned entries carry `OWNER_MARKER` in their command; legacy
unmarked registrations of frob-suggest.py are treated as frob's too and
collapsed on install (the double-registration bug).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

_log = logging.getLogger("frob_hook_settings")

#: Shell comment appended to the command; the unambiguous ownership mark.
OWNER_MARKER = "# frob-owned:frob-suggest"
_LEGACY_NAME = "frob-suggest.py"
EVENT = "PreToolUse"
MATCHER = "Bash|Edit"


def hook_command(script: Path) -> str:
    """The marked command string registered for `script`."""
    return f"python3 {script} {OWNER_MARKER}"


def _is_frob(entry: Any) -> bool:
    """True for a marked entry or a legacy unmarked frob-suggest.py one."""
    cmd = entry.get("command", "") if isinstance(entry, dict) else ""
    return OWNER_MARKER in cmd or _LEGACY_NAME in cmd


def _load(path: Path) -> dict[str, Any]:
    """Parse settings (missing or empty file is `{}`)."""
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        _log.info("no settings at %s; starting from {}", path)
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(data: dict[str, Any]) -> str:
    """Canonical serialization used for every write."""
    return json.dumps(data, indent=2) + "\n"


def _write(path: Path, data: dict[str, Any]) -> bool:
    """Atomically write `data` (temp file + rename), backing up the old file.
    Returns False (no write) when the bytes would be unchanged."""
    text = _dump(data)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        _log.info("settings unchanged; no write")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(path.name + ".frob-bak")
        backup.write_bytes(path.read_bytes())
        _log.info("backup written to %s", backup)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    _log.info("settings written to %s", path)
    return True


def _strip_frob(groups: list[Any]) -> tuple[list[Any], int]:
    """Remove frob entries from `groups`; drop a group only if it held frob
    entries and is now empty. Returns (new groups, removed count)."""
    out: list[Any] = []
    removed = 0
    for group in groups:
        hooks = group.get("hooks") if isinstance(group, dict) else None
        if not isinstance(hooks, list) or not any(_is_frob(h) for h in hooks):
            out.append(group)
            continue
        kept = [h for h in hooks if not _is_frob(h)]
        removed += len(hooks) - len(kept)
        if kept:
            out.append({**group, "hooks": kept})
        else:
            _log.info("dropping group emptied by frob removal")
    return out, removed


def install(settings: Path, script: Path) -> bool:
    """Register frob-suggest exactly once; idempotent. True if file written."""
    data = _load(settings)
    groups = data.get("hooks", {}).get(EVENT, [])
    marked = [h for g in groups for h in g.get("hooks", []) if OWNER_MARKER in h.get("command", "")]
    legacy = [h for g in groups for h in g.get("hooks", []) if _is_frob(h) and OWNER_MARKER not in h.get("command", "")]
    if len(marked) == 1 and not legacy and marked[0]["command"] == hook_command(script):
        _log.info("already installed once; no-op")
        return False
    if marked or legacy:
        _log.warning("collapsing %d existing frob-suggest registrations", len(marked) + len(legacy))
    groups, _ = _strip_frob(groups)
    groups.append({"matcher": MATCHER, "hooks": [{"type": "command", "command": hook_command(script)}]})
    data.setdefault("hooks", {})[EVENT] = groups
    _log.info("installing frob-suggest into %s", settings)
    return _write(settings, data)


def uninstall(settings: Path) -> bool:
    """Remove only frob entries; no-op when none. True if file written."""
    if not settings.exists():
        _log.info("no settings file; nothing to uninstall")
        return False
    data = _load(settings)
    groups = data.get("hooks", {}).get(EVENT)
    if not isinstance(groups, list):
        _log.info("no %s hooks; nothing to uninstall", EVENT)
        return False
    new, removed = _strip_frob(groups)
    if removed == 0:
        _log.info("no frob entries; no-op")
        return False
    if new:
        data["hooks"][EVENT] = new
    else:
        del data["hooks"][EVENT]
        if not data["hooks"]:
            del data["hooks"]
    _log.info("uninstalled %d frob entries", removed)
    return _write(settings, data)
