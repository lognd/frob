import os
from pathlib import Path

import pytest

import frob.tickets._land_git_ops as _land_git_ops_mod
from frob.tickets import (
    new_ticket,
)
from frob.tickets._land import land
from tests.ticket_land_suite.conftest import (
    _commit_all,
    _git_init,
    _make_closeable,
    _run,
    _spec,
)

pytestmark = pytest.mark.heavy_subprocess


class TestWipCommit:
    """`_wip_commit` -- uncommitted worktree changes at land time must be
    snapshotted before the merge that follows, both in dry-run (staged then
    unwound) and real (actually committed) mode."""

    def test_dry_run_wip_commits_uncommitted_changes(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-wip-dry", str(wt)], repo)
        created = new_ticket(wt, _spec("Wip dry", scope=("src/wip_dry.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip dry ticket bits")

        # An UNCOMMITTED change present when land() is called.
        (wt / "src" / "wip_dry.py").write_text("# uncommitted at land time\n")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.wip_committed is True

        # Dry run unwinds everything -- the uncommitted change is still
        # sitting uncommitted in the worktree afterward.
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() != ""

    def test_real_land_wip_commits_uncommitted_changes(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-wip-real", str(wt)], repo)
        created = new_ticket(wt, _spec("Wip real", scope=("src/wip_real.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "wip_real.py").write_text("# committed baseline\n")
        _commit_all(wt, "wip real ticket bits")

        # An UNCOMMITTED change present when land() is called, real run.
        (wt / "src" / "wip_real.py").write_text("# uncommitted change to snapshot\n")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.wip_committed is True

        wt_log = _run(["git", "log", "--oneline"], wt).stdout
        assert "wip: pre-land snapshot" in wt_log

        landed_content = (repo / "src" / "wip_real.py").read_text()
        assert landed_content == "# uncommitted change to snapshot\n"


# frob:ticket T-1184
# frob:ticket T-2550
class TestWipAddIgnoredPathFallback:
    """T-1184: `_wip_add_excluding_frob`'s `:!.frob` pathspec trips git
    2.34.1's "explicitly named ignored path" refusal the moment `.frob` IS
    actually gitignored (the normal real-repo case) -- the fallback
    (add-everything, then unstage `.frob` separately) must reach the same
    end state without ever naming an ignored path in a pathspec."""

    # frob:ticket T-2550
    def test_gitignored_frob_falls_back_and_still_lands(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_wip_add_excluding_frob \
        # kind="integration"
        # T-2550: exercised only through the full `land(..., dry_run=False)`
        # pipeline several call-hops deep, not a direct call a static
        # call-graph can see -- same COV006 kind="integration"
        # trust-at-face-value convention this file's own
        # test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch
        # already documents for `_merge_ledger_tickets`/`_resolve_divergence`.
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-wip-ignored-frob", str(wt)], repo
        )
        created = new_ticket(wt, _spec("Wip ignored frob", scope=("src/wip_ig.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # `.frob/` is gitignored (the normal real-repo case) -- naming it in
        # a negated pathspec is what trips the T-1184 refusal.
        (wt / ".gitignore").write_text(".frob/\n")
        (wt / "src" / "wip_ig.py").write_text("# committed baseline\n")
        _commit_all(wt, "wip ignored-frob ticket bits")

        # Scratch state under `.frob/` (as `land()`'s own lock/bookkeeping
        # writes leave behind) plus a real uncommitted change to snapshot.
        (wt / ".frob").mkdir(exist_ok=True)
        (wt / ".frob" / "scratch.txt").write_text("frob-local state\n")
        (wt / "src" / "wip_ig.py").write_text("# uncommitted change to snapshot\n")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.wip_committed is True

        wt_log = _run(["git", "log", "--oneline"], wt).stdout
        assert "wip: pre-land snapshot" in wt_log

        landed_content = (repo / "src" / "wip_ig.py").read_text()
        assert landed_content == "# uncommitted change to snapshot\n"

    def test_is_ignored_path_refusal_matches_gits_fixed_message(self) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_is_ignored_path_refusal \
        # kind="unit"
        stderr = (
            "The following paths are ignored by one of your .gitignore files:\n"
            ".frob\nhint: Use -f if you really want to add them.\n"
        )
        assert _land_git_ops_mod._is_ignored_path_refusal(stderr) is True
        assert (
            _land_git_ops_mod._is_ignored_path_refusal("some other git error") is False
        )


# frob:ticket T-2865
class TestWipCommitNormalizationOnlyDirty:
    """T-0847: a worktree that is `_porcelain_dirty` purely because of a
    line-ending normalization status line (WSL/autocrlf phantom-modified)
    must not fail land with `GitFailed` -- `add -A` renormalizes back to the
    identical committed blob, so `git commit` has nothing real to commit and
    used to exit 1 with no stderr, wrongly surfaced as a land failure."""

    def test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed(
        self, repo: Path
    ) -> None:
        # frob:ticket T-2865
        # frob:waive COV006 reason="T-2550 class: reached only through a public land \
        # entry point several hops out, a shape build_call_graph structurally cannot \
        # see through; confirmed reachable by direct read"
        # frob:tests src/frob/tickets/_land_git_ops.py::_do_wip_commit kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-wip-crlf", str(wt)], repo)
        created = new_ticket(wt, _spec("Wip crlf", scope=("src/wip_crlf.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # Force text normalization on this worktree and commit an LF file
        # under it -- the committed blob is normalized LF content.
        _run(["git", "config", "core.autocrlf", "true"], wt)
        (wt / "src" / "wip_crlf.py").write_text("line one\nline two\n")
        _commit_all(wt, "wip crlf ticket bits")

        # Simulate the WSL phantom-dirty symptom: the working-tree file now
        # carries CRLF endings, so `git status --porcelain` reports it
        # modified, but `add -A` will renormalize it right back to the
        # identical committed blob (nothing real to snapshot).
        (wt / "src" / "wip_crlf.py").write_bytes(b"line one\r\nline two\r\n")
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() != ""

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.wip_committed is False

        wt_log = _run(["git", "log", "--oneline"], wt).stdout
        assert "wip: pre-land snapshot" not in wt_log


# frob:ticket T-3123
class TestWorktreeLeaseEnvIsolation:
    """T-3123: `tests/conftest.py`'s autouse `FROB_WORKTREE`/`FROB_AGENT`/
    `PYTEST_XDIST_AUTO_NUM_WORKERS` snapshot/restore fixture must contain a
    leak of any of those three, regardless of what set them.

    Reproduces the exact leak measured for T-3123: `land()`'s post-merge
    evidence re-verification path (`_verify.py`) calls
    `frob.tickets._worktree_guard.apply_agent_env(worktree)`, which mutates
    `os.environ` DIRECTLY with no restore (correct for its real,
    short-lived-process production callers, wrong for a long-lived pytest
    worker). `TestLedgerV2LandMergeStory.test_disjoint_v2_tickets_land_
    with_no_custom_merge`'s own `land()` call is the ORIGINAL trigger this
    ticket traced (`FROB_WORKTREE` left pointed at its `wt-v2-a` fixture
    worktree), but the two tests below simulate the leak directly rather
    than depend on that test's specific internals, so this regression
    stays meaningful even if `apply_agent_env`'s own call sites change.

    Simulates two tests run in order in the SAME worker process, mirroring
    `tests/unit/test_conftest_parse_reset.py`'s established pattern for
    testing an autouse conftest fixture's cross-test isolation.

    Each assertion below compares against a fixed SENTINEL value, never
    against "unset" -- a dispatched agent's own real shell legitimately
    carries a real `FROB_WORKTREE` lease (`frob agent env`/`ticket
    work`), so an assertion of the shape `"FROB_WORKTREE" not in
    os.environ` would itself fail standalone under exactly that ordinary
    dispatch environment, independent of any leak. Comparing against a
    value no real lease will ever equal keeps this evidence node
    id individually re-runnable (a `frob ticket evidence` requirement)
    regardless of the ambient environment it runs in."""

    #: A path no real `FROB_WORKTREE` lease will ever resolve to -- used
    #: instead of "unset" so these assertions hold under a real dispatched
    #: agent's own ambient lease too (see class docstring).
    _LEAK_SENTINEL = "/nonexistent/T-3123-leak-sentinel/wt"

    #: Set by `test_apply_agent_env_leak_is_contained_to_its_own_test`,
    #: read by `test_must_stay_quiet_after_apply_agent_env_leak` -- a
    #: class attribute (not per-instance) so it survives across the two
    #: tests' separate `self` instances in the same worker process.
    _last_apply_agent_env_leak: str | None = None

    # frob:tests tests/ticket_land_suite/test_wip.py::TestWorktreeLeaseEnvIsolation.test_b_does_not_see_a_leaked_frob_worktree  # noqa: E501
    def test_a_leaves_frob_worktree_set_like_apply_agent_env_does(self) -> None:
        """First test: mutate `os.environ` DIRECTLY (bypassing
        `monkeypatch`, exactly like `apply_agent_env` does) -- without
        T-3123's autouse fixture this would leave `FROB_WORKTREE` set for
        whichever test runs next in this worker."""
        # frob:waive SEC110 reason="FROB_WORKTREE is a local worktree path, not a \
        # secret -- this test deliberately reads it directly to prove T-3123's \
        # leak-isolation fixture works"
        os.environ["FROB_WORKTREE"] = self._LEAK_SENTINEL
        # frob:waive SEC110 reason="FROB_WORKTREE is a local worktree path, not a \
        # secret -- this test deliberately reads it directly to prove T-3123's \
        # leak-isolation fixture works"
        assert os.environ.get("FROB_WORKTREE") == self._LEAK_SENTINEL

    def test_b_does_not_see_a_leaked_frob_worktree(self) -> None:
        """Second test, run immediately after the one above in file-
        declaration order: `FROB_WORKTREE` must not still be the leaked
        sentinel at its own start, even though it never cleans up after
        the prior test itself -- proving the autouse `tests/conftest.py`
        fixture (not accidental ordering, and not a hand-added cleanup in
        this test) is what isolates it. A `land()` call against a
        DIFFERENT `tmp_path` repo right after this would otherwise refuse
        with `TicketError.WorktreeLeaseViolation` -- the exact T-3123
        failure shape."""
        # frob:waive SEC110 reason="FROB_WORKTREE is a local worktree path, not a \
        # secret -- this test deliberately reads it directly to prove T-3123's \
        # leak-isolation fixture works"
        assert os.environ.get("FROB_WORKTREE") != self._LEAK_SENTINEL

    def test_apply_agent_env_leak_is_contained_to_its_own_test(
        self, tmp_path: Path
    ) -> None:
        """Direct proof against the REAL leaking call, not just a
        simulation: `apply_agent_env` (the production function T-3123
        traced) mutates this test's own `os.environ` to `tmp_path`'s
        resolved path, but the next test must never see THIS test's own
        `tmp_path` value -- checked immediately below."""
        from frob.tickets._worktree_guard import apply_agent_env

        _git_init(tmp_path)
        result = apply_agent_env(tmp_path)
        assert result.is_ok
        # frob:waive SEC110 reason="FROB_WORKTREE is a local worktree path, not a \
        # secret -- this test deliberately reads it directly to prove T-3123's \
        # leak-isolation fixture works"
        assert os.environ.get("FROB_WORKTREE") == str(tmp_path.resolve())
        # Recorded on the class (not an instance attribute) so the next
        # test -- a fresh instance, same worker process -- can compare
        # against exactly this test's own leaked value.
        type(self)._last_apply_agent_env_leak = str(tmp_path.resolve())

    def test_must_stay_quiet_after_apply_agent_env_leak(self) -> None:
        """Runs immediately after the real `apply_agent_env` leak above:
        must not still carry that test's own leaked `tmp_path` value,
        proving containment for the ACTUAL production leak path, not
        just the simulated one above.

        `pytest.skip`s (never fails) when run standalone, out of file
        order -- there is then no predecessor leak to have been contained
        in the first place, and `frob ticket evidence` requires every
        bound node id to also pass when re-run individually."""
        leaked = type(self)._last_apply_agent_env_leak
        if leaked is None:
            pytest.skip(
                "test_apply_agent_env_leak_is_contained_to_its_own_test did "
                "not run first in this process -- nothing to check standalone"
            )
        # frob:waive SEC110 reason="FROB_WORKTREE is a local worktree path, not a \
        # secret -- this test deliberately reads it directly to prove T-3123's \
        # leak-isolation fixture works"
        assert os.environ.get("FROB_WORKTREE") != leaked
