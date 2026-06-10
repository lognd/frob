"""
PyCharm headless inspection runner.

Locates PyCharm's inspect.bat on WSL/Windows, runs it, and returns the output
directory for parsing.
"""
from __future__ import annotations

import getpass
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from frob.logging import get_logger

_log = get_logger(__name__)

_WSL_SEARCH_PATTERNS = [
    "/mnt/c/Users/{user}/AppData/Local/Programs/PyCharm/bin/inspect.bat",
    "/mnt/c/Program Files/JetBrains/PyCharm*/bin/inspect.bat",
    "/mnt/c/Users/{user}/AppData/Local/JetBrains/Toolbox/apps/pycharm-professional/bin/inspect.bat",
]


@dataclass
class InspectError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def find_pycharm() -> Path | None:
    """Search common WSL locations for PyCharm inspect.bat."""
    try:
        user = getpass.getuser()
    except Exception:
        user = ""

    for pattern in _WSL_SEARCH_PATTERNS:
        expanded = pattern.format(user=user)
        if "*" in expanded:
            # Use glob
            parts = expanded.split("*", 1)
            base = Path(parts[0].rstrip("/"))
            suffix = parts[1].lstrip("/")
            parent = base.parent
            stem = base.name
            try:
                for candidate in sorted(parent.glob(stem + "*")):
                    p = candidate / suffix
                    if p.exists():
                        return p
            except (OSError, PermissionError):
                pass
        else:
            p = Path(expanded)
            if p.exists():
                return p

    return None


def run_inspection(
    pycharm_inspect: Path,
    project: Path,
    profile: Path,
    output_dir: Path,
    *,
    scope: str | None = None,
) -> tuple[bool, InspectError | None]:
    """
    Run PyCharm headless inspection via cmd.exe.

    Returns (success, error).  On success error is None.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert WSL paths to Windows paths for cmd.exe
    def to_win(p: Path) -> str:
        s = str(p)
        if s.startswith("/mnt/"):
            parts = s[5:].split("/", 1)
            drive = parts[0].upper() + ":"
            rest = parts[1].replace("/", "\\") if len(parts) > 1 else ""
            return drive + "\\" + rest
        return s.replace("/", "\\")

    cmd = [
        "cmd.exe", "/c",
        to_win(pycharm_inspect),
        to_win(project),
        to_win(profile),
        to_win(output_dir),
    ]
    if scope:
        cmd += ["-d", scope]

    _log.info("running: %s", shlex.join(str(c) for c in cmd))

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return False, InspectError(f"failed to launch PyCharm: {exc}")

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        return False, InspectError(
            f"PyCharm inspect exited {proc.returncode}: {stderr[:200]}"
        )

    return True, None
