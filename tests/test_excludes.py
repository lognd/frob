"""Shared exclude surface: dup/arch/cycle honor [graph] exclude (T-0026)."""

from __future__ import annotations

from pathlib import Path

from frob.excludes import is_excluded, is_skipped_dir, load_exclude_globs

_REPO_ROOT = Path(__file__).resolve().parent.parent


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
    # frob:tests src/frob/excludes.py kind="integration"
    # Drives excludes.py's public load_exclude_globs/is_excluded through a
    # real consumer (find_duplicates), not just in isolation.
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


def test_repo_excludes_litmus_strata_from_obligation_surface():
    """`design/litmus/**` is a T-0130 exclude, mirroring `tests/fixtures/**`.

    Litmus `.strata` files are example models exercised by
    `tests/unit/strata`'s parametrized suite, not maintained product
    surface -- they must stay out of `frob.graph`'s COV001/TEST001
    obligation scan (T-0129 made them graph-tracked; without this exclude
    every public strata construct in them fails the doc/test gate) while
    remaining directly parseable via explicit `frob outline`/`frob
    xref`/`frob cycle` invocations, which never consult this exclude list.
    """
    # frob:tests src/frob/excludes.py::load_exclude_globs kind="unit"
    globs = load_exclude_globs(_REPO_ROOT)
    assert is_excluded("design/litmus/chirp.strata", globs)
    assert is_excluded("design/litmus/payments.strata", globs)
    assert not is_excluded("src/frob/graph/__init__.py", globs)
