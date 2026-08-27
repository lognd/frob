"""Unit tests for frob.app._version_guard.binary_fingerprint_warning (T-3129).

T-3129: `frob.repo_meta.stale_install_warning`'s version-STRING comparison
cannot detect a stale global binary whose declared version never moved
past its last bump. This module's fingerprint check instead compares git
HEAD shas -- T-2884's precedent one layer down, applied to the CLI entry
point itself. These tests use a REAL git repo per tmp_path (subprocess
`git init`/`commit`) rather than mocking `git rev-parse`, so the tests
exercise the actual subprocess path, not just the parsing around it.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from frob.app._version_guard import binary_fingerprint_warning


def _init_git_repo(root: Path) -> str:
    """Initialize a real git repo at `root` with one commit, return its
    HEAD sha -- helper shared by every test below that needs a resolvable
    git ancestor."""
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "test"], cwd=root, check=True)
    (root / "placeholder.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _write_frob_pyproject(root: Path) -> None:
    """Minimal pyproject.toml declaring `[project] name = "frob"` -- the
    `is_frob_own_repo` gate this check's every non-trivial branch requires
    to be True before it does any git work at all."""
    (root / "pyproject.toml").write_text(
        '[project]\nname = "frob"\nversion = "1.0.0"\n'
    )


def test_non_frob_repo_is_quiet(tmp_path: Path) -> None:
    """T-3129 must-stay-quiet: a repo whose pyproject.toml does not
    declare itself as frob (or has none at all) never gets this warning,
    regardless of any git state -- this check is scoped to frob's own
    repo only, mirroring `stale_install_warning`'s identical guard."""
    assert binary_fingerprint_warning(tmp_path) is None


def test_editable_in_tree_run_is_quiet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-3129 must-stay-quiet: when the running package's __init__.py IS
    repo_root/src/frob/__init__.py exactly (an editable install / `uv run
    frob` from this same checkout), no git spawn is even needed -- file
    identity alone proves it is not stale."""
    _write_frob_pyproject(tmp_path)
    local_init = tmp_path / "src" / "frob" / "__init__.py"
    local_init.parent.mkdir(parents=True)
    local_init.write_text("")
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: SimpleNamespace(origin=str(local_init)),
    )

    assert binary_fingerprint_warning(tmp_path) is None


def test_matching_sha_is_quiet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T-3129 must-stay-quiet: the running binary lives OUTSIDE repo_root's
    own src/frob/ (a separate editable checkout, e.g. a sibling worktree)
    but its git HEAD sha matches repo_root's -- provably the same content,
    no warning even though the file path differs."""
    _write_frob_pyproject(tmp_path)
    repo_sha = _init_git_repo(tmp_path)

    other_checkout = tmp_path.parent / "other-checkout"
    # Give the sibling checkout the SAME content sha by checking out the
    # same commit into a linked worktree of tmp_path's repo -- git refuses
    # `worktree add` into a pre-existing non-empty directory, so this must
    # run BEFORE any file is written under other_checkout.
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "worktree",
            "add",
            "--detach",
            str(other_checkout),
        ],
        check=True,
    )
    assert (other_checkout / ".git").exists()
    other_init = other_checkout / "src" / "frob" / "__init__.py"
    other_init.parent.mkdir(parents=True)
    other_init.write_text("")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: SimpleNamespace(origin=str(other_init)),
    )

    result = binary_fingerprint_warning(tmp_path)
    assert result is None, f"expected quiet for matching sha {repo_sha}, got: {result}"


def test_mismatched_sha_warns_loudly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-3129 core case: the running binary's own git checkout resolves to
    a DIFFERENT HEAD sha than repo_root's -- version strings could still
    match (this check never even looks at them), but content provably
    differs. Warns loudly and names the mechanism (git HEAD sha)."""
    _write_frob_pyproject(tmp_path)
    repo_sha = _init_git_repo(tmp_path)

    other_checkout = tmp_path.parent / "other-checkout-diverged"
    other_checkout.mkdir()
    other_sha = _init_git_repo(other_checkout)
    assert other_sha != repo_sha
    other_init = other_checkout / "src" / "frob" / "__init__.py"
    other_init.parent.mkdir(parents=True)
    other_init.write_text("")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: SimpleNamespace(origin=str(other_init)),
    )

    warning = binary_fingerprint_warning(tmp_path)

    assert warning is not None
    assert "git HEAD" in warning
    assert repo_sha in warning
    assert other_sha in warning
    assert "version" in warning.lower()


def test_unresolvable_running_sha_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-2884's fail-safe-to-stale direction, reapplied: a running package
    location with NO .git ancestor at all (the real shape of a `uv tool
    install`ed global binary's site-packages copy) resolves to an
    unresolvable sha -- that must warn, never be silently treated as
    equivalent to a genuine in-tree match."""
    _write_frob_pyproject(tmp_path)
    _init_git_repo(tmp_path)

    no_git_dir = tmp_path.parent / "packaged-install-no-git"
    installed_init = no_git_dir / "site-packages" / "frob" / "__init__.py"
    installed_init.parent.mkdir(parents=True)
    installed_init.write_text("")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: SimpleNamespace(origin=str(installed_init)),
    )

    warning = binary_fingerprint_warning(tmp_path)

    assert warning is not None
    assert "unresolvable" in warning.lower()


def test_no_frob_spec_is_quiet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Defensive: if `importlib.util.find_spec('frob')` itself returns
    None or an origin-less spec (should not happen for a running `frob`
    process, but the code must not crash), the check degrades to quiet
    rather than raising."""
    _write_frob_pyproject(tmp_path)
    _init_git_repo(tmp_path)
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)

    assert binary_fingerprint_warning(tmp_path) is None
