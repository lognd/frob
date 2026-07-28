"""Tests for T-0453's scope-lease model: glob-set overlap, doable's
default collision filter, --show-blocked/--ignore-lease, and the
large-glob warning nudge (docs/modules/tickets.md#scope-lease-model)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

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
