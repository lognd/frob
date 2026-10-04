"""pytest plugin that records every `python -m crunk` subprocess call.

Loaded into a scratch copy of the Python crunk test suite (never into the
crunk repository itself).  For each call it stores argv, env overlay, stdin,
exit code, stdout, stderr, the project files the test wrote since the last
call (setup) and the files the call itself created or changed (effects).
Raw, un-normalized records are appended to $CRUNK_CAPTURE_OUT/raw.jsonl; the
regen script normalizes them afterwards.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

_MAX_FILE = 256 * 1024
_SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv"}

_real_run = subprocess.run
_state: dict[str, dict[str, str]] = {}
_basetemp: Path | None = None
_out: Path | None = None


def _snapshot(root: Path) -> dict[str, bytes]:
    """Map relative posix path -> bytes for every small file under root."""
    files: dict[str, bytes] = {}
    if not root.is_dir():
        return files
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        for name in sorted(filenames):
            p = Path(dirpath) / name
            try:
                if p.is_symlink() or p.stat().st_size > _MAX_FILE:
                    continue
                files[p.relative_to(root).as_posix()] = p.read_bytes()
            except OSError:
                continue
    return files


def _delta(before: dict[str, bytes], after: dict[str, bytes]) -> dict:
    """Changed/added files (base64) and deleted paths between two snapshots."""
    changed = {
        k: base64.b64encode(v).decode()
        for k, v in after.items()
        if before.get(k) != v
    }
    deleted = sorted(k for k in before if k not in after)
    return {"changed": changed, "deleted": deleted}


def _root_for(cwd: Path) -> Path:
    """The per-test tmp root: first path component below the basetemp."""
    assert _basetemp is not None
    try:
        first = cwd.resolve().relative_to(_basetemp.resolve()).parts[0]
    except (ValueError, IndexError):
        return cwd
    return _basetemp / first


def _is_crunk(args) -> bool:
    return (
        isinstance(args, (list, tuple))
        and len(args) >= 3
        and args[0] == sys.executable
        and args[1] == "-m"
        and args[2] == "crunk"
    )


def _recording_run(args, *a, **kw):
    if not _is_crunk(args):
        return _real_run(args, *a, **kw)
    cwd = Path(kw.get("cwd") or os.getcwd())
    root = _root_for(cwd)
    node = os.environ.get("PYTEST_CURRENT_TEST", "unknown").rsplit(" ", 1)[0]
    pre = _snapshot(root)
    key = node
    prev_after = _state.get(key)
    setup = _delta(prev_after if prev_after is not None else {}, pre)
    result = _real_run(args, *a, **kw)
    post = _snapshot(root)
    _state[key] = post
    rec = {
        "node": node,
        "root": str(root),
        "cwd": str(cwd),
        "argv": list(args[3:]),
        "env": {
            k: v
            for k, v in (kw.get("env") or {}).items()
            if os.environ.get(k) != v
        },
        "stdin": kw.get("input"),
        "exit": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "setup": setup,
        "effects": _delta(pre, post),
    }
    assert _out is not None
    with (_out / "raw.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return result


def pytest_configure(config) -> None:
    """Install the recording wrapper and resolve the base temp dir."""
    global _basetemp, _out
    _out = Path(os.environ["CRUNK_CAPTURE_OUT"])
    _out.mkdir(parents=True, exist_ok=True)
    _basetemp = Path(config.option.basetemp).resolve()
    subprocess.run = _recording_run  # type: ignore[assignment]
