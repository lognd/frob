"""
Unit tests for frob.app.config.load_arch_config (T-0373).

The arch gate (frob.gates._arch.arch_gate) used to always call
frob.arch.analyze_project with its own conservative keyword defaults
(30-line functions, 500-line files), silently ignoring a repo's disclosed
calibration decision. load_arch_config is the fix: it reads the [arch]
table from frob.toml, falling back to the calibrated defaults (60/800/etc)
when frob.toml is missing, unreadable, or has no [arch] table.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from frob.app.config import (
    ARCH_DEFAULT_MAX_CLASS_METHODS,
    ARCH_DEFAULT_MAX_FILE_LINES,
    ARCH_DEFAULT_MAX_FUNCTION_LINES,
    ARCH_DEFAULT_MAX_LOCAL_IMPORTS,
    ARCH_DEFAULT_MAX_NESTING_DEPTH,
    load_arch_config,
    stale_install_warning,
)


def test_reads_override(tmp_path: Path) -> None:
    """A frob.toml [arch] table fully overrides the calibrated defaults."""
    (tmp_path / "frob.toml").write_text(
        "[arch]\n"
        "max_function_lines = 45\n"
        "max_class_methods = 20\n"
        "max_local_imports = 10\n"
        "max_nesting_depth = 5\n"
        "max_file_lines = 900\n"
    )
    cfg = load_arch_config(tmp_path)
    assert cfg == {
        "max_function_lines": 45,
        "max_class_methods": 20,
        "max_local_imports": 10,
        "max_nesting_depth": 5,
        "max_file_lines": 900,
    }


def test_missing_toml_defaults(tmp_path: Path) -> None:
    """No frob.toml at all falls back to the calibrated 60/800/etc defaults."""
    cfg = load_arch_config(tmp_path)
    assert cfg == {
        "max_function_lines": ARCH_DEFAULT_MAX_FUNCTION_LINES,
        "max_class_methods": ARCH_DEFAULT_MAX_CLASS_METHODS,
        "max_local_imports": ARCH_DEFAULT_MAX_LOCAL_IMPORTS,
        "max_nesting_depth": ARCH_DEFAULT_MAX_NESTING_DEPTH,
        "max_file_lines": ARCH_DEFAULT_MAX_FILE_LINES,
    }
    assert cfg["max_function_lines"] == 60
    assert cfg["max_file_lines"] == 800


def test_missing_section_defaults(tmp_path: Path) -> None:
    """A frob.toml with no [arch] table at all also falls back to calibrated defaults."""
    (tmp_path / "frob.toml").write_text('[graph]\nexclude = ["vendor/**"]\n')
    cfg = load_arch_config(tmp_path)
    assert cfg["max_function_lines"] == 60
    assert cfg["max_file_lines"] == 800


def test_partial_override(tmp_path: Path) -> None:
    """Keys omitted from a present [arch] table keep their calibrated default."""
    (tmp_path / "frob.toml").write_text("[arch]\nmax_file_lines = 1200\n")
    cfg = load_arch_config(tmp_path)
    assert cfg["max_file_lines"] == 1200
    assert cfg["max_function_lines"] == ARCH_DEFAULT_MAX_FUNCTION_LINES
    assert cfg["max_class_methods"] == ARCH_DEFAULT_MAX_CLASS_METHODS


def test_malformed_toml_defaults(tmp_path: Path) -> None:
    """A frob.toml that fails to parse degrades to the calibrated defaults, not a crash."""
    (tmp_path / "frob.toml").write_text("this is not [valid toml")
    cfg = load_arch_config(tmp_path)
    assert cfg["max_function_lines"] == 60
    assert cfg["max_file_lines"] == 800


def _write_frob_pyproject(root: Path, version: str) -> None:
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "frob"\nversion = "{version}"\n'
    )


def test_stale_install_warning_flags_version_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-0358: an installed frob (metadata version 0.9.0) running against a
    checkout whose pyproject.toml declares 0.27.0, from a package location
    OUTSIDE that checkout's own src/frob/, gets a loud warning naming both
    versions -- the stale-global-binary phantom-numbers trap."""
    _write_frob_pyproject(tmp_path, "0.27.0")
    installed_init = tmp_path / "elsewhere" / "site-packages" / "frob" / "__init__.py"
    installed_init.parent.mkdir(parents=True)
    installed_init.write_text("")
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: SimpleNamespace(origin=str(installed_init)),
    )
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "0.9.0")

    warning = stale_install_warning(tmp_path)

    assert warning is not None
    assert "0.9.0" in warning
    assert "0.27.0" in warning


def test_stale_install_warning_none_for_editable_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No warning when the running package IS this checkout's own
    src/frob/__init__.py (an editable install / `uv run frob`), even if
    metadata reports a different version string than pyproject.toml."""
    _write_frob_pyproject(tmp_path, "0.27.0")
    local_init = tmp_path / "src" / "frob" / "__init__.py"
    local_init.parent.mkdir(parents=True)
    local_init.write_text("")
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: SimpleNamespace(origin=str(local_init)),
    )
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "0.9.0")

    assert stale_install_warning(tmp_path) is None


def test_stale_install_warning_none_when_versions_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No warning when the installed version already matches the
    checkout's declared version, even from an outside package location."""
    _write_frob_pyproject(tmp_path, "0.27.0")
    installed_init = tmp_path / "elsewhere" / "site-packages" / "frob" / "__init__.py"
    installed_init.parent.mkdir(parents=True)
    installed_init.write_text("")
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: SimpleNamespace(origin=str(installed_init)),
    )
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "0.27.0")

    assert stale_install_warning(tmp_path) is None
