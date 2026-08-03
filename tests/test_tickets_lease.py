"""Tests for T-0453's scope-lease model: glob-set overlap, doable's
default collision filter, --show-blocked/--ignore-lease, and the
large-glob warning nudge (docs/modules/tickets.md#scope-lease-model)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from frob.tickets import (
    Origin,
    Ticket,
    TicketKind,
    TicketQueue,
    TicketState,
    doable,
    doable_blocked,
    large_glob_warnings,
    leased_by,
    scope_breadth_context,
)
from frob.tickets._models import _globs_intersect, scope_overlap, scope_overlap_globs
from frob.tickets._store import _serialize_ticket


def _ticket(
    *,
    ticket_id: str,
    state: TicketState = TicketState.QUEUED,
    scope: tuple[str, ...] = (),
    created: date = date(2026, 1, 1),
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title=f"ticket {ticket_id}",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=created,
        blocked_by=(),
        parent=None,
        scope=scope,
        evidence=(),
        attachments=(),
        body="## Description\nsomething\n",
    )


def _queue(*tickets: Ticket) -> TicketQueue:
    return TicketQueue(tickets={t.id: t for t in tickets})


class TestGlobsIntersect:
    def test_wildcard_prefix_overlaps_literal(self) -> None:
        # frob:tests \
        # tests/test_tickets_lease.py::TestGlobsIntersect.test_wildcard_prefix_overlaps\
        # _literal
        assert _globs_intersect("tests/**", "tests/test_gates.py") is True

    def test_disjoint_literal_siblings(self) -> None:
        # frob:tests \
        # tests/test_tickets_lease.py::TestGlobsIntersect.test_disjoint_literal_siblings
        assert _globs_intersect("tests/test_gates.py", "tests/test_vet.py") is False

    def test_disjoint_directory_siblings(self) -> None:
        assert _globs_intersect("src/frob/gates/**", "src/frob/vet/**") is False

    def test_identical_globs_overlap(self) -> None:
        assert _globs_intersect("src/frob/gates/**", "src/frob/gates/**") is True


class TestScopeOverlap:
    def test_precise_scopes_disjoint(self) -> None:
        # frob:tests \
        # tests/test_tickets_lease.py::TestScopeOverlap.test_precise_scopes_disjoint
        scope_a = ("src/frob/gates/", "tests/test_gates.py")
        scope_b = ("src/frob/vet/", "tests/test_vet.py")
        assert scope_overlap(scope_a, scope_b) is False
        assert scope_overlap_globs(scope_a, scope_b) is None

    def test_real_collision_detected(self) -> None:
        # frob:tests \
        # tests/test_tickets_lease.py::TestScopeOverlap.test_real_collision_detected
        scope_a = ("src/frob/gates/", "tests/test_gates.py")
        scope_b = ("src/frob/gates/_arch.py", "tests/test_arch.py")
        assert scope_overlap(scope_a, scope_b) is True

    def test_ledger_alone_is_not_a_collision(self) -> None:
        # tickets.md is implicitly in every scope; ignored in overlap.
        scope_a = ("src/frob/gates/",)
        scope_b = ("src/frob/vet/",)
        assert scope_overlap(scope_a, scope_b) is False


class TestLeasedBy:
    def test_precise_in_progress_does_not_hide_disjoint(self) -> None:
        # frob:tests \
        # tests/test_tickets_lease.py::TestLeasedBy.test_precise_in_progress_does_not_h\
        # ide_disjoint
        holder_a = _ticket(
            ticket_id="T-1000",
            state=TicketState.IN_PROGRESS,
            scope=("src/frob/gates/", "tests/test_gates.py"),
        )
        holder_b = _ticket(
            ticket_id="T-1001",
            state=TicketState.IN_PROGRESS,
            scope=("src/frob/vet/", "tests/test_vet.py"),
        )
        candidate = _ticket(
            ticket_id="T-1002",
            scope=("src/frob/render/", "tests/test_render.py"),
        )
        queue = _queue(holder_a, holder_b, candidate)
        assert leased_by(queue, candidate) == ()

    def test_real_source_scope_collision_is_hidden(self) -> None:
        # frob:tests \
        # tests/test_tickets_lease.py::TestLeasedBy.test_real_source_scope_collision_is\
        # _hidden
        holder = _ticket(
            ticket_id="T-1000",
            state=TicketState.IN_PROGRESS,
            scope=("src/frob/gates/",),
        )
        candidate = _ticket(
            ticket_id="T-1001",
            scope=("src/frob/gates/_arch.py",),
        )
        queue = _queue(holder, candidate)
        hits = leased_by(queue, candidate)
        assert hits
        assert hits[0][0] == "T-1000"

    def test_over_broad_lease_demotes_to_warn_only(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_tickets_lease.py::TestLeasedBy.test_over_broad_lease_demotes_to_wa\
        # rn_only
        holder = _ticket(
            ticket_id="T-1000",
            state=TicketState.IN_PROGRESS,
            scope=("src/frob/**", "tests/**"),
        )
        candidate = _ticket(
            ticket_id="T-1001",
            scope=("src/frob/gates/_arch.py",),
        )
        queue = _queue(holder, candidate)
        # sound, undemoted check (no root): the over-broad lease really
        # does overlap -- this must stay a real collision.
        assert leased_by(queue, candidate) != ()
        # with a repo root, the named-over-broad lease demotes to
        # warn-only rather than hard-blocking the whole queue.
        assert leased_by(queue, candidate, tmp_path) == ()
        assert [t.id for t in doable(queue, tmp_path)] == ["T-1001"]

    def test_precise_portion_of_a_partly_broad_lease_still_blocks(
        self, tmp_path: Path
    ) -> None:
        holder = _ticket(
            ticket_id="T-1000",
            state=TicketState.IN_PROGRESS,
            scope=("src/frob/gates/", "tests/**"),
        )
        colliding = _ticket(
            ticket_id="T-1001",
            scope=("src/frob/gates/_arch.py",),
        )
        queue = _queue(holder, colliding)
        # tests/** demotes, but the precise src/frob/gates/ entry does not
        # -- the real collision on it must still be hidden.
        hits = leased_by(queue, colliding, tmp_path)
        assert hits
        assert hits[0][0] == "T-1000"


class TestDoable:
    def test_two_precise_in_progress_tickets_do_not_over_hide(self) -> None:
        holder_a = _ticket(
            ticket_id="T-1000",
            state=TicketState.IN_PROGRESS,
            scope=("src/frob/gates/", "tests/test_gates.py"),
        )
        holder_b = _ticket(
            ticket_id="T-1001",
            state=TicketState.IN_PROGRESS,
            scope=("src/frob/vet/", "tests/test_vet.py"),
        )
        disjoint = _ticket(
            ticket_id="T-1002",
            scope=("src/frob/render/", "tests/test_render.py"),
        )
        queue = _queue(holder_a, holder_b, disjoint)
        result = doable(queue)
        assert [t.id for t in result] == ["T-1002"]

    # invariant spec: [INV-024](invariants/INV-024.md)
    def test_real_collision_is_hidden_from_default_doable(self) -> None:
        holder = _ticket(
            ticket_id="T-1000",
            state=TicketState.IN_PROGRESS,
            scope=("src/frob/gates/",),
        )
        colliding = _ticket(
            ticket_id="T-1001",
            scope=("src/frob/gates/_arch.py",),
        )
        queue = _queue(holder, colliding)
        assert doable(queue) == ()

    def test_resurfaces_after_holder_closes(self) -> None:
        holder = _ticket(
            ticket_id="T-1000",
            state=TicketState.DONE,
            scope=("src/frob/gates/",),
        )
        candidate = _ticket(
            ticket_id="T-1001",
            scope=("src/frob/gates/_arch.py",),
        )
        queue = _queue(holder, candidate)
        assert [t.id for t in doable(queue)] == ["T-1001"]

    def test_ignore_lease_returns_raw_list(self) -> None:
        # frob:tests \
        # tests/test_tickets_lease.py::TestDoable.test_ignore_lease_returns_raw_list
        holder = _ticket(
            ticket_id="T-1000",
            state=TicketState.IN_PROGRESS,
            scope=("src/frob/gates/",),
        )
        colliding = _ticket(
            ticket_id="T-1001",
            scope=("src/frob/gates/_arch.py",),
        )
        queue = _queue(holder, colliding)
        assert doable(queue, ignore_lease=False) == ()
        assert [t.id for t in doable(queue, ignore_lease=True)] == ["T-1001"]


class TestShowBlocked:
    def test_show_blocked_lists_reasons(self) -> None:
        # frob:tests \
        # tests/test_tickets_lease.py::TestShowBlocked.test_show_blocked_lists_reasons
        holder = _ticket(
            ticket_id="T-1000",
            state=TicketState.IN_PROGRESS,
            scope=("src/frob/gates/",),
        )
        colliding = _ticket(
            ticket_id="T-1001",
            scope=("src/frob/gates/_arch.py",),
        )
        free = _ticket(
            ticket_id="T-1002",
            scope=("src/frob/render/",),
        )
        queue = _queue(holder, colliding, free)
        blocked = doable_blocked(queue)
        assert [t.id for t, _hits in blocked] == ["T-1001"]
        t, hits = blocked[0]
        assert hits[0][0] == "T-1000"


class TestLargeGlobWarnings:
    def test_fires_on_broad_tests_glob(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_tickets_lease.py::TestLargeGlobWarnings.test_fires_on_broad_tests_\
        # glob
        ticket = _ticket(ticket_id="T-2000", scope=("tests/**",))
        warnings = large_glob_warnings(ticket, tmp_path)
        assert warnings
        assert "T-2000" in warnings[0]

    def test_silent_on_precise_test_file(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_tickets_lease.py::TestLargeGlobWarnings.test_silent_on_precise_tes\
        # t_file
        ticket = _ticket(ticket_id="T-2001", scope=("tests/test_x.py",))
        assert large_glob_warnings(ticket, tmp_path) == ()

    def test_file_count_threshold_fires_on_broad_but_unnamed_glob(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "pkg").mkdir()
        for i in range(30):
            (tmp_path / "pkg" / f"mod_{i}.py").write_text("x = 1\n")
        ticket = _ticket(ticket_id="T-2002", scope=("pkg/**",))
        warnings = large_glob_warnings(ticket, tmp_path)
        assert warnings
        assert "matches 30 files" in warnings[0]

    def test_file_count_threshold_silent_under_configured_max(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "pkg").mkdir()
        for i in range(3):
            (tmp_path / "pkg" / f"mod_{i}.py").write_text("x = 1\n")
        ticket = _ticket(ticket_id="T-2003", scope=("pkg/**",))
        assert large_glob_warnings(ticket, tmp_path) == ()

    def test_tunable_via_frob_toml(self, tmp_path: Path) -> None:
        (tmp_path / "frob.toml").write_text(
            "[tickets]\nlarge_glob_max_files = 1\n", encoding="utf-8"
        )
        (tmp_path / "pkg").mkdir()
        for i in range(2):
            (tmp_path / "pkg" / f"mod_{i}.py").write_text("x = 1\n")
        ticket = _ticket(ticket_id="T-2004", scope=("pkg/**",))
        warnings = large_glob_warnings(ticket, tmp_path)
        assert warnings
        assert "matches 2 files" in warnings[0]


# frob:ticket T-0803
class TestBreadthPerf:
    """T-0453 perf-fix guard: the breadth walk (repo-file listing) must run
    ONCE per `doable`/`doable_blocked` call, never once per candidate x
    holder pair -- the bug that made `frob ticket doable` take minutes on
    this repo's real worktree count (a full-tree `rglob` re-walked per
    pair)."""

    def test_computed_once_per_doable_call(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests \
        # tests/test_tickets_lease.py::TestBreadthPerf.test_computed_once_per_doable_ca\
        # ll
        (tmp_path / "pkg").mkdir()
        for i in range(3):
            (tmp_path / "pkg" / f"mod_{i}.py").write_text("x = 1\n")

        calls = {"n": 0}
        import frob.tickets as tickets_mod

        real_repo_files = tickets_mod._repo_files

        def counting_repo_files(root: Path) -> tuple[str, ...]:
            calls["n"] += 1
            return real_repo_files(root)

        monkeypatch.setattr(tickets_mod, "_repo_files", counting_repo_files)

        holder_a = _ticket(
            ticket_id="T-3000",
            state=TicketState.IN_PROGRESS,
            scope=("pkg/",),
        )
        holder_b = _ticket(
            ticket_id="T-3001",
            state=TicketState.IN_PROGRESS,
            scope=("src/frob/vet/",),
        )
        candidates = tuple(
            _ticket(ticket_id=f"T-30{i:02d}", scope=(f"src/frob/mod{i}.py",))
            for i in range(2, 12)
        )
        queue = _queue(holder_a, holder_b, *candidates)

        result = doable(queue, tmp_path)

        assert len(result) == len(candidates)
        # ONE breadth walk for the whole call, not one per candidate (10)
        # x holder (2) pair -- would be 20 without the fix.
        assert calls["n"] == 1

    def test_doable_blocked_also_shares_one_breadth_walk(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        calls = {"n": 0}
        import frob.tickets as tickets_mod

        real_repo_files = tickets_mod._repo_files

        def counting_repo_files(root: Path) -> tuple[str, ...]:
            calls["n"] += 1
            return real_repo_files(root)

        monkeypatch.setattr(tickets_mod, "_repo_files", counting_repo_files)

        holder = _ticket(
            ticket_id="T-3100", state=TicketState.IN_PROGRESS, scope=("src/frob/",)
        )
        candidates = tuple(
            _ticket(ticket_id=f"T-31{i:02d}", scope=(f"src/frob/mod{i}.py",))
            for i in range(1, 6)
        )
        queue = _queue(holder, *candidates)

        doable_blocked(queue, tmp_path)

        assert calls["n"] == 1

    def test_breadth_context_uses_git_ls_files_when_available(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_tickets_lease.py::TestBreadthPerf.test_breadth_context_uses_git_ls\
        # _files_when_available
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / "a.py").write_text("x = 1\n")
        subprocess.run(["git", "add", "a.py"], cwd=tmp_path, check=True)
        # an untracked file must NOT count toward the git-backed file list.
        (tmp_path / "b.py").write_text("y = 2\n")

        _threshold, files = scope_breadth_context(tmp_path)
        assert files == ("a.py",)

    def test_repo_files_git_kill_switch_refuses_without_spawning(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/test_tickets_lease.py::TestBreadthPerf.test_repo_files_git_kill_switch_\
        # refuses_without_spawning
        # T-0803: FROB_DISABLE_EXEC=1 must make `_repo_files_git`'s `git
        # ls-files` spawn refuse (via `frob.gitio.run_argv` ->
        # `guarded_subprocess_run`) instead of bypassing the T-0200/T-0778
        # exec guard -- proven with a spy on the real `subprocess.run` so a
        # spawn attempt would be observed, not assumed.
        import subprocess

        from frob.tickets import _repo_files_git

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / "a.py").write_text("x = 1\n")
        subprocess.run(["git", "add", "a.py"], cwd=tmp_path, check=True)

        monkeypatch.setenv("FROB_DISABLE_EXEC", "1")
        spawned = False
        real_run = subprocess.run

        def _spy(*args, **kwargs):  # noqa: ANN001, ANN202
            nonlocal spawned
            spawned = True
            return real_run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", _spy)
        result = _repo_files_git(tmp_path)
        assert not spawned
        assert result is None


# frob:ticket T-1243
# frob:waive WIRE001 reason="test-only fixture helper used by \
# TestClusterScopeConflict's own three test methods below, in this same file -- a test \
# fixture calling itself is not the class of orphaned-production-code WIRE001 exists \
# to catch" follow_up="T-1487"
def _write_ticket_file(root: Path, ticket: Ticket, slug: str) -> None:
    """Write `ticket` into `root/tickets/<id>-<slug>.md` (T-1243) -- the
    on-disk fixture `_refuse_on_cluster_scope_conflict` needs, since it
    reads through `frob.tickets.load_queue` rather than an in-memory
    `TicketQueue` the way this file's other tests build one."""
    tickets_dir = root / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    (tickets_dir / f"{ticket.id}-{slug}.md").write_text(
        _serialize_ticket(ticket), encoding="utf-8"
    )


