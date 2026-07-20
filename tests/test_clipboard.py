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

    def test_has_image_true_when_xclip_lists_png_target(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The xclip TARGETS probe reports True on an image/png hit."""
        _clear_env(monkeypatch)
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setattr(
            clip.shutil,
            "which",
            lambda name: "/usr/bin/xclip" if name == "xclip" else None,
        )

        def fake_run(argv, **kwargs):
            return subprocess.CompletedProcess(
                argv, 0, stdout=b"TARGETS\nimage/png\n", stderr=b""
            )

        monkeypatch.setattr(clip.subprocess, "run", fake_run)
        assert clipboard_has_image() is True

    def test_xclip_probe_returns_false_when_no_png_target(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No `image/png` in the TARGETS list means no image available."""
        _clear_env(monkeypatch)
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setattr(
            clip.shutil,
            "which",
            lambda name: "/usr/bin/xclip" if name == "xclip" else None,
        )
        monkeypatch.setattr(
            clip.subprocess,
            "run",
            lambda argv, **kw: subprocess.CompletedProcess(
                argv, 0, stdout=b"TARGETS\ntext/plain\n", stderr=b""
            ),
        )
        assert clipboard_has_image() is False

    def test_xclip_no_image_data_is_err(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """xclip exits 0 but with empty stdout -- NoImage, not a false Ok."""
        _clear_env(monkeypatch)
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setattr(
            clip.shutil,
            "which",
            lambda name: "/usr/bin/xclip" if name == "xclip" else None,
        )
        monkeypatch.setattr(
            clip.subprocess,
            "run",
            lambda argv, **kw: subprocess.CompletedProcess(
                argv, 0, stdout=b"", stderr=b""
            ),
        )
        result = clipboard_image()
        assert result.is_err
        assert result.danger_err is ClipboardError.NoImage

    def test_xclip_backend_failed_on_nonzero_exit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A nonzero xclip exit is BackendFailed."""
        _clear_env(monkeypatch)
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setattr(
            clip.shutil,
            "which",
            lambda name: "/usr/bin/xclip" if name == "xclip" else None,
        )
        monkeypatch.setattr(
            clip.subprocess,
            "run",
            lambda argv, **kw: subprocess.CompletedProcess(
                argv, 1, stdout=b"", stderr=b"boom"
            ),
        )
        result = clipboard_image()
        assert result.is_err
        assert result.danger_err is ClipboardError.BackendFailed

    @pytest.mark.parametrize("probe_name", ["wl-paste", "xclip", "pngpaste"])
    def test_probe_oserror_is_treated_as_no_image(
        self, monkeypatch: pytest.MonkeyPatch, probe_name: str
    ) -> None:
        """An OSError/TimeoutExpired raised by the probe subprocess is caught
        and treated as "no image", not propagated."""
        _clear_env(monkeypatch)
        if probe_name == "wl-paste":
            monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        elif probe_name == "xclip":
            monkeypatch.setenv("DISPLAY", ":0")
        else:
            monkeypatch.setattr(clip, "_is_darwin", lambda: True)

        monkeypatch.setattr(
            clip.shutil,
            "which",
            lambda name: f"/usr/bin/{name}" if name == probe_name else None,
        )

        def raising_run(argv, **kwargs):
            raise OSError("no such backend")

        monkeypatch.setattr(clip.subprocess, "run", raising_run)
        assert clipboard_has_image() is False

    def test_darwin_pngpaste_selected_and_reads_image(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """On darwin with pngpaste present, clipboard_image uses it."""
        _no_backends(monkeypatch)
        monkeypatch.setattr(clip, "_is_darwin", lambda: True)
        monkeypatch.setattr(
            clip.shutil,
            "which",
            lambda name: "/usr/bin/pngpaste" if name == "pngpaste" else None,
        )
        monkeypatch.setattr(
            clip.subprocess,
            "run",
            lambda argv, **kw: subprocess.CompletedProcess(
                argv, 0, stdout=b"PNGDATA", stderr=b""
            ),
        )
        result = clipboard_image()
        assert result.is_ok
        assert result.danger_ok == b"PNGDATA"

    def test_pngpaste_backend_failed_and_no_image(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """pngpaste's nonzero-exit and empty-stdout paths both map correctly."""
        _no_backends(monkeypatch)
        monkeypatch.setattr(clip, "_is_darwin", lambda: True)
        monkeypatch.setattr(
            clip.shutil,
            "which",
            lambda name: "/usr/bin/pngpaste" if name == "pngpaste" else None,
        )
        monkeypatch.setattr(
            clip.subprocess,
            "run",
            lambda argv, **kw: subprocess.CompletedProcess(
                argv, 1, stdout=b"", stderr=b"nothing"
            ),
        )
        assert clipboard_image().is_err
        assert clipboard_image().danger_err is ClipboardError.BackendFailed

        monkeypatch.setattr(
            clip.subprocess,
            "run",
            lambda argv, **kw: subprocess.CompletedProcess(
                argv, 0, stdout=b"", stderr=b""
            ),
        )
        assert clipboard_image().danger_err is ClipboardError.NoImage

    def test_pngpaste_has_image_true_and_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`clipboard_has_image` under the darwin/pngpaste backend."""
        _no_backends(monkeypatch)
        monkeypatch.setattr(clip, "_is_darwin", lambda: True)
        monkeypatch.setattr(
            clip.shutil,
            "which",
            lambda name: "/usr/bin/pngpaste" if name == "pngpaste" else None,
        )
        monkeypatch.setattr(
            clip.subprocess,
            "run",
            lambda argv, **kw: subprocess.CompletedProcess(
                argv, 0, stdout=b"PNGDATA", stderr=b""
            ),
        )
        assert clipboard_has_image() is True

        monkeypatch.setattr(
            clip.subprocess,
            "run",
            lambda argv, **kw: subprocess.CompletedProcess(
                argv, 1, stdout=b"", stderr=b""
            ),
        )
        assert clipboard_has_image() is False

    def test_wsl_backend_requires_powershell_binary(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """WSL detection alone is not enough -- powershell.exe must also be
        on PATH, or the chain falls through to NoBackend."""
        _clear_env(monkeypatch)
        monkeypatch.setattr(clip.shutil, "which", lambda name: None)
        monkeypatch.setattr(
            clip.Path,
            "read_text",
            lambda self, **kw: "Linux version 5.15.0-microsoft-standard-WSL2\n",
        )
        monkeypatch.setattr(clip, "_is_darwin", lambda: False)
        result = clipboard_image()
        assert result.is_err
        assert result.danger_err is ClipboardError.NoBackend
        assert clipboard_has_image() is False

    def test_wsl_has_image_true_and_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`_wsl_has_image` parses the ContainsImage() powershell probe output."""
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
        monkeypatch.setattr(
            clip.subprocess,
            "run",
            lambda argv, **kw: subprocess.CompletedProcess(
                argv, 0, stdout=b"True", stderr=b""
            ),
        )
        assert clipboard_has_image() is True

        monkeypatch.setattr(
            clip.subprocess,
            "run",
            lambda argv, **kw: subprocess.CompletedProcess(
                argv, 0, stdout=b"False", stderr=b""
            ),
        )
        assert clipboard_has_image() is False

    def test_wsl_save_reports_no_image_on_exit_code_2(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """powershell exiting 2 means the clipboard held no image (the save
        script's own `if ($img -eq $null) {{ exit 2 }}` sentinel)."""
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
            return subprocess.CompletedProcess(argv, 2, stdout=b"", stderr=b"")

        monkeypatch.setattr(clip.subprocess, "run", fake_run)
        result = clipboard_image()
        assert result.is_err
        assert result.danger_err is ClipboardError.NoImage

    def test_wsl_save_backend_failed_on_other_nonzero_exit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Any other nonzero exit from the save script is BackendFailed."""
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
            return subprocess.CompletedProcess(argv, 1, stdout=b"", stderr=b"oops")

        monkeypatch.setattr(clip.subprocess, "run", fake_run)
        result = clipboard_image()
        assert result.is_err
        assert result.danger_err is ClipboardError.BackendFailed

    def test_wsl_save_backend_failed_when_output_file_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """powershell exits 0 but never wrote the expected PNG file."""
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
        monkeypatch.setattr(Path, "exists", lambda self: False)
        result = clipboard_image()
        assert result.is_err
        assert result.danger_err is ClipboardError.BackendFailed

    def test_wsl_wslpath_failure_is_backend_failed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A failing `wslpath` translation short-circuits to BackendFailed
        before ever invoking the save script."""
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
        monkeypatch.setattr(
            clip.subprocess,
            "run",
            lambda argv, **kw: subprocess.CompletedProcess(
                argv, 1, stdout=b"", stderr=b""
            ),
        )
        result = clipboard_image()
        assert result.is_err
        assert result.danger_err is ClipboardError.BackendFailed

    def test_probe_report_lists_all_four_backends(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`_probe_report`'s text mentions every backend it checks, for the
        NoBackend error's diagnostic detail."""
        _no_backends(monkeypatch)
        report = clip._probe_report()
        assert "wl-paste" in report
        assert "xclip" in report
        assert "powershell.exe" in report
        assert "pngpaste" in report

    def test_is_wsl_reads_proc_version_case_insensitively(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`_is_wsl` matches "microsoft" in /proc/version regardless of case."""
        monkeypatch.setattr(
            clip.Path, "read_text", lambda self, **kw: "Linux MICROSOFT-STANDARD\n"
        )
        assert clip._is_wsl() is True

    def test_is_wsl_false_when_proc_version_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A missing /proc/version (non-Linux, or sandboxed) is simply "not WSL"."""

        def raise_oserror(self, **kw):
            raise OSError("no such file")

        monkeypatch.setattr(clip.Path, "read_text", raise_oserror)
        assert clip._is_wsl() is False
