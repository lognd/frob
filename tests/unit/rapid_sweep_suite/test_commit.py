"""Rapid-debt commit and ledger-write tests for `frob.app.ticket_runner._rapid_sweep`
(T-3595 split of the former tests/unit/test_rapid_sweep.py)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from frob.app.ticket_runner import _rapid_sweep
from frob.app.ticket_runner._rapid_sweep import (
    _ticket_is_open,
)
from tests.conftest import (
    _git,
    _seed_repo,
    _seed_ticket,
)


class TestCommitRapidDebt:
    """T-1698: a rapid land must leave the ROOT CHECKOUT CLEAN. One
    uncommitted debt line deadlocked a whole three-agent wave, because
    every later land refused with DirtyMain."""

    def test_leaves_the_repo_clean(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt.test_leaves_\
        # the_repo_clean
        # T-2997: record_rapid_debt now writes under gitignored .frob/,
        # so the repo is already clean before _commit_rapid_debt even
        # runs -- it stays a correct, harmless no-op (nothing tracked to
        # stage or commit) rather than the "stage and commit one dirty
        # line" step it used to be.
        from frob.tickets._evidence import record_rapid_debt

        repo = _seed_repo(tmp_path)

        record_rapid_debt(repo, "T-0001", "post-land-unscoped-sweep-deferred")
        assert _git(repo, "status", "--porcelain").strip() == ""
        _rapid_sweep._commit_rapid_debt(repo, "T-0001")
        assert _git(repo, "status", "--porcelain").strip() == ""
        assert "rapid-debt.jsonl" not in _git(repo, "ls-files")

    # frob:ticket T-2669
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_guard_still_refuses_a_genuinely_foreign_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt.test_guard_still_refuses_a_genuinely_foreign_file  # noqa: E501
        """Must-fire control, other direction from the test above: T-2669's
        fix scopes `FROB_LAND_INTERNAL=1` to ONLY the one `git commit`
        spawn `_commit_rapid_debt` makes for `rapid-debt.jsonl` -- it must
        not leak into, or otherwise weaken, the T-2071 guard's refusal of
        an UNRELATED non-ledger file committed the same way a stray agent
        write would be. Proves the fix is a narrow exemption for this
        module's own machinery file, not a general bypass."""
        import subprocess

        from frob.scaffold import install_worktree_lease_hook

        repo = _seed_repo(tmp_path)
        installed = install_worktree_lease_hook(repo)
        assert installed.is_ok

        worktree_dir = tmp_path.parent / "linked-worktree-t2669-control"
        current_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
        _git(
            repo,
            "worktree",
            "add",
            "-b",
            "agent-branch-t2669-control",
            str(worktree_dir),
            current_branch,
        )

        (repo / "stray.py").write_text("z = 1\n", encoding="utf-8")
        _git(repo, "add", "--", "stray.py")

        monkeypatch.delenv("FROB_LAND_INTERNAL", raising=False)
        monkeypatch.delenv("FROB_AGENT", raising=False)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "stray agent write"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode != 0, commit.stdout + commit.stderr
        assert _git(repo, "status", "--porcelain").strip() != ""

    def test_stages_only_the_debt_file(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt.test_stages_only_the_debt_file  # noqa: E501
        from frob.tickets._evidence import record_rapid_debt

        repo = _seed_repo(tmp_path)

        # Another agent's in-flight edit on the shared root checkout: a
        # blanket `git add -A` here would swallow it into this commit.
        (repo / "seed.txt").write_text("someone else is mid-land\n", encoding="utf-8")
        record_rapid_debt(repo, "T-0002", "post-land-unscoped-sweep-deferred")
        _rapid_sweep._commit_rapid_debt(repo, "T-0002")
        porcelain = _git(repo, "status", "--porcelain")
        assert "seed.txt" in porcelain
        assert "rapid-debt.jsonl" not in porcelain

    def test_is_a_noop_when_nothing_was_appended(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt.test_is_a_noop_when_nothing_was_appended  # noqa: E501
        repo = _seed_repo(tmp_path)
        head_before = _git(repo, "rev-parse", "HEAD").strip()
        _rapid_sweep._commit_rapid_debt(repo, "T-0003")
        assert _git(repo, "rev-parse", "HEAD").strip() == head_before

    def test_a_non_repo_never_raises(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt.test_a_non_repo_never_raises  # noqa: E501
        # Best-effort: it must never fail a land that already succeeded.
        _rapid_sweep._commit_rapid_debt(tmp_path, "T-0004")

    # frob:ticket T-2669
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_survives_the_scaffolded_root_write_guard(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt.test_survives_the_scaffolded_root_write_guard  # noqa: E501
        """T-2669: `_seed_repo` above has no scaffolded pre-commit hook and
        no linked worktree, so none of the other tests in this class can
        reproduce the real incident -- a rapid land's shared-root checkout
        has BOTH (the T-0731/T-2071 `pre-commit` hook is scaffolded onto
        every real clone, and a dispatched fleet always has at least one
        linked worktree). Under that real shape, `_commit_rapid_debt`'s
        `git commit` spawn hits the T-2071 guard (`non-ledger file staged
        directly in the primary checkout while worktrees exist`) exactly
        like any other unflagged non-ledger commit would, because it never
        sets `FROB_LAND_INTERNAL=1` around the spawn the way every other
        land-internal commit in `_land_git_ops.py` does -- reproduced here
        by installing the real hook and adding a real linked worktree
        before calling it, not by asserting on the hook's shell source."""
        from frob.scaffold import install_worktree_lease_hook
        from frob.tickets._evidence import record_rapid_debt

        repo = _seed_repo(tmp_path)
        installed = install_worktree_lease_hook(repo)
        assert installed.is_ok

        worktree_dir = tmp_path.parent / "linked-worktree-t2669"
        current_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
        _git(
            repo,
            "worktree",
            "add",
            "-b",
            "agent-branch-t2669",
            str(worktree_dir),
            current_branch,
        )

        # T-2997: record_rapid_debt writes under gitignored .frob/ now,
        # so the repo is already clean -- the T-2071 guard this test
        # exists to prove `_commit_rapid_debt` survives is simply never
        # reached any more (nothing dirty to stage or commit). The guard
        # itself is exercised elsewhere (test_guard_still_refuses_a_
        # genuinely_foreign_file, above); this test now proves the
        # no-op stays a no-op under the same real-shape preconditions
        # (scaffolded hook + linked worktree).
        record_rapid_debt(repo, "T-2669", "post-land-unscoped-sweep-deferred")
        assert _git(repo, "status", "--porcelain").strip() == ""

        # The real incident's shell has neither var set -- this is a
        # dispatched land process's own environment, not an agent shell.
        monkeypatch.delenv("FROB_LAND_INTERNAL", raising=False)
        monkeypatch.delenv("FROB_AGENT", raising=False)
        _rapid_sweep._commit_rapid_debt(repo, "T-2669")

        # The actual invariant: the shared root must be left CLEAN, not
        # merely "a commit helper ran without raising".
        assert _git(repo, "status", "--porcelain").strip() == "", (
            "rapid-debt.jsonl commit was refused by the scaffolded "
            "pre-commit hook (T-2071) and the root was left dirty"
        )
        assert "rapid-debt.jsonl" not in _git(repo, "ls-files")

    # frob:ticket T-2671
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_commit_failure_persists_a_diagnostic_log(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt.test_commit_failure_persists_a_diagnostic_log  # noqa: E501
        """T-2671: reproduces the T-2669-shaped commit-failure directly
        (the scaffolded pre-commit hook refuses the commit spawn because
        neither lease-env var is set) and proves a retained diagnostic
        log survives it -- the exact artifact that did not exist for the
        real recurrence this ticket investigates. Before this fix,
        `_commit_rapid_debt`'s failure branch logged a one-line summary
        via the module logger and nothing else; this test would have
        found zero files under `.frob/rapid-sweep/` naming the failure."""
        from frob.scaffold import install_worktree_lease_hook

        repo = _seed_repo(tmp_path)
        installed = install_worktree_lease_hook(repo)
        assert installed.is_ok

        worktree_dir = tmp_path.parent / "linked-worktree-t2671"
        current_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
        _git(
            repo,
            "worktree",
            "add",
            "-b",
            "agent-branch-t2671",
            str(worktree_dir),
            current_branch,
        )

        # T-2997: record_rapid_debt no longer dirties the repo (it writes
        # under gitignored .frob/), so `_commit_rapid_debt`'s failure
        # branch (the thing under test here) can only still be reached
        # via a manually force-tracked rapid-debt.jsonl -- simulating
        # legacy/residual dirt at the pre-T-2997 root path, the one shape
        # left that can still make this now-mostly-dead helper's `git
        # status -- rapid-debt.jsonl` spawn see something dirty.
        (repo / "rapid-debt.jsonl").write_text(
            '{"ticket": "T-2671"}\n', encoding="utf-8"
        )
        _git(repo, "add", "--force", "rapid-debt.jsonl")
        assert _git(repo, "status", "--porcelain").strip() != ""

        # Force the commit step itself to be refused: bypass T-2669's own
        # `_land_internal_git_env` fix by monkeypatching it to a no-op
        # context manager, so the underlying hook refusal this test wants
        # to reproduce actually fires (T-2669 would otherwise mask it).
        import contextlib

        monkeypatch.setattr(
            "frob.tickets._land_git_ops._land_internal_git_env",
            contextlib.nullcontext,
        )
        monkeypatch.delenv("FROB_LAND_INTERNAL", raising=False)
        monkeypatch.delenv("FROB_AGENT", raising=False)

        _rapid_sweep._commit_rapid_debt(repo, "T-2671")

        # The commit was refused, so the root is still dirty ...
        assert _git(repo, "status", "--porcelain").strip() != ""
        # ... but a diagnostic log naming the failure now survives it.
        log_dir = repo / _rapid_sweep._LOG_DIR_REL
        logs = sorted(
            log_dir.glob(f"{_rapid_sweep._RAPID_DEBT_FAILURE_LOG_PREFIX}-T-2671-*.log")
        )
        assert len(logs) == 1, f"expected exactly one diagnostic log, found {logs}"
        payload = json.loads(logs[0].read_text(encoding="utf-8"))
        assert payload["ticket_id"] == "T-2671"
        assert payload["step"] == "commit"
        assert payload["outcome"] == "nonzero_returncode"
        assert payload["returncode"] != 0
        assert payload["stderr"]  # the hook's refusal text, not empty



class TestPersistCommitStepFailure:
    """T-2671: `_persist_commit_step_failure` is the retained-diagnostic
    primitive `_commit_rapid_debt` calls on every git-step failure -- the
    thing missing when the ticket's own DirtyMain recurrence could not be
    diagnosed because no land-invocation output survived it."""

    def test_writes_proc_result_diagnostics(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestPersistCommitStepFailure.test_writes_proc_result_diagnostics  # noqa: E501
        from typani.result import Ok

        from frob.gitio import ProcResult

        outcome = Ok(
            ProcResult(
                argv=("git", "commit", "-m", "x"),
                returncode=1,
                stdout="",
                stderr="hook refused: DirtyMain guard",
            )
        )
        path = _rapid_sweep._persist_commit_step_failure(
            tmp_path, "T-9001", "commit", outcome
        )
        assert path is not None
        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload == {
            "ticket_id": "T-9001",
            "step": "commit",
            "timestamp_utc": payload["timestamp_utc"],
            "outcome": "nonzero_returncode",
            "argv": ["git", "commit", "-m", "x"],
            "returncode": 1,
            "stdout": "",
            "stderr": "hook refused: DirtyMain guard",
        }

    def test_writes_spawn_error_diagnostics(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestPersistCommitStepFailure.test_writes_spawn_error_diagnostics  # noqa: E501
        from typani.result import Err

        from frob.gitio import GitError

        outcome = Err(GitError.GitFailed)
        path = _rapid_sweep._persist_commit_step_failure(
            tmp_path, "T-9002", "status", outcome
        )
        assert path is not None
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["outcome"] == "spawn_failed"
        assert payload["step"] == "status"
        assert "GitFailed" in payload["git_error"]
        # No ProcResult fields (no process ever ran) -- these key names
        # must not silently appear with a placeholder value.
        assert "argv" not in payload
        assert "returncode" not in payload

    def test_swallows_its_own_write_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestPersistCommitStepFailure.test_swallows_its_own_write_failure  # noqa: E501
        from typani.result import Err

        from frob.gitio import GitError

        # A root whose log dir cannot be created (a FILE sits where the
        # directory would go) -- this must return None, not raise, since
        # `_commit_rapid_debt` calls this from inside its own failure
        # path and a second exception there would be strictly worse.
        blocker = tmp_path / ".frob"
        blocker.write_text("not a directory\n", encoding="utf-8")
        outcome = Err(GitError.GitFailed)
        path = _rapid_sweep._persist_commit_step_failure(
            tmp_path, "T-9003", "add", outcome
        )
        assert path is None



# frob:ticket T-3216
class TestPorcelainStatusError:
    """T-3216: `_porcelain_status_error` -- the single source of truth
    for telling "git status could not be read" apart from "read fine,
    found nothing", which `_porcelain_dirty_paths`'s empty-tuple return
    collapses for its many other (unchanged) callers."""

    def test_readable_status_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestPorcelainStatusError.test_readable_status_is_none  # noqa: E501
        from frob.tickets._land_git_ops import _porcelain_status_error

        repo = _seed_repo(tmp_path)
        assert _porcelain_status_error(repo) is None

    def test_spawn_failure_names_the_git_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestPorcelainStatusError.test_spawn_failure_names_the_git_error  # noqa: E501
        from typani import Err

        import frob.tickets._land_git_ops as land_git_ops_mod
        from frob.gitio import GitError
        from frob.tickets._land_git_ops import _porcelain_status_error

        monkeypatch.setattr(
            land_git_ops_mod, "run_argv", lambda *a, **k: Err(GitError.GitFailed)
        )
        error = _porcelain_status_error(tmp_path)
        assert error is not None
        assert "spawn failed" in error

    def test_nonzero_exit_names_stderr(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestPorcelainStatusError.test_nonzero_exit_names_stderr  # noqa: E501
        from typani import Ok

        import frob.tickets._land_git_ops as land_git_ops_mod
        from frob.tickets._land_git_ops import _porcelain_status_error

        def _fail(*a: object, **k: object):
            class _Proc:
                returncode = 128
                stdout = ""
                stderr = "fatal: Unable to create '.git/index.lock': File exists."

            return Ok(_Proc())

        monkeypatch.setattr(land_git_ops_mod, "run_argv", _fail)
        error = _porcelain_status_error(tmp_path)
        assert error is not None
        assert "index.lock" in error



class TestDescribeRootDirt:
    """T-1698: a DirtyMain refusal must name what made it refuse."""

    def test_names_the_paths(self) -> None:
        # frob:tests \
        # tests/unit/rapid_sweep_suite/test_commit.py::TestDescribeRootDirt.test_names_\
        # the_paths
        from frob.tickets._land_git_ops import _render_dirty_paths

        assert _render_dirty_paths(("a.py", "b.md")) == "a.py, b.md"

    def test_truncation_declares_itself(self) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestDescribeRootDirt.test_truncation_declares_itself  # noqa: E501
        from frob.tickets._land_git_ops import _render_dirty_paths

        rendered = _render_dirty_paths(tuple(f"f{i}.py" for i in range(14)))
        assert rendered.endswith("(+4 more)")

    def test_empty_paths_renders_as_none_not_unavailable(self) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestDescribeRootDirt.test_empty_paths_renders_as_none_not_unavailable  # noqa: E501
        # T-3216: `_render_dirty_paths` no longer guesses "unreadable"
        # from emptiness -- its only caller (`describe_root_dirt`) now
        # asks `_porcelain_status_error` directly and never reaches this
        # function on the unreadable path, so an empty `paths` here
        # means the status call succeeded and found nothing.
        from frob.tickets._land_git_ops import _render_dirty_paths

        assert _render_dirty_paths(()) == "(none)"

    # frob:ticket T-3216
    def test_status_unreadable_names_the_git_error_not_uncommitted_work(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestDescribeRootDirt.test_status_unreadable_names_the_git_error_not_uncommitted_work  # noqa: E501
        # T-3216's exact incident: `git status` itself fails (index.lock
        # contention). The rendered description must name STATUS-
        # UNREADABLE and the underlying error, never assert uncommitted
        # work exists.
        import frob.tickets._land_git_ops as land_git_ops_mod
        from frob.tickets._land_git_ops import describe_root_dirt

        def _fail(*a: object, **k: object):
            from typani import Ok

            class _Proc:
                returncode = 128
                stdout = ""
                stderr = "fatal: Unable to create '.git/index.lock': File exists."

            return Ok(_Proc())

        monkeypatch.setattr(land_git_ops_mod, "run_argv", _fail)
        rendered = describe_root_dirt(tmp_path)
        assert "STATUS-UNREADABLE" in rendered
        assert "index.lock" in rendered
        # must state this is NOT a confirmed claim, never assert it flatly
        assert "NOT a confirmed claim" in rendered
        assert "retrying is appropriate" in rendered

    # frob:ticket T-3216
    def test_readable_clean_status_is_not_status_unreadable(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestDescribeRootDirt.test_readable_clean_status_is_not_status_unreadable  # noqa: E501
        # Must-stay-quiet: a real, readable `git status` (even one that
        # happens to find nothing) is never reported as unreadable.
        from frob.tickets._land_git_ops import describe_root_dirt

        repo = _seed_repo(tmp_path)
        assert "STATUS-UNREADABLE" not in describe_root_dirt(repo)

    def test_names_a_real_dirty_file(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestDescribeRootDirt.test_names_a_real_dirty_file  # noqa: E501
        from frob.tickets._land_git_ops import describe_root_dirt

        repo = _seed_repo(tmp_path)
        (repo / "seed.txt").write_text("changed\n", encoding="utf-8")
        assert "seed.txt" in describe_root_dirt(repo)

    def test_names_the_detached_sweep_as_likely_author(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestDescribeRootDirt.test_names_the_detached_sweep_as_likely_author  # noqa: E501
        from frob.tickets._land_git_ops import describe_root_dirt

        repo = _seed_repo(tmp_path)
        (repo / "tickets.md").write_text("dirty\n", encoding="utf-8")
        _git(repo, "add", "tickets.md")
        rendered = describe_root_dirt(repo)
        assert "tickets.md" in rendered
        assert "detached post-land sweep" in rendered

    def test_mixed_dirt_does_not_claim_the_sweep(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestDescribeRootDirt.test_mixed_dirt_does_not_claim_the_sweep  # noqa: E501
        from frob.tickets._land_git_ops import describe_root_dirt

        repo = _seed_repo(tmp_path)
        (repo / "tickets.md").write_text("dirty\n", encoding="utf-8")
        _git(repo, "add", "tickets.md")
        (repo / "seed.txt").write_text("also changed\n", encoding="utf-8")
        rendered = describe_root_dirt(repo)
        assert "detached post-land sweep" not in rendered

    # frob:ticket T-1795
    def test_names_the_real_ticket_from_a_staged_rapid_debt_line(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestDescribeRootDirt.test_names_the_real_ticket_from_a_staged_rapid_debt_line  # noqa: E501
        # Real incident: T-1222's sweep child staged rapid-debt.jsonl, and
        # the old static hint named T-1699/T-1755 (the tickets that BUILT
        # the sweep) instead of T-1222 -- symbolic attribution must read
        # the actual staged line's own ticket field.
        from frob.tickets._land_git_ops import describe_root_dirt

        repo = _seed_repo(tmp_path)
        (repo / "rapid-debt.jsonl").write_text(
            '{"commit": "abc123", "skipped": "post-land-unscoped-sweep-deferred", '
            '"ticket": "T-1222"}\n',
            encoding="utf-8",
        )
        _git(repo, "add", "rapid-debt.jsonl")
        rendered = describe_root_dirt(repo)
        assert "T-1222" in rendered
        assert "T-1699/T-1755" in rendered  # still names the mechanism
        assert "T-1699's sweep child" not in rendered  # never the wrong ticket

    # frob:ticket T-1795
    def test_unattributed_when_the_true_author_cannot_be_determined(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestDescribeRootDirt.test_unattributed_when_the_true_author_cannot_be_determined  # noqa: E501
        from frob.tickets._land_git_ops import describe_root_dirt

        repo = _seed_repo(tmp_path)
        (repo / "tickets.md").write_text("dirty\n", encoding="utf-8")
        _git(repo, "add", "tickets.md")
        rendered = describe_root_dirt(repo)
        assert "unattributed" in rendered



# frob:ticket T-2744
class TestCommitRegressionTicket:
    """T-1755: the filed regression ticket's `tickets.md` write must be
    committed by the sweep itself, scoped to the ledger paths only."""

    def test_commits_the_ledger_write(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRegressionTicket.test_commits_the_ledger_write  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _commit_regression_ticket
        from frob.tickets import Origin, TicketKind, new_ticket
        from frob.tickets._models import TicketSpec

        repo = _seed_repo(tmp_path)
        # T-1758: new_ticket now auto-commits internally by default;
        # no_commit=True reproduces the shape _file_regression_ticket
        # itself uses so this test still exercises _commit_regression_
        # ticket committing a genuinely-dirty ledger, not a no-op.
        created = new_ticket(
            repo,
            TicketSpec(title="regression", kind=TicketKind.BUG, origin=Origin.AGENT),
            no_commit=True,
        )
        assert created.is_ok
        assert _git(repo, "status", "--porcelain").strip()
        _commit_regression_ticket(repo, created.danger_ok.id, "T-9000")
        # `.frob/` (untracked local state) is expected to remain; the
        # LEDGER write specifically must be committed.
        assert "tickets" not in _git(repo, "status", "--porcelain")
        log = _git(repo, "log", "-1", "--format=%s")
        assert created.danger_ok.id in log
        assert "T-9000" in log

    def test_commit_failure_logs_at_error_and_does_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRegressionTicket.test_commit_failure_logs_at_error_and_does_not_raise  # noqa: E501
        from typani.result import Err

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Err(LeaseError.CommitFailed),
        )
        errors: list[str] = []
        monkeypatch.setattr(
            rapid_sweep_mod._log, "error", lambda msg, *a: errors.append(msg % a)
        )
        # Must not raise even though the commit "fails". max_attempts=1,
        # retry_delay_s=0: this test is about the exhausted-retries
        # discard path itself, not the retry loop's own timing (T-1841).
        rapid_sweep_mod._commit_regression_ticket(
            tmp_path, "T-1234", "T-9000", max_attempts=1, retry_delay_s=0
        )
        assert len(errors) == 1
        assert "T-1234" in errors[0]
        # A fresh tmp_path defaults to a v2 store (T-1553) -- the discard
        # branch fires (T-1841: nothing was ever written here, so the
        # rmtree is a no-op, but the log still fires).
        assert "DISCARDED" in errors[0]

    # frob:ticket T-1841
    def test_retries_then_succeeds_on_a_transient_land_in_progress(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-1841: a concurrent `frob ticket land` holding root's lock is
        the ROUTINE case for a detached sweep, not a rare fluke -- the
        commit must be retried, not given up on after one attempt."""
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRegressionTicket.test_retries_then_succeeds_on_a_transient_land_in_progress  # noqa: E501
        from typani.result import Err, Ok

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        attempts: list[int] = []

        def _flaky(root, ticket_id, message):
            attempts.append(1)
            if len(attempts) < 3:
                return Err(LeaseError.LandInProgress)
            return Ok(None)

        monkeypatch.setattr("frob.tickets._leases.commit_ticket_ledger_change", _flaky)
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)
        errors: list[str] = []
        monkeypatch.setattr(
            rapid_sweep_mod._log, "error", lambda msg, *a: errors.append(msg % a)
        )

        rapid_sweep_mod._commit_regression_ticket(
            tmp_path, "T-1234", "T-9000", max_attempts=5, retry_delay_s=0
        )

        assert len(attempts) == 3
        assert errors == []  # succeeded before exhausting retries

    # frob:ticket T-1841
    def test_exhausted_retries_discard_the_v2_ticket_dir_rather_than_leave_it_dirty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-1841's own requirement: "if the commit cannot succeed ... the
        sweep must NOT leave the file behind." A v2 store's just-written,
        never-committed `tickets/<id>/` directory must be REMOVED, not
        left as untracked dirt DirtyMain-blocking every concurrent land."""
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRegressionTicket.test_exhausted_retries_discard_the_v2_ticket_dir_rather_than_leave_it_dirty  # noqa: E501
        from typani.result import Err

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        ticket_dir = tmp_path / "tickets" / "T-1234"
        ticket_dir.mkdir(parents=True)
        (ticket_dir / "ticket.md").write_text("id: T-1234\n", encoding="utf-8")

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Err(LeaseError.LandInProgress),
        )
        monkeypatch.setattr("frob.tickets._store._store_mode", lambda root: "v2")
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)

        rapid_sweep_mod._commit_regression_ticket(
            tmp_path, "T-1234", "T-9000", max_attempts=2, retry_delay_s=0
        )

        assert not ticket_dir.exists()

    # frob:ticket T-1841
    def test_exhausted_retries_leave_a_v1_store_dirty_rather_than_guess(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-1841: a v1 (monofile) store's `tickets.md` is shared by every
        ledger op -- auto-discarding an uncommitted append there risks
        destroying a concurrent writer's own in-flight edit, so this
        deliberately leaves it dirty and loudly logged rather than
        guessing at a safe rollback."""
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRegressionTicket.test_exhausted_retries_leave_a_v1_store_dirty_rather_than_guess  # noqa: E501
        from typani.result import Err

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Err(LeaseError.LandInProgress),
        )
        monkeypatch.setattr("frob.tickets._store._store_mode", lambda root: "v1")
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)
        errors: list[str] = []
        monkeypatch.setattr(
            rapid_sweep_mod._log, "error", lambda msg, *a: errors.append(msg % a)
        )

        rapid_sweep_mod._commit_regression_ticket(
            tmp_path, "T-1234", "T-9000", max_attempts=2, retry_delay_s=0
        )

        assert len(errors) == 1
        assert "v1" in errors[0]
        assert "DIRTY" in errors[0]



# frob:ticket T-2034
class TestCommitOrDiscardLedgerWrite:
    """T-2034: the shared retry-then-discard shape every sweep
    ledger write path (regression-ticket filing, auto-drop, and whatever
    comes next) must go through."""

    def test_returns_true_on_first_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestCommitOrDiscardLedgerWrite.test_returns_true_on_first_success  # noqa: E501
        from typani.result import Ok

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Ok(None),
        )
        discarded: list[str] = []
        ok = rapid_sweep_mod._commit_or_discard_ledger_write(
            tmp_path,
            "T-1234",
            "msg",
            max_attempts=3,
            retry_delay_s=0,
            discard=lambda: discarded.append("T-1234"),
            label="T-9000",
        )
        assert ok is True
        assert discarded == []

    def test_retries_then_succeeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestCommitOrDiscardLedgerWrite.test_retries_then_succeeds  # noqa: E501
        from typani.result import Err, Ok

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        attempts: list[int] = []

        def _flaky(root, ticket_id, message):
            attempts.append(1)
            if len(attempts) < 3:
                return Err(LeaseError.LandInProgress)
            return Ok(None)

        monkeypatch.setattr("frob.tickets._leases.commit_ticket_ledger_change", _flaky)
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)
        discarded: list[str] = []
        ok = rapid_sweep_mod._commit_or_discard_ledger_write(
            tmp_path,
            "T-1234",
            "msg",
            max_attempts=5,
            retry_delay_s=0,
            discard=lambda: discarded.append("T-1234"),
            label="T-9000",
        )
        assert ok is True
        assert len(attempts) == 3
        assert discarded == []

    def test_exhausted_retries_calls_discard_exactly_once_and_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestCommitOrDiscardLedgerWrite.test_exhausted_retries_calls_discard_exactly_once_and_returns_false  # noqa: E501
        from typani.result import Err

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Err(LeaseError.LandInProgress),
        )
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)
        discarded: list[str] = []
        ok = rapid_sweep_mod._commit_or_discard_ledger_write(
            tmp_path,
            "T-1234",
            "msg",
            max_attempts=2,
            retry_delay_s=0,
            discard=lambda: discarded.append("T-1234"),
            label="T-9000",
        )
        assert ok is False
        assert discarded == ["T-1234"]



# frob:ticket T-2034
class TestDiscardUncommittedTicketDrop:
    """T-2034: the auto-drop write path's discard action must
    RESTORE the existing ticket file to its last committed state (not
    rmtree it -- it is real, already-landed history, unlike a fresh
    regression ticket's brand-new directory)."""

    def test_v2_store_restores_the_ticket_file_to_head(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestDiscardUncommittedTicketDrop.test_v2_store_restores_the_ticket_file_to_head  # noqa: E501
        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod

        repo = _seed_repo(tmp_path)
        ticket_dir = repo / "tickets" / "T-1234"
        ticket_dir.mkdir(parents=True)
        original = "id: T-1234\nstate: queued\n"
        (ticket_dir / "ticket.md").write_text(original, encoding="utf-8")
        _git(repo, "add", "tickets/T-1234/ticket.md")
        _git(repo, "commit", "-qm", "seed ticket")

        # Simulate the never-committed drop mutation.
        (ticket_dir / "ticket.md").write_text(
            "id: T-1234\nstate: dropped\n", encoding="utf-8"
        )
        assert _git(repo, "status", "--porcelain").strip()

        rapid_sweep_mod._discard_uncommitted_ticket_drop(repo, "T-1234")

        assert not _git(repo, "status", "--porcelain", "--", "tickets").strip()
        assert (ticket_dir / "ticket.md").read_text(encoding="utf-8") == original

    def test_v1_store_logs_and_leaves_root_alone(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestDiscardUncommittedTicketDrop.test_v1_store_logs_and_leaves_root_alone  # noqa: E501
        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod

        monkeypatch.setattr("frob.tickets._store._store_mode", lambda root: "v1")
        errors: list[str] = []
        monkeypatch.setattr(
            rapid_sweep_mod._log, "error", lambda msg, *a: errors.append(msg % a)
        )

        rapid_sweep_mod._discard_uncommitted_ticket_drop(tmp_path, "T-1234")

        assert len(errors) == 1
        assert "v1" in errors[0]
        assert "DIRTY" in errors[0]



class TestTicketIsOpen:
    """`_ticket_is_open` is the "still open" half of T-1690's filing rule."""

    def test_open_ticket_is_open(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/rapid_sweep_suite/test_commit.py::TestTicketIsOpen.test_open_ticke\
        # t_is_open
        ticket_id = _seed_ticket(tmp_path)
        assert _ticket_is_open(tmp_path, ticket_id) is True

    def test_done_ticket_is_not_open(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/rapid_sweep_suite/test_commit.py::TestTicketIsOpen.test_done_ticke\
        # t_is_not_open
        from frob.tickets._models import TicketState

        ticket_id = _seed_ticket(tmp_path, state=TicketState.DONE)
        assert _ticket_is_open(tmp_path, ticket_id) is False

    def test_missing_ticket_is_not_open(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_commit.py::TestTicketIsOpen.test_missing_ticket_is_not_open  # noqa: E501
        assert _ticket_is_open(tmp_path, "T-9999") is False
