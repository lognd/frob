"""T-1175: `frob ticket work` (worktree create/reuse + freshness + natives +
start, in one verb) and `frob ticket land`'s absorbed fmt/sync-interface/
Tier-A-fix pre-land step plus its `LAND-PROOF:` line and `--finish`
worktree removal.

Real git subprocesses (matching tests/test_ticket_land.py's own style) --
`work`/`land --finish` are themselves thin orchestration over real `git
worktree` commands, so the fixture reproduces the real shape rather than
mocking it away.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import _work
from frob.app.ticket_runner._land_cmd import (
    _absorb_pre_land_fixes,
    _delete_worktree_branch,
    _drop_checkpoint_exempt_findings,
    _finish_land_after_success,
    _finish_worktree,
    _post_land_unscoped_error_sweep,
    _pre_commit_unscoped_error_sweep,
    _print_land_proof,
    _worktree_branch_name,
    land_parity_findings,
)
from frob.app.ticket_runner._lifecycle import _default_work_worktree
from frob.tickets import Origin, TicketKind, TicketSpec, TicketState, new_ticket
from frob.tickets._land import land
from frob.tickets._models import LandReport
from frob.tickets._store import atomic_write, ledger_path, load_all, write_ticket


# frob:waive DUP001 reason="the run/git-init/commit-all trio is an established \
# real-git-fixture idiom this test module family repeats (tests/test_ticket_land.py, \
# tests/test_tickets_collision.py, tests/test_ticket_leases.py, \
# tests/test_ticket_merge_driver.py, tests/test_ticket_reconcile.py, ... all carry \
# byte-identical copies already, none of them waived) -- extracting a shared conftest \
# helper is a real, independent cleanup outside T-1175's own scope, not something to \
# fold into this ticket's own land"
def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:waive DUP001 reason="see _run's identical DUP001 waiver immediately above -- \
# same established fixture idiom, same real cleanup-later disposition"
def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


# frob:waive DUP001 reason="see _run's identical DUP001 waiver above -- same \
# established fixture idiom, same real cleanup-later disposition"
def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _spec(title: str) -> TicketSpec:
    return TicketSpec(title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A main checkout with an initialized ledger and one committed file."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    atomic_write(ledger_path(main_repo), "# Tickets\n\n")
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    # T-1175's own `.claude/worktrees/<id>` default must not itself show up
    # as an untracked change in `main`'s own working tree (real repos
    # gitignore `.claude/worktrees/`, matching this repo's own .gitignore).
    (main_repo / ".gitignore").write_text(".claude/\n")
    _commit_all(main_repo, "init")
    return main_repo


# frob:ticket T-1175
class TestDefaultWorkWorktree:
    def test_slug_is_lowercased_ticket_id_under_dot_claude_worktrees(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestDefaultWorkWorktree.test_slug_\
        # is_lowercased_ticket_id_under_dot_claude_worktrees
        result = _default_work_worktree(tmp_path, "T-1175")
        assert result == tmp_path / ".claude" / "worktrees" / "t-1175"


# frob:ticket T-1175
class TestWork:
    def test_creates_worktree_merges_main_and_starts_ticket(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestWork.test_creates_worktree_mer\
        # ges_main_and_starts_ticket
        created = new_ticket(repo, _spec("Work verb"))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        cfg = AppConfig(ticket_command="work", ticket_id=tid, ticket_foreground=True)
        _work(repo, cfg)

        worktree = _default_work_worktree(repo, tid)
        assert worktree.is_dir()
        assert (worktree / "src" / "feature.py").read_text() == "# landed feature\n"

        loaded = load_all(worktree)
        assert loaded.is_ok
        ticket = loaded.danger_ok[tid]
        assert ticket.state == TicketState.IN_PROGRESS

    def test_reuses_an_existing_worktree_and_merges_main_for_freshness(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestWork.test_reuses_an_existing_w\
        # orktree_and_merges_main_for_freshness
        created = new_ticket(repo, _spec("Work verb reuse"))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        worktree = _default_work_worktree(repo, tid)
        _run(["git", "worktree", "add", str(worktree), "-b", tid.lower(), "main"], repo)

        # `main` gains a commit AFTER the worktree was cut -- a stale
        # worktree the freshness merge must catch up.
        (repo / "src" / "later.py").write_text("# added after worktree cut\n")
        _commit_all(repo, "add later.py")

        cfg = AppConfig(ticket_command="work", ticket_id=tid, ticket_foreground=True)
        _work(repo, cfg)

        assert (worktree / "src" / "later.py").is_file()
        loaded = load_all(worktree)
        assert loaded.is_ok
        assert loaded.danger_ok[tid].state == TicketState.IN_PROGRESS


# frob:ticket T-1790
class TestRootIsItselfANestedWorktree:
    """T-1790: `frob ticket work` refuses to create a SECOND-level nested
    worktree when `root` is itself already a dispatched agent worktree
    -- the source of T-1766's incident (its own worktree was nested
    under another agent's, and died silently when the parent was
    retired, taking the nested one and orphaning its lease with it)."""

    def test_detects_root_under_dot_claude_worktrees(self, tmp_path: Path) -> None:
        # frob:tests \
        # src/frob/app/ticket_runner/_lifecycle.py::_root_is_itself_a_nested_worktree \
        # kind="unit"
        from frob.app.ticket_runner._lifecycle import (
            _root_is_itself_a_nested_worktree,
        )

        nested = tmp_path / "main" / ".claude" / "worktrees" / "agent-x"
        assert _root_is_itself_a_nested_worktree(nested) is True

    def test_primary_checkout_is_not_nested(self, tmp_path: Path) -> None:
        # frob:tests \
        # src/frob/app/ticket_runner/_lifecycle.py::_root_is_itself_a_nested_worktree \
        # kind="unit"
        from frob.app.ticket_runner._lifecycle import (
            _root_is_itself_a_nested_worktree,
        )

        primary = tmp_path / "main"
        assert _root_is_itself_a_nested_worktree(primary) is False

    def test_work_refuses_from_a_nested_worktree(self, repo: Path) -> None:
        # frob:tests src/frob/app/ticket_runner/_lifecycle.py::_work kind="unit"
        created = new_ticket(repo, _spec("Work verb nested refusal"))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        nested_root = repo / ".claude" / "worktrees" / "agent-outer"
        nested_root.mkdir(parents=True)

        cfg = AppConfig(ticket_command="work", ticket_id=tid, ticket_foreground=True)
        with pytest.raises(SystemExit) as exc_info:
            _work(nested_root, cfg)
        assert exc_info.value.code == 1
        # The doomed nested worktree must never actually be created.
        assert not (nested_root / ".claude" / "worktrees" / tid.lower()).exists()

    def test_work_cluster_refuses_from_a_nested_worktree(self, repo: Path) -> None:
        # frob:tests src/frob/app/ticket_runner/_lifecycle.py::_work_cluster kind="unit"
        from frob.tickets import TicketTier, set_tier

        epic = new_ticket(repo, _spec("Epic for nested refusal"))
        assert epic.is_ok
        epic_id = epic.danger_ok.id
        assert set_tier(repo, epic_id, TicketTier.EPIC).is_ok
        leaf_spec = TicketSpec(
            title="Leaf under epic",
            kind=TicketKind.FEATURE,
            origin=Origin.AGENT,
            parent=epic_id,
        )
        leaf = new_ticket(repo, leaf_spec)
        assert leaf.is_ok
        _commit_all(repo, "add cluster tickets")

        nested_root = repo / ".claude" / "worktrees" / "agent-outer"
        nested_root.mkdir(parents=True)

        cfg = AppConfig(ticket_command="work", ticket_cluster=epic_id)
        with pytest.raises(SystemExit) as exc_info:
            _work(nested_root, cfg)
        assert exc_info.value.code == 1


# frob:ticket T-1175
class TestAbsorbPreLandFixes:
    """T-1175's `_absorb_pre_land_fixes` -- the `frob fmt` half is exercised
    directly here (a real non-canonical `frob:` directive, `format_paths`'s
    own `TestFormatPaths.test_write_mode_rewrites_file` shape); the sys
    sync-interface/Tier-A-fix halves are no-ops on a `design/`-less
    fixture repo and are covered by their own dedicated suites
    (tests/unit/strata/test_sync_interface.py, tests/test_gates.py's
    TestFixEngineTierA) -- this test's job is only that `land`'s new
    absorption step actually reaches `format_paths` and rewrites a real
    file, not re-proving those two modules' own behavior."""

    def test_fmt_half_canonicalizes_a_non_canonical_directive(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes.test_fmt_ha\
        # lf_canonicalizes_a_non_canonical_directive
        target = repo / "src" / "noncanon.py"
        original = (
            '# frob:waive R reason="this reason is intentionally long so '
            'it overflows the line-length limit and must be wrapped"\n'
        )
        target.write_text(original)
        # `format_paths` walks via `frob.excludes.iter_files`'s git-ls-files
        # fast path in a real git repo -- an untracked file needs staging
        # first for the same reason a genuine WIP-but-uncommitted ticket
        # change would already be `git add`-ed by the time land runs.
        _run(["git", "add", "-A"], repo)

        _absorb_pre_land_fixes(repo, "T-0001")

        rewritten = target.read_text()
        assert rewritten != original
        for line in rewritten.splitlines():
            assert len(line) <= 88

    # frob:ticket T-1404
    def test_out_of_scope_file_with_noncanonical_directive_is_left_untouched(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes.test_out_of\
        # _scope_file_with_noncanonical_directive_is_left_untouched
        # T-1404 acceptance [0]: a file elsewhere in the tree, already
        # committed to `main` (never touched by this ticket's own diff),
        # carrying a non-canonical `frob:` directive, must be left
        # BYTE-IDENTICAL by the pre-land fix pass -- T-1391 built
        # `only_paths` but wired no real caller to it, so this used to get
        # rewritten by the whole-tree `frob fmt` pass regardless of scope.
        out_of_scope = repo / "src" / "out_of_scope.py"
        original = (
            '# frob:waive R reason="this reason is intentionally long so '
            'it overflows the line-length limit and must be wrapped"\n'
        )
        out_of_scope.write_text(original)
        _commit_all(repo, "add out-of-scope file with a non-canonical directive")

        # This ticket's own (unrelated) touched file.
        in_scope = repo / "src" / "in_scope.py"
        in_scope.write_text("def f():\n    return 1\n")
        _run(["git", "add", "-A"], repo)

        _absorb_pre_land_fixes(repo, "T-1404")

        assert out_of_scope.read_text() == original

    # frob:ticket T-1404
    def test_in_scope_file_with_noncanonical_directive_is_still_fixed(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes.test_in_sco\
        # pe_file_with_noncanonical_directive_is_still_fixed
        # T-1404 acceptance [1]: a file genuinely inside the landing
        # ticket's own touched set still gets fixed exactly as before,
        # even with an unrelated committed out-of-scope file also present.
        out_of_scope = repo / "src" / "out_of_scope.py"
        out_of_scope.write_text("def g():\n    return 2\n")
        _commit_all(repo, "add an unrelated already-committed file")

        target = repo / "src" / "noncanon.py"
        original = (
            '# frob:waive R reason="this reason is intentionally long so '
            'it overflows the line-length limit and must be wrapped"\n'
        )
        target.write_text(original)
        _run(["git", "add", "-A"], repo)

        _absorb_pre_land_fixes(repo, "T-1404")

        rewritten = target.read_text()
        assert rewritten != original
        for line in rewritten.splitlines():
            assert len(line) <= 88


# frob:ticket T-1796
class TestSyncInterfacePreLandRefusesOnParseFailed:
    """T-1796: a `design/**` file that fails to PARSE must refuse the
    land outright, not degrade to a WARNING and proceed -- the exact gap
    that let a single dropped quote in `design/frob.strata` break
    `strata` parsing repo-wide and survive three lands undetected."""

    def test_refuses_when_a_design_file_is_malformed(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestSyncInterfacePreLandRefusesOnParseFailed.test_refuses_when_a_design_file_is_malformed  # noqa: E501
        design_dir = repo / "design"
        design_dir.mkdir()
        (design_dir / "broken.strata").write_text(
            'node broken : trusted {\n    attr interface=["unterminated\n};\n'
        )
        _run(["git", "add", "-A"], repo)

        with pytest.raises(SystemExit) as exc_info:
            _absorb_pre_land_fixes(repo, "T-1796")
        assert exc_info.value.code == 1

    def test_still_proceeds_when_design_dir_absent(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestSyncInterfacePreLandRefusesOnParseFailed.test_still_proceeds_when_design_dir_absent  # noqa: E501
        # No design/ directory at all -- must NOT be treated as a parse
        # failure; a fixture repo with nothing to sync is the common case
        # every OTHER TestAbsorbPreLandFixes test already relies on.
        assert not (repo / "design").is_dir()
        _absorb_pre_land_fixes(repo, "T-1796")  # must not raise


# frob:ticket T-1578
class TestWorktreeNativesVerifiablyHealthy:
    """`_worktree_natives_verifiably_healthy` (T-1578): the pre-land
    preflight that decides whether this land's WAIVE004 self-run is even
    worth paying for."""

    def test_healthy_natives_return_true(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestWorktreeNativesVerifiablyHealt\
        # hy.test_healthy_natives_return_true
        from frob.app.ticket_runner._land_cmd import (
            _worktree_natives_verifiably_healthy,
        )

        monkeypatch.setattr("frob.gates._maybe_autorebuild_natives", lambda root: None)
        monkeypatch.setattr("frob.strata.stale_natives", lambda root: ())
        monkeypatch.setattr("frob.strata.unimportable_natives", lambda root: ())

        assert _worktree_natives_verifiably_healthy(repo) is True

    def test_stale_after_autorebuild_attempt_returns_false(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestWorktreeNativesVerifiablyHealt\
        # hy.test_stale_after_autorebuild_attempt_returns_false
        """A native still reported stale AFTER the auto-rebuild attempt
        (disabled, or the rebuild itself failed) must read as unhealthy --
        the whole point of preflighting before paying for a full
        `run_gates()` this land can no longer trust."""
        from frob.app.ticket_runner._land_cmd import (
            _worktree_natives_verifiably_healthy,
        )

        monkeypatch.setattr("frob.gates._maybe_autorebuild_natives", lambda root: None)
        monkeypatch.setattr("frob.strata.stale_natives", lambda root: ("still-stale",))
        monkeypatch.setattr("frob.strata.unimportable_natives", lambda root: ())

        assert _worktree_natives_verifiably_healthy(repo) is False

    def test_unimportable_native_returns_false(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestWorktreeNativesVerifiablyHealt\
        # hy.test_unimportable_native_returns_false
        from frob.app.ticket_runner._land_cmd import (
            _worktree_natives_verifiably_healthy,
        )

        monkeypatch.setattr("frob.gates._maybe_autorebuild_natives", lambda root: None)
        monkeypatch.setattr("frob.strata.stale_natives", lambda root: ())
        monkeypatch.setattr(
            "frob.strata.unimportable_natives", lambda root: ("broken-native",)
        )

        assert _worktree_natives_verifiably_healthy(repo) is False


# frob:ticket T-1456
# frob:ticket T-1513
class TestPostLandUnscopedSweep:
    """T-1456's `_post_land_unscoped_error_sweep`: `_unscoped_error_findings`/
    `_apply_root_tier_a_fixes` (the two functions that would otherwise spawn
    a real `frob check`/run Tier-A fixers) are monkeypatched so these stay
    fast, foreground-safe unit tests over the git-mutating logic (commit a
    fix, or hard-reset a revert) itself -- the spawn/parse half is already
    covered by `_verify.py`'s own `_parse_error_findings_from_stdout`
    suite, reused here unmodified (no second hand-typed copy)."""

    # frob:ticket T-1456
    def _landed_repo(self, tmp_path: Path) -> tuple[Path, str]:
        """A root checkout with one commit, then a SECOND commit standing
        in for `land()`'s own squash-apply -- returns `(root, pre_land_sha)`
        pointing at the first commit, the exact shape
        `_post_land_unscoped_error_sweep`'s caller captures before `land()`
        runs."""
        root = tmp_path / "root"
        _git_init(root)
        (root / "a.txt").write_text("one\n")
        _commit_all(root, "c1")
        pre_sha = _run(["git", "rev-parse", "HEAD"], root).stdout.strip()
        (root / "a.txt").write_text("two\n")
        _commit_all(root, "c2 (simulated land squash-apply)")
        return root, pre_sha

    # frob:ticket T-1456
    # frob:tests \
    # tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep.test_no_new_\
    # error_is_a_silent_no_op
    def test_no_new_error_is_a_silent_no_op(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root, pre_sha = self._landed_repo(tmp_path)
        baseline = frozenset({("X001", "a.txt")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda root, ticket_id, **kw: baseline,
        )
        ok = _post_land_unscoped_error_sweep(
            root, "T-0001", "T-0001", pre_sha, baseline
        )
        assert ok is True
        head = _run(["git", "rev-parse", "HEAD"], root).stdout.strip()
        assert head != pre_sha

    # frob:ticket T-1456
    # frob:ticket T-1513
    # frob:tests \
    # tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep.test_new_err\
    # or_fixed_by_tier_a_lands_with_a_followup_commit
    def test_new_error_fixed_by_tier_a_lands_with_a_followup_commit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root, pre_sha = self._landed_repo(tmp_path)
        baseline = frozenset({("X001", "a.txt")})
        calls = {"n": 0}

        def fake_fresh(root, ticket_id, **kw):  # noqa: ANN001, ANN202
            calls["n"] += 1
            if calls["n"] == 1:
                return frozenset({("X001", "a.txt"), ("Y002", "b.txt")})
            return frozenset({("X001", "a.txt")})

        def fake_fix(root, ticket_id):  # noqa: ANN001, ANN202
            (root / "b.txt").write_text("fixed\n")
            return ["b.txt"]

        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings", fake_fresh
        )
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._apply_root_tier_a_fixes", fake_fix
        )
        ok = _post_land_unscoped_error_sweep(
            root, "T-0001", "T-0001", pre_sha, baseline
        )
        assert ok is True
        log = _run(["git", "log", "--oneline", "-1"], root).stdout
        assert "post-land Tier-A cleanup" in log

    # frob:ticket T-1456
    # frob:ticket T-1513
    # frob:tests \
    # tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep.test_new_err\
    # or_absent_before_land_refuses_and_reverts
    def test_new_error_absent_before_land_refuses_and_reverts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root, pre_sha = self._landed_repo(tmp_path)
        baseline = frozenset({("X001", "a.txt")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda root, ticket_id, **kw: frozenset(
                {("X001", "a.txt"), ("Z003", "c.txt")}
            ),
        )
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._apply_root_tier_a_fixes",
            lambda root, ticket_id: [],
        )
        ok = _post_land_unscoped_error_sweep(
            root, "T-0001", "T-0001", pre_sha, baseline
        )
        assert ok is False
        head = _run(["git", "rev-parse", "HEAD"], root).stdout.strip()
        assert head == pre_sha

    # frob:ticket T-1513
    # frob:tests \
    # tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep.test_fix_com\
    # mit_stages_only_touched_paths_not_git_add_dash_a
    def test_fix_commit_stages_only_touched_paths_not_git_add_dash_a(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-1513: a Tier-A fix commit must stage ONLY the paths Tier-A
        actually touched -- never `git add -A`, which used to also sweep
        up an unrelated dirty file (standing in for the perpetually-dirty
        land-owned `uv.lock`) and get the whole commit refused by a
        pre-commit hook that inspects staged paths."""
        root, pre_sha = self._landed_repo(tmp_path)
        baseline = frozenset({("X001", "a.txt")})
        calls = {"n": 0}

        def fake_fresh(root, ticket_id, **kw):  # noqa: ANN001, ANN202
            calls["n"] += 1
            if calls["n"] == 1:
                return frozenset({("X001", "a.txt"), ("Y002", "b.txt")})
            return frozenset({("X001", "a.txt")})

        def fake_fix(root, ticket_id):  # noqa: ANN001, ANN202
            (root / "b.txt").write_text("fixed\n")
            # An unrelated dirty file Tier-A never touched -- must NOT be
            # staged or committed by the follow-up cleanup commit.
            (root / "unrelated-dirty.txt").write_text("do not stage me\n")
            return ["b.txt"]

        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings", fake_fresh
        )
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._apply_root_tier_a_fixes", fake_fix
        )
        ok = _post_land_unscoped_error_sweep(
            root, "T-0001", "T-0001", pre_sha, baseline
        )
        assert ok is True
        log = _run(["git", "log", "--oneline", "-1"], root).stdout
        assert "post-land Tier-A cleanup" in log
        committed_files = _run(
            ["git", "show", "--name-only", "--pretty=format:", "HEAD"], root
        ).stdout.split()
        assert "b.txt" in committed_files
        assert "unrelated-dirty.txt" not in committed_files
        status = _run(["git", "status", "--porcelain"], root).stdout
        assert "unrelated-dirty.txt" in status

    # frob:ticket T-1456
    # frob:tests \
    # tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep.test_unmeasu\
    # rable_baseline_or_fresh_skips_the_sweep
    def test_unmeasurable_baseline_or_fresh_skips_the_sweep(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root, pre_sha = self._landed_repo(tmp_path)
        ok = _post_land_unscoped_error_sweep(root, "T-0001", "T-0001", pre_sha, None)
        assert ok is True

        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda root, ticket_id, **kw: None,
        )
        ok2 = _post_land_unscoped_error_sweep(
            root, "T-0001", "T-0001", pre_sha, frozenset()
        )
        assert ok2 is True


# frob:ticket T-1514
# frob:ticket T-1524
class TestPreCommitUnscopedSweepFn:
    """T-1514's `_pre_commit_unscoped_error_sweep`: same identity-set
    comparison/Tier-A-retry logic as `TestPostLandUnscopedSweep` above,
    but the function itself never mutates git state (no commit, no
    reset) -- unwinding on a `False` verdict is `land()`'s own job via
    `_verified_reset_root`, tested at the `land()` level in
    tests/test_ticket_land.py::TestPreCommitUnscopedSweep instead."""

    # frob:ticket T-1514
    # frob:tests \
    # tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn.test_none\
    # _baseline_or_fresh_is_a_skip_not_a_pass
    def test_none_baseline_or_fresh_is_a_skip_not_a_pass(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _pre_commit_unscoped_error_sweep(tmp_path, "T-0001", "T-0001", None) is (
            None
        )

        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda root, ticket_id, **kw: None,
        )
        assert (
            _pre_commit_unscoped_error_sweep(tmp_path, "T-0001", "T-0001", frozenset())
            is None
        )

    # frob:ticket T-1514
    # frob:tests \
    # tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn.test_no_n\
    # ew_finding_is_true
    def test_no_new_finding_is_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        baseline = frozenset({("X001", "a.txt")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda root, ticket_id, **kw: baseline,
        )
        assert (
            _pre_commit_unscoped_error_sweep(tmp_path, "T-0001", "T-0001", baseline)
            is True
        )

    # frob:ticket T-1514
    # frob:tests \
    # tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn.test_new_\
    # finding_fixed_by_tier_a_stages_and_returns_true
    def test_new_finding_fixed_by_tier_a_stages_and_returns_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        baseline = frozenset({("X001", "a.txt")})
        calls = {"n": 0}

        def fake_fresh(root, ticket_id, **kw):  # noqa: ANN001, ANN202
            calls["n"] += 1
            if calls["n"] == 1:
                return frozenset({("X001", "a.txt"), ("Y002", "b.txt")})
            return frozenset({("X001", "a.txt")})

        staged: list[frozenset[str]] = []

        def fake_stage(root, ticket_id):  # noqa: ANN001, ANN202
            paths = frozenset({"b.txt"})
            staged.append(paths)
            return paths

        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings", fake_fresh
        )
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._sweep_apply_tier_a_pre_commit",
            fake_stage,
        )
        result = _pre_commit_unscoped_error_sweep(
            tmp_path, "T-0001", "T-0001", baseline
        )
        assert result is True
        assert staged == [frozenset({"b.txt"})]

    # frob:ticket T-1514
    # frob:tests \
    # tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn.test_new_\
    # finding_unresolved_by_tier_a_returns_false
    def test_new_finding_unresolved_by_tier_a_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        baseline = frozenset({("X001", "a.txt")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda root, ticket_id, **kw: frozenset(
                {("X001", "a.txt"), ("Z003", "c.txt")}
            ),
        )
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._sweep_apply_tier_a_pre_commit",
            lambda root, ticket_id: frozenset(),
        )
        result = _pre_commit_unscoped_error_sweep(
            tmp_path, "T-0001", "T-0001", baseline
        )
        assert result is False

    # frob:ticket T-1524
    # frob:tests \
    # tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn.test_land\
    # _owned_only_findings_are_exempt_and_pass
    def test_land_owned_only_findings_are_exempt_and_pass(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-1524: PRE001/SCOPE001 against the land's own staged REL001
        bump files must not refuse the land -- they are land-machinery
        artifacts, exempt (loudly logged) from the refusal decision."""
        baseline = frozenset({("X001", "a.txt")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda root, ticket_id, **kw: frozenset(
                {
                    ("X001", "a.txt"),
                    ("PRE001", ".frob-release.json"),
                    ("SCOPE001", str(tmp_path / "pyproject.toml")),
                }
            ),
        )
        result = _pre_commit_unscoped_error_sweep(
            tmp_path, "T-0001", "T-0001", baseline
        )
        assert result is True

    # frob:ticket T-1524
    # frob:tests \
    # tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn.test_chec\
    # kpoint_artifact_rules_are_exempt
    def test_checkpoint_artifact_rules_are_exempt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-1524: PRE001/SCOPE001 structurally false-positive at the
        staged-uncommitted checkpoint (the landing ticket is already
        finalized done, so its own staged diff reads as unlicensed) --
        exempt by RULE regardless of which file they name."""
        baseline: frozenset[tuple[str, str]] = frozenset()
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda root, ticket_id, **kw: frozenset(
                {
                    ("PRE001", "src/frob/app/ticket_runner/_land_cmd.py"),
                    ("SCOPE001", "src/frob/app/ticket_runner/_land_cmd.py"),
                }
            ),
        )
        result = _pre_commit_unscoped_error_sweep(
            tmp_path, "T-0001", "T-0001", baseline
        )
        assert result is True

    # frob:ticket T-1524
    # frob:tests \
    # tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn.test_nest\
    # ed_land_owned_name_is_not_exempt
    def test_nested_land_owned_name_is_not_exempt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-1524 boundary: a NESTED pyproject.toml (fixture tree, not the
        repo root's) is a real finding and still refuses -- using a rule
        outside _PRE_COMMIT_SWEEP_EXEMPT_RULES so only the file-level
        land-owned matching is under test."""
        baseline: frozenset[tuple[str, str]] = frozenset()
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda root, ticket_id, **kw: frozenset(
                {("E501", "tests/fixtures/proj/pyproject.toml")}
            ),
        )
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._sweep_apply_tier_a_pre_commit",
            lambda root, ticket_id: frozenset(),
        )
        result = _pre_commit_unscoped_error_sweep(
            tmp_path, "T-0001", "T-0001", baseline
        )
        assert result is False


# frob:ticket T-1175
# frob:ticket T-1685
class TestLandProofAndFinish:
    """T-1175's `_print_land_proof`/`_finish_worktree` -- land's own
    `frob.tickets.land()` (permissive, matching test_ticket_land.py's own
    direct-call style) produces the real `LandReport` these two helpers
    consume; the CLI wrapper (`_land`) just wires them in after a real
    (non-dry-run) `Ok` result, T-1175's own actual new code lives here."""

    # frob:ticket T-1685
    def _land_a_real_ticket(self, repo: Path) -> tuple[str, Path, LandReport]:
        """Land a freshly created ticket end-to-end and return its id,
        worktree path, and the resulting LandReport for assertion reuse
        across this class's tests."""
        created = new_ticket(repo, _spec("Land proof"))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        work_cfg = AppConfig(
            ticket_command="work", ticket_id=tid, ticket_foreground=True
        )
        _work(repo, work_cfg)
        worktree = _default_work_worktree(repo, tid)

        loaded = load_all(worktree)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(worktree, ticket).is_ok
        _run(["git", "add", "-A"], worktree)
        _run(["git", "commit", "-q", "-m", "wt: done report"], worktree)

        result = land(repo, tid, worktree, dry_run=False)
        assert result.is_ok, result.err
        return tid, worktree, result.danger_ok

    def test_proof_verifies_a_real_land(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_proof_\
        # verifies_a_real_land
        _tid, _worktree, report = self._land_a_real_ticket(repo)
        assert _print_land_proof(repo, report) is True

    def test_finish_removes_the_worktree(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_finish\
        # _removes_the_worktree
        tid, worktree, report = self._land_a_real_ticket(repo)
        assert _print_land_proof(repo, report) is True

        _finish_worktree(repo, worktree, tid)

        assert not worktree.exists()
        worktree_list = _run(["git", "worktree", "list"], repo).stdout
        assert str(worktree) not in worktree_list

    # frob:ticket T-1619
    def test_retire_on_proof_removes_worktree_and_deletes_its_branch(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_retire\
        # _on_proof_removes_worktree_and_deletes_its_branch
        tid, worktree, report = self._land_a_real_ticket(repo)
        assert _print_land_proof(repo, report) is True

        branch = _worktree_branch_name(repo, worktree)
        assert branch is not None

        _finish_worktree(repo, worktree, tid)
        _delete_worktree_branch(repo, branch, tid)

        assert not worktree.exists()
        branch_list = _run(["git", "branch", "--list"], repo).stdout
        assert branch not in branch_list.split()

    # frob:ticket T-1619
    def test_worktree_branch_name_returns_none_for_an_unregistered_path(
        self, repo: Path, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_worktr\
        # ee_branch_name_returns_none_for_an_unregistered_path
        bogus = tmp_path / "not-a-real-worktree"
        assert _worktree_branch_name(repo, bogus) is None

    # frob:ticket T-1619
    def test_delete_worktree_branch_is_a_logged_no_op_for_none(
        self, repo: Path, caplog
    ) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_delete\
        # _worktree_branch_is_a_logged_no_op_for_none
        with caplog.at_level("WARNING"):
            _delete_worktree_branch(repo, None, "T-0001")
        assert "could not determine the worktree's branch name" in caplog.text

    # frob:ticket T-1619
    def test_retire_on_proof_refuses_and_touches_nothing_when_unverified(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_retire\
        # _on_proof_refuses_and_touches_nothing_when_unverified
        # The exact "one command, not two" property the repo owner asked
        # for: an UNVERIFIED land (here, a report naming a commit that is
        # not an ancestor of main -- the shape a failed/interrupted land
        # would leave) must refuse outright, leaving both the worktree AND
        # its branch untouched, instead of the unsafe two-step sequence
        # (`land && git worktree remove`) that destroys the worktree
        # regardless of the land's own outcome.
        from types import SimpleNamespace

        tid, worktree, real_report = self._land_a_real_ticket(repo)
        assert worktree.exists()
        branch = _worktree_branch_name(repo, worktree)
        assert branch is not None
        branch_list_before = _run(["git", "branch", "--list"], repo).stdout

        fake_report = SimpleNamespace(
            dry_run=False,
            final_id=real_report.final_id,
            commit_sha="0" * 40,  # never an ancestor of anything real
        )
        cfg = AppConfig(
            ticket_command="land",
            ticket_id=tid,
            ticket_worktree=worktree,
            ticket_land_retire_on_proof=True,
        )
        with pytest.raises(SystemExit):
            _finish_land_after_success(repo, worktree, fake_report, cfg)

        assert worktree.exists(), "unverified retire-on-proof removed the worktree"
        branch_list_after = _run(["git", "branch", "--list"], repo).stdout
        assert branch_list_after == branch_list_before, (
            "unverified retire-on-proof touched a branch"
        )


# frob:ticket T-1535
class TestLandParityFindings:
    """T-1535's `frob check --land-parity` evaluation
    (`land_parity_findings`): the SAME `_unscoped_error_findings` +
    `_drop_checkpoint_exempt_findings` pair the real land sweeps use,
    cache-bypassed, against the current tree with no baseline diff."""

    # frob:tests \
    # tests/test_ticket_work_and_land_finish.py::TestLandParityFindings.test_none_when_\
    # unmeasurable
    def test_none_when_unmeasurable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda root, ticket_id, **kw: None,
        )
        assert land_parity_findings(tmp_path) is None

    # frob:tests \
    # tests/test_ticket_work_and_land_finish.py::TestLandParityFindings.test_forces_no_\
    # gate_cache_env_on_the_spawn
    def test_forces_no_gate_cache_env_on_the_spawn(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: dict[str, dict[str, str] | None] = {}

        def fake_unscoped(root, ticket_id, *, budget=0, env=None):  # noqa: ANN001, ANN202
            seen["env"] = env
            return frozenset()

        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            fake_unscoped,
        )
        land_parity_findings(tmp_path)
        seen_env = seen["env"]
        assert seen_env is not None
        assert seen_env["FROB_NO_GATE_CACHE"] == "1"

    # frob:tests \
    # tests/test_ticket_work_and_land_finish.py::TestLandParityFindings.test_parity_wit\
    # h_the_land_sweeps_own_exemption_function
    def test_parity_with_the_land_sweeps_own_exemption_function(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The property this ticket names: for a fixed raw finding set (one
        real error, one T-1524 checkpoint-artifact PRE001 exempt entry),
        `land_parity_findings`'s output equals calling the land sweeps'
        OWN `_drop_checkpoint_exempt_findings` directly against that same
        raw set -- same parser (both consume `_unscoped_error_findings`'s
        return value unchanged), same exclusions (both route through the
        one shared exemption function, never a second hand-copied rule
        list)."""
        raw = frozenset(
            {("X001", "a.txt"), ("PRE001", "tickets.md"), ("Y002", "b.txt")}
        )
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda root, ticket_id, **kw: raw,
        )
        parity = land_parity_findings(tmp_path)
        assert parity is not None
        expected = _drop_checkpoint_exempt_findings(
            tmp_path, "land-parity", raw, log_exclusions=False
        )
        assert parity == expected
        assert ("PRE001", "tickets.md") not in parity
        assert parity == frozenset({("X001", "a.txt"), ("Y002", "b.txt")})
