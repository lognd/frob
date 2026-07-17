"""Tests for frob.tickets.clipboard: backend probe order, no real clipboard use."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import clipboard as clip
from frob.tickets.clipboard import ClipboardError, clipboard_has_image, clipboard_image


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)


def _no_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setattr(clip.shutil, "which", lambda _name: None)
    monkeypatch.setattr(
        clip.Path, "read_text", lambda self, **kw: "Linux version 6.6.0\n"
    )
    monkeypatch.setattr(clip, "_is_darwin", lambda: False)


class TestBackends:
    def test_wl_paste_selected_when_wayland(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/clipboard.py::clipboard_image
        _clear_env(monkeypatch)
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        monkeypatch.setattr(
            clip.shutil,
            "which",
            lambda name: "/usr/bin/wl-paste" if name == "wl-paste" else None,
        )

        calls: list[list[str]] = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout=b"PNGDATA", stderr=b"")

        monkeypatch.setattr(clip.subprocess, "run", fake_run)
        result = clipboard_image()
        assert result.is_ok
        assert result.danger_ok == b"PNGDATA"
        assert calls[0][0] == "wl-paste"

    def test_xclip_selected_when_x11(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_env(monkeypatch)
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setattr(
            clip.shutil,
            "which",
            lambda name: "/usr/bin/xclip" if name == "xclip" else None,
        )

        def fake_run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, stdout=b"PNGDATA", stderr=b"")

        monkeypatch.setattr(clip.subprocess, "run", fake_run)
        result = clipboard_image()
        assert result.is_ok
        assert result.danger_ok == b"PNGDATA"

    def test_wayland_preferred_over_x11(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_env(monkeypatch)
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setattr(clip.shutil, "which", lambda name: f"/usr/bin/{name}")

        seen: list[str] = []

        def fake_run(argv, **kwargs):
            seen.append(argv[0])
            return subprocess.CompletedProcess(argv, 0, stdout=b"PNGDATA", stderr=b"")

        monkeypatch.setattr(clip.subprocess, "run", fake_run)
        clipboard_image()
        assert seen[0] == "wl-paste"

    def test_wsl_detection_via_proc_version(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_env(monkeypatch)
        monkeypatch.setattr(
            clip.shutil,
            "which",
            lambda name: (
                "/usr/bin/powershell.exe" if name == "powershell.exe" else None
            ),
        )
        monkeypatch.setattr(
            clip.Path,
            "read_text",
            lambda self, **kw: "Linux version 5.15.0-microsoft-standard-WSL2\n",
        )

        def fake_run(argv, **kwargs):
            if argv[0] == "wslpath":
                return subprocess.CompletedProcess(
                    argv, 0, stdout=b"C:\\Temp", stderr=b""
                )
            return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

        monkeypatch.setattr(clip.subprocess, "run", fake_run)

        def fake_read_bytes(self):
            return b"WSLPNG"

        monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
        monkeypatch.setattr(Path, "exists", lambda self: True)

        result = clipboard_image()
        assert result.is_ok
        assert result.danger_ok == b"WSLPNG"

    def test_no_backend_lists_probes_in_message(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _no_backends(monkeypatch)
        result = clipboard_image()
        assert result.is_err
        assert result.danger_err is ClipboardError.NoBackend

    def test_no_image(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_env(monkeypatch)
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        monkeypatch.setattr(
            clip.shutil,
            "which",
            lambda name: "/usr/bin/wl-paste" if name == "wl-paste" else None,
        )

        def fake_run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

        monkeypatch.setattr(clip.subprocess, "run", fake_run)
        result = clipboard_image()
        assert result.is_err
        assert result.danger_err is ClipboardError.NoImage

    def test_backend_failed_on_nonzero_exit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_env(monkeypatch)
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        monkeypatch.setattr(
            clip.shutil,
            "which",
            lambda name: "/usr/bin/wl-paste" if name == "wl-paste" else None,
        )

        def fake_run(argv, **kwargs):
            return subprocess.CompletedProcess(
                argv, 1, stdout=b"", stderr=b"error: no clipboard manager"
            )

        monkeypatch.setattr(clip.subprocess, "run", fake_run)
        result = clipboard_image()
        assert result.is_err
        assert result.danger_err is ClipboardError.BackendFailed

    def test_has_image_false_when_no_backend(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _no_backends(monkeypatch)
        assert clipboard_has_image() is False

    def test_has_image_true_when_wl_paste_lists_png(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/clipboard.py::clipboard_has_image
        _clear_env(monkeypatch)
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        monkeypatch.setattr(
            clip.shutil,
            "which",
            lambda name: "/usr/bin/wl-paste" if name == "wl-paste" else None,
        )

        def fake_run(argv, **kwargs):
            return subprocess.CompletedProcess(
                argv, 0, stdout=b"text/plain\nimage/png\n", stderr=b""
            )

        monkeypatch.setattr(clip.subprocess, "run", fake_run)
        assert clipboard_has_image() is True
