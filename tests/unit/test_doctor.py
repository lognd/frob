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
from frob.doctor import NativeExtensionStatus, native_degrade_warning


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
            lambda name: NativeExtensionStatus(name=name, available=True, version="0.1.0"),
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
