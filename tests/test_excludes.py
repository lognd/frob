"""Shared exclude surface: dup/arch/cycle honor [graph] exclude (T-0026)."""

from __future__ import annotations

from pathlib import Path

from frob.excludes import (
    _is_nested_worktree,
    _should_prune_dir,
    is_excluded,
    is_skipped_dir,
    is_test_file,
    iter_files,
    load_exclude_globs,
    walk_pruned,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_is_test_file_by_dir_component():
    """A file under any `tests/` directory component is a test file."""
    assert is_test_file("tests/test_foo.py")
    assert is_test_file("src/pkg/tests/helpers.py")
    assert is_test_file("a/b/tests/c/d.py")


def test_is_test_file_by_name_prefix_suffix():
    """Python `test_*`/`*_test` naming marks a test file anywhere."""
    assert is_test_file("pkg/test_module.py")
    assert is_test_file("pkg/module_test.py")


def test_is_test_file_typescript_naming():
    """TS/JS `*.test.*` and `*_test.*` naming is recognized (the drift the
    three former private copies missed)."""
    assert is_test_file("web/src/app.test.ts")
    assert is_test_file("web/src/app.test.tsx")
    assert is_test_file("web/src/app_test.js")


def test_is_test_file_false_for_production_module():
    """A plain production module is not a test file."""
    assert not is_test_file("src/frob/gates/__init__.py")
    assert not is_test_file("web/src/app.ts")
    assert not is_test_file("pkg/contest.py")  # 'test' as substring, not a marker


# frob:ticket T-0410
def test_builtin_skip_dirs():
    # frob:tests src/frob/excludes.py::is_skipped_dir
    assert is_skipped_dir("node_modules")
    assert is_skipped_dir(".worktrees")
    assert is_skipped_dir("thing.egg-info")
    # T-0410 perf audit finding M6: neither had a tree-sitter grammar to
    # misparse, but every rglob-based stage still walked/stat'd/opened
    # every entry inside them before this fix.
    assert is_skipped_dir(".hypothesis")
    assert is_skipped_dir(".serena")
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


def test_malformed_toml_is_empty_not_raise(tmp_path: Path):
    """A syntactically invalid frob.toml is logged and treated as no excludes,
    not propagated as a TOMLDecodeError."""
    # frob:tests src/frob/excludes.py::load_exclude_globs
    (tmp_path / "frob.toml").write_text("[graph\nnot valid toml", encoding="utf-8")
    assert load_exclude_globs(tmp_path) == ()


def test_exclude_not_a_list_is_empty(tmp_path: Path):
    """`[graph].exclude` set to a non-list value is rejected, not iterated."""
    (tmp_path / "frob.toml").write_text(
        '[graph]\nexclude = "not-a-list"\n', encoding="utf-8"
    )
    assert load_exclude_globs(tmp_path) == ()


def test_exclude_list_with_non_string_entry_is_empty(tmp_path: Path):
    """A list containing a non-string entry is rejected wholesale."""
    (tmp_path / "frob.toml").write_text(
        '[graph]\nexclude = ["ok/**", 42]\n', encoding="utf-8"
    )
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


def test_is_nested_worktree_detects_own_git_dir(tmp_path: Path):
    # frob:tests src/frob/excludes.py::_is_nested_worktree kind="unit"
    nested = tmp_path / ".claude" / "worktrees" / "agent-x"
    nested.mkdir(parents=True)
    (nested / ".git").mkdir()
    assert _is_nested_worktree(nested, tmp_path)


def test_is_nested_worktree_git_file_form(tmp_path: Path):
    """`git worktree add` checkouts use a `.git` FILE (gitdir pointer), not a
    directory -- both forms must be detected."""
    # frob:tests src/frob/excludes.py::_is_nested_worktree kind="unit"
    nested = tmp_path / ".claude" / "worktrees" / "agent-y"
    nested.mkdir(parents=True)
    (nested / ".git").write_text("gitdir: ../../../.git/worktrees/agent-y\n")
    assert _is_nested_worktree(nested, tmp_path)


def test_is_nested_worktree_false_for_root_itself(tmp_path: Path):
    # frob:tests src/frob/excludes.py::_is_nested_worktree kind="unit"
    (tmp_path / ".git").mkdir()
    assert not _is_nested_worktree(tmp_path, tmp_path)


def test_is_nested_worktree_false_for_plain_subdir(tmp_path: Path):
    # frob:tests src/frob/excludes.py::_is_nested_worktree kind="unit"
    plain = tmp_path / "src"
    plain.mkdir()
    assert not _is_nested_worktree(plain, tmp_path)


def test_should_prune_dir_covers_all_three_signals(tmp_path: Path):
    """`_should_prune_dir` prunes on builtin skip-name, exclude glob, or
    nested worktree -- any one signal is sufficient (T-0239)."""
    # frob:tests src/frob/excludes.py::_should_prune_dir kind="unit"
    plain = tmp_path / "src"
    plain.mkdir()
    assert not _should_prune_dir(plain, tmp_path)

    builtin = tmp_path / "node_modules"
    builtin.mkdir()
    assert _should_prune_dir(builtin, tmp_path)

    globbed = tmp_path / "generated"
    globbed.mkdir()
    assert _should_prune_dir(globbed, tmp_path, exclude_globs=("generated/**",))

    worktree = tmp_path / ".claude" / "worktrees" / "agent-z"
    worktree.mkdir(parents=True)
    (worktree / ".git").mkdir()
    assert _should_prune_dir(worktree, tmp_path)


def test_walk_pruned_does_not_descend_venv_or_git(tmp_path: Path):
    """`walk_pruned` never yields a file under a `.venv/` or `.git/`
    subtree -- T-0471's shared os.walk-prune fallback."""
    # frob:tests src/frob/excludes.py::walk_pruned kind="unit"
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x = 1\n")
    venv_dir = tmp_path / ".venv" / "lib" / "site-packages"
    venv_dir.mkdir(parents=True)
    (venv_dir / "pkg.py").write_text("y = 2\n")
    git_dir = tmp_path / ".git" / "objects"
    git_dir.mkdir(parents=True)
    (git_dir / "pack").write_text("binary-ish\n")

    found = {p.relative_to(tmp_path).as_posix() for p in walk_pruned(tmp_path)}

    assert "src/main.py" in found
    assert not any(part.startswith(".venv") for part in found)
    assert not any(part.startswith(".git") for part in found)


def test_iter_files_falls_back_to_walk_pruned_outside_git(tmp_path: Path):
    """A `tmp_path` with no `.git` (not a work tree) uses the `walk_pruned`
    fallback, still pruning `.venv`."""
    # frob:tests src/frob/excludes.py::iter_files kind="unit"
    (tmp_path / "a.py").write_text("1\n")
    (tmp_path / "a.md").write_text("# doc\n")
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    (venv_dir / "b.py").write_text("2\n")

    files = iter_files(tmp_path)
    names = {p.name for p in files}
    assert "a.py" in names
    assert "a.md" in names
    assert "b.py" not in names


def test_iter_files_suffix_filter(tmp_path: Path):
    """`suffix` filters the result set, case-insensitively."""
    # frob:tests src/frob/excludes.py::iter_files kind="unit"
    (tmp_path / "a.py").write_text("1\n")
    (tmp_path / "a.md").write_text("# doc\n")

    py_files = iter_files(tmp_path, suffix=".py")
    assert {p.name for p in py_files} == {"a.py"}


def test_iter_files_git_fast_path_matches_ls_files(tmp_path: Path):
    """Under a real git work tree, `iter_files` returns exactly the tracked
    files (the `git ls-files` fast path), never an untracked/ignored one."""
    # frob:tests src/frob/excludes.py::iter_files kind="unit"
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "tracked.py").write_text("1\n")
    subprocess.run(["git", "add", "tracked.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
    (tmp_path / "untracked.py").write_text("2\n")

    names = {p.name for p in iter_files(tmp_path)}
    assert "tracked.py" in names
    assert "untracked.py" not in names
