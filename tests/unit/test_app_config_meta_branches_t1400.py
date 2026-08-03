"""T-1400 branch-gap closure for `frob.app._config_meta.stale_install_warning`.

`tests/unit/test_config.py` already covers the version-mismatch,
editable-checkout, and matching-version branches (T-0358's original
suite). This file targets the remaining early-return branches that suite
never reaches: no declared repo version at all, an unresolvable
`importlib.util.find_spec` (no spec / no origin), and the two
`importlib.metadata.version` failure paths (`PackageNotFoundError` and a
generic lookup failure) -- each a distinct `None`-returning branch in the
function's body.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from frob.app._config_meta import stale_install_warning


def _write_frob_pyproject(root: Path, version: str) -> None:
    """Write a minimal `[project] name = "frob"` pyproject.toml declaring `version`."""
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "frob"\nversion = "{version}"\n'
    )


class TestStaleInstallWarningNoDeclaredVersion:
    """The `if not repo_version: return None` branch."""

    def test_no_pyproject_returns_none(self, tmp_path: Path) -> None:
        """No pyproject.toml at all means no declared version -- silent None."""
        assert stale_install_warning(tmp_path) is None

    def test_pyproject_not_frob_returns_none(self, tmp_path: Path) -> None:
        """A pyproject.toml for a DIFFERENT project name is not this repo at all."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "not-frob"\nversion = "1.0.0"\n'
        )
        assert stale_install_warning(tmp_path) is None


class TestStaleInstallWarningUnresolvableSpec:
    """The `spec is None or spec.origin is None` branch."""

    def test_find_spec_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`importlib.util.find_spec("frob")` returning None (package not
        importable under this name at all) is treated as unresolvable, not
        a crash."""
        _write_frob_pyproject(tmp_path, "0.27.0")
        monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
        assert stale_install_warning(tmp_path) is None

    def test_find_spec_origin_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A spec with `origin=None` (e.g. a namespace package) is also
        unresolvable."""
        _write_frob_pyproject(tmp_path, "0.27.0")
        monkeypatch.setattr(
            importlib.util,
            "find_spec",
            lambda name: SimpleNamespace(origin=None),
        )
        assert stale_install_warning(tmp_path) is None


class TestStaleInstallWarningMetadataLookupFailures:
    """The two `importlib.metadata.version` exception branches."""

    def test_package_not_found_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`PackageNotFoundError` (no installed distribution metadata at
        all -- e.g. a pure editable/no-dist-info checkout) degrades to
        None rather than propagating."""
        _write_frob_pyproject(tmp_path, "0.27.0")
        installed_init = (
            tmp_path / "elsewhere" / "site-packages" / "frob" / "__init__.py"
        )
        installed_init.parent.mkdir(parents=True)
        installed_init.write_text("")
        monkeypatch.setattr(
            importlib.util,
            "find_spec",
            lambda name: SimpleNamespace(origin=str(installed_init)),
        )

        def _raise_not_found(name: str) -> str:
            raise importlib.metadata.PackageNotFoundError(name)

        monkeypatch.setattr(importlib.metadata, "version", _raise_not_found)
        assert stale_install_warning(tmp_path) is None

    def test_generic_metadata_error_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Any other metadata-lookup failure is a best-effort probe --
        logged at debug and swallowed to None, never fatal to the caller."""
        _write_frob_pyproject(tmp_path, "0.27.0")
        installed_init = (
            tmp_path / "elsewhere" / "site-packages" / "frob" / "__init__.py"
        )
        installed_init.parent.mkdir(parents=True)
        installed_init.write_text("")
        monkeypatch.setattr(
            importlib.util,
            "find_spec",
            lambda name: SimpleNamespace(origin=str(installed_init)),
        )

        def _raise_generic(name: str) -> str:
            raise ValueError("corrupt metadata")

        monkeypatch.setattr(importlib.metadata, "version", _raise_generic)
        assert stale_install_warning(tmp_path) is None