# frob:ticket T-1243
class TestClusterScopeConflict:
    # frob:ticket T-1243
    def test_refuses_when_union_scope_collides_with_a_foreign_lease(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_lease.py::TestClusterScopeConflict.test_refuses_when_union_scope_collides_with_a_foreign_lease  # noqa: E501
        import pytest

        from frob.app.ticket_runner._lifecycle import (
            _refuse_on_cluster_scope_conflict,
        )

        _write_ticket_file(
            tmp_path,
            _ticket(ticket_id="T-0050", state=TicketState.IN_PROGRESS, scope=("a.py",)),
            "foreign",
        )
        member = _ticket(ticket_id="T-0002", scope=("a.py", "b.py"))
        with pytest.raises(SystemExit) as exc_info:
            _refuse_on_cluster_scope_conflict(tmp_path, "T-0001", (member,))
        assert exc_info.value.code == 1

    # frob:ticket T-1243
    def test_no_conflict_returns_quietly(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_lease.py::TestClusterScopeConflict.test_no_conflict_returns_quietly  # noqa: E501
        from frob.app.ticket_runner._lifecycle import (
            _refuse_on_cluster_scope_conflict,
        )

        _write_ticket_file(
            tmp_path,
            _ticket(ticket_id="T-0050", state=TicketState.IN_PROGRESS, scope=("c.py",)),
            "foreign",
        )
        member = _ticket(ticket_id="T-0002", scope=("a.py", "b.py"))
        _refuse_on_cluster_scope_conflict(tmp_path, "T-0001", (member,))

    # frob:ticket T-1243
    def test_a_conflict_with_its_own_member_is_never_a_conflict(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_lease.py::TestClusterScopeConflict.test_a_conflict_with_its_own_member_is_never_a_conflict  # noqa: E501
        from frob.app.ticket_runner._lifecycle import (
            _refuse_on_cluster_scope_conflict,
        )

        member = _ticket(
            ticket_id="T-0002", state=TicketState.IN_PROGRESS, scope=("a.py",)
        )
        _write_ticket_file(tmp_path, member, "member")
        _refuse_on_cluster_scope_conflict(tmp_path, "T-0001", (member,))


# frob:ticket T-1243
# frob:waive DUP001 reason="the run/git-init/commit-all trio is an established \
# real-git fixture idiom this test module family already repeats byte-identically \
# (tests/test_ticket_work_and_land_finish.py, tests/test_ticket_land.py, \
# tests/test_tickets_collision.py, tests/test_ticket_leases.py, \
# tests/test_ticket_merge_driver.py, tests/test_ticket_reconcile.py) -- extracting a \
# shared conftest helper is a real, independent cleanup outside T-1243's own scope"
class TestWorkCluster:
    # frob:ticket T-1243
    @staticmethod
    def _run(argv: list, cwd: Path) -> None:
        import subprocess

        subprocess.run(argv, cwd=str(cwd), check=True, capture_output=True, text=True)

    # frob:ticket T-1243
    def _git_init(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._run(["git", "init", "-q", "-b", "main"], root)
        self._run(["git", "config", "user.email", "test@example.com"], root)
        self._run(["git", "config", "user.name", "Test"], root)

    # frob:ticket T-1243
    # frob:tests tests/test_tickets_lease.py::TestWorkCluster.test_leases_every_dispatchable_member_into_one_worktree  # noqa: E501
    def test_leases_every_dispatchable_member_into_one_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # This test spawns its OWN real git repos/worktree under tmp_path,
        # simulating an end-user CLI invocation, not the dispatching
        # agent's own leased worktree -- strip the calling shell's
        # FROB_WORKTREE/FROB_AGENT (T-0880's same rationale for
        # tests/system/**'s run() helper) so a dispatched agent running
        # this file directly, with its own lease vars set per playbook
        # section 1, cannot spuriously trip the worktree-lease guard
        # against these tmp_path repos.
        monkeypatch.delenv("FROB_WORKTREE", raising=False)
        monkeypatch.delenv("FROB_AGENT", raising=False)

        from frob.app.config import AppConfig
        from frob.app.ticket_runner._lifecycle import _work
        from frob.tickets import TicketState, load_all
        from frob.tickets._models import Origin, TicketKind, TicketSpec, TicketTier
        from frob.tickets._new_renumber import new_ticket
        from frob.tickets._store import atomic_write, ledger_path

        main_repo = tmp_path / "main"
        self._git_init(main_repo)
        atomic_write(ledger_path(main_repo), "# Tickets\n\n")
        self._run(["git", "add", "-A"], main_repo)
        self._run(["git", "commit", "-q", "-m", "init"], main_repo)

        epic = new_ticket(
            main_repo,
            TicketSpec(
                title="epic",
                kind=TicketKind.FEATURE,
                origin=Origin.AGENT,
                tier=TicketTier.EPIC,
            ),
        ).danger_ok
        first = new_ticket(
            main_repo,
            TicketSpec(
                title="first",
                kind=TicketKind.FEATURE,
                origin=Origin.AGENT,
                parent=epic.id,
                scope=("a.py",),
            ),
        ).danger_ok
        second = new_ticket(
            main_repo,
            TicketSpec(
                title="second",
                kind=TicketKind.FEATURE,
                origin=Origin.AGENT,
                parent=epic.id,
                scope=("b.py",),
                blocked_by=(first.id,),
            ),
        ).danger_ok
        self._run(["git", "add", "-A"], main_repo)
        self._run(["git", "commit", "-q", "-m", "file cluster tickets"], main_repo)

        worktree = tmp_path / "cluster-worktree"
        cfg = AppConfig(
            ticket_command="work",
            ticket_cluster=epic.id,
            ticket_worktree=worktree,
            ticket_foreground=True,
            ticket_path=main_repo,
        )
        _work(main_repo, cfg)

        assert (worktree / ".git").exists()
        loaded = load_all(worktree).danger_ok
        # T-0002 (no blockers) starts immediately in this one pass; T-0003
        # (blocked_by T-0002) cannot legally start until T-0002 actually
        # CLOSES -- the state machine's own open-blocker guard refuses an
        # IN_PROGRESS blocker just as much as a QUEUED one -- so it is
        # never even auto-planned, deferred for an ordinary
        # `frob ticket start` later.
        assert loaded[first.id].state is TicketState.IN_PROGRESS
        assert loaded[second.id].state is TicketState.QUEUED
