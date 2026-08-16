"""T-1175: `frob ticket work` (worktree create/reuse + freshness + natives +
start, in one verb) and `frob ticket land`'s absorbed fmt/Tier-A-fix
pre-land step (T-1870: the sync-interface auto-write third leg was
deleted; `_assert_design_loads_pre_land`'s read-only parse guard is not
part of this best-effort absorption trio) plus its `LAND-PROOF:` line and
`--finish` worktree removal.

Real git subprocesses (matching tests/test_ticket_land.py's own style) --
`work`/`land --finish` are themselves thin orchestration over real `git
worktree` commands, so the fixture reproduces the real shape rather than
mocking it away.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typani.result import Ok

from frob.app.config import AppConfig
from frob.app.ticket_runner import _work
from frob.app.ticket_runner._land_cmd import (
    _absorb_pre_land_fixes,
    _delete_worktree_branch,
    _drop_checkpoint_exempt_findings,
    _finish_land_after_success,
    _finish_worktree,
    _land,
    _post_land_unscoped_error_sweep,
    _pre_commit_unscoped_error_sweep,
    _print_land_proof,
    _worktree_branch_name,
    land_parity_findings,
)
from frob.app.ticket_runner._lifecycle import _default_work_worktree
from frob.tickets import Origin, TicketKind, TicketSpec, TicketState, new_ticket
from frob.tickets._land import land
from frob.tickets._land_squash import _assert_still_on_expected_branch
from frob.tickets._models import LandError, LandReport
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
    own `TestFormatPaths.test_write_mode_rewrites_file` shape); the
    Tier-A-fix half is a no-op on a `design/`-less fixture repo and is
    covered by its own dedicated suite (tests/test_gates.py's
    TestFixEngineTierA) -- this test's job is only that `land`'s
    absorption step actually reaches `format_paths` and rewrites a real
    file, not re-proving that module's own behavior. T-1870: the former
    sys sync-interface half is gone (deleted along with the rest of that
    machinery); `_assert_design_loads_pre_land`'s own load-guard behavior
    is exercised separately below (TestAssertDesignLoadsPreLand)."""

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
# frob:ticket T-1870
# frob:ticket T-1903
class TestAssertDesignLoadsPreLand:
    """T-1796 (T-1870 renamed/narrowed this from `_sync_interface_pre_
    land_step` -- the write half went, this read-only guard did not): a
    `design/**` file that fails to PARSE must refuse the land outright,
    not degrade to a WARNING and proceed -- the exact gap that let a
    single dropped quote in `design/frob.strata` break `strata` parsing
    repo-wide and survive three lands undetected. This guard writes
    NOTHING -- unlike its pre-T-1870 shape, a clean design tree with
    interface= drift produces no side effect at all any more."""

    def test_refuses_when_a_design_file_is_malformed(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertDesignLoadsPreLand.test_refuses_when_a_design_file_is_malformed  # noqa: E501
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
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertDesignLoadsPreLand.test_still_proceeds_when_design_dir_absent  # noqa: E501
        # No design/ directory at all -- must NOT be treated as a parse
        # failure; a fixture repo with nothing to sync is the common case
        # every OTHER TestAbsorbPreLandFixes test already relies on.
        assert not (repo / "design").is_dir()
        _absorb_pre_land_fixes(repo, "T-1796")  # must not raise

    # frob:ticket T-1903
    def test_a_tier_a_handler_that_corrupts_design_after_it_was_healthy_refuses_the_land(
        self,
        repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertDesignLoadsPreLand.test_a_tier_a_handler_that_corrupts_design_after_it_was_healthy_refuses_the_land  # noqa: E501
        # T-1903: the pre-tier-a call to `_assert_design_loads_pre_land`
        # passes (the design root parses cleanly going in) -- but the
        # Tier-A fix batch itself is what corrupts `design/frob.strata`
        # here, simulating the T-1900 SYS-IFACE-ORDER incident. Before
        # T-1903, `_absorb_pre_land_fixes` never re-checked after the
        # rewrite and this would have returned normally (a false green);
        # the fix is that the SECOND (post-tier-a) call must catch it and
        # refuse the land, naming the post-tier-a stage in its error.
        design_dir = repo / "design"
        design_dir.mkdir()
        (design_dir / "sample.strata").write_text(
            'module sample\n\nnode checker : trusted {\n    may "exec";\n}\n'
        )
        _run(["git", "add", "-A"], repo)

        def _corrupting_tier_a_fix(*_args: object, **_kwargs: object) -> tuple[object, ...]:
            (design_dir / "sample.strata").write_text(
                'module sample\n\nnode checker : trusted {\n'
                '    attr interface=["unterminated\n};\n'
            )
            return ()

        monkeypatch.setattr(
            "frob.gates._fix_engine.apply_tier_a_fixes", _corrupting_tier_a_fix
        )

        with caplog.at_level("ERROR"):
            with pytest.raises(SystemExit) as exc_info:
                _absorb_pre_land_fixes(repo, "T-1903")
        assert exc_info.value.code == 1
        # T-1903's whole point: the refusal must name WHICH side of the
        # Tier-A rewrite broke design/frob.strata -- a "pre-tier-a"
        # (pre-existing corruption) message would be misleading here,
        # since the design root was genuinely healthy before this land's
        # own Tier-A batch ran.
        assert any(
            "AFTER" in record.message and "Tier-A" in record.message
            for record in caplog.records
        )


# frob:ticket T-1907
# frob:ticket T-1982
class TestAssertTouchedFilesTypeCheckPreLand:
    """`_assert_touched_files_type_check_pre_land` (T-1907): a real `ty`
    subprocess scoped to this ticket's own touched `.py` files, run
    unconditionally at land regardless of profile -- the minimum gate
    the rapid profile may not relax. Real `ty` invocation (matching this
    module's own real-git-subprocess style), not a mocked parser, so the
    test proves the actual wiring (cwd, extra-search-path, exit code
    parsing) works end to end, not just that some mocked call happened."""

    def test_a_type_error_in_a_touched_file_refuses_the_land(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand.test_a_type_error_in_a_touched_file_refuses_the_land  # noqa: E501
        from frob.app.ticket_runner._land_cmd import (
            _assert_touched_files_type_check_pre_land,
        )

        bad = repo / "src" / "bad_types.py"
        bad.write_text('def f(x: int) -> int:\n    return "not an int"\n')
        _run(["git", "add", "-A"], repo)

        with pytest.raises(SystemExit) as exc_info:
            _assert_touched_files_type_check_pre_land(
                repo, "T-1907", frozenset({"src/bad_types.py"})
            )
        assert exc_info.value.code == 1

    def test_a_clean_touched_file_does_not_refuse(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand.test_a_clean_touched_file_does_not_refuse  # noqa: E501
        from frob.app.ticket_runner._land_cmd import (
            _assert_touched_files_type_check_pre_land,
        )

        good = repo / "src" / "good_types.py"
        good.write_text("def f(x: int) -> int:\n    return x + 1\n")
        _run(["git", "add", "-A"], repo)

        _assert_touched_files_type_check_pre_land(
            repo, "T-1907", frozenset({"src/good_types.py"})
        )  # must not raise

    # frob:ticket T-1982
    def test_a_fixture_file_excluded_by_pyproject_is_not_type_checked(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand.test_a_fixture_file_excluded_by_pyproject_is_not_type_checked  # noqa: E501
        # T-1982's own acceptance: a fixture is deliberately ill-typed BY
        # DESIGN (that is the whole point of a detector-testing fixture),
        # yet must not refuse the land -- `pyproject.toml`'s `[tool.ty.
        # src].exclude` says so, and this is the guard that must now
        # honor it even though `_ty_check_files` passes explicit paths.
        from frob.app.ticket_runner._land_cmd import (
            _assert_touched_files_type_check_pre_land,
        )

        (repo / "pyproject.toml").write_text(
            '[tool.ty.src]\nexclude = ["tests/fixtures/**"]\n'
        )
        fixture_dir = repo / "tests" / "fixtures" / "dup_type_name"
        fixture_dir.mkdir(parents=True)
        bad = fixture_dir / "mod_a.py"
        bad.write_text('def f(x: int) -> int:\n    return "not an int"\n')
        _run(["git", "add", "-A"], repo)

        _assert_touched_files_type_check_pre_land(
            repo,
            "T-1982",
            frozenset({"pyproject.toml", "tests/fixtures/dup_type_name/mod_a.py"}),
        )  # must not raise -- the fixture is excluded, so it is never checked

    # frob:ticket T-1982
    def test_a_bad_file_outside_fixtures_still_refuses_with_exclude_configured(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand.test_a_bad_file_outside_fixtures_still_refuses_with_exclude_configured  # noqa: E501
        # The exclude must not WIDEN -- a real touched-file type error
        # outside tests/fixtures/ is still caught even once a
        # [tool.ty.src].exclude is configured.
        from frob.app.ticket_runner._land_cmd import (
            _assert_touched_files_type_check_pre_land,
        )

        (repo / "pyproject.toml").write_text(
            '[tool.ty.src]\nexclude = ["tests/fixtures/**"]\n'
        )
        bad = repo / "src" / "bad_types.py"
        bad.write_text('def f(x: int) -> int:\n    return "not an int"\n')
        _run(["git", "add", "-A"], repo)

        with pytest.raises(SystemExit) as exc_info:
            _assert_touched_files_type_check_pre_land(
                repo,
                "T-1982",
                frozenset({"pyproject.toml", "src/bad_types.py"}),
            )
        assert exc_info.value.code == 1

    # frob:ticket T-1982
    def test_dup_region_fixture_is_covered_by_the_exclude(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand.test_dup_region_fixture_is_covered_by_the_exclude  # noqa: E501
        # The pre-existing sibling fixture named in T-1982's own body,
        # confirmed covered by the same fix (not a name-specific patch).
        from frob.app.ticket_runner._land_cmd import (
            _assert_touched_files_type_check_pre_land,
        )

        (repo / "pyproject.toml").write_text(
            '[tool.ty.src]\nexclude = ["tests/fixtures/**"]\n'
        )
        fixture_dir = repo / "tests" / "fixtures" / "dup_region"
        fixture_dir.mkdir(parents=True)
        bad = fixture_dir / "mod_a.py"
        bad.write_text('def f(x: int) -> int:\n    return "not an int"\n')
        _run(["git", "add", "-A"], repo)

        _assert_touched_files_type_check_pre_land(
            repo,
            "T-1982",
            frozenset({"pyproject.toml", "tests/fixtures/dup_region/mod_a.py"}),
        )  # must not raise

    def test_empty_touched_set_is_a_no_op(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand.test_empty_touched_set_is_a_no_op  # noqa: E501
        from frob.app.ticket_runner._land_cmd import (
            _assert_touched_files_type_check_pre_land,
        )

        _assert_touched_files_type_check_pre_land(
            repo, "T-1907", frozenset()
        )  # must not raise
        _assert_touched_files_type_check_pre_land(
            repo, "T-1907", None
        )  # must not raise

    # frob:ticket T-1907
    def test_cli_land_end_to_end_refuses_a_worktree_with_a_real_ty_error(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand.test_cli_land_end_to_end_refuses_a_worktree_with_a_real_ty_error  # noqa: E501
        # T-1907's DESIGNATED REPRO (BUG002): unlike the unit test above
        # (which calls the new guard function directly -- a function that
        # does not exist at all before this ticket, so a parent-commit
        # repro run of it is vacuous, not a real "did the defect exist"
        # check), this calls `_land` -- the CLI entrypoint that exists at
        # BOTH revisions -- end to end against a worktree whose OWN
        # touched file carries a real `ty` error. At the parent commit
        # (no guard wired into `_land_core_prepare`), this land would
        # PROCEED (no refusal from the type family at all, precisely the
        # T-1894/T-1896 gap T-1907 measured); at this fix, it REFUSES
        # with `SystemExit(1)` before ever reaching the merge.
        from frob.app.config import AppConfig

        created = new_ticket(repo, _spec("Land with a real ty error"))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        work_cfg = AppConfig(
            ticket_command="work", ticket_id=tid, ticket_foreground=True
        )
        _work(repo, work_cfg)
        worktree = _default_work_worktree(repo, tid)

        # This ticket's own touched file carries a genuine, unambiguous
        # `ty` error -- the exact T-1894/T-1896 shape (a real static type
        # defect, not a runtime bug).
        (worktree / "src" / "bad_types.py").write_text(
            'def f(x: int) -> int:\n    return "not an int"\n'
        )
        (worktree / "tests").mkdir(exist_ok=True)
        (worktree / "tests" / "test_ok.py").write_text(
            "def test_ok():\n    assert True\n"
        )
        loaded = load_all(worktree)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_ok.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(worktree, ticket).is_ok
        _run(["git", "add", "-A"], worktree)
        _run(["git", "commit", "-q", "-m", "wt: bad_types.py + done report"], worktree)

        land_cfg = AppConfig(
            ticket_command="land",
            ticket_id=tid,
            ticket_worktree=worktree,
            ticket_dry_run=False,
        )
        with pytest.raises(SystemExit) as exc_info:
            _land(repo, land_cfg)
        assert exc_info.value.code == 1
        # The land must genuinely not have merged: main's own tip is
        # unchanged (no commit for this ticket landed onto it).
        loaded_main = load_all(repo)
        assert loaded_main.is_ok
        assert loaded_main.danger_ok[tid].state != TicketState.DONE


# frob:ticket T-2114
# frob:ticket T-2201
class TestAssertNewPublicSymbolsHaveDocAndTestEdges:
    """`_assert_new_public_symbols_have_doc_and_test_edge_pre_land`
    (T-2114): generalizes T-1907's touched-set shape from the type family
    to the doc/test-edge families -- a rapid-profile land that introduces
    a new public top-level symbol with no `frob:doc`/`frob:tests` edge
    used to publish it anyway, red until the DEFERRED post-land sweep
    eventually caught it against an already-published commit."""

    def test_a_new_public_symbol_with_no_edges_refuses_the_land(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges.test_a_new_public_symbol_with_no_edges_refuses_the_land  # noqa: E501
        from frob.app.ticket_runner._land_cmd import (
            _assert_new_public_symbols_have_doc_and_test_edge_pre_land,
        )

        new_file = repo / "src" / "undocumented.py"
        new_file.write_text("def brand_new_public_function():\n    return 1\n")
        _run(["git", "add", "-A"], repo)

        with pytest.raises(SystemExit) as exc_info:
            _assert_new_public_symbols_have_doc_and_test_edge_pre_land(
                repo, "T-2114", frozenset({"src/undocumented.py"})
            )
        assert exc_info.value.code == 1

    def test_a_new_public_symbol_with_both_edges_does_not_refuse(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges.test_a_new_public_symbol_with_both_edges_does_not_refuse  # noqa: E501
        from frob.app.ticket_runner._land_cmd import (
            _assert_new_public_symbols_have_doc_and_test_edge_pre_land,
        )

        new_file = repo / "src" / "documented.py"
        new_file.write_text(
            "# frob:doc docs/modules/example.md#brand-new-public-function\n"
            "# frob:tests tests/test_example.py::test_brand_new_public_function\n"
            "def brand_new_public_function():\n"
            "    return 1\n"
        )
        _run(["git", "add", "-A"], repo)

        _assert_new_public_symbols_have_doc_and_test_edge_pre_land(
            repo, "T-2114", frozenset({"src/documented.py"})
        )  # must not raise

    def test_an_unrelated_land_touching_no_new_public_symbols_is_unaffected(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges.test_an_unrelated_land_touching_no_new_public_symbols_is_unaffected  # noqa: E501
        # `repo`'s own fixture file (src/feature.py) already exists at the
        # merge-base -- editing its BODY (not adding a new top-level
        # public symbol) must never refuse, matching this check's own
        # name-based "new" definition, not a hunk-span one.
        from frob.app.ticket_runner._land_cmd import (
            _assert_new_public_symbols_have_doc_and_test_edge_pre_land,
        )

        (repo / "src" / "feature.py").write_text("# landed feature, edited\n")
        _run(["git", "add", "-A"], repo)

        _assert_new_public_symbols_have_doc_and_test_edge_pre_land(
            repo, "T-2114", frozenset({"src/feature.py"})
        )  # must not raise

    # frob:ticket T-2201
    def test_a_directive_looking_line_inside_a_docstring_does_not_satisfy_the_gate(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges.test_a_directive_looking_line_inside_a_docstring_does_not_satisfy_the_gate  # noqa: E501
        # T-2201's DESIGNATED REPRO (BUG002): the old check did a plain
        # substring test over whatever "#"-prefixed-looking lines sit
        # directly above the def -- including a line that only LOOKS like
        # a comment because it happens to start with "#" while actually
        # being part of a preceding multi-line string literal's own
        # content. This constant's own text has the shape of the two
        # required directives, sitting immediately above
        # brand_new_public_function, that is NOT a grammar comment at all
        # -- it is string content. The gate must still refuse (no GENUINE
        # doc/tests edge exists).
        from frob.app.ticket_runner._land_cmd import (
            _assert_new_public_symbols_have_doc_and_test_edge_pre_land,
        )

        new_file = repo / "src" / "fake_directive.py"
        new_file.write_text(
            '_X = """\n'
            "# frob:doc docs/modules/example.md#brand-new-public-function\n"
            '# frob:tests tests/test_example.py::test_brand_new_public_function"""\n'
            "def brand_new_public_function():\n"
            "    return 1\n"
        )
        _run(["git", "add", "-A"], repo)

        with pytest.raises(SystemExit) as exc_info:
            _assert_new_public_symbols_have_doc_and_test_edge_pre_land(
                repo, "T-2201", frozenset({"src/fake_directive.py"})
            )
        assert exc_info.value.code == 1

    def test_empty_touched_set_is_a_no_op(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges.test_empty_touched_set_is_a_no_op  # noqa: E501
        from frob.app.ticket_runner._land_cmd import (
            _assert_new_public_symbols_have_doc_and_test_edge_pre_land,
        )

        _assert_new_public_symbols_have_doc_and_test_edge_pre_land(
            repo, "T-2114", frozenset()
        )  # must not raise
        _assert_new_public_symbols_have_doc_and_test_edge_pre_land(
            repo, "T-2114", None
        )  # must not raise

    # frob:ticket T-2114
    def test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges.test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol  # noqa: E501
        # T-2114's DESIGNATED REPRO (BUG002), mirroring T-1907's own
        # `test_cli_land_end_to_end_refuses_a_worktree_with_a_real_ty_error`
        # precedent exactly: this calls `_land`, the CLI entrypoint that
        # exists at BOTH revisions, end to end against a worktree whose
        # own diff introduces a new public top-level symbol with no
        # frob:doc/frob:tests edge. At the parent commit (no guard wired
        # into `_land_core_prepare`), this land PROCEEDS -- the exact gap
        # this ticket measured, a new public symbol landing clean, red
        # only once the deferred post-land sweep eventually catches it
        # against an already-published commit. At this fix, it REFUSES
        # with `SystemExit(1)` before ever reaching the merge.
        created = new_ticket(repo, _spec("Land with a new undocumented symbol"))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        work_cfg = AppConfig(
            ticket_command="work", ticket_id=tid, ticket_foreground=True
        )
        _work(repo, work_cfg)
        worktree = _default_work_worktree(repo, tid)

        (worktree / "src" / "undocumented.py").write_text(
            "def brand_new_public_function():\n    return 1\n"
        )
        (worktree / "tests").mkdir(exist_ok=True)
        (worktree / "tests" / "test_ok.py").write_text(
            "def test_ok():\n    assert True\n"
        )
        loaded = load_all(worktree)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_ok.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(worktree, ticket).is_ok
        _run(["git", "add", "-A"], worktree)
        _run(
            ["git", "commit", "-q", "-m", "wt: undocumented.py + done report"],
            worktree,
        )

        land_cfg = AppConfig(
            ticket_command="land",
            ticket_id=tid,
            ticket_worktree=worktree,
            ticket_dry_run=False,
        )
        with pytest.raises(SystemExit) as exc_info:
            _land(repo, land_cfg)
        assert exc_info.value.code == 1
        # The land must genuinely not have merged: main's own tip is
        # unchanged (no commit for this ticket landed onto it).
        loaded_main = load_all(repo)
        assert loaded_main.is_ok
        assert loaded_main.danger_ok[tid].state != TicketState.DONE


# frob:ticket T-2214
def _long_complex_function_source(name: str) -> str:
    """A python function source, long AND cyclomatically complex enough to
    trip ARCH001's calibrated default threshold (60 lines, cyclomatic-proxy
    >= 8) -- shared by every `TestAssertDiffDoesNotWorsenLongFunctions`
    case that needs a genuine over-threshold function rather than hand-
    writing 80+ lines of `if`/`for` per test."""
    lines = [f"def {name}(x):"]
    for i in range(20):
        lines.append(f"    if x == {i}:")
        lines.append(f"        x = x + {i}")
        lines.append(f"        for j in range({i}):")
        lines.append(f"            x = x + j")
    lines.append("    return x")
    return "\n".join(lines) + "\n"


# frob:ticket T-2214
class TestAssertDiffDoesNotWorsenLongFunctions:
    """`_assert_diff_does_not_worsen_long_functions_pre_land` (T-2214):
    ARCH001 is a size threshold, not a doc/test-edge family, so it needs
    its own diff-scoped check rather than a `_DOC_TEST_EDGE_FAMILIES`
    entry -- refuse only a function the CURRENT diff itself pushes past
    threshold, never one already over threshold before the diff."""

    def test_a_new_over_threshold_function_refuses_the_land(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions.test_a_new_over_threshold_function_refuses_the_land  # noqa: E501
        from frob.app.ticket_runner._land_cmd import (
            _assert_diff_does_not_worsen_long_functions_pre_land,
        )

        new_file = repo / "src" / "grown.py"
        new_file.write_text(_long_complex_function_source("brand_new_long_function"))
        _run(["git", "add", "-A"], repo)

        with pytest.raises(SystemExit) as exc_info:
            _assert_diff_does_not_worsen_long_functions_pre_land(
                repo, "T-2214", frozenset({"src/grown.py"})
            )
        assert exc_info.value.code == 1

    def test_a_pre_existing_over_threshold_function_merely_touched_does_not_refuse(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions.test_a_pre_existing_over_threshold_function_merely_touched_does_not_refuse  # noqa: E501
        # The function is ALREADY over threshold at the merge-base commit
        # (committed once, unchanged in shape) -- a later diff that only
        # adds a trailing comment must not be blamed on THIS land, the
        # exact global-vs-attributable distinction T-2198 already fixed
        # for the TICK gate.
        from frob.app.ticket_runner._land_cmd import (
            _assert_diff_does_not_worsen_long_functions_pre_land,
        )

        already_long = repo / "src" / "already_long.py"
        already_long.write_text(_long_complex_function_source("pre_existing_long_function"))
        _commit_all(repo, "pre-existing over-threshold function")

        already_long.write_text(
            already_long.read_text() + "# trailing comment, function body unchanged\n"
        )
        _run(["git", "add", "-A"], repo)

        _assert_diff_does_not_worsen_long_functions_pre_land(
            repo, "T-2214", frozenset({"src/already_long.py"})
        )  # must not raise

    def test_an_unrelated_land_touching_no_python_files_is_unaffected(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions.test_an_unrelated_land_touching_no_python_files_is_unaffected  # noqa: E501
        from frob.app.ticket_runner._land_cmd import (
            _assert_diff_does_not_worsen_long_functions_pre_land,
        )

        (repo / "README.md").write_text("# landed feature, edited\n")
        _run(["git", "add", "-A"], repo)

        _assert_diff_does_not_worsen_long_functions_pre_land(
            repo, "T-2214", frozenset({"README.md"})
        )  # must not raise

    def test_a_waived_over_threshold_function_does_not_refuse(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions.test_a_waived_over_threshold_function_does_not_refuse  # noqa: E501
        # A real ARCH001 waiver comment directly above the def is the same
        # reasoned-waiver escape hatch arch_gate/frob.gates._match_waiver
        # already honor for this rule -- this check must not invent a
        # second, stricter one.
        from frob.app.ticket_runner._land_cmd import (
            _assert_diff_does_not_worsen_long_functions_pre_land,
        )

        new_file = repo / "src" / "waived.py"
        new_file.write_text(
            '# frob:waive ARCH001 reason="test fixture, genuinely irreducible"\n'
            + _long_complex_function_source("waived_long_function")
        )
        _run(["git", "add", "-A"], repo)

        _assert_diff_does_not_worsen_long_functions_pre_land(
            repo, "T-2214", frozenset({"src/waived.py"})
        )  # must not raise

    def test_empty_touched_set_is_a_no_op(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions.test_empty_touched_set_is_a_no_op  # noqa: E501
        from frob.app.ticket_runner._land_cmd import (
            _assert_diff_does_not_worsen_long_functions_pre_land,
        )

        _assert_diff_does_not_worsen_long_functions_pre_land(
            repo, "T-2214", frozenset()
        )  # must not raise
        _assert_diff_does_not_worsen_long_functions_pre_land(
            repo, "T-2214", None
        )  # must not raise


# frob:ticket T-1907
class TestReverifyDoneReportClaimsDisclosesUnknownGateState:
    """T-1907 proposal (2): a Done report with no `### Captured claims`
    section used to make `_reverify_done_report_claims_post_merge` a
    silent no-op -- this land's fresh gate-state check is simply never
    compared, with nothing in the log distinguishing "compared and
    passed" from "never compared at all". Now it logs a WARNING naming
    that distinction explicitly."""

    def test_no_captured_claims_section_logs_unknown_not_clean(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestReverifyDoneReportClaimsDisclosesUnknownGateState.test_no_captured_claims_section_logs_unknown_not_clean  # noqa: E501
        from frob.tickets._land_verify import _reverify_done_report_claims_post_merge

        created = new_ticket(repo, _spec("No captured claims"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(repo)
        assert loaded.is_ok
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "body": ticket.body
                + "\n## Done report\n\nDone by hand, no capture run.\n"
            }
        )
        assert write_ticket(repo, ticket).is_ok
        _commit_all(repo, "add done report with no captured claims")

        with caplog.at_level("WARNING"):
            result = _reverify_done_report_claims_post_merge(
                repo, tid, frozenset(), lambda: (0, 0, 0)
            )
        assert result.is_ok
        assert any(
            "UNKNOWN" in record.message and "not clean" in record.message
            for record in caplog.records
        )


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
# frob:ticket T-1910
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

    # frob:ticket T-1884
    def test_cli_land_invoked_with_root_equal_to_worktree_still_verifies(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_cli_land_invoked_with_root_equal_to_worktree_still_verifies  # noqa: E501
        # T-1884's second, non-anchor reproduction (T-1895): `_land` (the
        # CLI wrapper `frob ticket land` dispatches to) is called with its
        # own `root` argument -- when a caller invokes it with `root`
        # equal to `--worktree` (the common "cwd defaulted to inside the
        # worktree" shape T-1003 names), the CLI's OWN `root` local used
        # to stay pointed at the worktree for every post-land step,
        # including `_print_land_proof`'s `is_ancestor_of_main` check --
        # which then queried the WRONG checkout (the worktree branch the
        # commit was merged FROM, not the primary checkout it was merged
        # ONTO) and always read False, even on a fully successful land.
        # Calling `_land` directly with `root=worktree` reproduces that
        # exact shape without needing a real `--worktree`-flag CLI
        # invocation.
        from frob.app.config import AppConfig

        created = new_ticket(repo, _spec("CLI land root-equals-worktree"))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        work_cfg = AppConfig(
            ticket_command="work", ticket_id=tid, ticket_foreground=True
        )
        _work(repo, work_cfg)
        worktree = _default_work_worktree(repo, tid)

        # T-0398: the CLI `_land` wrapper (unlike `land()` called directly)
        # ALWAYS supplies real `collected`/`passed` closures that re-verify
        # evidence against the merged tree -- a fake, never-collectable
        # node id (`_land_a_real_ticket`'s own shortcut) would fail real
        # evidence re-verification here, so this needs a genuinely
        # collectable, passing test.
        (worktree / "tests").mkdir(exist_ok=True)
        (worktree / "tests" / "test_ok.py").write_text(
            "def test_ok():\n    assert True\n"
        )
        loaded = load_all(worktree)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_ok.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(worktree, ticket).is_ok
        _run(["git", "add", "-A"], worktree)
        _run(["git", "commit", "-q", "-m", "wt: done report"], worktree)

        land_cfg = AppConfig(
            ticket_command="land",
            ticket_id=tid,
            ticket_worktree=worktree,
            ticket_dry_run=False,
        )
        with caplog.at_level("INFO"):
            _land(worktree, land_cfg)  # root == worktree, the bug shape

        proof_lines = [
            rec.message for rec in caplog.records if rec.message.startswith("LAND-PROOF:")
        ]
        assert len(proof_lines) == 1
        # T-2091: this fixture's Done report carries no "### Captured
        # claims" section, so claims re-verification is legitimately
        # SKIPPED-UNMEASURED (not PASSED) -- and T-2091 deliberately makes
        # a skip print the literal `verified=SKIPPED-UNMEASURED`, never
        # `True`, so a skip can never be mistaken for a real pass on the
        # one line the fleet trusts to confirm a land. The property this
        # test actually guards -- `is_ancestor_of_main=True` even when
        # `root == worktree` -- is unaffected by T-2091 and still checked
        # below.
        assert "verified=SKIPPED-UNMEASURED" in proof_lines[0]
        assert "claims_reverify=skipped-unmeasured" in proof_lines[0]
        assert "is_ancestor_of_main=True" in proof_lines[0]

    def test_proof_verifies_a_real_land(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_proof_\
        # verifies_a_real_land
        _tid, _worktree, report = self._land_a_real_ticket(repo)
        assert _print_land_proof(repo, report) is True

    # frob:ticket T-1884
    def test_proof_verifies_an_anchor_ticket_left_queued_on_main(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_proof_verifies_an_anchor_ticket_left_queued_on_main  # noqa: E501
        # T-1884: a legitimately anchored ticket (T-1856's anchor=True
        # marker) that T-1874's skip-close path lands with its state left
        # QUEUED on main by design must still read verified=True -- before
        # this fix, `_land_proof_checks`'s state_ok only ever accepted
        # done/dropped, so a completely correct anchor land always printed
        # verified=False (observed landing T-1820, 2026-08-08).
        from types import SimpleNamespace

        created = new_ticket(repo, _spec("Anchor left queued"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(repo)
        assert loaded.is_ok
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={"anchor": True, "anchor_reason": "permanent waiver target"}
        )
        assert write_ticket(repo, ticket).is_ok
        _commit_all(repo, "anchor ticket, still queued")
        commit_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        fake_report = SimpleNamespace(ticket_id=tid, final_id=tid, commit_sha=commit_sha)
        assert _print_land_proof(repo, fake_report) is True

    # frob:ticket T-1884
    def test_proof_still_refuses_a_non_anchor_ticket_left_queued(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_proof_still_refuses_a_non_anchor_ticket_left_queued  # noqa: E501
        # The anchor carve-out must not become a blanket "queued is fine"
        # -- an ORDINARY (non-anchor) ticket left queued on main is a real
        # unverified-land signal and must still read verified=False.
        from types import SimpleNamespace

        created = new_ticket(repo, _spec("Ordinary ticket left queued"))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "ordinary ticket, still queued")
        commit_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        fake_report = SimpleNamespace(ticket_id=tid, final_id=tid, commit_sha=commit_sha)
        assert _print_land_proof(repo, fake_report) is False

    # frob:ticket T-2129
    def test_proof_verifies_a_queued_ticket_with_a_recorded_failure_log(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_proof_verifies_a_queued_ticket_with_a_recorded_failure_log  # noqa: E501
        # T-2129 (T-2109's own landed shape): `frob ticket fail` returns a
        # ticket to QUEUED with a recorded `## Failure log` entry, and
        # `land` correctly publishes that record to `main` as-is
        # (`_skip_close_for_legitimate_fail`, T-1818) -- no done
        # transition is ever attempted. Before this fix, `_land_proof_
        # checks`'s terminal-state allowlist only recognized done/dropped/
        # anchor-left-queued, so this genuinely successful publish (real
        # ancestor of main) still printed verified=False, contradicting
        # its own is_ancestor_of_main=True field on the same LAND-PROOF
        # line. FAILS at pre-fix behavior (`_print_land_proof` returns
        # False here even though the commit is a real ancestor of main).
        from types import SimpleNamespace

        created = new_ticket(repo, _spec("Queued with failure log"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(repo)
        assert loaded.is_ok
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "body": ticket.body
                + "\n## Failure log\n\nattempt 1: could not build it as scoped\n"
            }
        )
        assert write_ticket(repo, ticket).is_ok
        _commit_all(repo, "queued ticket with a recorded failure log")
        commit_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        fake_report = SimpleNamespace(
            ticket_id=tid, final_id=tid, commit_sha=commit_sha
        )
        assert _print_land_proof(repo, fake_report) is True

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
            ticket_id=tid,
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

    # frob:ticket T-1910
    # frob:tests tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_unverified_land_exits_nonzero_even_without_finish  # noqa: E501
    def test_unverified_land_exits_nonzero_even_without_finish(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # T-1910: the T-1895 incident's own shape -- `frob ticket land`
        # (no `--finish`/`--retire-on-proof` at all, the ordinary,
        # overwhelmingly common invocation) printed "landed as <sha>" plus
        # a REL001 bump, then `LAND-PROOF: ... verified=False`, and still
        # EXITED 0. Before the T-1910 fix, `_finish_land_after_success`
        # only ever `sys.exit(1)`ed on an unverified proof when
        # `--finish`/`--retire-on-proof` was passed -- an ordinary land
        # with neither flag just printed the LAND-PROOF line and returned
        # normally, reporting success by exit code to any caller that
        # does not grep the log for `verified=`. This test reproduces
        # that exact ordinary-invocation shape (no finish flags) and
        # asserts a `SystemExit` -- FAILS at the pre-fix behavior (no
        # exception raised, silent return) and PASSES once `verified=
        # False` refuses unconditionally.
        from types import SimpleNamespace

        tid, worktree, real_report = self._land_a_real_ticket(repo)

        fake_report = SimpleNamespace(
            ticket_id=tid,
            dry_run=False,
            final_id=real_report.final_id,
            commit_sha="0" * 40,  # a real-looking sha, never an ancestor of main
        )
        cfg = AppConfig(
            ticket_command="land",
            ticket_id=tid,
            ticket_worktree=worktree,
            # deliberately no ticket_land_finish / ticket_land_retire_on_proof
        )
        with caplog.at_level("INFO"), pytest.raises(SystemExit) as exc_info:
            _finish_land_after_success(repo, worktree, fake_report, cfg)

        assert exc_info.value.code != 0
        proof_lines = [
            rec.message for rec in caplog.records if rec.message.startswith("LAND-PROOF:")
        ]
        assert len(proof_lines) == 1
        # T-2091: `_land_a_real_ticket`'s earlier real `land()` call left
        # `_LAST_CLAIMS_OUTCOME[tid]` as SKIPPED_UNMEASURED (that fixture's
        # Done report also carries no "### Captured claims" section), and
        # `_print_land_proof` reads it back for this SAME `ticket_id` --
        # so the PRINTED token is the literal `SKIPPED-UNMEASURED`, never
        # `False`, even though the fake commit is not really an ancestor
        # of main. This is deliberate: a skip must never be spelled as
        # either boolean (see `_print_land_proof`'s own docstring). The
        # property this test actually guards -- the RETURNED verified
        # bool (unaffected by the skip) still refuses via nonzero exit
        # even without `--finish` -- is asserted above via `exc_info`.
        assert "is_ancestor_of_main=False" in proof_lines[0]
        assert "verified=SKIPPED-UNMEASURED" in proof_lines[0]


# frob:ticket T-1913
class TestLandProofAncestorRetry:
    """`_is_ancestor_with_retry` (T-1913): a short, bounded retry around
    `git merge-base --is-ancestor` before `_land_proof_checks` concludes
    a commit is not on `main` -- T-1913's own investigation could not pin
    down the real T-1895 incident's mechanism in a synchronous fixture,
    but named "retry the check" as a concrete, implementable mitigation
    for a suspected commit/ref visibility race. These tests exercise the
    RETRY MECHANISM itself (a real git repo, a monkeypatched `run_argv`
    that fails N times then succeeds) -- they do not, and cannot, prove
    the retry fixes the still-unreproduced T-1895 race; see this ticket's
    own Done report for that disclosure."""

    def test_retries_until_ancestor_check_settles_true(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.app.ticket_runner import _land_cmd as _land_cmd_mod
        from frob.gitio import ProcResult

        commit_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        real_run_argv = _land_cmd_mod.run_argv
        calls = {"n": 0}

        def _flaky_run_argv(argv, **kwargs):  # noqa: ANN001, ANN202
            if "merge-base" in argv and "--is-ancestor" in argv:
                calls["n"] += 1
                if calls["n"] < 3:
                    return Ok(
                        ProcResult(
                            argv=tuple(argv), returncode=1, stdout="", stderr=""
                        )
                    )
            return real_run_argv(argv, **kwargs)

        monkeypatch.setattr(_land_cmd_mod, "run_argv", _flaky_run_argv)
        sleeps: list[float] = []

        result = _land_cmd_mod._is_ancestor_with_retry(
            repo, commit_sha, sleep=sleeps.append
        )

        assert result is True
        assert calls["n"] == 3
        assert sleeps == [0.1, 0.2]

    def test_gives_up_after_exhausting_retries_on_a_genuine_non_ancestor(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.app.ticket_runner import _land_cmd as _land_cmd_mod
        from frob.gitio import ProcResult

        def _always_false(argv, **kwargs):  # noqa: ANN001, ANN202
            return Ok(ProcResult(argv=tuple(argv), returncode=1, stdout="", stderr=""))

        monkeypatch.setattr(_land_cmd_mod, "run_argv", _always_false)
        sleeps: list[float] = []

        result = _land_cmd_mod._is_ancestor_with_retry(
            repo, "0" * 40, sleep=sleeps.append
        )

        assert result is False
        assert sleeps == [0.1, 0.2, 0.4]


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


# frob:ticket T-1920
class TestBranchDriftGuard:
    """T-1920 (T-1910 residue, REQUIRED FIXES 2-4): `_assert_still_on_
    expected_branch` refuses a land's final squash commit BY CONSTRUCTION
    when `root`'s checked-out branch drifted away from the branch the
    land began operating on -- exactly the T-1895 incident's own shape (a
    fully-formed, complete land commit reachable only from an unrelated
    branch). Simulates the drift via the `bump_version` callable seam
    `land()` already exposes (called late, immediately before the final
    commit) rather than a real concurrent process, since T-1920's own
    investigation -- mirroring T-1913's for the sibling ancestor-retry
    mitigation -- could not reproduce the underlying race in a
    synchronous fixture either; this proves the fix closes the SHAPE of
    the incident by construction, disclosed honestly as an injected
    repro rather than a spontaneous one."""

    # frob:tests tests/test_ticket_work_and_land_finish.py::TestBranchDriftGuard.test_branch_drift_before_final_commit_refuses_by_construction  # noqa: E501
    def test_branch_drift_before_final_commit_refuses_by_construction(
        self, repo: Path
    ) -> None:
        # Pre-T-1920 fix, this exact sequence let `land()` return `Ok`
        # after committing the ticket's `state: done` write (plus any
        # REL001 bump) onto the DRIFTED branch, not onto `main` -- a
        # commit `LAND-PROOF` would only discover was unreachable from
        # `main` AFTER the fact. This test FAILS at that pre-fix
        # behavior (asserts `is_err`, which used to be `False`/`is_ok`)
        # and PASSES once `_assert_still_on_expected_branch` refuses
        # before the commit ever happens.
        created = new_ticket(repo, _spec("Branch drift regression"))
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

        main_tip_before = _run(["git", "rev-parse", "main"], repo).stdout.strip()

        def _bump_version_that_drifts_root_off_main(r, t, fid):  # noqa: ANN001, ANN202
            # Simulates a concurrent process moving `root`'s HEAD off
            # `main` in the window between `_land_precheck` resolving
            # `main_branch_name` and the final squash commit -- the
            # ledger splice (state=done) is already staged in `r`'s
            # index at this call site (T-0338: `bump_version` runs after
            # the squash-and-splice, before the final commit), so
            # committing from here on would carry it onto whatever
            # branch is now checked out.
            _run(["git", "checkout", "-b", "sim-drift-t1920"], r)
            return Ok(None)

        result = land(
            repo,
            tid,
            worktree,
            dry_run=False,
            bump_version=_bump_version_that_drifts_root_off_main,
        )

        assert result.is_err, (
            "land() succeeded despite root drifting off main mid-land -- "
            "the T-1920 guard did not fire"
        )
        assert result.danger_err == LandError.BranchDrift

        # Acceptance 1: the ticket's state on the REAL `main` branch (not
        # whatever `repo`'s working tree currently has checked out) must
        # not have moved to a terminal state.
        main_ledger = _run(
            ["git", "show", f"main:{ledger_path(repo).relative_to(repo)}"], repo
        ).stdout
        assert f"# {tid} " in main_ledger or tid in main_ledger
        assert "state: done" not in main_ledger.split(tid, 1)[-1].split("# T-", 1)[0]

        # Acceptance 2: `main` itself did not move at all -- no bump, no
        # squash commit, nothing landed on it.
        main_tip_after = _run(["git", "rev-parse", "main"], repo).stdout.strip()
        assert main_tip_after == main_tip_before

    # frob:tests tests/test_ticket_work_and_land_finish.py::TestBranchDriftGuard.test_no_drift_is_a_noop  # noqa: E501
    def test_no_drift_is_a_noop(self, repo: Path) -> None:
        # Sanity/baseline: an ordinary land (no branch movement) must not
        # be refused by the new guard.
        result = _assert_still_on_expected_branch(repo, "main", "T-0001")
        assert result.is_ok
