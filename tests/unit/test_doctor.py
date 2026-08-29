"""Tests for `frob.doctor.native_degrade_warning` (T-3011): the loud,
by-name, PLATFORM001-doctrine stderr warning printed on every subcommand
when `frob_core`/`strata_core` are not importable -- see the function's
own docstring and docs/guides/release.md's "Decision 2" for the full
reasoning (an sdist-fallback silent Rust build was rejected in favor of
this)."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob import doctor
from frob.doctor import (
    ExternalToolStatus,
    NativeExtensionStatus,
    ToolCategory,
    _external_tools_remediation,
    native_degrade_warning,
    scan_external_tools,
)


class TestNativeDegradeWarning:
    """Must-fire fixture: a wheel-less/natives-less environment MUST
    produce a loud message naming every missing extension, and a fully-
    accelerated environment MUST NOT produce any message at all."""

    def test_missing_extensions_named_loudly(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Both natives missing: the message names BOTH `frob_core` and
        `strata_core` explicitly -- not a generic "something is missing"
        line. This is the must-fire case the whole degrade doctrine
        exists to guarantee."""
        monkeypatch.setattr(
            doctor,
            "_extension_status",
            lambda name: NativeExtensionStatus(name=name, available=False),
        )
        message = native_degrade_warning(tmp_path)
        assert message is not None
        assert "frob_core" in message
        assert "strata_core" in message
        assert "pure-Python mode" in message

    def test_fully_accelerated_produces_no_warning(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Both natives importable: `None`, not an empty/quiet message --
        this is the common case and it must never fire here."""
        monkeypatch.setattr(
            doctor,
            "_extension_status",
            lambda name: NativeExtensionStatus(
                name=name, available=True, version="0.1.0"
            ),
        )
        assert native_degrade_warning(tmp_path) is None

    def test_partial_availability_still_names_the_missing_one(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Only one of the two natives missing: the message names exactly
        the missing one, not the available one -- proves this is a real
        per-extension check, not an all-or-nothing flag."""

        def fake_status(name: str) -> NativeExtensionStatus:
            return NativeExtensionStatus(
                name=name, available=(name == "frob_core"), version=None
            )

        monkeypatch.setattr(doctor, "_extension_status", fake_status)
        message = native_degrade_warning(tmp_path)
        assert message is not None
        assert "strata_core" in message
        assert "frob_core" not in message.split("--")[0].split("(")[1]

    def test_source_checkout_gets_make_core_hint(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A `repo_root` containing `frob-core/Cargo.toml` (a source
        checkout) gets pointed at `make core`, not the PyPI extra -- the
        wrong remediation for a dev checkout would send a contributor on
        a pointless `pip install` detour."""
        monkeypatch.setattr(
            doctor,
            "_extension_status",
            lambda name: NativeExtensionStatus(name=name, available=False),
        )
        (tmp_path / "frob-core").mkdir()
        (tmp_path / "frob-core" / "Cargo.toml").write_text("", encoding="utf-8")
        message = native_degrade_warning(tmp_path)
        assert message is not None
        assert "make core" in message

    def test_installed_package_gets_pip_extra_hint(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """No source checkout under `repo_root` (or `repo_root=None`): the
        remediation names the PyPI `frob[native]` extra, not `make core`
        (which an installed-package adopter has no Rust toolchain or
        source tree to run)."""
        monkeypatch.setattr(
            doctor,
            "_extension_status",
            lambda name: NativeExtensionStatus(name=name, available=False),
        )
        message = native_degrade_warning(tmp_path)
        assert message is not None
        assert "frob[native]" in message
        assert native_degrade_warning(None) is not None


class TestScanExternalTools:
    """T-3276: `scan_external_tools` probes every `_EXTERNAL_TOOLS` entry
    -- binaries via `shutil.which`+`--version`, Python packages via
    `importlib.metadata.version` -- and never raises regardless of what
    is present or absent."""

    def test_present_binary_reports_version(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A binary found on PATH reports present=True with a probed
        version string."""
        monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/usr/bin/{name}")
        monkeypatch.setattr(doctor, "_probe_binary_version", lambda name: f"{name} 1.0")
        statuses = {s.name: s for s in scan_external_tools()}
        assert statuses["git"].present is True
        assert statuses["git"].version == "git 1.0"

    def test_missing_binary_reports_absent_with_install_hint(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A binary NOT found on PATH reports present=False, version=None,
        and still carries its `install_hint` (T-3276's must-fire fixture:
        the loud failure must name the tool and how to install it)."""
        monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
        statuses = {s.name: s for s in scan_external_tools()}
        assert statuses["git"].present is False
        assert statuses["git"].version is None
        assert statuses["git"].install_hint

    def test_present_package_reports_version_via_importlib(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A Python-plugin entry (pytest-xdist/pytest-cov) is probed via
        `importlib.metadata.version`, never `shutil.which` (it is loaded
        in-process by pytest, not spawned as its own binary)."""
        monkeypatch.setattr(doctor, "version", lambda name: "3.8.0")
        statuses = {s.name: s for s in scan_external_tools()}
        assert statuses["pytest-xdist"].present is True
        assert statuses["pytest-xdist"].version == "3.8.0"

    def test_missing_package_reports_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`importlib.metadata.version` raising (package not installed)
        reports present=False, never propagates the exception -- this is
        the exact F-011 shape: pytest-xdist absent in a consumer venv."""

        def _raise(name: str) -> str:
            raise ModuleNotFoundError(name)

        monkeypatch.setattr(doctor, "version", _raise)
        statuses = {s.name: s for s in scan_external_tools()}
        assert statuses["pytest-xdist"].present is False
        assert statuses["pytest-xdist"].version is None


class TestExternalToolsRemediation:
    """T-3276: only a missing REQUIRED tool produces a remediation line --
    the category rule (`ToolCategory`'s own docstring) applied."""

    def test_missing_required_tool_names_it_and_the_install_command(self) -> None:
        """Must-fire fixture: a REQUIRED tool's absence names the tool
        and the install command in the returned remediation text."""
        statuses = [
            ExternalToolStatus(
                name="git",
                category=ToolCategory.REQUIRED,
                present=False,
                version=None,
                install_hint="install git (https://git-scm.com)",
            )
        ]
        remediation = _external_tools_remediation(statuses)
        assert remediation is not None
        assert "git" in remediation
        assert "git-scm.com" in remediation

    def test_missing_optional_tool_is_silent(self) -> None:
        """An OPTIONAL or OPTIONAL_FOR_GATE tool's absence never produces
        a `frob doctor` remediation line -- that is the affected gate's
        own UNMEASURED concern, never a doctor health failure."""
        statuses = [
            ExternalToolStatus(
                name="cargo",
                category=ToolCategory.OPTIONAL,
                present=False,
                version=None,
                install_hint="install rustup",
            ),
            ExternalToolStatus(
                name="pytest-xdist",
                category=ToolCategory.OPTIONAL_FOR_GATE,
                present=False,
                version=None,
                install_hint="pip install pytest-xdist",
            ),
        ]
        assert _external_tools_remediation(statuses) is None
