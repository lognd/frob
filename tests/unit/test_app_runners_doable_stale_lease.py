"""T-1876: `frob ticket doable` must FLAG (never silently hide, never
auto-release) a lease whose holding worktree looks dead -- a lease
survives its agent's death with no liveness check today, and blocks every
ticket in its scope indefinitely (the measured 2026-08-08 incident: a
lease recorded hours after its worktree's own last commit kept blocking
five other tickets, with `doable` presenting it identically to live
work).

`_stale_lease_reasons` (`frob.app.ticket_runner._query`) is the
read-only surfacing half of the fix: it reuses `lease_staleness_reason`
(T-1806, already used by `frob worktree release-lease`) rather than
inventing a second liveness signal, and proves BOTH directions -- a dead
holder's lease is reported stale, and a live holder's lease is NOT (the
assertion that stops this from becoming a corruption bug: a
too-eager staleness check would let two worktrees mutate the same scope
at once, T-1868's failure mode)."""

# frob:ticket T-1876

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import run as ticket_run
from frob.app.ticket_runner._query import (
    _load_unlanded_summary_cache,
    _render_unlanded_branch_work_summary,
    _save_unlanded_summary_cache,
    _stale_lease_reasons,
)
from frob.tickets._leases import LEASE_TTL_SECONDS, _LeaseRecord, leases_dir


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A main checkout with a real git history and an initialized ledger,
    same shape as `tests/test_ticket_leases.py`'s own `repo` fixture."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# feature\n")
    ticket_run(
        AppConfig(
            ticket_command="new",
            ticket_path=main_repo,
            ticket_title="feature ticket",
            ticket_kind="docs",
            ticket_scope=["src/feature.py"],
            ticket_body="## Done report\n\nDone.\n",
        )
    )
    _commit_all(main_repo, "init: ticket + ledger committed")
    return main_repo


@pytest.fixture
def second_worktree(repo: Path) -> Path:
    """A second linked `git worktree` of `repo`, branched from the SAME
    commit `repo` is on -- the real double-dispatch shape."""
    wt = repo.parent / "wt"
    _run(["git", "worktree", "add", "-b", "feature-wt", str(wt)], repo)
    return wt


def _write_lease(
    root: Path, ticket_id: str, worktree: Path, *, recorded_at: str
) -> None:
    resolved = leases_dir(root)
    assert resolved.is_ok
    leases_root = resolved.danger_ok
    leases_root.mkdir(parents=True, exist_ok=True)
    record = _LeaseRecord(
        ticket_id=ticket_id,
        scope=("src/feature.py",),
        worktree=str(worktree),
        branch="feature-wt",
        recorded_at=recorded_at,
    )
    (leases_root / f"{ticket_id}.json").write_text(
        record.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )


