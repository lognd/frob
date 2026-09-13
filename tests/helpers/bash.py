"""T-4455: resolve a real `bash` executable for tests that spawn one.

On the GitHub Windows runner, plain PATH resolution of "bash" hits
C:\\Windows\\System32\\bash.exe -- the WSL launcher stub -- ahead of Git
for Windows' bash, because System32 is always on PATH and a stock
windows-latest image has no WSL distribution installed. The stub prints a
UTF-16 "Windows Subsystem for Linux has no installed distributions ...
'wsl.exe --install <Distro>' to install." message and exits 1 without ever
running the script, so any test that spawns `["bash", "-c", ...]` directly
fails before frob is invoked at all. `resolve_bash()` centralizes the fix
(NO DUPLICATION) so every such spawn in `tests/` goes through one place.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

#: Marker substring of the WSL launcher stub's install path -- used to
#: reject any `shutil.which("bash")` hit that resolves under it, even if
#: PATH ordering changes underneath us.
_WSL_STUB_DIR = "system32"


def resolve_bash() -> str:
    """Return a real bash executable path, never the WSL System32 stub.

    On non-Windows platforms this is just `"bash"` (normal PATH lookup,
    where no WSL stub shadowing exists). On win32, probes Git for
    Windows' bash locations (both common install layouts, plus whatever
    `shutil.which("git")`'s own resolved location implies about the Git
    install root -- Git for Windows lays out `Git\\cmd` next to `Git\\bin`
    and `Git\\usr\\bin`), then falls back to `shutil.which("bash")` only
    if that hit is not under `System32`. Raises `pytest.skip.Exception`
    (via `pytest.skip`) with a reason naming the stub if nothing
    qualifies -- callers should call this from inside a test, not at
    import/collection time.
    """
    if sys.platform != "win32":
        return "bash"

    import pytest

    candidates: list[Path] = []
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        candidates.append(Path(program_files) / "Git" / "bin" / "bash.exe")
        candidates.append(Path(program_files) / "Git" / "usr" / "bin" / "bash.exe")

    git_path = shutil.which("git")
    if git_path:
        git_root = Path(git_path).resolve().parent.parent
        candidates.append(git_root / "bin" / "bash.exe")
        candidates.append(git_root / "usr" / "bin" / "bash.exe")

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    which_bash = shutil.which("bash")
    if which_bash and _WSL_STUB_DIR not in {
        part.lower() for part in Path(which_bash).parts
    }:
        return which_bash

    pytest.skip(
        "no usable bash found (only the WSL launcher stub under "
        "System32 is on PATH, which prints a UTF-16 "
        "'no installed distributions' message and never runs the "
        "script); install Git for Windows to provide bash"
    )
    raise AssertionError("unreachable")  # pragma: no cover
