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
    _file_regression_ticket,
    _read_baseline,
    _ticket_is_open,
    _write_baseline,
    run_deferred_post_land_sweep,
    spawn_deferred_post_land_sweep,
)


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
