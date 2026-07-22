"""T-0736: managed boilerplate blocks (Makefile core-shim, standard
`.gitignore` entries, worktree-lease hooks) -- conformance status and
idempotent `apply`."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.scaffold._managed import (
    MANAGED_HOOK_NAMES,
    MANAGED_TEXT_BLOCKS,
    apply_managed_blocks,
    scaffold_conformance_status,
)


# frob:ticket T-0736
def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    """Run a git command in `cwd`, never raising -- callers assert on the
    returncode/output themselves."""
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )


# frob:ticket T-0736
def _init_repo(root: Path) -> None:
    """A minimal git repo at `root`, enough for `_hooks_dir`/git-hook
    installation to resolve a real hooks path."""
    root.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)


# frob:ticket T-0736
class TestScaffoldConformanceStatus:
    """Tests for `scaffold_conformance_status` (T-0736)."""

    # frob:ticket T-0736
    def test_non_frob_repo_reports_nothing(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_scaffold_managed.py::TestScaffoldConformanceStatus.test_non_frob_repo_reports_nothing  # noqa: E501
        """No `frob.toml` under `root` -- opt-in, nothing to be behind on,
        so this reports empty rather than flagging every block missing."""
        assert scaffold_conformance_status(tmp_path) == ()

    # frob:ticket T-0736
    def test_clean_after_apply(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_scaffold_managed.py::TestScaffoldConformanceStatus.test_clean_after_apply  # noqa: E501
        """After `apply_managed_blocks`, every block reports present and
        not stale."""
        _init_repo(tmp_path)
        (tmp_path / "frob.toml").write_text("[project]\n")
        result = apply_managed_blocks(tmp_path)
        assert result.is_ok

        statuses = scaffold_conformance_status(tmp_path)
        expected_count = len(MANAGED_TEXT_BLOCKS) + len(MANAGED_HOOK_NAMES)
        assert len(statuses) == expected_count
        assert all(s.present and not s.stale for s in statuses)


# frob:ticket T-0736
class TestApplyManagedBlocks:
    """Tests for `apply_managed_blocks` (T-0736)."""

    # frob:ticket T-0736
    def test_creates_missing_and_updates_stale(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks.test_creates_missing_and_updates_stale  # noqa: E501
        """A repo with no Makefile/.gitignore/hooks at all gets every block
        created; re-applying after hand-corrupting one block's region
        reports it updated, not re-created."""
        _init_repo(tmp_path)
        (tmp_path / "frob.toml").write_text("[project]\n")

        first = apply_managed_blocks(tmp_path).danger_ok
        assert any("created" in line for line in first)
        assert (tmp_path / "Makefile").exists()
        assert (tmp_path / ".gitignore").exists()

        # Corrupt the gitignore block's content in place (still between
        # its markers) to simulate drift from an older frob version.
        gitignore = tmp_path / ".gitignore"
        text = gitignore.read_text()
        corrupted = text.replace("build/", "build/\nstale-extra-line/")
        gitignore.write_text(corrupted)

        statuses = scaffold_conformance_status(tmp_path)
        by_id = {s.block_id: s for s in statuses}
        assert by_id["gitignore-standard"].stale is True

        second = apply_managed_blocks(tmp_path).danger_ok
        assert any("updated stale block gitignore-standard" in line for line in second)

        statuses_after = scaffold_conformance_status(tmp_path)
        by_id_after = {s.block_id: s for s in statuses_after}
        assert by_id_after["gitignore-standard"].stale is False

    # frob:ticket T-0736
    def test_idempotent_second_run_is_noop(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks.test_idempotent_second_run_is_noop  # noqa: E501
        """Applying twice in a row with no changes in between reports every
        text block already current the second time."""
        _init_repo(tmp_path)
        (tmp_path / "frob.toml").write_text("[project]\n")

        apply_managed_blocks(tmp_path)
        second = apply_managed_blocks(tmp_path).danger_ok
        text_block_lines = [
            line
            for line in second
            if any(line.startswith(f"{b.target}:") for b in MANAGED_TEXT_BLOCKS)
        ]
        assert text_block_lines
        assert all("already current" in line for line in text_block_lines)

    # frob:ticket T-0736
    def test_refuses_to_clobber_foreign_hook(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks.test_refuses_to_clobber_foreign_hook  # noqa: E501
        """A pre-existing, non-frob `pre-commit` hook is left untouched --
        `apply` reports it as foreign rather than overwriting it."""
        _init_repo(tmp_path)
        (tmp_path / "frob.toml").write_text("[project]\n")
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        foreign = hooks_dir / "pre-commit"
        foreign.write_text("#!/bin/sh\necho custom hook\n")

        changes = apply_managed_blocks(tmp_path).danger_ok
        assert any("NOT frob's own" in line for line in changes)
        assert foreign.read_text() == "#!/bin/sh\necho custom hook\n"
