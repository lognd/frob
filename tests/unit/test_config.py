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

from pathlib import Path

from frob.app.config import (
    ARCH_DEFAULT_MAX_CLASS_METHODS,
    ARCH_DEFAULT_MAX_FILE_LINES,
    ARCH_DEFAULT_MAX_FUNCTION_LINES,
    ARCH_DEFAULT_MAX_LOCAL_IMPORTS,
    ARCH_DEFAULT_MAX_NESTING_DEPTH,
    load_arch_config,
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
