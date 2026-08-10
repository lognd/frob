"""T-1934: `frob.tickets._unlanded` -- finished-but-unlanded branch work.

Real git fixtures (branches, commits, `git ls-tree`/`git show` reads) --
this module's whole job is comparing branch CONTENT against `main`, which a
single in-memory ledger object can never exercise. Ticket bodies are
written directly as raw v2 `tickets/T-####/ticket.md` blobs (the exact
layout `frob.tickets._store.v2_ticket_path`/`v2_done_report_path` produce)
rather than going through `new_ticket`/`transition`, so each fixture can
place a branch and `main` in any state shape independently, including the
186-false-positive archive shape T-1934's own brief called out by name.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets._leases import record_lease
from frob.tickets._unlanded import (
    _unlanded_branch_work,
    _unlanded_findings_for_branch,
)


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:waive DUP001 reason="the git-init/commit trio is the established \
# real-git-fixture idiom this test module family repeats (tests/test_gates_tick005.py, \
# tests/test_serve_daemon.py, tests/unit/test_gitattributes_merge.py and many other \
# siblings all carry equivalent copies) -- extracting one repo-wide shared conftest \
# helper is a real, independent cleanup outside T-1934's scope, not something to fold \
# into its land"
def _git_init(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


# frob:waive DUP001 reason="same established git-fixture idiom as _git_init's own \
# waiver above -- see that comment"
def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


_TICKET_MD = """---
id: {tid}
title: '{title}'
state: {state}
kind: bug
origin: human
created: '2026-08-09'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Body text for {tid}.
"""


def _write_ticket_md(root: Path, tid: str, *, state: str, archived: bool = False) -> None:
    subdir = "tickets/archive" if archived else "tickets"
    path = root / subdir / tid / "ticket.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_TICKET_MD.format(tid=tid, title=tid, state=state), encoding="utf-8")


def _write_done_report(root: Path, tid: str) -> None:
    path = root / "tickets" / tid / "done-report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("## Done report\n\nFinished.\n", encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    (main_repo / "README.md").write_text("# repo\n", encoding="utf-8")
    _commit_all(main_repo, "init")
    return main_repo


def _branch(repo: Path, name: str) -> None:
    _run(["git", "checkout", "-q", "-b", name], repo)


def _back_to_main(repo: Path) -> None:
    _run(["git", "checkout", "-q", "main"], repo)


class TestUnlandedBranchWork:
    def test_confirmed_leak_shape_done_report_plus_in_progress(
        self, repo: Path
    ) -> None:
        """T-1934 acceptance 1's core shape: a branch carries a complete
        done-report for a ticket whose branch-local `ticket.md` still reads
        `in-progress`, and `main` has never heard of the ticket at all --
        this must be flagged.

        This is the FAIL-THEN-PASS proof for T-1934 acceptance 1: this
        assertion is what failed before `frob.tickets._unlanded` existed
        (import error / detector absent) and passes now that it does.
        """
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork.test_confirme\
        # d_leak_shape_done_report_plus_in_progress
        _branch(repo, "runner-wiring")
        _write_ticket_md(repo, "T-1315", state="in-progress")
        _write_done_report(repo, "T-1315")
        _commit_all(repo, "finish T-1315")
        _back_to_main(repo)

        findings = _unlanded_branch_work(repo)
        assert len(findings) == 1
        finding = findings[0]
        assert finding.ticket_id == "T-1315"
        assert finding.branch == "runner-wiring"
        assert finding.signal == "done-report"
        assert finding.state_on_main is None

    def test_archived_done_ticket_is_not_a_false_positive(self, repo: Path) -> None:
        """The 186-false-positive regression T-1934 names explicitly: a
        ticket that IS done and IS on main, but archived to
        `tickets/archive/<id>/ticket.md` rather than left at
        `tickets/<id>/ticket.md`. A path-existence-only check misreads this
        as "not on main at all"; this detector must not."""
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork.test_archived\
        # _done_ticket_is_not_a_false_positive
        _write_ticket_md(repo, "T-9001", state="done", archived=True)
        _commit_all(repo, "archive T-9001 on main")

        _branch(repo, "stale-branch")
        _write_ticket_md(repo, "T-9001", state="in-progress")
        _write_done_report(repo, "T-9001")
        _commit_all(repo, "stale branch still carries T-9001 pre-archive")
        _back_to_main(repo)

        findings = _unlanded_branch_work(repo)
        assert findings == ()

    def test_dropped_ticket_on_main_is_not_a_false_positive(self, repo: Path) -> None:
        """`dropped` is the other terminal state (T-1934's `_TERMINAL_
        STATES`) -- must be excluded exactly like `done`."""
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork.test_dropped_\
        # ticket_on_main_is_not_a_false_positive
        _write_ticket_md(repo, "T-9002", state="dropped")
        _commit_all(repo, "drop T-9002 on main")

        _branch(repo, "old-branch")
        _write_ticket_md(repo, "T-9002", state="in-progress")
        _write_done_report(repo, "T-9002")
        _commit_all(repo, "old branch predates the drop")
        _back_to_main(repo)

        findings = _unlanded_branch_work(repo)
        assert findings == ()

    def test_local_state_done_with_no_done_report_file_is_flagged(
        self, repo: Path
    ) -> None:
        """The second REQUIRED-A signal: no `done-report.md` at all, but
        the branch's own `ticket.md` reads `state: done`."""
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork.test_local_st\
        # ate_done_with_no_done_report_file_is_flagged
        _branch(repo, "no-report-branch")
        _write_ticket_md(repo, "T-9003", state="done")
        _commit_all(repo, "finish T-9003 without writing a done-report")
        _back_to_main(repo)

        findings = _unlanded_branch_work(repo)
        assert len(findings) == 1
        assert findings[0].ticket_id == "T-9003"
        assert findings[0].signal == "local-state-done"

    def test_queued_ticket_on_branch_is_not_flagged(self, repo: Path) -> None:
        """A ticket that is merely `queued`/`in-progress` on a branch with
        no done-report and no `state: done`/`dropped` carries no finished
        signal at all -- never reported (there is no work to lose)."""
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork.test_queued_t\
        # icket_on_branch_is_not_flagged
        _branch(repo, "wip-branch")
        _write_ticket_md(repo, "T-9004", state="in-progress")
        _commit_all(repo, "still working T-9004")
        _back_to_main(repo)

        findings = _unlanded_branch_work(repo)
        assert findings == ()

    def test_live_leased_ticket_is_excluded(self, repo: Path) -> None:
        """T-1934 acceptance 3: a ticket currently held by a LIVE lease
        (its worktree exists on disk, the ticket is in the ledger, no TTL
        expiry) must never be reported -- a live agent is still working
        it, this is not a leak."""
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork.test_live_lea\
        # sed_ticket_is_excluded
        _branch(repo, "live-branch")
        _write_ticket_md(repo, "T-9005", state="in-progress")
        _write_done_report(repo, "T-9005")
        _commit_all(repo, "finish T-9005 but the agent is still alive")
        _back_to_main(repo)

        # A live lease needs `record.ticket_id` present in the LOCAL
        # ledger (`lease_staleness_reason`'s "ticket-gone" check) and its
        # worktree path to exist on disk -- `repo` itself, resolved, is a
        # real existing path, so recording the lease against `repo` with a
        # local `tickets/T-9005/ticket.md` present satisfies both.
        _write_ticket_md(repo, "T-9005", state="in-progress")
        record_lease(repo, "T-9005", ())

        findings = _unlanded_branch_work(repo)
        assert findings == ()

    # frob:ticket T-1955
    def test_fresh_branch_reports_zero_despite_main_history(
        self, repo: Path
    ) -> None:
        """T-1955: a branch cut from `main` MINUTES ago, carrying only its
        own unrelated commit, must report ZERO unlanded tickets -- even
        though `main` itself has a large history of finished tickets fully
        reachable from the branch tip. The pre-fix `git ls-tree <branch>
        -- tickets` read listed every ticket path reachable from the
        branch, which includes everything already finished on `main`
        before the branch existed (216 false positives across 4 tickets x
        77 branches, T-1955's own measured repro). This is the FAIL-THEN-
        PASS proof: before the `_branch_own_changed_files` intersection,
        this asserted zero findings and got one (T-9101, inherited from
        main's own history)."""
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork.test_fresh_br\
        # anch_reports_zero_despite_main_history
        _write_ticket_md(repo, "T-9101", state="in-progress")
        _write_done_report(repo, "T-9101")
        _commit_all(repo, "finished work sitting directly on main, unlanded to itself")

        _branch(repo, "floor-zero")
        (repo / "unrelated.txt").write_text("fresh work\n", encoding="utf-8")
        _commit_all(repo, "fresh, unrelated commit on a brand-new branch")
        _back_to_main(repo)

        findings = _unlanded_branch_work(repo)
        assert findings == ()

    # frob:ticket T-1955
    def test_genuine_leak_still_reported_after_the_fix(self, repo: Path) -> None:
        """T-1955 acceptance 2: fixing the false-positive shape above must
        NOT also break the true-positive shape -- a branch whose OWN
        commits add a done-report for a ticket that is non-terminal on
        `main` is still flagged."""
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork.test_genuine_\
        # leak_still_reported_after_the_fix
        _write_ticket_md(repo, "T-9102", state="in-progress")
        _commit_all(repo, "queue T-9102 on main")

        _branch(repo, "real-leak-branch")
        _write_ticket_md(repo, "T-9102", state="in-progress")
        _write_done_report(repo, "T-9102")
        _commit_all(repo, "finish T-9102 on the branch, never landed")
        _back_to_main(repo)

        findings = _unlanded_branch_work(repo)
        assert len(findings) == 1
        assert findings[0].ticket_id == "T-9102"
        assert findings[0].branch == "real-leak-branch"
        assert findings[0].signal == "done-report"

    def test_findings_for_one_branch_matches_the_aggregate(self, repo: Path) -> None:
        """`_unlanded_findings_for_branch` (the single-branch entry
        `frob.tickets._leases.sweep_worktrees`'s new `kept:unlanded` gate
        calls) reports the same finding the all-branches scan does, for
        the branch it is pointed at."""
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork.test_findings\
        # _for_one_branch_matches_the_aggregate
        _branch(repo, "solo-branch")
        _write_ticket_md(repo, "T-9006", state="in-progress")
        _write_done_report(repo, "T-9006")
        _commit_all(repo, "finish T-9006")
        _back_to_main(repo)

        one = _unlanded_findings_for_branch(repo, "solo-branch")
        assert len(one) == 1
        assert one[0].ticket_id == "T-9006"
        assert one == _unlanded_branch_work(repo)
