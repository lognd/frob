"""Unit tests for `frob.app.ticket_runner._rapid_sweep` (T-1684): the
rapid profile's deferred, non-blocking post-land unscoped sweep."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from frob.app.ticket_runner import _rapid_sweep
from frob.app.ticket_runner._rapid_sweep import (
    RapidSweepError,
    _read_baseline,
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
        # frob:tests tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_leaves_the_repo_clean  # noqa: E501
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
        # frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_names_the_paths  # noqa: E501
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