class TestStaleLeaseReasons:
    def test_dead_holder_flagged_with_reason(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons.test\
        # _dead_holder_flagged_with_reason
        # T-0001 is a real ticket in `repo`'s own ledger (per the `repo`
        # fixture) -- the holder-dead check requires the ticket id to
        # still exist in the ledger, only its lease's `recorded_at` to be
        # long past `LEASE_TTL_SECONDS` and its worktree to hold no live
        # process, matching the real dead-agent shape T-1876 measured.
        stale_time = (
            datetime.now(UTC) - timedelta(seconds=LEASE_TTL_SECONDS + 60)
        ).isoformat()
        _write_lease(repo, "T-0001", second_worktree, recorded_at=stale_time)

        reasons = _stale_lease_reasons(repo)

        assert reasons == {"T-0001": "holder-dead"}

    def test_live_holder_not_flagged(self, repo: Path, second_worktree: Path) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons.test\
        # _live_holder_not_flagged
        # A lease recorded just now, for a worktree that genuinely exists
        # and a ticket genuinely in the ledger, must NOT be reported --
        # this is the assertion that stops the staleness surfacing from
        # becoming a corruption bug (a too-eager flag inviting a
        # premature reclaim of a merely-slow agent's lease, T-1868's
        # failure mode).
        _write_lease(
            repo,
            "T-0001",
            second_worktree,
            recorded_at=datetime.now(UTC).isoformat(),
        )

        reasons = _stale_lease_reasons(repo)

        assert reasons == {}

    def test_no_root_returns_empty(self) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons.test\
        # _no_root_returns_empty
        assert _stale_lease_reasons(None) == {}


# frob:ticket T-1934
# frob:ticket T-2127
class TestRenderUnlandedBranchWorkSummary:
    """T-1934 REQUIRED-C: `frob ticket doable` surfaces "N branch(es)
    carry unlanded ticket work" alongside T-1876's own stale-lease
    warning, in the same place a coordinator already looks."""

    def test_no_root_is_a_noop(self, capsys) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWo\
        # rkSummary.test_no_root_is_a_noop
        _render_unlanded_branch_work_summary(None)
        assert capsys.readouterr().out == ""

    def test_no_unlanded_work_prints_nothing(self, repo: Path, caplog) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWo\
        # rkSummary.test_no_unlanded_work_prints_nothing
        # T-2629: a cache populated with zero branches renders silently,
        # same posture as before -- this is the "cache says nothing to
        # report" case, distinct from "no cache at all" below.
        _save_unlanded_summary_cache(repo, ())
        _render_unlanded_branch_work_summary(repo)
        assert "unlanded ticket work" not in caplog.text

    def test_unlanded_branch_is_summarized(self, repo: Path, caplog) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWo\
        # rkSummary.test_unlanded_branch_is_summarized
        # T-2629: render is now a pure cache reader -- populate the cache
        # directly rather than relying on render itself to scan (it no
        # longer does).
        import logging

        caplog.set_level(logging.INFO)
        _save_unlanded_summary_cache(repo, ("runner-wiring",))

        _render_unlanded_branch_work_summary(repo)

        assert "1 branch(es) carry unlanded ticket work" in caplog.text
        assert "runner-wiring" in caplog.text

    # frob:ticket T-2629
    def test_render_never_scans_branches_inline(
        self, repo: Path, caplog, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWo\
        # rkSummary.test_render_never_scans_branches_inline
        # T-2629: `frob ticket doable` did not complete -- a cache miss
        # fell through to a synchronous `_unlanded_branch_work` scan of
        # every branch in the repo (938 branches, 35 worktrees on the
        # real repo; a temp-file tree-sitter parse per directive
        # candidate), which does not finish inside any sane foreground
        # budget and took the primary queue command down with it. This
        # is the repro: before the fix, a cache miss triggers the scan
        # and this test fails on the planted `_boom`; after the fix, a
        # cache miss only discloses that the summary was not computed.
        import logging

        caplog.set_level(logging.INFO)

        def _boom(*_args, **_kwargs):  # noqa: ANN001, ANN401
            raise AssertionError(
                "a cache miss must not trigger an inline branch scan (T-2629)"
            )

        monkeypatch.setattr("frob.tickets._unlanded._unlanded_branch_work", _boom)

        _render_unlanded_branch_work_summary(repo)  # no cache present

        assert "not computed" in caplog.text
        assert "frob ticket reconcile" in caplog.text

    # frob:ticket T-2127
    def test_second_call_within_ttl_reuses_the_cache_not_a_fresh_scan(
        self, repo: Path, caplog, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWo\
        # rkSummary.test_second_call_within_ttl_reuses_the_cache_not_a_fresh_scan
        # T-2127/T-2629: a cache hit is served twice without ever calling
        # the underlying scan, confirmed here by making a real scan
        # explode both times.
        import logging

        caplog.set_level(logging.INFO)
        _save_unlanded_summary_cache(repo, ("runner-wiring",))

        def _boom(*_args, **_kwargs):  # noqa: ANN001, ANN401
            raise AssertionError("a cache hit must not re-run the scan")

        monkeypatch.setattr("frob.tickets._unlanded._unlanded_branch_work", _boom)
        _render_unlanded_branch_work_summary(repo)
        assert "runner-wiring" in caplog.text
        caplog.clear()

        _render_unlanded_branch_work_summary(repo)
        assert "runner-wiring" in caplog.text

    # frob:ticket T-2127
    def test_expired_cache_is_ignored(self, repo: Path) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWo\
        # rkSummary.test_expired_cache_is_ignored
        import time

        _save_unlanded_summary_cache(repo, ("stale-branch",))
        path = repo / ".frob" / "unlanded-summary-cache.json"
        raw = path.read_text(encoding="utf-8")
        assert '"stale-branch"' in raw
        # Backdate the cache past the TTL by writing an ancient
        # computed_at directly (no public setter for "expired" on
        # purpose -- the cache never lies about its own age).
        import json as _json

        payload = _json.loads(raw)
        payload["computed_at"] = time.time() - 10_000.0
        path.write_text(_json.dumps(payload), encoding="utf-8")
        assert _load_unlanded_summary_cache(repo) is None

    # frob:ticket T-2127
    def test_fresh_cache_round_trips(self, repo: Path) -> None:
        # frob:tests \
        # tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWo\
        # rkSummary.test_fresh_cache_round_trips
        _save_unlanded_summary_cache(repo, ("a", "b"))
        cached = _load_unlanded_summary_cache(repo)
        assert cached is not None
        assert cached.branches == ("a", "b")
