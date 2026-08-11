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
    _branch_own_changed_files,
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

    # frob:ticket T-1948
    def test_directive_anchored_code_with_queued_ticket_is_flagged(
        self, repo: Path
    ) -> None:
        """T-1948's real specimen (t1552-ledger-v2/T-1691): a branch
        commits a source file opening with a `frob:ticket T-####`
        directive, but that ticket's OWN `ticket.md` on the branch was
        never transitioned past `queued` -- no done-report, no `state:
        done`/`dropped`, so neither of T-1934's original two signals see
        it. This is the FAIL-THEN-PASS proof for T-1948: before the third
        `"directive-anchored"` signal existed, this asserted one finding
        and got zero."""
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork.test_directiv\
        # e_anchored_code_with_queued_ticket_is_flagged
        _branch(repo, "t1552-ledger-v2")
        _write_ticket_md(repo, "T-1691", state="queued")
        (repo / "src").mkdir(parents=True, exist_ok=True)
        (repo / "src" / "_bisect.py").write_text(
            "# frob:ticket T-1691\n"
            "def bisect() -> None:\n"
            '    """Real, committed, ticket-anchored work."""\n',
            encoding="utf-8",
        )
        _commit_all(repo, "preserve uncommitted T-1691 bisect work")
        _back_to_main(repo)

        findings = _unlanded_branch_work(repo)
        assert len(findings) == 1
        finding = findings[0]
        assert finding.ticket_id == "T-1691"
        assert finding.branch == "t1552-ledger-v2"
        assert finding.signal == "directive-anchored"
        assert finding.state_on_main is None

    # frob:ticket T-1948
    def test_directive_anchored_code_with_in_progress_ticket_is_not_flagged(
        self, repo: Path
    ) -> None:
        """The expected, healthy shape: an agent ran `ticket start`
        (branch-local `ticket.md` reads `in-progress`) before writing the
        anchored code -- normal in-flight work, not a ledger gap. Must
        stay silent."""
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork.test_directiv\
        # e_anchored_code_with_in_progress_ticket_is_not_flagged
        _branch(repo, "healthy-branch")
        _write_ticket_md(repo, "T-1700", state="in-progress")
        (repo / "src").mkdir(parents=True, exist_ok=True)
        (repo / "src" / "_thing.py").write_text(
            "# frob:ticket T-1700\ndef thing() -> None: ...\n", encoding="utf-8"
        )
        _commit_all(repo, "still working T-1700, ticket started normally")
        _back_to_main(repo)

        findings = _unlanded_branch_work(repo)
        assert findings == ()

    # frob:ticket T-1948
    def test_directive_anchor_yields_to_a_stronger_signal(self, repo: Path) -> None:
        """A ticket that ALREADY has a `done-report` signal must not also
        produce a duplicate `directive-anchored` finding for the same id
        -- the stronger, more specific signal wins, exactly one finding
        per ticket per branch."""
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork.test_directiv\
        # e_anchor_yields_to_a_stronger_signal
        _branch(repo, "both-signals-branch")
        _write_ticket_md(repo, "T-1701", state="queued")
        _write_done_report(repo, "T-1701")
        (repo / "src").mkdir(parents=True, exist_ok=True)
        (repo / "src" / "_thing.py").write_text(
            "# frob:ticket T-1701\ndef thing() -> None: ...\n", encoding="utf-8"
        )
        _commit_all(repo, "finish T-1701, anchored code plus a done-report")
        _back_to_main(repo)

        findings = _unlanded_branch_work(repo)
        assert len(findings) == 1
        assert findings[0].ticket_id == "T-1701"
        assert findings[0].signal == "done-report"

    # frob:ticket T-1948
    def test_directive_anchor_in_tickets_path_is_not_a_self_signal(
        self, repo: Path
    ) -> None:
        """A ticket's OWN ledger files legitimately cite `frob:ticket
        T-####` (its own id, or a related one) -- `tickets/**` paths must
        never themselves be scanned as an anchor source, or every ticket
        with a body mentioning another ticket id would falsely flag that
        other id."""
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork.test_directiv\
        # e_anchor_in_tickets_path_is_not_a_self_signal
        _branch(repo, "ledger-only-branch")
        _write_ticket_md(repo, "T-1702", state="queued")
        path = repo / "tickets" / "T-1702" / "ticket.md"
        path.write_text(path.read_text() + "\nfrob:ticket T-1703 mentioned in prose.\n")
        _commit_all(repo, "queue T-1702, mentioning T-1703 in its own body")
        _back_to_main(repo)

        findings = _unlanded_branch_work(repo)
        assert findings == ()

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


