"""Cross-platform clipboard image capture (docs/modules/tickets.md "Clipboard capture").

Backend chain, first available wins: wl-paste (Wayland), xclip (X11),
powershell.exe Get-Clipboard (WSL), pngpaste/osascript (macOS). Every probe
and invocation is logged; a missing backend is Err(NoBackend) with the full
probe report so the caller can see exactly why nothing worked.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import cast

from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run

_log = get_logger(__name__)

_PROBE_TIMEOUT_S = 5.0
_PASTE_TIMEOUT_S = 15.0


# frob:doc docs/modules/tickets.md#error-types
class ClipboardError(ErrorSet):
    """Fallible outcomes of clipboard image capture."""

    NoBackend = "No clipboard backend available on this platform"
    NoImage = "Clipboard does not contain an image"
    BackendFailed = "Clipboard backend exited nonzero"


def _is_wayland() -> bool:
    return (
        bool(os.environ.get("WAYLAND_DISPLAY")) and shutil.which("wl-paste") is not None
    )


def _is_x11() -> bool:
    return bool(os.environ.get("DISPLAY")) and shutil.which("xclip") is not None


def _is_wsl() -> bool:
    try:
        text = Path("/proc/version").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "microsoft" in text.lower()


def _is_darwin() -> bool:
    import sys

    return sys.platform == "darwin"


def _probe_report() -> str:
    """Human-readable summary of which backend preconditions held (for NoBackend)."""
    lines = [
        f"wl-paste: wayland={bool(os.environ.get('WAYLAND_DISPLAY'))} "
        f"binary={shutil.which('wl-paste') is not None}",
        f"xclip: x11={bool(os.environ.get('DISPLAY'))} "
        f"binary={shutil.which('xclip') is not None}",
        f"powershell.exe (WSL): detected={_is_wsl()} "
        f"binary={shutil.which('powershell.exe') is not None}",
        f"pngpaste (darwin): platform={_is_darwin()} "
        f"binary={shutil.which('pngpaste') is not None}",
    ]
    return "; ".join(lines)


def _wl_paste_has_image() -> bool:
    _log.debug("clipboard: probing wl-paste --list-types")
    try:
        guarded = guarded_subprocess_run(
            ["wl-paste", "--list-types"],
            capture_output=True,
            timeout=_PROBE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.warning("clipboard: wl-paste probe failed: %s", exc)
        return False
    if guarded.is_err:
        _log.warning("clipboard: wl-paste probe refused (exec disabled)")
        return False
    proc = cast("subprocess.CompletedProcess[bytes]", guarded.danger_ok)
    return b"image/png" in proc.stdout or b"image/" in proc.stdout


def _wl_paste_image() -> Result[bytes, ClipboardError]:
    _log.info("clipboard: fetching image via wl-paste")
    try:
        guarded = guarded_subprocess_run(
            ["wl-paste", "-t", "image/png"],
            capture_output=True,
            timeout=_PASTE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.error("clipboard: wl-paste invocation failed: %s", exc)
        return Err(ClipboardError.BackendFailed)
    if guarded.is_err:
        _log.error("clipboard: wl-paste invocation refused (exec disabled)")
        return Err(ClipboardError.BackendFailed)
    proc = cast("subprocess.CompletedProcess[bytes]", guarded.danger_ok)
    if proc.returncode != 0:
        _log.error("clipboard: wl-paste exited %d: %s", proc.returncode, proc.stderr)
        return Err(ClipboardError.BackendFailed)
    if not proc.stdout:
        _log.info("clipboard: wl-paste returned no image data")
        return Err(ClipboardError.NoImage)
    return Ok(proc.stdout)


def _xclip_has_image() -> bool:
    _log.debug("clipboard: probing xclip -o -t TARGETS")
    try:
        guarded = guarded_subprocess_run(
            ["xclip", "-selection", "clipboard", "-t", "TARGETS", "-o"],
            capture_output=True,
            timeout=_PROBE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.warning("clipboard: xclip probe failed: %s", exc)
        return False
    if guarded.is_err:
        _log.warning("clipboard: xclip probe refused (exec disabled)")
        return False
    proc = cast("subprocess.CompletedProcess[bytes]", guarded.danger_ok)
    return b"image/png" in proc.stdout


def _xclip_image() -> Result[bytes, ClipboardError]:
    _log.info("clipboard: fetching image via xclip")
    try:
        guarded = guarded_subprocess_run(
            ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
            capture_output=True,
            timeout=_PASTE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.error("clipboard: xclip invocation failed: %s", exc)
        return Err(ClipboardError.BackendFailed)
    if guarded.is_err:
        _log.error("clipboard: xclip invocation refused (exec disabled)")
        return Err(ClipboardError.BackendFailed)
    proc = cast("subprocess.CompletedProcess[bytes]", guarded.danger_ok)
    if proc.returncode != 0:
        _log.error("clipboard: xclip exited %d: %s", proc.returncode, proc.stderr)
        return Err(ClipboardError.BackendFailed)
    if not proc.stdout:
        _log.info("clipboard: xclip returned no image data")
        return Err(ClipboardError.NoImage)
    return Ok(proc.stdout)


def _wsl_has_image() -> bool:
    _log.debug("clipboard: probing WSL clipboard via powershell.exe ContainsImage")
    try:
        guarded = guarded_subprocess_run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "[Console]::Out.Write([Windows.Forms.Clipboard]::ContainsImage())",
            ],
            capture_output=True,
            timeout=_PROBE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.warning("clipboard: WSL probe failed: %s", exc)
        return False
    if guarded.is_err:
        _log.warning("clipboard: WSL probe refused (exec disabled)")
        return False
    proc = cast("subprocess.CompletedProcess[bytes]", guarded.danger_ok)
    return b"True" in proc.stdout


_WSL_SAVE_SCRIPT = (
    "Add-Type -AssemblyName System.Windows.Forms; "
    "Add-Type -AssemblyName System.Drawing; "
    "$img = [Windows.Forms.Clipboard]::GetImage(); "
    "if ($img -eq $null) {{ exit 2 }} "
    "$img.Save('{win_png}', [System.Drawing.Imaging.ImageFormat]::Png)"
)


def _wsl_save_and_read(tmp_dir: str, win_png: str) -> Result[bytes, ClipboardError]:
    """Save the WSL clipboard image to `win_png` via powershell, then read it back."""
    script = _WSL_SAVE_SCRIPT.format(win_png=win_png)
    try:
        guarded = guarded_subprocess_run(
            ["powershell.exe", "-NoProfile", "-Command", script],
            capture_output=True,
            timeout=_PASTE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.error("clipboard: WSL powershell invocation failed: %s", exc)
        return Err(ClipboardError.BackendFailed)
    if guarded.is_err:
        _log.error("clipboard: WSL powershell invocation refused (exec disabled)")
        return Err(ClipboardError.BackendFailed)
    proc = cast("subprocess.CompletedProcess[bytes]", guarded.danger_ok)
    if proc.returncode == 2:
        _log.info("clipboard: WSL clipboard has no image")
        return Err(ClipboardError.NoImage)
    if proc.returncode != 0:
        _log.error(
            "clipboard: WSL powershell exited %d: %s", proc.returncode, proc.stderr
        )
        return Err(ClipboardError.BackendFailed)
    wsl_png = Path(tmp_dir) / "clip.png"
    if not wsl_png.exists():
        _log.error("clipboard: WSL expected output %s missing", wsl_png)
        return Err(ClipboardError.BackendFailed)
    return Ok(wsl_png.read_bytes())


def _wsl_image() -> Result[bytes, ClipboardError]:
    _log.info("clipboard: fetching image via WSL powershell.exe")
    with tempfile.TemporaryDirectory() as tmp_dir:
        guarded_win_tmp = guarded_subprocess_run(
            ["wslpath", "-w", tmp_dir],
            capture_output=True,
            timeout=_PROBE_TIMEOUT_S,
            check=False,
        )
        if guarded_win_tmp.is_err:
            _log.error("clipboard: wslpath refused (exec disabled) for %s", tmp_dir)
            return Err(ClipboardError.BackendFailed)
        win_tmp = cast("subprocess.CompletedProcess[bytes]", guarded_win_tmp.danger_ok)
        if win_tmp.returncode != 0:
            _log.error("clipboard: wslpath failed to translate %s", tmp_dir)
            return Err(ClipboardError.BackendFailed)
        win_tmp_path = win_tmp.stdout.decode("ascii", errors="replace").strip()
        win_png = f"{win_tmp_path}\\clip.png"
        return _wsl_save_and_read(tmp_dir, win_png)


def _pngpaste_has_image() -> bool:
    _log.debug("clipboard: probing pngpaste to /dev/null")
    try:
        guarded = guarded_subprocess_run(
            ["pngpaste", "-"],
            capture_output=True,
            timeout=_PROBE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.warning("clipboard: pngpaste probe failed: %s", exc)
        return False
    if guarded.is_err:
        _log.warning("clipboard: pngpaste probe refused (exec disabled)")
        return False
    proc = cast("subprocess.CompletedProcess[bytes]", guarded.danger_ok)
    return proc.returncode == 0 and bool(proc.stdout)


def _pngpaste_image() -> Result[bytes, ClipboardError]:
    _log.info("clipboard: fetching image via pngpaste")
    try:
        guarded = guarded_subprocess_run(
            ["pngpaste", "-"],
            capture_output=True,
            timeout=_PASTE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.error("clipboard: pngpaste invocation failed: %s", exc)
        return Err(ClipboardError.BackendFailed)
    if guarded.is_err:
        _log.error("clipboard: pngpaste invocation refused (exec disabled)")
        return Err(ClipboardError.BackendFailed)
    proc = cast("subprocess.CompletedProcess[bytes]", guarded.danger_ok)
    if proc.returncode != 0:
        _log.error("clipboard: pngpaste exited %d: %s", proc.returncode, proc.stderr)
        return Err(ClipboardError.BackendFailed)
    if not proc.stdout:
        _log.info("clipboard: pngpaste returned no image data")
        return Err(ClipboardError.NoImage)
    return Ok(proc.stdout)


# frob:doc docs/modules/tickets.md#public-api
def clipboard_image() -> Result[bytes, ClipboardError]:
    """PNG bytes from the platform clipboard, via the first working backend."""
    if _is_wayland():
        _log.debug("clipboard: selecting wl-paste backend")
        return _wl_paste_image()
    if _is_x11():
        _log.debug("clipboard: selecting xclip backend")
        return _xclip_image()
    if _is_wsl() and shutil.which("powershell.exe") is not None:
        _log.debug("clipboard: selecting WSL powershell backend")
        return _wsl_image()
    if _is_darwin() and shutil.which("pngpaste") is not None:
        _log.debug("clipboard: selecting pngpaste backend")
        return _pngpaste_image()
    report = _probe_report()
    _log.warning("clipboard: no backend available (%s)", report)
    return Err(ClipboardError.NoBackend)


# frob:doc docs/modules/tickets.md#public-api
def clipboard_has_image() -> bool:
    """Cheap probe used to decide whether to offer the interactive paste prompt."""
    if _is_wayland():
        return _wl_paste_has_image()
    if _is_x11():
        return _xclip_has_image()
    if _is_wsl() and shutil.which("powershell.exe") is not None:
        return _wsl_has_image()
    if _is_darwin() and shutil.which("pngpaste") is not None:
        return _pngpaste_has_image()
    _log.debug("clipboard: no backend available for has_image probe")
    return False
