"""Shared exclude surface: dup/arch/cycle honor [graph] exclude (T-0026)."""

from __future__ import annotations

from pathlib import Path

from frob.excludes import is_excluded, is_skipped_dir, load_exclude_globs


def test_builtin_skip_dirs():
    # frob:tests src/frob/excludes.py::is_skipped_dir
    assert is_skipped_dir("node_modules")
    assert is_skipped_dir(".worktrees")
    assert is_skipped_dir("thing.egg-info")
    assert not is_skipped_dir("src")


def test_load_and_match_globs(tmp_path: Path):
    # frob:tests src/frob/excludes.py::load_exclude_globs
    (tmp_path / "frob.toml").write_text(
        '[graph]\nexclude = ["generated/**", "vendor/**"]\n', encoding="utf-8"
    )
    globs = load_exclude_globs(tmp_path)
    # frob:tests src/frob/excludes.py::is_excluded kind="unit"
    assert is_excluded("generated/api.ts", globs)
    assert is_excluded("vendor/dep/x.py", globs)
    assert not is_excluded("src/main.py", globs)


def test_absent_config_is_empty(tmp_path: Path):
    assert load_exclude_globs(tmp_path) == ()


def test_dup_scanner_honors_exclude(tmp_path: Path):
    # frob:tests src/frob/dup/_legacy.py::find_duplicates
    from frob.dup import find_duplicates

    (tmp_path / "frob.toml").write_text(
        '[graph]\nexclude = ["generated/**"]\n', encoding="utf-8"
    )
    dup_body = "def a(x):\n    y = x + 1\n    z = y * 2\n    return z + y - x\n"
    (tmp_path / "real.py").write_text(dup_body)
    gen = tmp_path / "generated"
    gen.mkdir()
    (gen / "copy.py").write_text(dup_body)
    result = find_duplicates(tmp_path)
    hit_files = {frag.file for group in result.groups for frag in group.fragments}
    assert not any("generated" in f for f in hit_files)
