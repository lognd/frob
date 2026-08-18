"""T-2509: `_evidence_check_repro`/`_validate_designate_repro_at_parent`'s
merge-base resolution must honour an explicit `--base-ref` that names a
commit reachable from the TICKET's own (worktree) branch, not silently
collapse every such commit to the fork point with whatever `root`'s own
checked-out `HEAD` happens to be.

Deliberately real `git` subprocesses (unlike `test_ticket_runner_designate_
repro.py`, which mocks `frob.gitio._merge_base` entirely) -- mocking that
function would hide exactly the regression this file exists to catch: the
bug was in HOW `_merge_base` gets invoked (against which checkout's HEAD),
not in `_merge_base` itself.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.ticket_runner._verify import (
    _repro_merge_base_root,
    _warn_if_base_ref_not_honoured_exactly,
)
from frob.gitio import _merge_base
from frob.tickets._worktree_guard import FROB_WORKTREE_ENV


# frob:ticket T-2509
def _git(cwd: Path, *args: str) -> None:
    """Run `git <args>` in `cwd`, raising on failure -- this file's own
    minimal spawn helper, no dependency on `frob.gitio` for the SETUP
    steps (only the function under test uses that module)."""
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


# frob:ticket T-2509
def _commit(cwd: Path, name: str, content: str) -> str:
    """Write `name` with `content`, commit it, return the new commit sha."""
    (cwd / name).write_text(content, encoding="utf-8")
    _git(cwd, "add", name)
    _git(cwd, "commit", "-q", "-m", f"add {name}")
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


# frob:ticket T-2509
def _init_repo_with_worktree(tmp_path: Path) -> tuple[Path, Path, str, str]:
    """A primary checkout (`root`) that stays on `main`'s ORIGINAL tip
    (simulating T-1003's root-redirection landing on a checkout that is
    NOT the ticket's own work) plus a real `git worktree add` branch
    (`worktree`) carrying two extra commits (A: test-only, B: fix, B's
    parent is A) -- the exact production topology T-2509's bug fires
    under. Returns `(root, worktree, sha_a, sha_b)`."""
    root = tmp_path / "root"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _git(root, "checkout", "-q", "-b", "main")
    _commit(root, "base.txt", "base")

    worktree = tmp_path / "worktree"
    _git(root, "worktree", "add", "-q", "-b", "ticket-branch", str(worktree), "main")

    sha_a = _commit(worktree, "a.txt", "commit A: test only")
    sha_b = _commit(worktree, "b.txt", "commit B: fix")

    # `root` (the primary checkout) advances PAST the point the ticket
    # branch forked from, exactly like this repo's own fast-moving `main`
    # -- the scenario T-2509's own incident report was measured against.
    _commit(root, "unrelated.txt", "root moved on without this ticket")

    return root, worktree, sha_a, sha_b


# frob:ticket T-2509
class TestReproMergeBaseRoot:
    """`_repro_merge_base_root`: prefers `FROB_WORKTREE` over `root`."""

    # frob:ticket T-2509
    def test_prefers_frob_worktree_env_when_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2509: with `FROB_WORKTREE` set, the ticket's real worktree
        path is returned -- never the (possibly unrelated) `root` this
        command's outer dispatcher resolved."""
        worktree_path = tmp_path / "some-worktree"
        monkeypatch.setenv(FROB_WORKTREE_ENV, str(worktree_path))
        assert _repro_merge_base_root(tmp_path / "root") == worktree_path

    # frob:ticket T-2509
    def test_falls_back_to_root_when_unset(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No `FROB_WORKTREE`: `root` is returned unchanged -- a
        coordinator/human running this directly from the correct
        checkout sees no behavior change."""
        monkeypatch.delenv(FROB_WORKTREE_ENV, raising=False)
        root = tmp_path / "root"
        assert _repro_merge_base_root(root) == root


# frob:ticket T-2509
class TestExplicitBaseRefHonoured:
    """The end-to-end regression T-2509 was filed against."""

    # frob:ticket T-2509
    def test_explicit_base_ref_on_own_branch_is_honoured_not_collapsed_to_fork_point(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2509: passing commit A (a real ancestor of the ticket
        branch's HEAD, commit B) as `--base-ref`, with `FROB_WORKTREE`
        pointed at the real worktree, resolves to A ITSELF -- not to
        `root`'s unrelated fork point. Before the fix, `_merge_base(root,
        sha_a)` (using `root`'s own advanced HEAD) collapsed to the
        ticket branch's single fork point with `root`'s `main`,
        regardless of which of A/B was passed."""
        root, worktree, sha_a, sha_b = _init_repo_with_worktree(tmp_path)
        monkeypatch.setenv(FROB_WORKTREE_ENV, str(worktree))

        merge_base_root = _repro_merge_base_root(root)
        assert merge_base_root == worktree

        resolved = _merge_base(merge_base_root, sha_a)
        assert resolved.is_ok
        assert resolved.danger_ok == sha_a

    # frob:ticket T-2509
    def test_distinct_ancestors_resolve_distinctly(self, tmp_path: Path) -> None:
        """POSITIVE CONTROL: commit A and commit B are DIFFERENT commits
        on the same branch -- passing each as `--base-ref` must resolve
        to a DIFFERENT sha, proving the fix does not just accidentally
        return a fixed value for every input (the exact failure mode the
        original bug report described: every sha collapsed to the SAME
        result)."""
        root, worktree, sha_a, sha_b = _init_repo_with_worktree(tmp_path)
        assert sha_a != sha_b

        resolved_a = _merge_base(worktree, sha_a)
        resolved_b = _merge_base(worktree, sha_b)
        assert resolved_a.is_ok
        assert resolved_b.is_ok
        assert resolved_a.danger_ok == sha_a
        assert resolved_b.danger_ok == sha_b
        assert resolved_a.danger_ok != resolved_b.danger_ok

    # frob:ticket T-2509
    def test_root_without_fix_reproduces_the_original_bug(self, tmp_path: Path) -> None:
        """NEGATIVE CONTROL, documenting the bug this ticket fixes:
        calling `_merge_base` directly against `root` (skipping
        `_repro_merge_base_root`, i.e. the PRE-FIX call shape) DOES
        collapse both A and B to the same (wrong) fork-point commit --
        proving the bug was real, and that `_repro_merge_base_root` is
        the actual fix, not incidental."""
        root, worktree, sha_a, sha_b = _init_repo_with_worktree(tmp_path)

        resolved_a = _merge_base(root, sha_a)
        resolved_b = _merge_base(root, sha_b)
        assert resolved_a.is_ok
        assert resolved_b.is_ok
        assert resolved_a.danger_ok == resolved_b.danger_ok
        assert resolved_a.danger_ok != sha_a
        assert resolved_a.danger_ok != sha_b


# frob:ticket T-2509
class TestWarnIfBaseRefNotHonouredExactly:
    """`_warn_if_base_ref_not_honoured_exactly`: loud, not silent, when a
    caller's literal `--base-ref` genuinely cannot be honoured."""

    # frob:ticket T-2509
    def test_no_warning_when_base_ref_already_matches(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """`base_ref == parent_ref` -- the common, correct case -- logs
        nothing."""
        root, worktree, sha_a, _sha_b = _init_repo_with_worktree(tmp_path)
        _warn_if_base_ref_not_honoured_exactly(worktree, sha_a, sha_a)
        assert "could not be honoured exactly" not in caplog.text

    # frob:ticket T-2509
    def test_warns_when_base_ref_is_not_an_ancestor(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """`base_ref` names a real commit that is NOT an ancestor of the
        checked HEAD (a genuinely diverged ref) -- `parent_ref` differs
        from it, and this must be LOUD, not a silent substitution."""
        root, worktree, sha_a, sha_b = _init_repo_with_worktree(tmp_path)
        # `root`'s own tip is unrelated to the worktree branch -- using it
        # as `base_ref` against `worktree`'s HEAD cannot resolve to itself.
        root_tip = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        resolved = _merge_base(worktree, root_tip)
        assert resolved.is_ok
        with caplog.at_level("WARNING"):
            _warn_if_base_ref_not_honoured_exactly(
                worktree, root_tip, resolved.danger_ok
            )
        assert "could not be honoured exactly" in caplog.text
