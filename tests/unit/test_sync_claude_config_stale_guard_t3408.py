"""Coverage for `.claude/hooks/sync-claude-config.py`'s T-3408 stale-
source guard: a worktree that has not incorporated a sibling's already-
landed change to a managed file must never silently overwrite that
change globally when it syncs.

Loads the REAL script by file path (`importlib`, mirroring `frob.app.
claude_runner._load_sync_module`'s own technique) rather than a hand-
copied stub -- `.claude/hooks/**` is TEST001-exempt (harness-only
invocation, T-1838/T-1861's precedent), but T-3408's own MUST-FIRE/MUST-
STAY-QUIET fixtures need real coverage against the actual guard logic,
not a re-typed approximation of it that could quietly drift from what
ships.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

_REAL_HOOK = (
    Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "sync-claude-config.py"
)


# frob:waive WIRE001 reason="private test-fixture helper used only by this file's own \
# tests -- no production caller to wire it to by design" permanent="true"
def _load_hook_module() -> ModuleType:
    """Import the real `sync-claude-config.py` by path -- its hyphenated
    filename blocks a normal `import`, same constraint `_load_sync_
    module` (`frob.app.claude_runner`) documents for the identical
    load."""
    spec = importlib.util.spec_from_file_location(
        "_sync_claude_config_under_test", _REAL_HOOK
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def hook():  # noqa: ANN201
    """The real hook module, freshly loaded per test (module-level state
    -- `_REPO`, `MANAGED` -- is cheap enough to not bother caching)."""
    return _load_hook_module()


class TestIsSourceStaleVsMain:
    """`_is_source_stale_vs_main` (T-3408): the pure decision, no git, no
    I/O -- directly testable against synthetic content."""

    # frob:tests tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestIsSourceStaleVsMain.test_unmodified_source_behind_main_is_stale  # noqa: E501
    def test_unmodified_source_behind_main_is_stale(self, hook) -> None:  # noqa: ANN001
        """MUST-FIRE shape: the worktree never touched the file since
        branching (source == merge-base), and main moved it on -- stale."""
        assert (
            hook._is_source_stale_vs_main("old content", "new content", "old content")
            is True
        )

    # frob:tests tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestIsSourceStaleVsMain.test_worktree_own_edit_is_never_stale_even_if_main_also_moved  # noqa: E501
    def test_worktree_own_edit_is_never_stale_even_if_main_also_moved(
        self, hook
    ) -> None:  # noqa: ANN001
        """MUST-STAY-QUIET shape: the worktree edited the file itself
        (source != merge-base) -- ordinary in-place testing, never stale,
        regardless of what main did meanwhile."""
        assert (
            hook._is_source_stale_vs_main(
                "worktree's own edit", "main's own different edit", "old content"
            )
            is False
        )

    # frob:tests tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestIsSourceStaleVsMain.test_source_matches_main_is_not_stale  # noqa: E501
    def test_source_matches_main_is_not_stale(self, hook) -> None:  # noqa: ANN001
        """The ordinary in-sync case -- nothing to refuse."""
        assert (
            hook._is_source_stale_vs_main("same content", "same content", "same content")
            is False
        )

    # frob:tests tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestIsSourceStaleVsMain.test_unknown_git_readings_fail_open  # noqa: E501
    def test_unknown_git_readings_fail_open(self, hook) -> None:  # noqa: ANN001
        """A `None` main/merge-base reading (git failure) must never be
        read as stale -- fail open, matching this module's other best-
        effort git reads."""
        assert hook._is_source_stale_vs_main("x", None, "x") is False
        assert hook._is_source_stale_vs_main("x", "y", None) is False
        assert hook._is_source_stale_vs_main("x", None, None) is False


class TestStaleManagedSourcesAndWriteRefusal:
    """`stale_managed_sources`/`main`'s write path (T-3408): an end-to-end
    fixture against a REAL tiny git repo, one managed file behind main
    (must-fire) and one managed file the worktree itself moved forward
    (must-stay-quiet), synced in the same run."""

    @staticmethod
    def _git(repo: Path, *args: str) -> None:
        env = dict(os.environ)
        env.update(
            {
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@t",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@t",
            }
        )
        subprocess.run(  # noqa: S603
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            env=env,
        )

    def _build_repo(self, tmp_path: Path) -> Path:
        """A real git repo shaped like this one: `.claude/hooks/sync-
        claude-config.py` (the real script, copied verbatim so `_REPO`
        resolves correctly from ITS OWN `parents[2]`) plus two managed
        source files, `stale.py` and `forward.py`. `main` gets a change
        to `stale.py` that a branched-off worktree never sees, and the
        worktree independently edits `forward.py` itself."""
        repo = tmp_path / "repo"
        (repo / ".claude" / "hooks").mkdir(parents=True)
        hook_dest = repo / ".claude" / "hooks" / "sync-claude-config.py"
        hook_dest.write_text(_REAL_HOOK.read_text(encoding="utf-8"), encoding="utf-8")
        (repo / ".claude" / "hooks" / "stale.py").write_text(
            "# original\n", encoding="utf-8"
        )
        (repo / ".claude" / "hooks" / "forward.py").write_text(
            "# original\n", encoding="utf-8"
        )
        self._git(repo, "init", "-q", "-b", "main")
        self._git(repo, "add", "-A")
        self._git(repo, "commit", "-q", "-m", "initial")
        # The worktree branches here.
        self._git(repo, "checkout", "-q", "-b", "wt")
        # The worktree edits forward.py itself (its own in-place change).
        (repo / ".claude" / "hooks" / "forward.py").write_text(
            "# worktree's own edit\n", encoding="utf-8"
        )
        self._git(repo, "add", "-A")
        self._git(repo, "commit", "-q", "-m", "worktree edits forward.py")
        # main, meanwhile, gets a fix to stale.py the worktree never sees.
        self._git(repo, "checkout", "-q", "main")
        (repo / ".claude" / "hooks" / "stale.py").write_text(
            "# main's landed fix\n", encoding="utf-8"
        )
        self._git(repo, "add", "-A")
        self._git(repo, "commit", "-q", "-m", "main lands a fix")
        self._git(repo, "checkout", "-q", "wt")
        return repo

    # frob:tests tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestStaleManagedSourcesAndWriteRefusal.test_stale_file_skipped_forward_file_synced  # noqa: E501
    def test_stale_file_skipped_forward_file_synced(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-FIRE + MUST-STAY-QUIET in one run: syncing from `wt`
        refuses `stale.py` (behind main, would revert main's fix) while
        `forward.py` (the worktree's own ordinary forward change) syncs
        normally, unaffected."""
        repo = self._build_repo(tmp_path)
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
        module = _load_hook_module_at(repo)
        monkeypatch.setattr(
            module,
            "MANAGED",
            [
                (".claude/hooks/stale.py", "hooks/stale.py"),
                (".claude/hooks/forward.py", "hooks/forward.py"),
            ],
        )
        exit_code = module.main([])
        assert exit_code == 1  # a stale skip is reported as a failure
        # stale.py: NOT synced (still reflects wt's own stale copy locally,
        # but the destination must not have been written at all).
        assert not (home / ".claude" / "hooks" / "stale.py").exists()
        # forward.py: synced, because the worktree's own edit is not stale.
        dest = home / ".claude" / "hooks" / "forward.py"
        assert dest.exists()
        assert "worktree's own edit" in dest.read_text(encoding="utf-8")

    # frob:tests tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestStaleManagedSourcesAndWriteRefusal.test_allow_stale_overrides_the_refusal  # noqa: E501
    def test_allow_stale_overrides_the_refusal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`--allow-stale` forces the stale file through anyway -- the
        explicit, named escape hatch, never a silent default."""
        repo = self._build_repo(tmp_path)
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
        module = _load_hook_module_at(repo)
        monkeypatch.setattr(
            module,
            "MANAGED",
            [(".claude/hooks/stale.py", "hooks/stale.py")],
        )
        exit_code = module.main(["--allow-stale"])
        assert exit_code == 0
        assert (home / ".claude" / "hooks" / "stale.py").exists()


# frob:waive WIRE001 reason="private test-fixture helper used only by this file's own \
# tests -- no production caller to wire it to by design" permanent="true"
def _load_hook_module_at(repo: Path) -> ModuleType:
    """Load the copy of `sync-claude-config.py` committed inside `repo`
    (not the real checkout's own copy) so its module-level `_REPO`
    resolves to `repo`, not this repo."""
    path = repo / ".claude" / "hooks" / "sync-claude-config.py"
    spec = importlib.util.spec_from_file_location("_sync_claude_config_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
