"""Unit tests for `frob.app.ticket_runner._rapid_sweep` (T-1684): the
rapid profile's deferred, non-blocking post-land unscoped sweep."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from frob.app.ticket_runner import _rapid_sweep
from frob.app.ticket_runner._rapid_sweep import (
    RapidSweepError,
    _attribute_new_findings,
    _close_resolved_sweep_tickets,
    _file_regression_ticket,
    _identities_still_reproducing,
    _land_ids_between,
    _parse_sweep_ticket_identities,
    _read_baseline,
    _read_baseline_commit,
    _resolve_actual_head,
    _ticket_is_open,
    _true_finding_count_for_identities,
    _write_baseline,
    run_deferred_post_land_sweep,
    spawn_deferred_post_land_sweep,
)


def _init_git_repo(root: Path) -> None:
    """A minimal real git repo for T-2009's `_land_ids_between`/`_resolve_
    actual_head` tests -- these shell out to real `git log`/`rev-parse`,
    unlike most of this module's tests which use a plain `tmp_path`."""
    import subprocess

    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "config", "user.name", "Test"], check=True
    )


def _git_commit(root: Path, message: str) -> str:
    """One empty, real commit with `message`; returns its full sha."""
    import subprocess

    subprocess.run(
        ["git", "-C", str(root), "commit", "--allow-empty", "-q", "-m", message],
        check=True,
    )
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class TestRollingBaseline:
    """The rolling baseline is what lets a deferred sweep cost ONE check
    instead of the two `standard` pays."""

    def test_absent_baseline_reads_as_none_not_empty(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_absent_baseline_reads_as_none_not_empty  # noqa: E501
        assert _read_baseline(tmp_path) is None

    def test_corrupt_baseline_reads_as_none_not_empty(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_corrupt_baseline_reads_as_none_not_empty  # noqa: E501
        path = tmp_path / ".frob" / "rapid-sweep-baseline.json"
        path.parent.mkdir(parents=True)
        path.write_text("{not json", encoding="utf-8")
        assert _read_baseline(tmp_path) is None

    def test_write_then_read_round_trips(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_write_then_read_round_trips  # noqa: E501
        findings = frozenset({("COV003", "a.py"), ("DOC011", "b.md")})
        _write_baseline(tmp_path, findings, "deadbeef" * 5)
        assert _read_baseline(tmp_path) == findings
        stored = json.loads(
            (tmp_path / ".frob" / "rapid-sweep-baseline.json").read_text(
                encoding="utf-8"
            )
        )
        assert stored["commit"] == "deadbeef" * 5

    def test_read_baseline_commit_absent_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_read_baseline_commit_absent_is_none  # noqa: E501
        assert _read_baseline_commit(tmp_path) is None

    def test_read_baseline_commit_round_trips(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_read_baseline_commit_round_trips  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "abc123")
        assert _read_baseline_commit(tmp_path) == "abc123"


class TestLandIdsBetween:
    """T-2009: the mechanical fix for misattribution -- tell how many
    lands (and which) actually landed in a commit range, instead of
    assuming it was always exactly the one that spawned this sweep."""

    def test_single_land_in_range(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestLandIdsBetween.test_single_land_in_range  # noqa: E501
        _init_git_repo(tmp_path)
        start = _git_commit(tmp_path, "chore: init")
        _git_commit(tmp_path, "fix(tickets): land T-1001 something")
        end = _git_commit(tmp_path, "chore(rapid): record T-1001's deferred sweep")
        assert _land_ids_between(tmp_path, start, end) == ["T-1001"]

    def test_multiple_lands_in_range_oldest_first(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestLandIdsBetween.test_multiple_lands_in_range_oldest_first  # noqa: E501
        _init_git_repo(tmp_path)
        start = _git_commit(tmp_path, "chore: init")
        _git_commit(tmp_path, "fix(tickets): land T-1977 first fix")
        _git_commit(tmp_path, "chore(rapid): record T-1977's deferred sweep")
        _git_commit(tmp_path, "feat(tickets): land T-1995 second fix")
        end = _git_commit(tmp_path, "chore(rapid): record T-1995's deferred sweep")
        # T-1998's real misattribution shape: two lands landed in the
        # window this sweep measured, so both must be named -- neither
        # gets silently dropped, and order is oldest-first (git log
        # --reverse).
        assert _land_ids_between(tmp_path, start, end) == ["T-1977", "T-1995"]

    def test_non_land_commits_are_ignored(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestLandIdsBetween.test_non_land_commits_are_ignored  # noqa: E501
        _init_git_repo(tmp_path)
        start = _git_commit(tmp_path, "chore: init")
        _git_commit(tmp_path, "chore(tickets): file T-2000")
        _git_commit(tmp_path, "fix(tickets): land T-2001 real fix")
        end = _git_commit(tmp_path, "chore: unrelated housekeeping")
        assert _land_ids_between(tmp_path, start, end) == ["T-2001"]

    def test_non_repo_returns_empty_list(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestLandIdsBetween.test_non_repo_returns_empty_list  # noqa: E501
        # tmp_path is not a git repo -- degrade to [] rather than raise,
        # so a caller falls back to the pre-T-2009 single-attribution
        # behavior instead of crashing an otherwise-successful sweep.
        assert _land_ids_between(tmp_path, "abc", "def") == []


class TestResolveActualHead:
    def test_non_repo_falls_back_to_the_given_commit(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestResolveActualHead.test_non_repo_falls_back_to_the_given_commit  # noqa: E501
        assert _resolve_actual_head(tmp_path, "fallback-sha") == "fallback-sha"

    def test_real_repo_resolves_the_true_head(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestResolveActualHead.test_real_repo_resolves_the_true_head  # noqa: E501
        _init_git_repo(tmp_path)
        _git_commit(tmp_path, "chore: init")
        real_head = _git_commit(tmp_path, "chore: second commit")
        # "fallback-sha" is deliberately NOT the real head -- proving the
        # real HEAD is what's returned, not the caller's own guess.
        assert _resolve_actual_head(tmp_path, "fallback-sha") == real_head


class TestDeferredSweepRun:
    """`run_deferred_post_land_sweep` files, never reverts."""

    @pytest.fixture
    def _no_debt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`record_rapid_debt` shells out to git; a tmp_path is not a repo."""
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt", lambda *a, **k: None
        )

    def test_unmeasurable_check_leaves_the_baseline_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_unmeasurable_check_leaves_the_baseline_untouched  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: None,
        )
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_err
        assert result.danger_err is RapidSweepError.Unmeasurable
        assert _read_baseline(tmp_path) == frozenset({("COV003", "a.py")})

    def test_first_sweep_records_a_baseline_and_files_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_first_sweep_records_a_baseline_and_files_nothing  # noqa: E501
        fresh = frozenset({("COV003", "a.py")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: fresh,
        )
        filed: list[object] = []
        monkeypatch.setattr(
            _rapid_sweep, "_file_regression_ticket", lambda *a: filed.append(a)
        )
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_ok
        assert result.danger_ok is None
        assert filed == []
        assert _read_baseline(tmp_path) == fresh

    def test_no_new_findings_is_clean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_no_new_findings_is_clean  # noqa: E501
        existing = frozenset({("COV003", "a.py")})
        _write_baseline(tmp_path, existing, "old")
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: existing,
        )
        filed: list[object] = []
        monkeypatch.setattr(
            _rapid_sweep, "_file_regression_ticket", lambda *a: filed.append(a)
        )
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_ok
        assert result.danger_ok is None
        assert filed == []

    def test_new_findings_file_a_ticket_and_rebaseline(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_new_findings_file_a_ticket_and_rebaseline  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        fresh = frozenset({("COV003", "a.py"), ("DOC011", "b.md")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: fresh,
        )
        seen: list[frozenset[tuple[str, str]]] = []

        def _fake_file(root, final_id, commit, new_findings):  # noqa: ANN001, ANN202
            seen.append(new_findings)
            return "T-9999"

        monkeypatch.setattr(_rapid_sweep, "_file_regression_ticket", _fake_file)
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_ok
        assert result.danger_ok == "T-9999"
        assert seen == [frozenset({("DOC011", "b.md")})]
        # Rebaselined even though the sweep was red: an already-filed
        # error must not be re-filed by the next land.
        assert _read_baseline(tmp_path) == fresh


class TestDeferredSweepSpawn:
    """The spawn records debt BEFORE spawning and never blocks."""

    def test_exec_disabled_records_debt_and_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepSpawn.test_exec_disabled_records_debt_and_refuses  # noqa: E501
        debts: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt",
            lambda root, tid, what: debts.append((tid, what)),
        )
        monkeypatch.setattr("frob.process.exec_enabled", lambda: False)
        result = spawn_deferred_post_land_sweep(tmp_path, "T-0001", "T-0001", "abc123")
        assert result.is_err
        assert result.danger_err is RapidSweepError.SpawnRefused
        assert debts == [("T-0001", "post-land-unscoped-sweep-deferred")]

    # frob:ticket T-2030
    def test_spawn_pins_frob_root_env_not_bare_os_environ(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2030's own repro: watch this FAIL first against the unfixed
        code -- `Popen` used to be called with no `env=` kwarg at all
        (bare inherited `os.environ`), so an ambient stale `FROB_ROOT` in
        the landing process's own shell silently overrode the correctly
        resolved `cwd=root` in the detached child's OWN root resolution.
        This asserts the actual `Popen` call always pins `FROB_ROOT` to
        `root`, regardless of what `os.environ` already contains."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepSpawn.test_spawn_pins_frob_root_env_not_bare_os_environ  # noqa: E501
        import subprocess as subprocess_mod

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod

        monkeypatch.setattr("frob.process.exec_enabled", lambda: True)
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt", lambda root, tid, what: None
        )
        monkeypatch.setattr(rapid_sweep_mod, "_commit_rapid_debt", lambda root, tid: None)
        # A STALE FROB_ROOT in the ambient environment, naming a
        # DIFFERENT tree than `root` -- exactly T-2030's measured shape.
        monkeypatch.setenv("FROB_ROOT", "/some/other/worktree")
        monkeypatch.setenv("FROB_WORKTREE", "/some/other/worktree")
        monkeypatch.setenv("FROB_AGENT", "1")

        captured: dict = {}

        class _FakeProc:
            pid = 4242

        def _fake_popen(argv, **kwargs):
            captured.update(kwargs)
            return _FakeProc()

        monkeypatch.setattr(subprocess_mod, "Popen", _fake_popen)

        result = spawn_deferred_post_land_sweep(tmp_path, "T-0001", "T-0001", "abc123")
        assert result.is_ok

        env = captured.get("env")
        assert env is not None, "Popen must be called with an explicit env= kwarg"
        assert env["FROB_ROOT"] == str(tmp_path)
        assert "FROB_WORKTREE" not in env
        assert "FROB_AGENT" not in env


# frob:ticket T-2030
class TestDetachedSweepEnv:
    """T-2030: `_detached_sweep_env`'s own unit-level contract."""

    def test_pins_frob_root_to_the_correct_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDetachedSweepEnv.test_pins_frob_root_to_the_correct_root  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _detached_sweep_env

        monkeypatch.setenv("FROB_ROOT", "/stale/other/worktree")
        env = _detached_sweep_env(tmp_path)
        assert env["FROB_ROOT"] == str(tmp_path)

    def test_strips_worktree_lease_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDetachedSweepEnv.test_strips_worktree_lease_env  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _detached_sweep_env

        monkeypatch.setenv("FROB_WORKTREE", "/some/worktree")
        monkeypatch.setenv("FROB_AGENT", "1")
        env = _detached_sweep_env(tmp_path)
        assert "FROB_WORKTREE" not in env
        assert "FROB_AGENT" not in env


def _git(repo: Path, *args: str) -> str:
    """Run git in `repo` and return stdout (test helper, T-1698)."""
    import subprocess

    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


# frob:waive WIRE001 reason="a module-local test helper called only by this file's own \
# tests -- no production caller to wire it to by design" permanent="true"
def _seed_repo(tmp_path: Path) -> Path:
    """A real one-commit git repo -- `_commit_rapid_debt`'s whole contract
    is about git state, so a fake would prove nothing. A plain helper
    called explicitly, not a pytest fixture: fixture wiring is by NAME
    INJECTION, which WIRE001's reachability scan cannot see. Only called
    from within this same file (T-1558's gate fix recognizes cross-test-
    file calls as wired now, but same-file usage stays genuinely unwired
    by design, matching T-1592's precedent) -- `permanent="true"`, not a
    follow_up, since there is no accountable future work left to bind."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "test")
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(tmp_path, "add", "seed.txt")
    _git(tmp_path, "commit", "-qm", "seed")
    return tmp_path


class TestCommitRapidDebt:
    """T-1698: a rapid land must leave the ROOT CHECKOUT CLEAN. One
    uncommitted debt line deadlocked a whole three-agent wave, because
    every later land refused with DirtyMain."""

    def test_leaves_the_repo_clean(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_leaves_the_repo_clean
        from frob.tickets._evidence import record_rapid_debt

        repo = _seed_repo(tmp_path)

        record_rapid_debt(repo, "T-0001", "post-land-unscoped-sweep-deferred")
        assert _git(repo, "status", "--porcelain").strip() != ""
        _rapid_sweep._commit_rapid_debt(repo, "T-0001")
        # The actual invariant, not "a commit helper was called".
        assert _git(repo, "status", "--porcelain").strip() == ""
        assert "rapid-debt.jsonl" in _git(repo, "ls-files")

    def test_stages_only_the_debt_file(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_stages_only_the_debt_file  # noqa: E501
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
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_is_a_noop_when_nothing_was_appended  # noqa: E501
        repo = _seed_repo(tmp_path)
        head_before = _git(repo, "rev-parse", "HEAD").strip()
        _rapid_sweep._commit_rapid_debt(repo, "T-0003")
        assert _git(repo, "rev-parse", "HEAD").strip() == head_before

    def test_a_non_repo_never_raises(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_a_non_repo_never_raises  # noqa: E501
        # Best-effort: it must never fail a land that already succeeded.
        _rapid_sweep._commit_rapid_debt(tmp_path, "T-0004")


class TestDescribeRootDirt:
    """T-1698: a DirtyMain refusal must name what made it refuse."""

    def test_names_the_paths(self) -> None:
        # frob:tests \
        # tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_names_the_paths
        from frob.tickets._land_git_ops import _render_dirty_paths

        assert _render_dirty_paths(("a.py", "b.md")) == "a.py, b.md"

    def test_truncation_declares_itself(self) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_truncation_declares_itself  # noqa: E501
        from frob.tickets._land_git_ops import _render_dirty_paths

        rendered = _render_dirty_paths(tuple(f"f{i}.py" for i in range(14)))
        assert rendered.endswith("(+4 more)")

    def test_unavailable_status_is_not_reported_as_clean(self) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_unavailable_status_is_not_reported_as_clean  # noqa: E501
        from frob.tickets._land_git_ops import _render_dirty_paths

        # "cannot tell" must never render as "clean".
        assert _render_dirty_paths(()) == "(git status unavailable)"

    def test_names_a_real_dirty_file(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_names_a_real_dirty_file  # noqa: E501
        from frob.tickets._land_git_ops import describe_root_dirt

        repo = _seed_repo(tmp_path)
        (repo / "seed.txt").write_text("changed\n", encoding="utf-8")
        assert "seed.txt" in describe_root_dirt(repo)

    def test_names_the_detached_sweep_as_likely_author(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_names_the_detached_sweep_as_likely_author  # noqa: E501
        from frob.tickets._land_git_ops import describe_root_dirt

        repo = _seed_repo(tmp_path)
        (repo / "tickets.md").write_text("dirty\n", encoding="utf-8")
        _git(repo, "add", "tickets.md")
        rendered = describe_root_dirt(repo)
        assert "tickets.md" in rendered
        assert "detached post-land sweep" in rendered

    def test_mixed_dirt_does_not_claim_the_sweep(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_mixed_dirt_does_not_claim_the_sweep  # noqa: E501
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
        # frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_names_the_real_ticket_from_a_staged_rapid_debt_line  # noqa: E501
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
        # frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_unattributed_when_the_true_author_cannot_be_determined  # noqa: E501
        from frob.tickets._land_git_ops import describe_root_dirt

        repo = _seed_repo(tmp_path)
        (repo / "tickets.md").write_text("dirty\n", encoding="utf-8")
        _git(repo, "add", "tickets.md")
        rendered = describe_root_dirt(repo)
        assert "unattributed" in rendered


class TestCommitRegressionTicket:
    """T-1755: the filed regression ticket's `tickets.md` write must be
    committed by the sweep itself, scoped to the ledger paths only."""

    def test_commits_the_ledger_write(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_commits_the_ledger_write  # noqa: E501
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
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_commit_failure_logs_at_error_and_does_not_raise  # noqa: E501
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
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_retries_then_succeeds_on_a_transient_land_in_progress  # noqa: E501
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
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_exhausted_retries_discard_the_v2_ticket_dir_rather_than_leave_it_dirty  # noqa: E501
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
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_exhausted_retries_leave_a_v1_store_dirty_rather_than_guess  # noqa: E501
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
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitOrDiscardLedgerWrite.test_returns_true_on_first_success  # noqa: E501
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
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitOrDiscardLedgerWrite.test_retries_then_succeeds  # noqa: E501
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
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitOrDiscardLedgerWrite.test_exhausted_retries_calls_discard_exactly_once_and_returns_false  # noqa: E501
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
        # frob:tests tests/unit/test_rapid_sweep.py::TestDiscardUncommittedTicketDrop.test_v2_store_restores_the_ticket_file_to_head  # noqa: E501
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
        # frob:tests tests/unit/test_rapid_sweep.py::TestDiscardUncommittedTicketDrop.test_v1_store_logs_and_leaves_root_alone  # noqa: E501
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


def _seed_ticket(tmp_path: Path, *, state=None) -> str:
    """A minimal ticket for T-1690's attribution-filing tests. `state`
    (a `TicketState`), when given, transitions the ticket there -- `DONE`
    is reached the cheap way (via `drop_ticket`, landing on `DROPPED`,
    which is in `_ticket_is_open`'s CLOSED set alongside `DONE`) rather
    than satisfying `done`'s own evidence/Done-report requirements, which
    this test has no need to exercise."""
    from frob.tickets import Origin, TicketKind, new_ticket
    from frob.tickets._models import TicketSpec, TicketState

    spec = TicketSpec(title="seed", kind=TicketKind.BUG, origin=Origin.AGENT)
    created = new_ticket(tmp_path, spec)
    assert created.is_ok
    ticket_id = created.danger_ok.id
    if state is TicketState.DONE:
        from frob.tickets import drop_ticket

        dropped = drop_ticket(tmp_path, ticket_id, reason="seed")
        assert dropped.is_ok
    return ticket_id


class TestTicketIsOpen:
    """`_ticket_is_open` is the "still open" half of T-1690's filing rule."""

    def test_open_ticket_is_open(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_rapid_sweep.py::TestTicketIsOpen.test_open_ticket_is_open
        ticket_id = _seed_ticket(tmp_path)
        assert _ticket_is_open(tmp_path, ticket_id) is True

    def test_done_ticket_is_not_open(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_rapid_sweep.py::TestTicketIsOpen.test_done_ticket_is_not_open
        from frob.tickets._models import TicketState

        ticket_id = _seed_ticket(tmp_path, state=TicketState.DONE)
        assert _ticket_is_open(tmp_path, ticket_id) is False

    def test_missing_ticket_is_not_open(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestTicketIsOpen.test_missing_ticket_is_not_open  # noqa: E501
        assert _ticket_is_open(tmp_path, "T-9999") is False


class TestAttributeNewFindings:
    """`_attribute_new_findings` degrades to `{}` (no attribution info,
    never a false 'everything unattributed') whenever the queue or the
    graph is unavailable."""

    def test_empty_queue_returns_empty_mapping(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestAttributeNewFindings.test_empty_queue_returns_empty_mapping  # noqa: E501
        assert _attribute_new_findings(tmp_path, [("RULE1", "a.py")]) == {}

    def test_attributed_and_unattributed_round_trip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestAttributeNewFindings.test_attributed_and_unattributed_round_trip  # noqa: E501
        import frob.verify._attribution as attribution_mod
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.verify import record_intent

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        call_graph = CallGraph(calls={})
        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, call_graph),
        )
        result = _attribute_new_findings(
            tmp_path, [("RULE1", "a.py", 2), ("RULE2", "nowhere.py", 9)]
        )
        assert result[("RULE1", "a.py")].status == "attributed"
        assert result[("RULE1", "a.py")].commit_sha == "commitA"
        assert result[("RULE2", "nowhere.py")].status == "unattributed"


# frob:ticket T-1935
class TestTrueFindingCount:
    """`_true_finding_count_for_identities` re-measures the TRUE
    per-finding count for a set of `(rule, file)` identities -- proving
    the T-1923 undercount (6 identities reported, 19 real findings) is
    now recoverable rather than silently lost."""

    # frob:ticket T-1935
    @staticmethod
    def _ok_result(stdout: str):
        from typani import Ok

        class _Proc:
            def __init__(self, stdout: str) -> None:
                self.stdout = stdout
                self.returncode = 1

        return Ok(_Proc(stdout))

    # frob:ticket T-1935
    def test_counts_every_diagnostic_matching_an_identity(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestTrueFindingCount.test_counts_every_diagnostic_matching_an_identity  # noqa: E501
        # T-1923's real shape: 5 files each carrying MULTIPLE COV003
        # findings (18 total) plus one F401 -- a coarse (rule, file)
        # identity set has only 6 entries, but the true finding count is
        # 19. This reproduces that undercount and proves the fix
        # recovers the real number.
        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {
                            "code": "COV003",
                            "file": "tickets/T-1872",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1872",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1895",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1895",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1895",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1895",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1896",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1896",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1900",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1900",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1900",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1900",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1900",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1906",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1906",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1906",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1906",
                            "severity": "error",
                        },
                        {
                            "code": "COV003",
                            "file": "tickets/T-1906",
                            "severity": "error",
                        },
                        {"code": "F401", "file": "src/frob/x.py", "severity": "error"},
                        # A finding NOT in `pairs` below must not be counted.
                        {"code": "SCOPE001", "file": "other.py", "severity": "error"},
                    ],
                }
            ]
        }
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result(json.dumps(payload)),
        )
        pairs = frozenset(
            {
                ("COV003", "tickets/T-1872"),
                ("COV003", "tickets/T-1895"),
                ("COV003", "tickets/T-1896"),
                ("COV003", "tickets/T-1900"),
                ("COV003", "tickets/T-1906"),
                ("F401", "src/frob/x.py"),
            }
        )
        assert len(pairs) == 6
        count = _true_finding_count_for_identities(tmp_path, pairs)
        assert count == 19

    # frob:ticket T-1935
    def test_unparsable_json_is_none_not_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestTrueFindingCount.test_unparsable_json_is_none_not_zero  # noqa: E501
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result("not json at all"),
        )
        assert (
            _true_finding_count_for_identities(tmp_path, frozenset({("R", "f.py")}))
            is None
        )

    # frob:ticket T-1935
    def test_spawn_refused_is_none_not_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestTrueFindingCount.test_spawn_refused_is_none_not_zero  # noqa: E501
        from typani import Err

        from frob.process._guard import ProcessGuardError

        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: Err(ProcessGuardError.ExecDisabled),
        )
        assert (
            _true_finding_count_for_identities(tmp_path, frozenset({("R", "f.py")}))
            is None
        )


# frob:ticket T-2006
class TestIdentitiesStillReproducing:
    """T-2006: `_identities_still_reproducing` -- which of a candidate
    set STILL reproduce right now, as an identity set (not merely a
    count) -- what `revalidate_dispatchable_sweep_tickets` needs to
    decide which sweep-filed tickets to drop."""

    # frob:ticket T-2006
    @staticmethod
    def _ok_result(stdout: str):
        from typani import Ok

        class _Proc:
            def __init__(self, stdout: str) -> None:
                self.stdout = stdout
                self.returncode = 1

        return Ok(_Proc(stdout))

    # frob:ticket T-2006
    def test_only_reproducing_identities_returned(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestIdentitiesStillReproducing.test_only_reproducing_identities_returned  # noqa: E501
        import json

        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {"code": "COV003", "file": "a.py", "severity": "error"},
                        # DOC002/b.py is in the queried `pairs` below but
                        # NOT in this fresh measurement -- it has
                        # resolved and must not appear in the result.
                        {"code": "F401", "file": "unrelated.py", "severity": "error"},
                    ],
                }
            ]
        }
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result(json.dumps(payload)),
        )
        result = _identities_still_reproducing(
            tmp_path, frozenset({("COV003", "a.py"), ("DOC002", "b.py")})
        )
        assert result == frozenset({("COV003", "a.py")})

    # frob:ticket T-2006
    def test_unmeasurable_is_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestIdentitiesStillReproducing.test_unmeasurable_is_none  # noqa: E501
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result("not json at all"),
        )
        assert (
            _identities_still_reproducing(tmp_path, frozenset({("R", "f.py")})) is None
        )


# frob:ticket T-2006
class TestRevalidateDispatchableSweepTickets:
    """T-2006, end-to-end: `frob ticket doable`'s residual gap after
    T-1983 -- a sweep-filed ticket must be re-verified at DISPATCH time,
    not only inside the next unrelated land's own sweep."""

    # frob:ticket T-2006
    def test_no_sweep_tickets_is_zero_cost(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets.test_no_sweep_tickets_is_zero_cost  # noqa: E501
        called = []
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: called.append(1),
        )

        class _PlainTicket:
            title = "some ordinary ticket"
            body = "nothing sweep-shaped here"

        dropped = _rapid_sweep.revalidate_dispatchable_sweep_tickets(
            tmp_path, [_PlainTicket()]
        )
        assert dropped == ()
        assert called == []  # no check spawn was attempted at all

    # frob:ticket T-2006
    def test_fully_resolved_candidate_is_dropped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets.test_fully_resolved_candidate_is_dropped  # noqa: E501
        from frob.tickets import TicketState, load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(
                f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n"
                "- COV003  a.py\n"
            ),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        # Fresh measurement: COV003/a.py no longer appears at all.
        import json

        payload = {"results": [{"tool": "gate-summary", "diagnostics": []}]}
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: TestIdentitiesStillReproducing._ok_result(
                json.dumps(payload)
            ),
        )

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())
        dropped = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert dropped == (ticket_id,)

        requeried = load_queue(tmp_path)
        assert requeried.is_ok
        assert requeried.danger_ok.tickets[ticket_id].state == TicketState.DROPPED

    # frob:ticket T-2006
    def test_still_reproducing_candidate_is_left_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets.test_still_reproducing_candidate_is_left_untouched  # noqa: E501
        from frob.tickets import TicketState, load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(
                f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n"
                "- COV003  a.py\n"
            ),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        # Fresh measurement: COV003/a.py STILL reproduces.
        import json

        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {"code": "COV003", "file": "a.py", "severity": "error"}
                    ],
                }
            ]
        }
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: TestIdentitiesStillReproducing._ok_result(
                json.dumps(payload)
            ),
        )

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())
        dropped = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert dropped == ()

        requeried = load_queue(tmp_path)
        assert requeried.is_ok
        assert requeried.danger_ok.tickets[ticket_id].state == TicketState.QUEUED

    # frob:ticket T-2006
    def test_unmeasurable_recheck_drops_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets.test_unmeasurable_recheck_drops_nothing  # noqa: E501
        from frob.tickets import TicketState, load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        spec = TicketSpec(
            title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
            "(rule, file) identit(ies) (COV003)",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("a.py",),
            body=(
                f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n"
                "- COV003  a.py\n"
            ),
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: TestIdentitiesStillReproducing._ok_result(
                "not json at all"
            ),
        )

        queue = load_queue(tmp_path)
        assert queue.is_ok
        tickets = list(queue.danger_ok.tickets.values())
        dropped = _rapid_sweep.revalidate_dispatchable_sweep_tickets(tmp_path, tickets)
        assert dropped == ()

        requeried = load_queue(tmp_path)
        assert requeried.is_ok
        assert requeried.danger_ok.tickets[ticket_id].state == TicketState.QUEUED


# frob:ticket T-1791
class TestFileRegressionTicket:
    """T-1690: attributed findings owned by a still-open ticket are not
    re-filed; everything else is filed with a full attribution trail."""

    def _patch_graph(
        self, monkeypatch: pytest.MonkeyPatch, snapshot, call_graph
    ) -> None:
        import frob.verify._attribution as attribution_mod

        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, call_graph),
        )

    # frob:ticket T-1791
    def test_no_attribution_files_everything_as_before(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_no_attribution_files_everything_as_before  # noqa: E501
        # No verify queue at all -- attribution unavailable, falls back to
        # the pre-T-1690 behavior of filing every pair.
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

    def test_attributed_to_open_ticket_is_not_refiled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_attributed_to_open_ticket_is_not_refiled  # noqa: E501
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.verify import record_intent

        owner = _seed_ticket(tmp_path)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is None

    def test_attributed_to_closed_ticket_is_refiled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_attributed_to_closed_ticket_is_refiled  # noqa: E501
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.tickets._models import TicketState
        from frob.verify import record_intent

        owner = _seed_ticket(tmp_path, state=TicketState.DONE)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

    def test_unattributed_is_filed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_unattributed_is_filed  # noqa: E501
        from frob.graph import CallGraph, GraphSnapshot
        from frob.verify import record_intent

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("unrelated.py::other",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

    def test_all_attributed_to_open_tickets_files_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_all_attributed_to_open_tickets_files_nothing  # noqa: E501
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.verify import record_intent

        owner = _seed_ticket(tmp_path)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn", "b.py::fn2"),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                ),
                "b.py::fn2": SymbolRecord(
                    id=SymbolId(path="b.py", qualname="fn2"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                ),
            },
            edges=(),
        )
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("RULE1", "a.py"), ("RULE2", "b.py")}),
        )
        assert filed is None


# frob:ticket T-1791
# frob:ticket T-1847
class TestRaiseQuarantineForRedBatch:
    """T-1791: wiring `raise_quarantine` into the shared "a red batch
    verification came back" seam both drivers (`_file_regression_ticket`)
    call through."""

    # frob:ticket T-1791
    def test_raises_with_attributed_and_unattributed_findings(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_raises_with_attributed_and_unattributed_findings  # noqa: E501
        from frob.verify import record_intent
        from frob.verify._quarantine import is_quarantined, load_quarantine

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        # No graph patched -- attribution degrades to "unavailable",
        # exactly the pre-T-1690 fallback `_file_regression_ticket`'s own
        # docstring already documents; every pair is filed, and every
        # QuarantinedFinding here carries no commit_sha/ticket_id.
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("RULE1", "a.py"), ("RULE2", "b.py")}),
        )
        assert filed is not None

        assert is_quarantined(tmp_path).danger_ok is True
        record = load_quarantine(tmp_path)
        assert record.is_ok
        assert record.danger_ok is not None
        assert record.danger_ok.batch_commit_shas == ("commitA",)
        assert {(f.rule_id, f.file) for f in record.danger_ok.findings} == {
            ("RULE1", "a.py"),
            ("RULE2", "b.py"),
        }

    # frob:ticket T-1791
    def test_empty_queue_logs_and_skips_the_raise(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_empty_queue_logs_and_skips_the_raise  # noqa: E501
        from frob.verify._quarantine import is_quarantined

        # No verify queue at all -- nothing to name as the raising batch.
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-1791
    def test_raised_even_when_every_pair_already_has_an_open_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_raised_even_when_every_pair_already_has_an_open_ticket  # noqa: E501
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.verify import record_intent
        from frob.verify._quarantine import is_quarantined

        owner = _seed_ticket(tmp_path)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        import frob.verify._attribution as attribution_mod

        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, CallGraph(calls={})),
        )
        # Every pair attributes to an already-open ticket -- no NEW
        # regression ticket is filed, but the batch was still red, so
        # quarantine must still be raised.
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is None
        assert is_quarantined(tmp_path).danger_ok is True

    # frob:ticket T-1791
    def test_raise_failure_is_logged_not_raised(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_raise_failure_is_logged_not_raised  # noqa: E501
        from typani.result import Err

        from frob.verify import _quarantine as quarantine_mod
        from frob.verify import record_intent
        from frob.verify._quarantine import QuarantineError

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        monkeypatch.setattr(
            quarantine_mod,
            "raise_quarantine",
            lambda root, **kw: Err(QuarantineError.StoreCorrupt),
        )
        # Must not raise or otherwise fail the caller -- the regression
        # ticket filing is the durable record; a quarantine write failure
        # is logged and swallowed.
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

    # frob:ticket T-1847
    def test_warm_tree_recheck_drops_cold_worktree_native_noise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_warm_tree_recheck_drops_cold_worktree_native_noise  # noqa: E501
        from frob.strata import _native_staleness
        from frob.verify import record_intent
        from frob.verify._quarantine import is_quarantined

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        # Every declared native imports cleanly RIGHT NOW -- the sole
        # finding is UNATTRIBUTED + "unresolved-import", the exact
        # cold-worktree-noise shape, so the warm re-check must clear it
        # and the raise must be skipped entirely.
        monkeypatch.setattr(_native_staleness, "unimportable_natives", lambda root: ())
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("unresolved-import", "a.py")}),
        )
        assert filed is not None  # still filed as a regression ticket
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-1847
    def test_warm_tree_recheck_keeps_finding_when_native_still_broken(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_warm_tree_recheck_keeps_finding_when_native_still_broken  # noqa: E501
        from frob.strata import _native_staleness
        from frob.testing._models import NativeSpec
        from frob.verify import record_intent
        from frob.verify._quarantine import is_quarantined, load_quarantine

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        broken = (NativeSpec(name="strata_core", build_cmd="true"),)
        monkeypatch.setattr(
            _native_staleness, "unimportable_natives", lambda root: broken
        )
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("unresolved-import", "a.py")}),
        )
        assert filed is not None
        assert is_quarantined(tmp_path).danger_ok is True
        record = load_quarantine(tmp_path)
        assert record.danger_ok is not None
        assert {(f.rule_id, f.file) for f in record.danger_ok.findings} == {
            ("unresolved-import", "a.py"),
        }

    # frob:ticket T-1847
    def test_warm_tree_recheck_never_drops_an_attributed_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_warm_tree_recheck_never_drops_an_attributed_finding  # noqa: E501
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.strata import _native_staleness
        from frob.verify import record_intent
        from frob.verify._quarantine import is_quarantined, load_quarantine

        owner = _seed_ticket(tmp_path)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        import frob.verify._attribution as attribution_mod

        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, CallGraph(calls={})),
        )
        # unimportable_natives says everything is warm -- if the finding
        # were unattributed this would clear it, but this pair reaches
        # a.py::fn and must attribute to a STILL-OPEN ticket (owner), a
        # wholly different case than "unattributed". The finding must NOT
        # be treated as cold-worktree noise just because the rule id
        # matches.
        monkeypatch.setattr(_native_staleness, "unimportable_natives", lambda root: ())
        filed = _file_regression_ticket(
            tmp_path,
            owner,
            "deadbeef",
            frozenset({("unresolved-import", "a.py")}),
        )
        assert filed is None  # already attributed to an open ticket
        assert is_quarantined(tmp_path).danger_ok is True
        record = load_quarantine(tmp_path)
        assert record.danger_ok is not None
        assert {(f.rule_id, f.file) for f in record.danger_ok.findings} == {
            ("unresolved-import", "a.py"),
        }


# frob:ticket T-1983
class TestCloseResolvedSweepTickets:
    """T-1983: a sweep-filed regression ticket whose findings stop
    reproducing must be auto-DROPPED (not closed, not left forever) the
    next time the sweep can prove it, reusing the rolling-baseline diff
    the sweep already computes for the opposite direction."""

    def test_non_sweep_ticket_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_non_sweep_ticket_returns_none  # noqa: E501
        ticket_id = _seed_ticket(tmp_path)
        from frob.tickets import load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        ticket = queue.danger_ok.tickets[ticket_id]
        assert _parse_sweep_ticket_identities(ticket) is None

    def test_parses_a_sweep_titled_ticket_identity_set(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_parses_a_sweep_titled_ticket_identity_set  # noqa: E501
        findings = frozenset({("RULE1", "a.py"), ("RULE2", "b.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None
        from frob.tickets import load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        ticket = queue.danger_ok.tickets[filed]
        assert _parse_sweep_ticket_identities(ticket) == findings

    def test_drops_a_fully_resolved_sweep_ticket(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_drops_a_fully_resolved_sweep_ticket  # noqa: E501
        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None

        dropped = _close_resolved_sweep_tickets(tmp_path, "T-9001", findings)
        assert dropped == (filed,)

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.DROPPED

    def test_leaves_a_partially_resolved_ticket_untouched(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_leaves_a_partially_resolved_ticket_untouched  # noqa: E501
        findings = frozenset({("RULE1", "a.py"), ("RULE2", "b.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None

        # Only RULE1/a.py vanished -- RULE2/b.py still reproduces, so the
        # ticket as a whole must not be dropped.
        dropped = _close_resolved_sweep_tickets(
            tmp_path, "T-9001", frozenset({("RULE1", "a.py")})
        )
        assert dropped == ()

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.QUEUED

    def test_leaves_a_still_reproducing_ticket_untouched(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_leaves_a_still_reproducing_ticket_untouched  # noqa: E501
        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None

        dropped = _close_resolved_sweep_tickets(tmp_path, "T-9001", frozenset())
        assert dropped == ()

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.QUEUED

    def test_in_progress_sweep_ticket_is_never_touched(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_in_progress_sweep_ticket_is_never_touched  # noqa: E501
        from frob.tickets import TicketState, transition

        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None
        planned = transition(tmp_path, filed, TicketState.PLANNED)
        assert planned.is_ok
        started = transition(tmp_path, filed, TicketState.IN_PROGRESS)
        assert started.is_ok

        dropped = _close_resolved_sweep_tickets(tmp_path, "T-9001", findings)
        assert dropped == ()

    # frob:ticket T-2030
    def test_a_done_ticket_body_is_byte_for_byte_untouched(
        self, tmp_path: Path
    ) -> None:
        """T-2030: a `done` ticket's own Done report was found silently
        REPLACED in an incident this ticket investigates -- verify the
        QUEUED/PLANNED state filter (`_close_resolved_sweep_tickets`'s
        own scan, `ticket.state not in (QUEUED, PLANNED)`) genuinely
        protects a terminal ticket's file content, byte for byte, rather
        than trusting the guard exists by reading it."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_a_done_ticket_body_is_byte_for_byte_untouched  # noqa: E501
        from frob.tickets import TicketState, drop_ticket, transition

        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", findings)
        assert filed is not None
        planned = transition(tmp_path, filed, TicketState.PLANNED)
        assert planned.is_ok
        started = transition(tmp_path, filed, TicketState.IN_PROGRESS)
        assert started.is_ok
        # DROPPED is the cheap way to reach a terminal state here (same
        # trick `_seed_ticket`'s own docstring above uses) -- terminal is
        # the property under test, not which terminal state.
        dropped_result = drop_ticket(tmp_path, filed, "done for this test")
        assert dropped_result.is_ok

        ticket_path = tmp_path / "tickets" / filed / "ticket.md"
        before = ticket_path.read_bytes()

        result = _close_resolved_sweep_tickets(tmp_path, "T-9001", findings)
        assert result == ()

        after = ticket_path.read_bytes()
        assert after == before

    # frob:ticket T-2034
    def test_commit_failure_restores_root_to_clean_not_left_dirty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2034's own repro: `_maybe_drop_resolved_ticket`'s
        `drop_ticket()` write must never survive an exhausted commit retry
        uncommitted in `root` -- that is exactly the DirtyMain-blocking
        defect this ticket exists to close. Before the fix this asserted
        root DIRTY; after the fix root must be CLEAN and the ticket
        restored to QUEUED (droppable again on the next sweep, not
        silently lost)."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_commit_failure_restores_root_to_clean_not_left_dirty  # noqa: E501
        from typani.result import Err

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        repo = _seed_repo(tmp_path)
        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(repo, "T-9000", "deadbeef", findings)
        assert filed is not None
        assert not _git(repo, "status", "--porcelain", "--", "tickets").strip()

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Err(LeaseError.LandInProgress),
        )
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)

        dropped = rapid_sweep_mod._close_resolved_sweep_tickets(
            repo, "T-9001", findings
        )
        assert dropped == ()  # commit failed -- not reported as dropped

        # THE FIX: root must be clean, never left with an uncommitted
        # drop write DirtyMain-blocking every concurrent land.
        assert not _git(repo, "status", "--porcelain", "--", "tickets").strip()

        from frob.tickets import TicketState, load_queue

        queue = load_queue(repo)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.QUEUED

    # frob:ticket T-2034
    def test_retry_after_commit_failure_does_not_duplicate_the_reason(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2034: T-2000/T-2008/T-2022 each carried the SAME
        auto-drop reason line TWICE because the never-discarded write let
        the NEXT sweep pass see the ticket as still QUEUED and drop it
        again. Restoring on discard (this test's first sweep) must leave
        the ticket genuinely droppable, and the SECOND, successful sweep
        must append the reason exactly once."""
        # frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_retry_after_commit_failure_does_not_duplicate_the_reason  # noqa: E501
        from typani.result import Err

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.tickets._leases import LeaseError

        repo = _seed_repo(tmp_path)
        findings = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(repo, "T-9000", "deadbeef", findings)
        assert filed is not None

        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda root, ticket_id, message: Err(LeaseError.LandInProgress),
        )
        monkeypatch.setattr(rapid_sweep_mod.time, "sleep", lambda _s: None)
        monkeypatch.setattr(rapid_sweep_mod, "_TICKET_DROP_COMMIT_MAX_ATTEMPTS", 1)
        rapid_sweep_mod._close_resolved_sweep_tickets(repo, "T-9001", findings)
        monkeypatch.undo()

        # Second sweep, this time the commit succeeds for real.
        dropped = rapid_sweep_mod._close_resolved_sweep_tickets(
            repo, "T-9002", findings
        )
        assert dropped == (filed,)

        from frob.tickets import load_queue

        queue = load_queue(repo)
        assert queue.is_ok
        reason_count = queue.danger_ok.tickets[filed].body.count("auto-dropped by")
        assert reason_count == 1


# frob:ticket T-2038
class TestNormalizeIdentityFile:
    """T-2038 (DRIFT002 fix): `_normalize_identity_file`'s own `frob:tests`
    directives were added ahead of these tests -- filling the gap."""

    def test_absolute_under_root_becomes_relative(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestNormalizeIdentityFile.test_absolute_under_root_becomes_relative  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _normalize_identity_file

        file = str(tmp_path / "a" / "b.py")
        assert _normalize_identity_file(tmp_path, file) == "a/b.py"

    def test_already_relative_is_unchanged(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestNormalizeIdentityFile.test_already_relative_is_unchanged  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _normalize_identity_file

        assert _normalize_identity_file(tmp_path, "a/b.py") == "a/b.py"

    def test_absolute_outside_root_falls_back_unchanged(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestNormalizeIdentityFile.test_absolute_outside_root_falls_back_unchanged  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _normalize_identity_file

        other = tmp_path.parent / "elsewhere" / "c.py"
        assert _normalize_identity_file(tmp_path, str(other)) == other.as_posix()


# frob:ticket T-2036
class TestAbsoluteVsRelativePathIdentityMismatch:
    """T-2036's own repro: T-2022 was auto-dropped while its
    findings were still live because the identity it was FILED with
    (absolute path, from an earlier sweep's measurement) never matched a
    LATER sweep's fresh measurement of the SAME still-broken file
    reported in repo-relative form -- a plain string-tuple diff cannot
    see these as the same identity. Watch this fail first: before the
    fix, the still-broken ticket ends up DROPPED."""

    def test_format_drift_between_sweeps_does_not_falsely_resolve_a_live_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestAbsoluteVsRelativePathIdentityMismatch.test_format_drift_between_sweeps_does_not_falsely_resolve_a_live_ticket  # noqa: E501
        _write_baseline(tmp_path, frozenset(), "c0")
        abs_path = str(tmp_path / "a.py")

        # Land 1: the tool reports an ABSOLUTE path for the broken file.
        # A ticket gets filed naming that identity.
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("RULE1", abs_path)}),
        )
        first = run_deferred_post_land_sweep(tmp_path, "T-1001", "c1")
        assert first.is_ok
        filed = first.danger_ok
        assert filed is not None

        # Land 2: the SAME file, SAME rule, genuinely STILL broken -- but
        # this time the tool reports it REPO-RELATIVE (format drift
        # between runs, T-2022's measured shape). The ticket must NOT
        # read as resolved just because the raw strings differ.
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("RULE1", "a.py")}),
        )
        second = run_deferred_post_land_sweep(tmp_path, "T-1002", "c2")
        assert second.is_ok

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        # THE FIX: still QUEUED, never falsely auto-dropped.
        assert queue.danger_ok.tickets[filed].state == TicketState.QUEUED


# frob:ticket T-1983
class TestDeferredSweepClosesResolvedRegressions:
    """End-to-end: `run_deferred_post_land_sweep` itself closes the loop
    on a prior sweep ticket whose findings vanish, and leaves one whose
    findings still reproduce alone -- the acceptance shape T-1983 itself
    demands (first assert must FAIL before the fix)."""

    def test_resolved_finding_is_dropped_by_the_next_sweep(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepClosesResolvedRegressions.test_resolved_finding_is_dropped_by_the_next_sweep  # noqa: E501
        _write_baseline(tmp_path, frozenset(), "c0")

        # Land 1: RULE1/a.py appears -- files a real regression ticket.
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("RULE1", "a.py")}),
        )
        first = run_deferred_post_land_sweep(tmp_path, "T-1001", "c1")
        assert first.is_ok
        filed = first.danger_ok
        assert filed is not None

        # Land 2: RULE1/a.py is fixed -- the fresh measurement no longer
        # finds it, so the sweep must drop the ticket it filed for it.
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset(),
        )
        second = run_deferred_post_land_sweep(tmp_path, "T-1002", "c2")
        assert second.is_ok

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.DROPPED

    def test_still_reproducing_finding_is_left_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepClosesResolvedRegressions.test_still_reproducing_finding_is_left_untouched  # noqa: E501
        _write_baseline(tmp_path, frozenset(), "c0")

        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("RULE1", "a.py")}),
        )
        first = run_deferred_post_land_sweep(tmp_path, "T-1001", "c1")
        assert first.is_ok
        filed = first.danger_ok
        assert filed is not None

        # Land 2: RULE1/a.py is STILL present -- must not be dropped.
        second = run_deferred_post_land_sweep(tmp_path, "T-1002", "c2")
        assert second.is_ok

        from frob.tickets import TicketState, load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        assert queue.danger_ok.tickets[filed].state == TicketState.QUEUED


class TestDeferredSweepMultiLandAttribution:
    """T-2009, end-to-end: the T-1998 measured shape -- two real lands
    happen between the previous baseline and the tree THIS sweep
    actually measures (the sweep is detached, off the land critical
    path, so other agents' lands routinely land in the window before it
    runs). The regression must be attributed to BOTH lands, never
    silently pinned on whichever one happened to spawn this sweep
    process."""

    def test_two_lands_in_the_window_are_both_named_not_just_the_spawning_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepMultiLandAttribution.test_two_lands_in_the_window_are_both_named_not_just_the_spawning_one  # noqa: E501
        _init_git_repo(tmp_path)
        c0 = _git_commit(tmp_path, "chore: init")
        _write_baseline(tmp_path, frozenset(), c0)

        # Land T-1977 lands (this is the sweep that gets SPAWNED)...
        _git_commit(tmp_path, "fix(tickets): land T-1977 first fix")
        # ...but before its detached sweep child actually gets to run,
        # T-1995 ALSO lands (this is exactly the T-1998 incident: the
        # sweep is off the critical path on purpose, T-1684, so this is
        # normal, not a race bug). The real HEAD by the time the check
        # runs is past BOTH lands.
        real_head = _git_commit(tmp_path, "feat(tickets): land T-1995 second fix")

        # The new finding actually lives in a file T-1995 touched -- the
        # exact T-1998 shape (misattributed to T-1977, whose files were
        # never involved).
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: frozenset({("F401", "t1995_file.py")}),
        )
        # `_resolve_actual_head` reads the real git HEAD of tmp_path
        # (real_head) -- the sweep was merely SPAWNED naming T-1977 and
        # commit_sha=stale-spawn-sha (a stale value by the time it
        # actually runs).
        result = run_deferred_post_land_sweep(tmp_path, "T-1977", "stale-spawn-sha")
        assert result.is_ok
        filed = result.danger_ok
        assert filed is not None

        from frob.tickets import load_queue

        queue = load_queue(tmp_path)
        assert queue.is_ok
        ticket = queue.danger_ok.tickets[filed]
        title = ticket.title
        body = ticket.body
        # Before T-2009's fix: title/body named ONLY "T-1977" -- the land
        # that spawned the sweep, not the land whose files actually went
        # red. Both must be named now.
        assert "T-1977" in title
        assert "T-1995" in title
        assert "T-1995" in body
        # The baseline's own recorded commit must be the REAL head this
        # sweep measured, not the stale spawn-time commit_sha -- this is
        # what lets the NEXT sweep compute an honest window in turn.
        assert _read_baseline_commit(tmp_path) == real_head