class TestUnlandedBranchWorkMainStateSpawnScaling:
    """T-2125: a `PYTHONFAULTHANDLER=1` stack sample of a stuck shared-root
    `doable` landed inside `_ticket_state_on_main` -> `_blob_text` ->
    `guarded_subprocess_run` -- up to two `git show` spawns PER TICKET ID
    PER BRANCH, an O(branches x tickets) product that a worktree's much
    smaller branch/ticket count hides completely (this repo alone: ~644
    branches x ~2100 ticket directories). The fix resolves every ticket's
    main-side state in ONE `git grep` call
    (`_all_ticket_states_on_main`), shared across every branch, instead of
    re-resolving it per (branch, ticket) pair."""

    # frob:tests \
    # tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWorkMainStateSpawnScal\
    # ing.test_main_state_resolution_does_not_scale_with_branch_times_ticket
    def test_main_state_resolution_does_not_scale_with_branch_times_ticket(
        self, repo: Path
    ) -> None:
        """FAIL before this fix: total git-spawn count scaled with the
        branch x ticket product (up to 2 `git show` calls per pair, just
        for main-state resolution). PASS after: total spawns stay well
        below the product regardless of how many (branch, ticket) pairs
        exist, because main-state resolution is a single `git grep` call
        no matter how many pairs there are."""
        from frob.gitio import spawn_recorder

        num_branches = 4
        tickets_per_branch = 5
        for b in range(num_branches):
            branch_name = f"agent-branch-{b}"
            _branch(repo, branch_name)
            for t in range(tickets_per_branch):
                tid = f"T-90{b}{t}"
                _write_ticket_md(repo, tid, state="in-progress")
                _write_done_report(repo, tid)
            _commit_all(repo, f"finish tickets on {branch_name}")
            _back_to_main(repo)

        product = num_branches * tickets_per_branch

        with spawn_recorder() as recorder:
            findings = _unlanded_branch_work(repo)

        # Sanity: the fixture's own shape really does surface one finding
        # per (branch, ticket) pair -- if this assertion ever fails, the
        # spawn-count assertion below would be meaningless (comparing
        # against a product the run never actually processed).
        assert len(findings) == product

        total_spawns = sum(recorder.counts().values())
        # The pre-fix implementation alone would spawn up to 2 * product
        # `git show` calls for main-state resolution (40, here), on top
        # of every other per-branch cost -- so total_spawns would be
        # AT LEAST the product, scaling linearly with it. The fix bounds
        # main-state resolution to exactly one spawn total, so overall
        # cost must stay strictly below the product, not scale with it.
        assert total_spawns < product, (
            f"expected total git spawn count ({total_spawns}) to stay "
            f"below the branch x ticket product ({product}) -- main-state "
            "resolution must not multiply per (branch, ticket) pair "
            f"(spawned argvs: {recorder.counts()!r})"
        )


# frob:ticket T-1966
class TestBranchOwnChangedFilesConsolidation:
    """T-1966: 'files this branch's own commits changed' used to be
    implemented independently in `frob.tickets._land` and
    `frob.tickets._unlanded`, and got the two-dot/three-dot lesson wrong
    twice in different clothes (T-1922, T-1955). These tests pin the
    consolidated shape: exactly ONE real implementation, both former
    call sites agreeing on a real diff, and the empty-set case for a
    freshly-cut branch."""

    def test_unlanded_has_no_second_implementation(self) -> None:
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestBranchOwnChangedFilesConsolidati\
        # on.test_unlanded_has_no_second_implementation
        """The concept must have exactly one home. Before T-1966,
        `_unlanded._branch_own_changed_files` ran its own `git diff
        --name-only` spawn (`run_argv(("git", ..., "diff", ...))`)
        independently of `frob.tickets._land._branch_changed_files` --
        this is the DUPLICATION the ticket measured. After the fix,
        `_unlanded`'s function is a thin delegate to the `_land` one and
        its own source carries no `run_argv` call at all."""
        import inspect

        source = inspect.getsource(_branch_own_changed_files)
        assert "run_argv" not in source, (
            "_branch_own_changed_files still spawns its own git diff -- "
            "it must delegate to frob.tickets._land._branch_changed_files "
            "instead of keeping a second implementation (T-1966)"
        )

    def test_both_former_call_sites_agree_on_a_real_branch(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestBranchOwnChangedFilesConsolidati\
        # on.test_both_former_call_sites_agree_on_a_real_branch
        """A branch with commits on BOTH sides of the merge-base: `main`
        advances after the branch is cut (a file only `main` touched),
        and the branch commits its own file. `_land._branch_changed_files`
        (worktree checked out AT the branch, base_ref='main', implicit
        HEAD) and `_unlanded._branch_own_changed_files` (root need not be
        checked out at the branch at all, explicit branch name) must
        report the IDENTICAL set: only the branch's own file, never the
        post-divergence main-only file."""
        from frob.tickets._land import _branch_changed_files

        _branch(repo, "feature-x")
        (repo / "branch_only.txt").write_text("branch\n", encoding="utf-8")
        _commit_all(repo, "branch commits its own file")
        _back_to_main(repo)
        (repo / "main_only.txt").write_text("main\n", encoding="utf-8")
        _commit_all(repo, "main advances after divergence")

        # _unlanded's call site: root need not be checked out at the
        # branch (it is on main here, deliberately, since this is the
        # shared-root scan shape T-1955 introduced this function for).
        via_unlanded = _branch_own_changed_files(repo, "feature-x")

        # _land's call site: assumes the worktree IS checked out at the
        # branch (its many real callers run at land time, mid-ticket).
        _run(["git", "checkout", "-q", "feature-x"], repo)
        via_land_result = _branch_changed_files(repo, "main")
        assert via_land_result.is_ok
        via_land = via_land_result.danger_ok

        assert via_unlanded == via_land == frozenset({"branch_only.txt"})
        assert "main_only.txt" not in via_unlanded
        assert "main_only.txt" not in via_land

    def test_freshly_cut_branch_yields_empty_set(self, repo: Path) -> None:
        # frob:tests \
        # tests/unit/test_unlanded_branch_work.py::TestBranchOwnChangedFilesConsolidati\
        # on.test_freshly_cut_branch_yields_empty_set
        """A branch cut from `main` with no commits of its own reports
        the empty set from the shared helper -- the exact T-1955
        regression shape (a `git ls-tree`-based predecessor inherited
        `main`'s entire history as "this branch's own work")."""
        _branch(repo, "just-cut")
        result = _branch_own_changed_files(repo, "just-cut")
        assert result == frozenset()
