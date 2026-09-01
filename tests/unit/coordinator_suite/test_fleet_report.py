import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tests.unit.conftest import (
    _write_ticket,  # noqa: F401 -- T-3596
    fleet_status,
)


# frob:ticket T-2179
class TestTicketReadiness:
    """`fleet_status.ticket_readiness` (T-2133)."""

    # frob:ticket T-2179
    def test_dispatchable_when_no_lease_no_commits_no_divergence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A queued ticket, no live lease, no sibling-branch commits: ready."""
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda tid: None)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "queued", "scope": ["src/a.py"]},
        )
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        readiness = fleet_status.ticket_readiness("T-2114")
        assert readiness["dispatchable"] is True
        assert readiness["scope_diverges"] is False
        assert readiness["worktrees_with_commits"] == []

    # frob:ticket T-2179
    def test_not_dispatchable_when_a_live_lease_exists(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A live lease (someone already working it) blocks dispatch --
        the exact T-2114 incident: dispatched believing the lease 'should
        be free now' when another worktree still held it."""
        monkeypatch.setattr(
            fleet_status,
            "ticket_lease",
            lambda tid: {
                "ticket_id": tid,
                "scope": ["src/a.py"],
                "worktree": "/w",
                "branch": "b",
                "recorded_at": "2026-08-01T00:00:00+00:00",
            },
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "queued", "scope": ["src/a.py"]},
        )
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        assert fleet_status.ticket_readiness("T-2114")["dispatchable"] is False

    # frob:ticket T-2179
    def test_not_dispatchable_when_another_branch_already_has_commits(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Already-implemented-elsewhere (no lease left, but real commits
        on a sibling branch) also blocks dispatch."""
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda tid: None)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "queued", "scope": ["src/a.py"]},
        )
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: ["sibling"]
        )
        readiness = fleet_status.ticket_readiness("T-2114")
        assert readiness["dispatchable"] is False
        assert readiness["worktrees_with_commits"] == ["sibling"]

    # frob:ticket T-2179
    def test_flags_scope_divergence_between_the_live_lease_and_main(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The live lease's scope differing from main's committed scope is
        surfaced as `scope_diverges`, the 'single highest-value signal'
        this ticket exists to add."""
        monkeypatch.setattr(
            fleet_status,
            "ticket_lease",
            lambda tid: {
                "ticket_id": tid,
                "scope": ["src/a.py"],
                "worktree": "/w",
                "branch": "b",
                "recorded_at": "2026-08-01T00:00:00+00:00",
            },
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "queued", "scope": ["src/a.py", "src/b.py"]},
        )
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        readiness = fleet_status.ticket_readiness("T-2114")
        assert readiness["scope_diverges"] is True
        assert readiness["dispatchable"] is False

    # frob:ticket T-2196
    # frob:tests \
    # tests/unit/coordinator_suite/test_fleet_report.py::TestTicketReadiness.test_not_d\
    # ispatchable_when_ticket_does_not_exist_on_main
    def test_not_dispatchable_when_ticket_does_not_exist_on_main(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2196's own reproduction: a ticket absent from `main` must
        never read `dispatchable: True`, no matter how clean the lease/
        commit checks come back -- the fact `ticket_frontmatter_on_main`
        already measures (and `main: ticket does not exist on main`
        already PRINTS) must gate the verdict, not be computed and then
        discarded."""
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda tid: None)
        monkeypatch.setattr(
            fleet_status, "ticket_frontmatter_on_main", lambda tid: None
        )
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        readiness = fleet_status.ticket_readiness("T-9999")
        assert readiness["main"] is None
        assert readiness["dispatchable"] is False

    # frob:ticket T-2196
    # frob:tests \
    # tests/unit/coordinator_suite/test_fleet_report.py::TestTicketReadiness.test_not_d\
    # ispatchable_when_a_blocker_is_still_open
    def test_not_dispatchable_when_a_blocker_is_still_open(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`blocked_by` naming a still-open ticket must block dispatch --
        acceptance [2]'s named audit target: this edge was never checked
        at all before T-2196, so a ticket correctly blocked on an open
        dependency still read as `dispatchable: True`."""
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda tid: None)

        def fake_main(tid: str) -> dict | None:
            if tid == "T-2114":
                return {
                    "state": "queued",
                    "scope": ["src/a.py"],
                    "blocked_by": ["T-0001"],
                }
            if tid == "T-0001":
                return {"state": "in-progress", "scope": [], "blocked_by": []}
            return None

        monkeypatch.setattr(fleet_status, "ticket_frontmatter_on_main", fake_main)
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        readiness = fleet_status.ticket_readiness("T-2114")
        assert readiness["open_blockers"] == ["T-0001"]
        assert readiness["dispatchable"] is False

    # frob:ticket T-2196
    # frob:tests \
    # tests/unit/coordinator_suite/test_fleet_report.py::TestTicketReadiness.test_dispa\
    # tchable_when_every_blocker_is_done
    def test_dispatchable_when_every_blocker_is_done(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A `blocked_by` entry that is `done` on `main` does not block
        dispatch -- the positive control for the previous test, proving
        the new check discriminates rather than always refusing."""
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda tid: None)

        def fake_main(tid: str) -> dict | None:
            if tid == "T-2114":
                return {
                    "state": "queued",
                    "scope": ["src/a.py"],
                    "blocked_by": ["T-0001"],
                }
            if tid == "T-0001":
                return {"state": "done", "scope": [], "blocked_by": []}
            return None

        monkeypatch.setattr(fleet_status, "ticket_frontmatter_on_main", fake_main)
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        readiness = fleet_status.ticket_readiness("T-2114")
        assert readiness["open_blockers"] == []
        assert readiness["dispatchable"] is True


class TestScopeLeaseCollisions:
    """`fleet_status.scope_lease_collisions` / `_expand_scope_globs_to_paths`
    (T-2225)."""

    def _make_tree(self, tmp_path: Path) -> Path:
        (tmp_path / "src" / "frob" / "tickets").mkdir(parents=True)
        (tmp_path / "src" / "frob" / "tickets" / "_land.py").write_text(
            "x = 1\n", encoding="utf-8"
        )
        (tmp_path / "src" / "frob" / "app").mkdir(parents=True)
        (tmp_path / "src" / "frob" / "app" / "config.py").write_text(
            "y = 2\n", encoding="utf-8"
        )
        return tmp_path

    def test_glob_scope_collides_with_a_literal_lease_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2225 acceptance [1]/[2]: a glob scope entry (`src/frob/**`)
        colliding only after EXPANSION against the real filesystem with a
        live lease's literal scope file (`src/frob/tickets/_land.py`) is
        detected -- the measured incident this fixes: no lexical/string
        comparison of those two texts would ever match."""
        root = self._make_tree(tmp_path)
        monkeypatch.setattr(fleet_status, "REPO", root)
        monkeypatch.setattr(
            fleet_status,
            "lease_classification",
            lambda record: "live",
        )
        held = [
            {
                "ticket_id": "T-2215",
                "worktree": str(root),
                "scope": ["src/frob/tickets/_land.py"],
                "recorded_at": "2026-08-01T00:00:00+00:00",
            }
        ]
        collisions = fleet_status.scope_lease_collisions(
            "T-2220", ["src/frob/**"], held
        )
        assert len(collisions) == 1
        assert collisions[0]["ticket_id"] == "T-2215"
        assert any("_land.py" in p for p in collisions[0]["paths"])

    def test_no_collision_when_files_are_disjoint(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2225 acceptance [3]: a ticket whose scope files do not overlap
        any live lease's own MUST STILL report no collision (must-still-
        pass control against a fix that flags everything)."""
        root = self._make_tree(tmp_path)
        monkeypatch.setattr(fleet_status, "REPO", root)
        monkeypatch.setattr(fleet_status, "lease_classification", lambda record: "live")
        held = [
            {
                "ticket_id": "T-2215",
                "worktree": str(root),
                "scope": ["src/frob/tickets/_land.py"],
                "recorded_at": "2026-08-01T00:00:00+00:00",
            }
        ]
        collisions = fleet_status.scope_lease_collisions(
            "T-2220", ["src/frob/app/config.py"], held
        )
        assert collisions == []

    def test_a_reclaimable_lease_is_never_a_collision(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2225 acceptance [4]: a lease `lease_classification` calls
        reclaimable (or root-resident) is not held by anyone and must
        never count as a collision, even though its scope files
        genuinely overlap on disk -- reuses T-2222's own classification,
        never re-implements staleness rules here."""
        root = self._make_tree(tmp_path)
        monkeypatch.setattr(fleet_status, "REPO", root)
        monkeypatch.setattr(
            fleet_status, "lease_classification", lambda record: "reclaimable"
        )
        held = [
            {
                "ticket_id": "T-2215",
                "worktree": str(root),
                "scope": ["src/frob/tickets/_land.py"],
                "recorded_at": "2026-08-01T00:00:00+00:00",
            }
        ]
        collisions = fleet_status.scope_lease_collisions(
            "T-2220", ["src/frob/**"], held
        )
        assert collisions == []

    # frob:ticket T-2281
    def test_land_in_progress_ticket_with_no_lease_still_collides(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """(MUST FAIL FIRST) T-2281's measured incident: a ticket whose
        land is actively running holds NO lease (released locally before
        the squash reaches main) but its scope files are genuinely still
        contended. `land_ticket_ids` (from `land_invocations()`) is a
        SECOND occupancy source, independent of `held`; its scope is read
        from `main` since no lease exists to read it from."""
        root = self._make_tree(tmp_path)
        monkeypatch.setattr(fleet_status, "REPO", root)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: (
                {"state": "in-progress", "scope": ["src/frob/tickets/_land.py"]}
                if tid == "T-2254"
                else None
            ),
        )
        collisions = fleet_status.scope_lease_collisions(
            "T-2220", ["src/frob/**"], [], land_ticket_ids=["T-2254"]
        )
        assert len(collisions) == 1
        assert collisions[0]["ticket_id"] == "T-2254"
        assert any("_land.py" in p for p in collisions[0]["paths"])

    # frob:ticket T-2281
    def test_land_ticket_disjoint_scope_is_not_a_collision(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-STILL-PASS: a ticket with a land in flight whose scope
        does NOT overlap must still report no collision -- a fix that
        treats every in-flight land as blocking every dispatch would
        recreate an unreclaimable-lease-class defect from the opposite
        side."""
        root = self._make_tree(tmp_path)
        monkeypatch.setattr(fleet_status, "REPO", root)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: (
                {"state": "in-progress", "scope": ["src/frob/tickets/_land.py"]}
                if tid == "T-2254"
                else None
            ),
        )
        collisions = fleet_status.scope_lease_collisions(
            "T-2220", ["src/frob/app/config.py"], [], land_ticket_ids=["T-2254"]
        )
        assert collisions == []

    # frob:ticket T-2281
    def test_land_ticket_id_matching_a_live_lease_is_not_double_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ticket present in BOTH a live lease AND `land_ticket_ids`
        (a lease that has not yet been released, mid-land) is reported
        ONCE, from the lease path -- never twice."""
        root = self._make_tree(tmp_path)
        monkeypatch.setattr(fleet_status, "REPO", root)
        monkeypatch.setattr(fleet_status, "lease_classification", lambda record: "live")
        held = [
            {
                "ticket_id": "T-2254",
                "worktree": str(root),
                "scope": ["src/frob/tickets/_land.py"],
                "recorded_at": "2026-08-01T00:00:00+00:00",
            }
        ]
        collisions = fleet_status.scope_lease_collisions(
            "T-2220", ["src/frob/**"], held, land_ticket_ids=["T-2254"]
        )
        assert len(collisions) == 1

    # frob:ticket T-2281
    def test_the_ticket_s_own_id_in_land_ticket_ids_is_never_self_collision(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ticket's own id appearing in `land_ticket_ids` (it is itself
        actively landing right now) must never be reported as colliding
        with itself."""
        root = self._make_tree(tmp_path)
        monkeypatch.setattr(fleet_status, "REPO", root)
        collisions = fleet_status.scope_lease_collisions(
            "T-2220", ["src/frob/**"], [], land_ticket_ids=["T-2220"]
        )
        assert collisions == []


class TestTicketReadinessScopeCollision:
    """`fleet_status.ticket_readiness`'s scope-collision integration
    (T-2225)."""

    def test_not_dispatchable_when_scope_files_are_held_by_another_live_lease(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2225's own reproduction: `--ticket` on a ticket whose scope
        files are held by another ticket's live lease must report the
        collision and `dispatchable: False` -- fails today: prints
        `lease: none` / `dispatchable: True`."""
        (tmp_path / "src" / "frob" / "tickets").mkdir(parents=True)
        (tmp_path / "src" / "frob" / "tickets" / "_land.py").write_text(
            "x = 1\n", encoding="utf-8"
        )
        monkeypatch.setattr(fleet_status, "REPO", tmp_path)
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda tid: None)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "queued", "scope": ["src/frob/**"], "blocked_by": []},
        )
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        monkeypatch.setattr(
            fleet_status,
            "leases",
            lambda: [
                {
                    "ticket_id": "T-2215",
                    "worktree": str(tmp_path),
                    "scope": ["src/frob/tickets/_land.py"],
                    "recorded_at": "2026-08-01T00:00:00+00:00",
                }
            ],
        )
        monkeypatch.setattr(fleet_status, "lease_classification", lambda record: "live")
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        readiness = fleet_status.ticket_readiness("T-2220")
        assert readiness["scope_lease_collisions"] != []
        assert readiness["dispatchable"] is False

    def test_dispatchable_when_no_colliding_lease(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Must-still-pass control: a ticket whose scope files are held
        by no one still reports dispatchable."""
        (tmp_path / "src" / "frob" / "app").mkdir(parents=True)
        (tmp_path / "src" / "frob" / "app" / "config.py").write_text(
            "y = 2\n", encoding="utf-8"
        )
        monkeypatch.setattr(fleet_status, "REPO", tmp_path)
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda tid: None)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {
                "state": "queued",
                "scope": ["src/frob/app/config.py"],
                "blocked_by": [],
            },
        )
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        readiness = fleet_status.ticket_readiness("T-2114")
        assert readiness["scope_lease_collisions"] == []
        assert readiness["dispatchable"] is True


# frob:ticket T-2172
class TestFleetStatusMain:
    """`fleet_status.main`."""

    def test_exit_zero_when_clean(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A clean root, with no leases/worktrees, exits 0."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(sys, "argv", ["fleet_status.py"])
        assert fleet_status.main() == 0
        assert "CLEAN" in capsys.readouterr().out

    def test_exit_one_when_dirty(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Any dirt line exits 1 and is echoed under a DIRTY banner."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [" M x.py"])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(sys, "argv", ["fleet_status.py"])
        assert fleet_status.main() == 1
        out = capsys.readouterr().out
        assert "DIRTY" in out
        assert " M x.py" in out

    # frob:ticket T-2133
    def test_ticket_flag_exits_one_when_not_dispatchable(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A clean root but a NOT-dispatchable `--ticket` still exits 1,
        with the reason (a live lease) printed -- T-2133's own exit-code
        gate, so this can drive a dispatch loop without prose parsing."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(
            fleet_status,
            "ticket_readiness",
            lambda tid: {
                "ticket_id": tid,
                "lease": {
                    "recorded_at": "2026-08-01T00:00:00+00:00",
                    "worktree": "/w",
                    "scope": ["src/a.py"],
                },
                "main": {"state": "in-progress", "scope": ["src/a.py"]},
                "scope_diverges": False,
                "worktrees_with_commits": [],
                "dispatchable": False,
            },
        )
        monkeypatch.setattr(sys, "argv", ["fleet_status.py", "--ticket", "T-2114"])
        assert fleet_status.main() == 1
        out = capsys.readouterr().out
        assert "TICKET T-2114" in out
        assert "dispatchable: False" in out

    # frob:ticket T-2133
    def test_ticket_flag_exits_zero_when_dispatchable(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A clean root and a dispatchable `--ticket` exits 0."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(
            fleet_status,
            "ticket_readiness",
            lambda tid: {
                "ticket_id": tid,
                "lease": None,
                "main": {"state": "queued", "scope": ["src/a.py"]},
                "scope_diverges": False,
                "worktrees_with_commits": [],
                "dispatchable": True,
            },
        )
        monkeypatch.setattr(sys, "argv", ["fleet_status.py", "--ticket", "T-2114"])
        assert fleet_status.main() == 0
        assert "dispatchable: True" in capsys.readouterr().out

    # frob:ticket T-2172
    def test_ticket_readiness_prints_before_the_general_report(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`TICKET <id>` prints FIRST, ahead of `ROOT` -- the coordinator's
        own report that a per-ticket answer was buried below the general
        fleet report; `--ticket` exists precisely to be the first thing
        read."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(
            fleet_status,
            "ticket_readiness",
            lambda tid: {
                "ticket_id": tid,
                "lease": None,
                "main": {"state": "queued", "scope": ["src/a.py"]},
                "scope_diverges": False,
                "worktrees_with_commits": [],
                "dispatchable": True,
            },
        )
        monkeypatch.setattr(sys, "argv", ["fleet_status.py", "--ticket", "T-2114"])
        fleet_status.main()
        out = capsys.readouterr().out
        assert out.index("TICKET T-2114") < out.index("ROOT")


# frob:ticket T-2172
class TestPrintTicketReadiness:
    """`fleet_status._print_ticket_readiness` (ARCH001/ARCH103 split,
    T-2172)."""

    # frob:ticket T-2172
    def test_prints_dispatchable_true(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A dispatchable, no-lease readiness dict prints the plain shape
        and returns True."""
        readiness = {
            "ticket_id": "T-2114",
            "lease": None,
            "main": {"state": "queued", "scope": ["src/a.py"]},
            "scope_diverges": False,
            "worktrees_with_commits": [],
            "dispatchable": True,
        }
        assert fleet_status._print_ticket_readiness(readiness) is True
        out = capsys.readouterr().out
        assert "TICKET T-2114" in out
        assert "lease: none" in out
        assert "dispatchable: True" in out

    # frob:ticket T-2172
    def test_prints_lease_scope_divergence_and_sibling_commits(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A held lease, a scope divergence, and sibling-branch commits
        each print their own dedicated line, and the function returns
        False (not dispatchable)."""
        readiness = {
            "ticket_id": "T-2114",
            "lease": {
                "recorded_at": "2026-08-01T00:00:00+00:00",
                "worktree": "/w",
                "scope": ["src/a.py"],
            },
            "main": {"state": "in-progress", "scope": ["src/a.py", "src/b.py"]},
            "scope_diverges": True,
            "worktrees_with_commits": ["sibling"],
            "dispatchable": False,
        }
        assert fleet_status._print_ticket_readiness(readiness) is False
        out = capsys.readouterr().out
        assert "lease: recorded_at=2026-08-01T00:00:00+00:00" in out
        assert "SCOPE DIVERGES" in out
        assert "ALREADY IMPLEMENTED on: sibling" in out
        assert "dispatchable: False" in out


# frob:ticket T-2172
# frob:ticket T-2654
class TestPrintFleetReport:
    """`fleet_status._print_fleet_report` (ARCH001/ARCH103 split,
    T-2172)."""

    # frob:ticket T-2172
    # frob:ticket T-2180
    def test_prints_all_four_sections(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """ROOT, LANDS, QUARANTINE, LEASES, and WORKTREES each print their
        own section, in that order (T-2180 added LANDS between ROOT and
        QUARANTINE)."""
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("clear", 0))
        monkeypatch.setattr(
            fleet_status,
            "leases",
            lambda: [{"ticket_id": "T-2114", "worktree": "/w/t-2114"}],
        )
        monkeypatch.setattr(
            fleet_status, "worktrees", lambda idle_seconds: [("one", 10, False)]
        )
        fleet_status._print_fleet_report([" M x.py"], idle_seconds=1200)
        out = capsys.readouterr().out
        assert out.index("ROOT") < out.index("QUARANTINE") < out.index("LEASES")
        assert out.index("LEASES") < out.index("WORKTREES")
        assert "DIRTY" in out and " M x.py" in out

    # frob:ticket T-2222
    # frob:ticket T-2654
    def test_leases_section_shows_classification_per_lease(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2222: each LEASES row prints its own `lease_classification`
        verdict, and the section header shows the LIVE count alongside
        the raw total -- a reclaimable lease (path-gone here) never reads
        indistinguishably from a live one."""
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("clear", 0))
        monkeypatch.setattr(
            fleet_status,
            "leases",
            lambda: [{"ticket_id": "T-2114", "worktree": "/does/not/exist"}],
        )
        monkeypatch.setattr(fleet_status, "in_progress_ticket_scope_leases", lambda: [])
        monkeypatch.setattr(fleet_status, "blocked_in_progress_leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        fleet_status._print_fleet_report([], idle_seconds=1200)
        out = capsys.readouterr().out
        assert "LEASES 1 (0 live, 0 leaked, 0 blocked-open)" in out
        assert "T-2114 -> exist  [reclaimable]" in out

    # frob:ticket T-2654
    def test_leases_section_reports_ledger_leak_missing_from_held(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2651: an in-progress ticket `in_progress_ticket_scope_leases`
        finds with no resolvable worktree, and that `leases()` (file-
        based) never held at all, still prints in the LEASES section,
        flagged LEAK -- the missing case this ticket fixes."""
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("clear", 0))
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(
            fleet_status,
            "in_progress_ticket_scope_leases",
            lambda: [
                {
                    "ticket_id": "T-2377",
                    "scope": ["docs/modules/gates.md"],
                    "worktree": None,
                    "leaked": True,
                }
            ],
        )
        monkeypatch.setattr(fleet_status, "blocked_in_progress_leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        fleet_status._print_fleet_report([], idle_seconds=1200)
        out = capsys.readouterr().out
        assert "LEASES 1 (0 live, 1 leaked, 0 blocked-open)" in out
        assert "T-2377 -> <no worktree>  [LEAK]" in out

    # frob:ticket T-2654
    def test_leases_section_flags_blocked_open_lease(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2654: a held lease for an in-progress ticket whose
        `blocked_by` still names an open blocker gets a distinct
        `[BLOCKED-OPEN: ...]` suffix, and the header's `blocked-open`
        count reflects it -- the T-2377 shape, this time WITH a live
        lease held so it is not also a LEAK."""
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("clear", 0))
        monkeypatch.setattr(
            fleet_status,
            "leases",
            lambda: [{"ticket_id": "T-2377", "worktree": "/w/t-2377"}],
        )
        monkeypatch.setattr(fleet_status, "in_progress_ticket_scope_leases", lambda: [])
        monkeypatch.setattr(
            fleet_status,
            "blocked_in_progress_leases",
            lambda: [{"ticket_id": "T-2377", "open_blockers": ["T-2568"]}],
        )
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        fleet_status._print_fleet_report([], idle_seconds=1200)
        out = capsys.readouterr().out
        assert "LEASES 1 (0 live, 0 leaked, 1 blocked-open)" in out
        assert "T-2377 -> t-2377" in out
        assert "[BLOCKED-OPEN: T-2568]" in out


class TestRottingTickets:
    """`fleet_status.rotting_tickets` (T-2182)."""

    def test_flags_a_ticket_past_its_priority_threshold(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A queued CRITICAL ticket older than its own 3-day threshold is
        reported, with age and threshold both present -- this MUST fail
        against current main (rotting_tickets does not exist there)."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir,
            "T-0001",
            state="queued",
            priority="critical",
            created="2020-01-01",
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        monkeypatch.setattr(
            fleet_status,
            "_rot_day_thresholds",
            lambda: {"critical": 3, "high": 7, "medium": 30, "low": 90},
        )
        rotting = fleet_status.rotting_tickets()
        assert len(rotting) == 1
        assert rotting[0]["id"] == "T-0001"
        assert rotting[0]["priority"] == "critical"
        assert rotting[0]["threshold_days"] == 3
        assert rotting[0]["age_days"] > 3

    def test_ignores_tickets_still_under_threshold(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ticket created today never rots, regardless of priority."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir,
            "T-0002",
            state="queued",
            priority="critical",
            created=date.today().isoformat(),
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        assert fleet_status.rotting_tickets() == []

    def test_only_queued_and_planned_states_are_considered(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An old ticket that is in-progress/done/dropped/blocked is NOT
        rotting -- TICK004's own selection (only queued/planned) is
        mirrored exactly, not a broader 'any old ticket' sweep."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir,
            "T-0003",
            state="in-progress",
            priority="critical",
            created="2020-01-01",
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        assert fleet_status.rotting_tickets() == []

    def test_distinguishes_epic_and_story_tier_from_ticket_tier(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rotting tickets, stories, and epics are all reported (epics are
        NOT exempted) with their own `tier` field intact, so a caller can
        split them by required action."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir,
            "T-0004",
            state="queued",
            priority="critical",
            created="2020-01-01",
            tier="ticket",
        )
        _write_ticket(
            tickets_dir,
            "T-0005",
            state="queued",
            priority="critical",
            created="2020-01-01",
            tier="epic",
        )
        _write_ticket(
            tickets_dir,
            "T-0006",
            state="planned",
            priority="critical",
            created="2020-01-01",
            tier="story",
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        rotting = fleet_status.rotting_tickets()
        tiers = {t["id"]: t["tier"] for t in rotting}
        assert tiers == {"T-0004": "ticket", "T-0005": "epic", "T-0006": "story"}

    def test_reads_runs_last_as_a_structured_field_not_from_title(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2200: `runs_last` comes from the ledger frontmatter's own
        `runs_last:` line, never inferred from `title` text -- a ticket
        whose title literally says 'RUNS LAST' (mirroring T-1614's real
        title) but whose `runs_last:` line is `false` must read as an
        ordinary (non-deferred) rotting ticket, and vice versa."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir,
            "T-0007",
            state="queued",
            priority="critical",
            created="2020-01-01",
            runs_last=True,
        )
        _write_ticket(
            tickets_dir,
            "T-0008",
            state="queued",
            priority="critical",
            created="2020-01-01",
            runs_last=False,
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        rotting = fleet_status.rotting_tickets()
        flags = {t["id"]: t["runs_last"] for t in rotting}
        assert flags == {"T-0007": True, "T-0008": False}

    # frob:ticket T-2229
    def test_epic_with_active_child_is_flagged_has_active_child(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2229's measured incident: T-1623 (epic, rotting) had children
        T-2223/T-2224 in-progress on main. `has_active_child` must read
        `True` for the epic -- the child need not itself be rotting."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir,
            "T-1623",
            state="queued",
            priority="critical",
            created="2020-01-01",
            tier="epic",
        )
        _write_ticket(
            tickets_dir,
            "T-2223",
            state="in-progress",
            priority="high",
            created=date.today().isoformat(),
            parent="T-1623",
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        rotting = fleet_status.rotting_tickets()
        by_id = {t["id"]: t for t in rotting}
        assert by_id["T-1623"]["has_active_child"] is True

    # frob:ticket T-2229
    def test_epic_with_no_children_at_all_is_not_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-STILL-PASS: a genuinely undecomposed epic (no children at
        all) must still read `has_active_child=False` -- it keeps rotting
        under the ordinary message."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir,
            "T-0009",
            state="queued",
            priority="critical",
            created="2020-01-01",
            tier="epic",
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        rotting = fleet_status.rotting_tickets()
        assert rotting[0]["has_active_child"] is False

    # frob:ticket T-2229
    def test_epic_whose_only_child_is_terminal_is_not_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A child that is `done`/`dropped` does NOT count as active --
        an epic whose decomposition is fully finished (or whose only
        child was dropped) is not 'being worked', it is either finished
        or genuinely stalled again."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir,
            "T-0010",
            state="queued",
            priority="critical",
            created="2020-01-01",
            tier="epic",
        )
        _write_ticket(
            tickets_dir,
            "T-0011",
            state="done",
            priority="high",
            created=date.today().isoformat(),
            parent="T-0010",
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        rotting = fleet_status.rotting_tickets()
        assert rotting[0]["has_active_child"] is False

    # frob:ticket T-2449
    def test_archived_done_blockers_do_not_keep_a_ticket_permanently_blocked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2449's own reproduction of the T-1696 incident: a rotting
        leaf ticket names two blockers that are both DONE and ARCHIVED.
        MUST-NOW-DISPATCH: `open_blockers`/`unresolved_blockers` must
        both read empty, exactly reversing the pre-fix 'BLOCKED BY (still
        open): T-1692, T-1693' misdiagnosis."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir / "archive",
            "T-1692",
            state="done",
            priority="critical",
        )
        _write_ticket(
            tickets_dir / "archive",
            "T-1693",
            state="done",
            priority="critical",
        )
        _write_ticket(
            tickets_dir,
            "T-1696",
            state="queued",
            priority="high",
            created="2020-01-01",
            blocked_by=("T-1692", "T-1693"),
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        rotting = fleet_status.rotting_tickets()
        assert len(rotting) == 1
        assert rotting[0]["id"] == "T-1696"
        assert rotting[0]["open_blockers"] == []
        assert rotting[0]["unresolved_blockers"] == []

    # frob:ticket T-2449
    def test_a_genuinely_open_blocker_still_blocks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-STILL-BLOCK control: a blocker that is neither done nor
        dropped still reports as open -- this fix must never simply stop
        checking blocked_by."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(tickets_dir, "T-5000", state="in-progress", priority="critical")
        _write_ticket(
            tickets_dir,
            "T-5001",
            state="queued",
            priority="high",
            created="2020-01-01",
            blocked_by=("T-5000",),
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        rotting = fleet_status.rotting_tickets()
        assert rotting[0]["open_blockers"] == ["T-5000"]
        assert rotting[0]["unresolved_blockers"] == []


class TestPrintTicketRot:
    """`fleet_status._print_ticket_rot` (T-2182)."""

    # frob:ticket T-2449
    def test_blocked_leaf_never_appears_under_needs_dispatch(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2449 acceptance [3]: a leaf ticket with a still-open (or
        unresolved) blocker must print under 'BLOCKED (dependency not
        yet resolved)', never under 'NEEDS DISPATCH' -- this is the exact
        structural shape T-1696 had (rot alarm demanding dispatch while
        `ticket_readiness` refused it three ticks running)."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-1696",
                    "priority": "high",
                    "tier": "ticket",
                    "state": "queued",
                    "age_days": 12,
                    "threshold_days": 7,
                    "open_blockers": ["T-1692"],
                    "unresolved_blockers": [],
                },
                {
                    "id": "T-2000",
                    "priority": "high",
                    "tier": "ticket",
                    "state": "queued",
                    "age_days": 12,
                    "threshold_days": 7,
                    "open_blockers": [],
                    "unresolved_blockers": [],
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "TICKET ROT: 2" in out
        assert "NEEDS DISPATCH (1):" in out
        assert "BLOCKED (dependency not yet resolved) (1):" in out
        assert "T-1696" not in out.split("BLOCKED (dependency")[0]
        assert "T-1696" in out.split("BLOCKED (dependency")[1]
        assert "T-2000" in out.split("BLOCKED (dependency")[0]

    # frob:ticket T-2449
    def test_unresolved_blocker_also_keeps_leaf_out_of_needs_dispatch(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """An UNRESOLVED (not just open) blocker also excludes a leaf from
        NEEDS DISPATCH -- fail-loudly, T-2391: 'cannot confirm' is never
        treated as 'safe to dispatch'."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-3000",
                    "priority": "high",
                    "tier": "ticket",
                    "state": "queued",
                    "age_days": 12,
                    "threshold_days": 7,
                    "open_blockers": [],
                    "unresolved_blockers": ["T-9999"],
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "NEEDS DISPATCH" not in out
        assert "BLOCKED (dependency not yet resolved) (1):" in out
        assert "T-3000" in out

    def test_splits_by_tier_under_distinct_action_headings(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A leaf ticket prints under 'NEEDS DISPATCH'; an epic/story
        prints under 'NEEDS DECOMPOSITION' -- two distinct headings naming
        the required action, never one undifferentiated count (T-0411/
        T-2182's own incident: 10 of 15 rotting tickets were epics, only
        4 leaf tickets, and reporting them as one count read as noise for
        a whole session)."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-0004",
                    "priority": "critical",
                    "tier": "ticket",
                    "state": "queued",
                    "age_days": 20,
                    "threshold_days": 3,
                },
                {
                    "id": "T-0005",
                    "priority": "critical",
                    "tier": "epic",
                    "state": "queued",
                    "age_days": 20,
                    "threshold_days": 3,
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "TICKET ROT: 2" in out
        assert "NEEDS DISPATCH (1):" in out
        assert "NEEDS DECOMPOSITION (1):" in out
        assert "T-0004" in out.split("NEEDS DECOMPOSITION")[0]
        assert "T-0005" in out.split("NEEDS DECOMPOSITION")[1]

    # frob:ticket T-2229
    def test_decomposed_epic_prints_under_its_own_heading_not_needs_decomposition(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2229's measured incident: an epic already decomposed (a
        non-terminal child ticket exists) must print under 'DECOMPOSED,
        BEING WORKED', never under 'NEEDS DECOMPOSITION' -- and must
        still be reported (never dropped), same as the runs_last
        precedent."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-0005",
                    "priority": "critical",
                    "tier": "epic",
                    "state": "queued",
                    "age_days": 20,
                    "threshold_days": 3,
                    "has_active_child": False,
                },
                {
                    "id": "T-1623",
                    "priority": "critical",
                    "tier": "epic",
                    "state": "queued",
                    "age_days": 11,
                    "threshold_days": 3,
                    "has_active_child": True,
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "TICKET ROT: 2" in out
        assert "NEEDS DECOMPOSITION (1):" in out
        assert "DECOMPOSED, BEING WORKED (1):" in out
        assert "T-0005" in out.split("DECOMPOSED, BEING WORKED")[0]
        assert "T-1623" in out.split("DECOMPOSED, BEING WORKED")[1]

    # frob:ticket T-2468
    def test_epic_all_terminal_children_prints_under_needs_close(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2468 acceptance [0]: an epic whose children are all terminal
        (T-1135's exact shape -- one child, T-1197, done and archived)
        must print under 'NEEDS CLOSE', never under 'NEEDS
        DECOMPOSITION' -- the epic's own work is finished, it needs a
        rollup Done report and a close, not more decomposition."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-1135",
                    "priority": "high",
                    "tier": "epic",
                    "state": "queued",
                    "age_days": 20,
                    "threshold_days": 3,
                    "has_active_child": False,
                    "has_any_child": True,
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "TICKET ROT: 1" in out
        assert "NEEDS CLOSE (1):" in out
        assert "T-1135" in out
        assert "NEEDS DECOMPOSITION" not in out

    # frob:ticket T-2475
    def test_blocked_story_with_terminal_child_prints_under_blocked_not_needs_close(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2475 positive control: T-1599's live shape -- tier=story,
        one archived-done child (so `has_active_child=False`,
        `has_any_child=True`, the exact NEEDS CLOSE trigger from T-2468's
        own test above) but an open `blocked_by` edge naming a still-open
        id. This must NOT print under NEEDS CLOSE -- there is no rollup
        to write, the other deliverables are still blocked -- it must
        print under BLOCKED (dependency not yet resolved) instead, with
        its tier disclosed even though a blocked LEAF ticket in the same
        bucket has no tier of its own (T-2475's per-ticket tier-display
        fix)."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-1599",
                    "priority": "high",
                    "tier": "story",
                    "state": "queued",
                    "age_days": 20,
                    "threshold_days": 3,
                    "has_active_child": False,
                    "has_any_child": True,
                    "open_blockers": ["T-2411"],
                    "unresolved_blockers": [],
                },
                {
                    "id": "T-2000",
                    "priority": "high",
                    "tier": "ticket",
                    "state": "queued",
                    "age_days": 12,
                    "threshold_days": 7,
                    "open_blockers": ["T-2001"],
                    "unresolved_blockers": [],
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "TICKET ROT: 2" in out
        assert "NEEDS CLOSE" not in out
        assert "BLOCKED (dependency not yet resolved) (2):" in out
        blocked_section = out.split("BLOCKED (dependency")[1]
        assert "T-1599 tier=story" in blocked_section
        assert "T-2000 priority=" in blocked_section

    # frob:ticket T-2468
    def test_epic_with_no_children_at_all_still_prints_under_needs_decomposition(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2468 acceptance [1]: an epic with NO children at all (never
        decomposed) still reports under 'NEEDS DECOMPOSITION' -- the
        NEEDS CLOSE split must not empty this bucket by
        reclassification, only siphon off the genuinely-finished case."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-9000",
                    "priority": "high",
                    "tier": "epic",
                    "state": "queued",
                    "age_days": 20,
                    "threshold_days": 3,
                    "has_active_child": False,
                    "has_any_child": False,
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "TICKET ROT: 1" in out
        assert "NEEDS DECOMPOSITION (1):" in out
        assert "T-9000" in out
        assert "NEEDS CLOSE" not in out

    def test_runs_last_ticket_gets_its_own_deferred_bucket_not_needs_dispatch(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2200: a rotting leaf ticket with `runs_last=True` (T-1614's
        real shape) is reported under 'DEFERRED (RUNS LAST)', never under
        'NEEDS DISPATCH' -- `frob ticket start` structurally refuses a
        `runs_last` ticket with `RunsLastBlocked`, so listing it as
        dispatchable is advice the tool itself rejects. This MUST fail
        against the pre-fix report, which had no third bucket at all and
        put every leaf ticket -- runs_last or not -- under NEEDS DISPATCH.
        The must-still-pass control lives alongside it: an ordinary
        (non-runs_last) rotting leaf ticket still appears under NEEDS
        DISPATCH, unaffected."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-1614",
                    "priority": "high",
                    "tier": "ticket",
                    "state": "queued",
                    "age_days": 11,
                    "threshold_days": 7,
                    "runs_last": True,
                },
                {
                    "id": "T-0004",
                    "priority": "critical",
                    "tier": "ticket",
                    "state": "queued",
                    "age_days": 20,
                    "threshold_days": 3,
                    "runs_last": False,
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "TICKET ROT: 2" in out
        assert "NEEDS DISPATCH (1):" in out
        assert "DEFERRED (RUNS LAST) (1):" in out
        # T-1614 must NOT be listed under NEEDS DISPATCH.
        needs_dispatch_block = out.split("DEFERRED (RUNS LAST)")[0]
        assert "T-1614" not in needs_dispatch_block
        assert "T-0004" in needs_dispatch_block
        deferred_block = out.split("DEFERRED (RUNS LAST)")[1]
        assert "T-1614" in deferred_block
        assert "RunsLastBlocked" in deferred_block


class TestQuarantineState:
    """`fleet_status.quarantine_state` (T-2049)."""

    def test_reports_raised_with_undisposed_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An uncleared record reports 'raised' plus the count of findings
        with an empty (undisposed) `disposition`."""
        store = tmp_path / "quarantine.json"
        store.write_text(
            json.dumps(
                {
                    "cleared_at": None,
                    "findings": [
                        {"disposition": ""},
                        {"disposition": "filed"},
                        {"disposition": ""},
                    ],
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(fleet_status, "QUARANTINE", store)
        assert fleet_status.quarantine_state() == ("raised", 2)

    def test_reports_clear_when_store_says_cleared(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A record with `cleared_at` set is 'clear', regardless of its
        (now-historical) findings list."""
        store = tmp_path / "quarantine.json"
        store.write_text(
            json.dumps({"cleared_at": "2026-01-01T00:00:00+00:00", "findings": []}),
            encoding="utf-8",
        )
        monkeypatch.setattr(fleet_status, "QUARANTINE", store)
        assert fleet_status.quarantine_state() == ("clear", 0)

    def test_reports_clear_when_no_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No quarantine has ever been raised (missing store) is 'clear'."""
        monkeypatch.setattr(
            fleet_status, "QUARANTINE", tmp_path / "does-not-exist.json"
        )
        assert fleet_status.quarantine_state() == ("clear", 0)

    def test_unreadable_store_is_unknown_never_clear(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Malformed JSON is 'unknown', never misread as 'clear' -- an
        unreadable store must never look like a green light to dispatch."""
        store = tmp_path / "quarantine.json"
        store.write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(fleet_status, "QUARANTINE", store)
        assert fleet_status.quarantine_state() == ("unknown", 0)

    def test_non_dict_record_is_unknown(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Valid JSON that is not an object (e.g. a bare list) is 'unknown',
        not misparsed as a clear/empty record."""
        store = tmp_path / "quarantine.json"
        store.write_text("[]", encoding="utf-8")
        monkeypatch.setattr(fleet_status, "QUARANTINE", store)
        assert fleet_status.quarantine_state() == ("unknown", 0)


# frob:ticket T-2126
class TestVerifyQueueState:
    """`fleet_status.verify_queue_state` (T-2126, symmetric to
    `quarantine_state`/T-2049)."""

    # frob:ticket T-2126
    def test_reports_depth_and_oldest_age(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/coordinator_suite/test_fleet_report.py::TestVerifyQueueState.test_\
        # reports_depth_and_oldest_age
        """(MUST FAIL FIRST on main -- `verify_queue_state` does not exist
        yet): depth is the entry count, oldest_age_s is the OLDEST
        `enqueued_at` entry's age (the entry a coordinator most needs to
        know about, not the newest)."""
        store = tmp_path / "verify-queue.json"
        now = datetime(2026, 1, 1, tzinfo=UTC)
        store.write_text(
            json.dumps(
                [
                    {"enqueued_at": "2026-01-01T00:00:00+00:00"},  # 0s old
                    {"enqueued_at": "2025-12-31T23:00:00+00:00"},  # 3600s old
                ]
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(fleet_status, "VERIFY_QUEUE", store)
        depth, oldest_age_s = fleet_status.verify_queue_state(now=now)
        assert depth == 2
        assert oldest_age_s == pytest.approx(3600.0)

    # frob:ticket T-2126
    def test_zero_depth_when_no_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/coordinator_suite/test_fleet_report.py::TestVerifyQueueState.test_\
        # zero_depth_when_no_file
        """MUST-STILL-PASS control: no queue file at all means nothing is
        queued -- `(0, None)`, not `(-1, None)` (the unreadable case)."""
        monkeypatch.setattr(
            fleet_status, "VERIFY_QUEUE", tmp_path / "does-not-exist.json"
        )
        assert fleet_status.verify_queue_state() == (0, None)

    # frob:ticket T-2126
    def test_unreadable_queue_is_unknown_never_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/coordinator_suite/test_fleet_report.py::TestVerifyQueueState.test_\
        # unreadable_queue_is_unknown_never_zero
        """Malformed JSON is `(-1, None)`, never misread as `(0, None)` --
        mirrors `quarantine_state`'s own "cannot verify is never
        verified" posture: an unreadable store must never look like an
        empty, safe-to-dispatch queue."""
        store = tmp_path / "verify-queue.json"
        store.write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(fleet_status, "VERIFY_QUEUE", store)
        assert fleet_status.verify_queue_state() == (-1, None)


# frob:ticket T-2126
class TestFleetStatusMainVerifyQueue:
    """`fleet_status.main`'s VERIFY QUEUE line (T-2126)."""

    # frob:ticket T-2126
    def test_prints_depth_and_age_when_nonempty(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests \
        # tests/unit/coordinator_suite/test_fleet_report.py::TestFleetStatusMainVerifyQ\
        # ueue.test_prints_depth_and_age_when_nonempty
        """A nonzero queue depth is printed with its age, next to
        QUARANTINE -- symmetric to T-2049's own quarantine-line placement
        test above."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("clear", 0))
        monkeypatch.setattr(fleet_status, "verify_queue_state", lambda: (3, 1234.0))
        monkeypatch.setattr(sys, "argv", ["fleet_status.py"])
        fleet_status.main()
        out = capsys.readouterr().out
        assert "VERIFY QUEUE depth=3" in out
        assert "1234s old" in out

    # frob:ticket T-2126
    def test_prints_empty_when_zero_depth(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests \
        # tests/unit/coordinator_suite/test_fleet_report.py::TestFleetStatusMainVerifyQ\
        # ueue.test_prints_empty_when_zero_depth
        """MUST-STILL-PASS control: a zero-depth queue is reported as
        empty, not silently omitted."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("clear", 0))
        monkeypatch.setattr(fleet_status, "verify_queue_state", lambda: (0, None))
        monkeypatch.setattr(sys, "argv", ["fleet_status.py"])
        fleet_status.main()
        out = capsys.readouterr().out
        assert "VERIFY QUEUE empty" in out


class TestFleetStatusMainQuarantine:
    """`fleet_status.main`'s quarantine line (T-2049)."""

    def test_prints_raised_with_undisposed_count_and_consequence(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A raised quarantine is printed with its undisposed count and the
        deferred-landing consequence -- the whole point of T-2049 is that
        this line appears in the ONE place already read before dispatch."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("raised", 2))
        monkeypatch.setattr(sys, "argv", ["fleet_status.py"])
        fleet_status.main()
        out = capsys.readouterr().out
        assert "QUARANTINE RAISED" in out
        assert "2" in out
        assert "synchronous" in out

    def test_prints_clear(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A clear quarantine is reported plainly, not silently omitted."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("clear", 0))
        monkeypatch.setattr(sys, "argv", ["fleet_status.py"])
        fleet_status.main()
        out = capsys.readouterr().out
        assert "QUARANTINE clear" in out

    def test_prints_unknown_as_unsafe(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """An unreadable store is reported as unknown/unsafe, never as
        clear."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("unknown", 0))
        monkeypatch.setattr(sys, "argv", ["fleet_status.py"])
        fleet_status.main()
        out = capsys.readouterr().out
        assert "QUARANTINE UNKNOWN" in out
        assert "clear" not in out.lower().split("quarantine unknown")[0]


class TestFleetStatusLarge001WaiverParses:
    """T-2845: scripts/fleet_status.py's frob:waive LARGE001 directive was
    corrected to record real cross-calls found between its four concerns
    (readiness->rot, readiness->procscan) and a monkeypatch-coupling risk
    that made an actual file split unsafe. This is a regression test for
    the directive-DSL parser hazard flagged this session (an embedded
    escaped quote in a frob:waive reason broke the comment DSL repo-wide):
    the multi-line corrected reason must still parse cleanly and still
    suppress LARGE001 for this file via the real arch gate + waiver
    machinery `frob check` itself uses.

    frob:tests tests/unit/coordinator_suite/test_fleet_report.py::TestFleetStatusLarge001WaiverParses.test_waiver_still_suppresses_large001
    """

    def test_waiver_still_suppresses_large001(self, tmp_path: Path) -> None:
        """arch_gate() + _apply_waivers() against a SCOPED fixture repo
        containing a real, byte-for-byte copy of scripts/fleet_status.py
        report zero KEPT LARGE001 findings for it -- proving the
        corrected, multi-line frob:quote(frob:waive reason) still parses
        as one directive and still binds, rather than silently
        regressing to a bare unwaived LARGE001 error the way a malformed
        directive would.

        T-3532: this used to `build_graph`/`arch_gate` the WHOLE live
        repo tree per test invocation, outside the T-3495 shared
        `frob_self_scan_heavy` artifacts and paying its own private
        multi-minute scan on a slow CI runner. The subject under test is
        the WAIVER-BINDING mechanism, not "does this repo have zero
        LARGE001 findings repo-wide" (that property belongs to
        `test_sys_gate_zero_violations` and friends, which already share
        `frob_self_scan_artifacts`) -- `arch_gate` also has no snapshot
        parameter to piggyback on that shared session fixture the way
        `test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses`
        (T-3532, `tests/test_gates.py`) now does for `perf_gate`. A
        SCOPED one-file fixture repo is the right substitute per this
        ticket's own accepted alternative: the real file's real waiver
        directive still binds through the real `arch_gate`/
        `_apply_waivers` machinery, at a cost of one small-tree AST parse
        instead of the whole repo."""
        from frob.gates._arch import arch_gate  # noqa: PLC0415
        from frob.gates._waive import _apply_waivers  # noqa: PLC0415
        from frob.graph import build_graph  # noqa: PLC0415

        repo_root = Path(__file__).resolve().parents[3]
        real_file = repo_root / "scripts" / "fleet_status.py"
        scoped_root = tmp_path / "scoped_repo"
        scoped_scripts = scoped_root / "scripts"
        scoped_scripts.mkdir(parents=True)
        (scoped_scripts / "fleet_status.py").write_text(
            real_file.read_text(encoding="utf-8"), encoding="utf-8"
        )
        snapshot = build_graph(scoped_root, tmp_path / "cache.db").danger_ok
        raw = arch_gate(scoped_root)
        kept, waived = _apply_waivers(raw, snapshot)
        kept_offenders = [
            v for v in kept if v.rule == "LARGE001" and "fleet_status.py" in v.file
        ]
        waived_offenders = [
            v for v in waived if v.rule == "LARGE001" and "fleet_status.py" in v.file
        ]
        assert kept_offenders == [], (
            f"unwaived LARGE001 on fleet_status.py: {kept_offenders}"
        )
        assert waived_offenders != [], (
            "expected fleet_status.py's LARGE001 to be waived"
        )


# frob:ticket T-2854
class TestOwnDocstringHasNoMalformedDirective:
    """T-2854: this file's own TestFleetStatusLarge001WaiverParses docstring
    used to contain an unescaped line ('frob:waive reason still parses as
    one directive and still binds,') that the directive DSL parses per-line
    -- a docstring is directive-scannable too (T-0342), and that line's
    SHAPE (starts with 'frob:<verb>') is indistinguishable from a genuine
    one-line directive, so it was reported as a MalformedDirective ('bad
    attribute syntax'). Fixed by wrapping the mention in the DSL's own
    `frob:quote(...)` escape (T-1970) rather than weakening the scanner --
    see tests/unit/graph/test_dsl_mention_escape.py::TestDocstringMention
    Escape for the escape mechanism's own isolated coverage. This test
    binds directly to THIS file's real content so a future edit re-
    introducing an unescaped directive-shaped docstring line here is
    caught immediately, not just in the synthetic fixture."""

    def test_no_malformed_directives_in_this_file(self) -> None:
        # frob:tests tests/unit/coordinator_suite/test_fleet_report.py::TestOwnDocstringHasNoMalformedDirective.test_no_malformed_directives_in_this_file  # noqa: E501
        from frob.graph.dsl import parse_directives  # noqa: PLC0415
        from frob.lang import parse_file  # noqa: PLC0415

        this_file = Path(__file__)
        parsed = parse_file(this_file).danger_ok
        _edges, malformed = parse_directives(parsed)
        assert malformed == (), (
            f"unescaped directive-shaped prose in {this_file.name}: {malformed}"
        )
