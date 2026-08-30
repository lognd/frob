"""T-0323: `frob ticket merge-driver %O %A %B` -- the git merge-driver entry
point for `tickets.md` (docs/modules/tickets-merge-driver.md#git-merge-driver).

Two layers, matching this repo's `test_ticket_land.py` style:

1. `TestMergeDriverHandler` calls `frob.app.ticket_runner._merge_driver`
   directly against synthetic base/ours/theirs temp files -- fast, no git
   subprocess.
2. `TestMergeDriverViaRealGit` registers the driver with real `git config`
   and `.gitattributes` in a fixture repo, then runs an ACTUAL `git merge`
   between two branches that each independently appended a ticket near the
   same line -- the exact false-conflict class this ticket exists to
   eliminate -- and asserts git reports a clean merge with both sides'
   tickets present, not a conflict requiring a human.

"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import _merge_driver
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    load_all,
    new_ticket,
    transition,
)
from frob.tickets._store import atomic_write, ledger_path, load_archive, write_ticket


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


def _spec(title: str) -> TicketSpec:
    return TicketSpec(title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT)


def _make_closeable(root: Path, ticket_id: str) -> None:
    """Drive `ticket_id` to a state `transition(..., DONE)` will accept:
    planned -> in-progress, evidence + Done report attached (T-1437,
    mirroring `test_ticket_land.py`'s identical helper)."""
    assert transition(root, ticket_id, TicketState.PLANNED).is_ok
    assert transition(root, ticket_id, TicketState.IN_PROGRESS).is_ok
    loaded = load_all(root)
    ticket = loaded.danger_ok[ticket_id]
    ticket = ticket.model_copy(
        update={
            "evidence": ("tests/test_x.py::test_ok",),
            "body": ticket.body + "\n## Done report\n\nevidence attached\n",
        }
    )
    assert write_ticket(root, ticket).is_ok


def _cfg(base: Path, ours: Path, theirs: Path, *, path: Path) -> AppConfig:
    return AppConfig(
        ticket_merge_base=base,
        ticket_merge_ours=ours,
        ticket_merge_theirs=theirs,
        ticket_path=path,
    )


class TestArchivedIdsForMergeDriver:
    """T-1437: `_archived_ids_for_merge_driver`'s own branch coverage,
    isolated from the full `_merge_driver` end-to-end path -- both the
    git-object resolution (covered by `TestMergeDriverViaRealGit`'s real
    `MERGE_HEAD` test) and the disk-read fallback for when there is no
    live merge in progress at all (this class)."""

    def test_not_mid_merge_falls_back_to_disk_based_archived_ids(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_ticket_merge_driver.py::TestArchivedIdsForMergeDriver.test_not_mid_merge_falls_back_to_disk_based_archived_ids  # noqa: E501
        # A real git repo with NO in-progress merge -- `git rev-parse
        # MERGE_HEAD` must fail (nonzero exit), and the helper must fall
        # back to the plain disk-based `_archived_ids(root)` rather than
        # silently returning "nothing archived".
        from frob.app.ticket_runner._land_cmd import _archived_ids_for_merge_driver

        root = tmp_path / "root"
        _git_init(root)
        atomic_write(ledger_path(root), "# Tickets\n\n")
        _commit_all(root, "init")

        created = new_ticket(root, _spec("Will be archived"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(root, tid)
        assert transition(root, tid, TicketState.DONE).is_ok
        from frob.tickets import archive

        archived = archive(root)
        assert archived.is_ok and archived.danger_ok == 1

        # No MERGE_HEAD exists at all right now -- confirm the precondition.
        no_merge_head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "MERGE_HEAD"],
            capture_output=True,
        )
        assert no_merge_head.returncode != 0

        result = _archived_ids_for_merge_driver(root)
        assert tid in result, (
            "the not-mid-merge fallback must still resolve the real, "
            "disk-current archived id set via the plain _archived_ids(root) "
            "read (T-1437 branch-coverage regression)"
        )


class TestMergeDriverHandler:
    """`_merge_driver` against synthetic %O/%A/%B files -- no git subprocess.

    frob:ticket T-1165
    """

    def test_disjoint_ids_both_survive_the_splice(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverHandler.test_disjoint_ids_both_survive_the_splice  # noqa: E501
        root = tmp_path / "root"
        root.mkdir()
        atomic_write(ledger_path(root), "# Tickets\n\n")

        ours_created = new_ticket(root, _spec("Ours-side ticket"))
        assert ours_created.is_ok
        ours_text = ledger_path(root).read_text()

        theirs_root = tmp_path / "theirs"
        theirs_root.mkdir()
        theirs_ticket = ours_created.danger_ok.model_copy(
            update={"id": "T-0002", "title": "Theirs-side ticket"}
        )
        atomic_write(ledger_path(theirs_root), "# Tickets\n\n")
        assert write_ticket(theirs_root, theirs_ticket).is_ok
        theirs_text = ledger_path(theirs_root).read_text()

        base = tmp_path / "base.md"
        ours = tmp_path / "ours.md"
        theirs = tmp_path / "theirs.md"
        base.write_text("# Tickets\n\n")
        ours.write_text(ours_text)
        theirs.write_text(theirs_text)

        # A clean splice returns normally (no sys.exit) -- git treats the
        # command's plain exit(0) as a non-conflicted merge.
        _merge_driver(root, _cfg(base, ours, theirs, path=root))

        result_text = ours.read_text()
        assert "Ours-side ticket" in result_text
        assert "Theirs-side ticket" in result_text

    def test_same_id_newer_state_wins_and_is_written_back(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverHandler.test_same_id_newer_state_wins_and_is_written_back  # noqa: E501
        root = tmp_path / "root"
        root.mkdir()
        atomic_write(ledger_path(root), "# Tickets\n\n")
        created = new_ticket(root, _spec("Shared ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        ours_text = ledger_path(root).read_text()

        assert transition(root, tid, TicketState.PLANNED).is_ok
        theirs_text = ledger_path(root).read_text()

        base = tmp_path / "base.md"
        ours = tmp_path / "ours.md"
        theirs = tmp_path / "theirs.md"
        base.write_text("# Tickets\n\n")
        ours.write_text(ours_text)
        theirs.write_text(theirs_text)

        _merge_driver(root, _cfg(base, ours, theirs, path=root))

        result_text = ours.read_text()
        assert "state: planned" in result_text
        assert "state: queued" not in result_text

    def test_malformed_theirs_exits_nonzero_and_leaves_ours_untouched(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverHandler.test_malformed_theirs_exits_nonzero_and_leaves_ours_untouched  # noqa: E501
        root = tmp_path / "root"
        root.mkdir()
        atomic_write(ledger_path(root), "# Tickets\n\n")
        created = new_ticket(root, _spec("Ours ticket"))
        assert created.is_ok
        ours_text = ledger_path(root).read_text()

        base = tmp_path / "base.md"
        ours = tmp_path / "ours.md"
        theirs = tmp_path / "theirs.md"
        base.write_text("# Tickets\n\n")
        ours.write_text(ours_text)
        theirs.write_text("# Tickets\n\n<!-- ticket:T-0002 -->\nno frontmatter here\n")

        with pytest.raises(SystemExit) as exc:
            _merge_driver(root, _cfg(base, ours, theirs, path=root))
        assert exc.value.code == 1

        # A failed splice must never overwrite ours -- git falls back to
        # its normal conflict report over whatever is on disk.
        assert ours.read_text() == ours_text

    def test_missing_args_exits_nonzero(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverHandler.test_missing_args_exits_nonzero  # noqa: E501
        cfg = AppConfig(ticket_path=tmp_path)
        with pytest.raises(SystemExit) as exc:
            _merge_driver(tmp_path, cfg)
        assert exc.value.code == 1

    def test_base_o_arg_prevents_wrong_side_merge_via_live_driver(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverHandler.test_base_o_arg_prevents_wrong_side_merge_via_live_driver  # noqa: E501
        # frob:ticket T-1165
        # T-1165 (T-1154 follow-up): T-1154 fixed this exact wrong-side-merge
        # tiebreak for `land`'s own internal splice call, but
        # `_merge_driver` (the LIVE `git merge` entry point) discarded
        # git's own %O merge-base argument entirely -- a real `git merge`
        # through the registered driver had no such protection. Reproduce
        # T-1154's tie shape (both sides at state=done, same evidence
        # count -- richness tied) directly at the merge-driver's own
        # base/ours/theirs file boundary: `ours` makes a real content edit
        # since `base`, `theirs` is byte-identical to `base` (no edit at
        # all). Pre-T-1165 (base_text never threaded through, so
        # `_resolve_divergence` always fell back to `_newer`'s tier-3
        # `b`-wins tiebreak) this reverted `ours`'s real edit in favor of
        # `theirs`'s untouched copy -- exactly the incident T-1154's Done
        # report named as "observed live during T-1154's own worktree
        # warm-up".
        root = tmp_path / "root"
        root.mkdir()
        atomic_write(ledger_path(root), "# Tickets\n\n")
        created = new_ticket(root, _spec("Shared ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(root, tid, TicketState.PLANNED).is_ok
        assert transition(root, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(root)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(root, ticket).is_ok
        assert transition(root, tid, TicketState.DONE).is_ok
        base_text = ledger_path(root).read_text()

        # `ours`: a real content edit since base (the T-1143 shape -- an
        # evidence-path migration inside the Done report text), same
        # state/evidence count as base, so richness alone cannot tell
        # ours and theirs apart without the base-aware tiebreak.
        ours_text = base_text.replace(
            "evidence attached", "evidence attached (src/parse/mod.py)"
        )
        # `theirs`: byte-identical to base -- no edit at all.
        theirs_text = base_text

        base = tmp_path / "base.md"
        ours = tmp_path / "ours.md"
        theirs = tmp_path / "theirs.md"
        base.write_text(base_text)
        ours.write_text(ours_text)
        theirs.write_text(theirs_text)

        _merge_driver(root, _cfg(base, ours, theirs, path=root))

        result_text = ours.read_text()
        assert "src/parse/mod.py" in result_text, (
            "ours's real content edit was reverted in favor of theirs's "
            "untouched copy -- the %O base argument was not threaded "
            "through to splice_ledger (T-1165 regression)"
        )

    def test_missing_base_file_degrades_to_newer_only_tiebreak(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverHandler.test_missing_base_file_degrades_to_newer_only_tiebreak  # noqa: E501
        # frob:ticket T-1165
        # A base (%O) path git failed to populate (or that vanished before
        # we read it) must degrade to the pre-T-1165 `_newer`-only
        # tiebreak, never raise or refuse the merge -- git always supplies
        # %O for a registered driver, but this is a defensive posture, not
        # a documented failure mode.
        root = tmp_path / "root"
        root.mkdir()
        atomic_write(ledger_path(root), "# Tickets\n\n")
        created = new_ticket(root, _spec("Shared ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        ours_text = ledger_path(root).read_text()
        assert transition(root, tid, TicketState.PLANNED).is_ok
        theirs_text = ledger_path(root).read_text()

        base = tmp_path / "does-not-exist.md"
        ours = tmp_path / "ours.md"
        theirs = tmp_path / "theirs.md"
        ours.write_text(ours_text)
        theirs.write_text(theirs_text)

        _merge_driver(root, _cfg(base, ours, theirs, path=root))

        result_text = ours.read_text()
        assert "state: planned" in result_text
        assert "state: queued" not in result_text


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A main checkout with an initialized ledger, the driver registered
    (`git config` + `.gitattributes`), and one committed file."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    atomic_write(ledger_path(main_repo), "# Tickets\n\n")
    # .frob/ is local state (T-0178 telemetry writes .frob/telemetry.jsonl on
    # every CLI call); gitignore it so the clean-status assertions below are
    # not tripped by an incidental untracked telemetry file. `.coverage*` is
    # the same class: under `make coverage` the subprocess .pth hook drops a
    # `.coverage.<host>.<pid>.<rand>` file into whatever cwd the child ran in,
    # which is this fixture repo.
    (main_repo / ".gitignore").write_text(".frob/\n.coverage*\n")
    (main_repo / ".gitattributes").write_text("tickets.md merge=frob-ledger\n")
    _run(
        [
            "git",
            "config",
            "merge.frob-ledger.name",
            "frob ticket ledger splice",
        ],
        main_repo,
    )
    _run(
        [
            "git",
            "config",
            "merge.frob-ledger.driver",
            "uv run frob ticket merge-driver %O %A %B",
        ],
        main_repo,
    )
    _commit_all(main_repo, "init")
    return main_repo


class TestMergeDriverViaRealGit:
    """End-to-end: a real `git merge` between two branches that each
    independently appended a ticket near the same ledger line -- the
    false-conflict class T-0323 removes the manual splice_ledger-by-hand
    step for."""

    def test_real_git_merge_auto_splices_both_sides_append(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit.test_real_git_merge_auto_splices_both_sides_append  # noqa: E501
        _run(["git", "checkout", "-q", "-b", "feature"], repo)
        # T-2120: no_commit=True -- new_ticket (T-1758) auto-commits the
        # ledger write itself by default, which would leave nothing for
        # this fixture's own _commit_all to commit.
        feature_created = new_ticket(
            repo, _spec("Feature-branch ticket"), no_commit=True
        )
        assert feature_created.is_ok
        feature_tid = feature_created.danger_ok.id
        _commit_all(repo, "feature: file a ticket")

        _run(["git", "checkout", "-q", "main"], repo)
        main_created = new_ticket(repo, _spec("Main-branch ticket"), no_commit=True)
        assert main_created.is_ok
        main_tid = main_created.danger_ok.id
        _commit_all(repo, "main: file a ticket")

        merge = subprocess.run(
            ["git", "merge", "-q", "--no-edit", "feature"],
            cwd=str(repo),
            capture_output=True,
            text=True,
        )
        assert merge.returncode == 0, (
            f"expected the frob-ledger driver to auto-splice cleanly, got "
            f"a real conflict instead: stdout={merge.stdout!r} "
            f"stderr={merge.stderr!r}"
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""

        merged = load_all(repo)
        assert merged.is_ok
        assert feature_tid in merged.danger_ok
        assert main_tid in merged.danger_ok
        assert merged.danger_ok[feature_tid].title == "Feature-branch ticket"
        assert merged.danger_ok[main_tid].title == "Main-branch ticket"

    # frob:ticket T-1437
    # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit.test_merge_driver_reads_archived_ids_from_merge_head_not_stale_disk  # noqa: E501
    def test_merge_driver_reads_archived_ids_from_merge_head_not_stale_disk(
        self, repo: Path
    ) -> None:
        """T-1437's own incident shape: a ticket done+archived on `main`
        AFTER a feature branch already branched off (so the feature
        branch's own on-disk `tickets-archive.md` has never seen the
        archive at all -- a plain disk read from inside the feature
        checkout would see it as NOT archived). `_merge_driver` must still
        resolve it as archived by reading `MERGE_HEAD`'s real committed
        content via git objects, not the stale disk copy.

        Drives a REAL, in-progress git merge (`git merge --no-commit`,
        driver NOT registered so git leaves an ordinary conflict rather
        than auto-splicing) purely to get a genuine `MERGE_HEAD` ref set
        on disk, then calls `_merge_driver` DIRECTLY, in-process (so this
        test exercises the actual editable-install code under test, not
        whatever `frob` a shelled-out `uv run` would resolve to from a
        tmp-dir cwd with no pyproject.toml -- see `TestMergeDriverHandler`
        for this repo's own precedent of calling `_merge_driver` directly
        rather than through a spawned CLI)."""
        # T-2120: no_commit=True -- new_ticket (T-1758) auto-commits the
        # ledger write itself by default, which would leave nothing for
        # this fixture's own _commit_all to commit.
        created = new_ticket(repo, _spec("Will be archived on main"), no_commit=True)
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "file the ticket that will later be archived")

        _run(["git", "checkout", "-q", "-b", "feature"], repo)
        # Feature does its own unrelated work -- nothing touching `tid` --
        # so tickets.md genuinely diverges on both sides (a real 3-way
        # merge is needed, not a fast-forward).
        unrelated = new_ticket(repo, _spec("Unrelated feature work"), no_commit=True)
        assert unrelated.is_ok
        unrelated_tid = unrelated.danger_ok.id
        _commit_all(repo, "feature: unrelated work")

        _run(["git", "checkout", "-q", "main"], repo)
        _make_closeable(repo, tid)
        assert transition(repo, tid, TicketState.DONE).is_ok
        from frob.tickets import archive

        archived_count = archive(repo)
        assert archived_count.is_ok and archived_count.danger_ok == 1
        _commit_all(repo, "main: close and archive the ticket")
        main_tip = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        # Confirm the precondition: `tid` really is only on main's side at
        # this point, feature's checkout has never seen it archived.
        _run(["git", "checkout", "-q", "feature"], repo)
        pre_merge_archive = load_archive(repo)
        assert pre_merge_archive.is_ok
        assert tid not in pre_merge_archive.danger_ok

        # A plain `git merge --no-commit` that FORCES the registered
        # driver off for this one invocation (`-c
        # merge.frob-ledger.driver=false`, git's own documented way to
        # make a path's custom merge driver always fail) genuinely
        # conflicts on tickets.md and leaves MERGE_HEAD pointing at main's
        # tip -- exactly what a live driver invocation would see mid-merge,
        # without this test depending on the `repo` fixture's already-
        # registered driver command (a shelled-out `uv run frob`, which
        # resolves to whatever `frob` a tmp-dir cwd's `uv run` finds --
        # not necessarily this worktree's own patched code under test).
        merge = subprocess.run(
            [
                "git",
                "-c",
                "merge.frob-ledger.driver=false",
                "merge",
                "--no-commit",
                "--no-ff",
                "main",
            ],
            cwd=str(repo),
            capture_output=True,
            text=True,
        )
        assert merge.returncode != 0, "expected a real conflict, not a clean merge"
        merge_head = _run(["git", "rev-parse", "MERGE_HEAD"], repo).stdout.strip()
        assert merge_head == main_tip

        base_sha = _run(["git", "merge-base", "feature", "main"], repo).stdout.strip()
        ours_text = _run(["git", "show", "feature:tickets.md"], repo).stdout
        theirs_text = _run(["git", "show", f"{main_tip}:tickets.md"], repo).stdout
        base_text = _run(["git", "show", f"{base_sha}:tickets.md"], repo).stdout

        ours_path = repo / "ours.md"
        theirs_path = repo / "theirs.md"
        base_path = repo / "base.md"
        ours_path.write_text(ours_text)
        theirs_path.write_text(theirs_text)
        base_path.write_text(base_text)

        _merge_driver(
            repo,
            AppConfig(
                ticket_merge_base=base_path,
                ticket_merge_ours=ours_path,
                ticket_merge_theirs=theirs_path,
                ticket_path=repo,
            ),
        )

        spliced_text = ours_path.read_text()
        assert f"<!-- ticket:{tid} -->" not in spliced_text, (
            f"{tid} was resurrected into the spliced tickets.md despite "
            "being archived on main (T-1437 regression) -- "
            "_archived_ids_for_merge_driver did not see MERGE_HEAD's "
            "committed archive content"
        )
        assert f"<!-- ticket:{unrelated_tid} -->" in spliced_text

        # Clean up the in-progress conflicted merge state this test set up
        # purely to get a real MERGE_HEAD -- never leave it dangling for
        # git's own working-tree assertions elsewhere in this test class.
        subprocess.run(["git", "merge", "--abort"], cwd=str(repo), capture_output=True)


# frob:ticket T-3297
class TestMergeDriverContentShapeDispatch:
    """T-3297: `_merge_driver` is now ALSO registered (via `.gitattributes`,
    see that file's own T-3297 note) for `tickets/<id>/ticket.md` (v2
    per-ticket files) and `frob-coverage.lock.json`, neither of which had
    any merge driver before -- git's raw textual 3-way merge cannot
    resolve either shape and, per the reported incident, can commit
    literal conflict markers into `ticket.md`. Since git's merge-driver
    protocol hands `_merge_driver` %O/%A/%B temp files, never the real
    path, dispatch is by CONTENT SHAPE -- these tests exercise that
    dispatch directly against synthetic files, no git subprocess."""

    # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverContentShapeDispatch.test_single_ticket_file_conflict_resolves_by_state_precedence_must_fire  # noqa: E501
    def test_single_ticket_file_conflict_resolves_by_state_precedence_must_fire(
        self, tmp_path: Path
    ) -> None:
        """MUST-FIRE fixture (the ticket's own acceptance test): two
        branches each independently mutated the SAME ticket's state -- one
        to `done`, one still `in-progress` -- merged through the driver.
        The result must be the terminal (`done`) state, never conflict
        markers written into the committed file."""
        from frob.tickets._store import _parse_ticket_text, _serialize_ticket

        root = tmp_path / "root"
        root.mkdir()
        created = new_ticket(root, _spec("Racing ticket"))
        assert created.is_ok
        ticket = created.danger_ok

        in_progress = ticket.model_copy(update={"state": TicketState.IN_PROGRESS})
        done = ticket.model_copy(
            update={
                "state": TicketState.DONE,
                "evidence": ("tests/test_x.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )

        base = tmp_path / "base.md"
        ours = tmp_path / "ours.md"
        theirs = tmp_path / "theirs.md"
        base.write_text(_serialize_ticket(ticket))
        ours.write_text(_serialize_ticket(in_progress))
        theirs.write_text(_serialize_ticket(done))

        _merge_driver(root, _cfg(base, ours, theirs, path=root))

        result_text = ours.read_text()
        assert "<<<<<<<" not in result_text and ">>>>>>>" not in result_text, (
            "conflict markers were written into the merged ticket file -- "
            "exactly the incident this ticket exists to prevent"
        )
        resolved = _parse_ticket_text(result_text, "merged")
        assert resolved.is_ok, f"merged ticket file failed to re-parse: {result_text!r}"
        assert resolved.danger_ok.state == TicketState.DONE, (
            "terminal state (done) must win over in-progress regardless of "
            "which side is 'ours'/'theirs' -- got "
            f"{resolved.danger_ok.state!r}"
        )

    # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverContentShapeDispatch.test_single_ticket_file_dropped_beats_queued_must_fire  # noqa: E501
    def test_single_ticket_file_dropped_beats_queued_must_fire(
        self, tmp_path: Path
    ) -> None:
        """F-038's exact reported shape: a ticket filed from a worktree
        (still `queued` there) and dropped on main -- merged through the
        driver, `dropped` (terminal) must win, never a conflict."""
        from frob.tickets._store import _parse_ticket_text, _serialize_ticket

        root = tmp_path / "root"
        root.mkdir()
        created = new_ticket(root, _spec("Out-of-scope discovery"))
        assert created.is_ok
        ticket = created.danger_ok
        dropped = ticket.model_copy(update={"state": TicketState.DROPPED})

        base = tmp_path / "base.md"
        ours = tmp_path / "ours.md"
        theirs = tmp_path / "theirs.md"
        base.write_text(_serialize_ticket(ticket))
        ours.write_text(_serialize_ticket(ticket))  # worktree: still queued
        theirs.write_text(_serialize_ticket(dropped))  # main: dropped

        _merge_driver(root, _cfg(base, ours, theirs, path=root))

        result_text = ours.read_text()
        assert "<<<<<<<" not in result_text
        resolved = _parse_ticket_text(result_text, "merged")
        assert resolved.is_ok
        assert resolved.danger_ok.state == TicketState.DROPPED

    # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverContentShapeDispatch.test_coverage_lock_shaped_conflict_merges_elementwise_max  # noqa: E501
    def test_coverage_lock_shaped_conflict_merges_elementwise_max(
        self, tmp_path: Path
    ) -> None:
        """`frob-coverage.lock.json`'s JSON shape is recognized and merged
        via the T-1434 elementwise-max-per-module strategy, never a
        textual merge that could silently drop one side's freshly stamped
        numbers."""
        import json

        root = tmp_path / "root"
        root.mkdir()

        base = tmp_path / "base.json"
        ours = tmp_path / "ours.json"
        theirs = tmp_path / "theirs.json"
        base.write_text(
            json.dumps({"source_sha": "base", "module_line": {"a": 50.0}})
        )
        ours.write_text(
            json.dumps(
                {"source_sha": "ours", "module_line": {"a": 60.0, "b": 40.0}}
            )
        )
        theirs.write_text(
            json.dumps(
                {"source_sha": "theirs", "module_line": {"a": 55.0, "b": 70.0}}
            )
        )

        _merge_driver(root, _cfg(base, ours, theirs, path=root))

        merged = json.loads(ours.read_text())
        assert merged["module_line"] == {"a": 60.0, "b": 70.0}, (
            "expected the higher of both sides' per-module percentage, "
            f"got {merged['module_line']!r}"
        )

    # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverContentShapeDispatch.test_whole_ledger_shape_still_falls_back_to_splice_ledger_must_stay_quiet  # noqa: E501
    def test_whole_ledger_shape_still_falls_back_to_splice_ledger_must_stay_quiet(
        self, tmp_path: Path
    ) -> None:
        """MUST-STAY-QUIET (regression guard): the legacy whole-ledger
        `tickets.md` shape -- neither a single ticket file nor a
        coverage-lock JSON doc -- must still route through the ORIGINAL
        `splice_ledger` path unchanged; the new content-shape dispatch
        added by T-3297 must not intercept or otherwise disturb it."""
        root = tmp_path / "root"
        root.mkdir()
        atomic_write(ledger_path(root), "# Tickets\n\n")

        ours_created = new_ticket(root, _spec("Ours-side ticket"))
        assert ours_created.is_ok
        ours_text = ledger_path(root).read_text()

        theirs_root = tmp_path / "theirs"
        theirs_root.mkdir()
        theirs_ticket = ours_created.danger_ok.model_copy(
            update={"id": "T-0002", "title": "Theirs-side ticket"}
        )
        atomic_write(ledger_path(theirs_root), "# Tickets\n\n")
        assert write_ticket(theirs_root, theirs_ticket).is_ok
        theirs_text = ledger_path(theirs_root).read_text()

        base = tmp_path / "base.md"
        ours = tmp_path / "ours.md"
        theirs = tmp_path / "theirs.md"
        base.write_text("# Tickets\n\n")
        ours.write_text(ours_text)
        theirs.write_text(theirs_text)

        _merge_driver(root, _cfg(base, ours, theirs, path=root))

        result_text = ours.read_text()
        assert "Ours-side ticket" in result_text
        assert "Theirs-side ticket" in result_text


# frob:ticket T-3297
class TestMergeDriverV2TicketFileViaRealGit:
    """T-3297 end-to-end: real `git merge` exercising the NEW
    `tickets/*/ticket.md merge=frob-ledger` and `frob-coverage.lock.json
    merge=frob-ledger` `.gitattributes` registrations this ticket adds --
    without them, git never even invokes the driver for these paths, no
    matter how correct its content-shape dispatch is."""

    @pytest.fixture
    def v2_repo(self, tmp_path: Path) -> tuple[Path, str]:
        """A main checkout with BOTH the v1 `tickets.md` line (existing,
        unrelated to this ticket) and the new v2/coverage-lock lines
        registered, one shared `merge.frob-ledger.driver` git config
        entry (matching the real `.gitattributes` this ticket adds)."""
        main_repo = tmp_path / "main"
        _git_init(main_repo)
        (main_repo / ".gitignore").write_text(".frob/\n.coverage*\n")
        (main_repo / ".gitattributes").write_text(
            "tickets/*/ticket.md merge=frob-ledger\n"
            "frob-coverage.lock.json merge=frob-ledger\n"
        )
        _run(
            ["git", "config", "merge.frob-ledger.name", "frob ticket ledger splice"],
            main_repo,
        )
        _run(
            [
                "git",
                "config",
                "merge.frob-ledger.driver",
                "uv run frob ticket merge-driver %O %A %B",
            ],
            main_repo,
        )
        from frob.tickets._store import _serialize_ticket

        spec_created = new_ticket(main_repo, _spec("v2 ticket"), no_commit=True)
        assert spec_created.is_ok
        tid = spec_created.danger_ok.id
        ticket_dir = main_repo / "tickets" / tid
        ticket_dir.mkdir(parents=True, exist_ok=True)
        (ticket_dir / "ticket.md").write_text(
            _serialize_ticket(spec_created.danger_ok)
        )
        # T-0323/T-1758's `new_ticket` writes the v1 monofile by default;
        # this fixture only needs a v2-shaped file on disk to register the
        # NEW attribute against, so its own monofile write is harmless
        # noise here -- remove it so this fixture is unambiguously v2-shaped.
        if ledger_path(main_repo).exists():
            ledger_path(main_repo).unlink()
        _commit_all(main_repo, "init")
        return main_repo, tid

    # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverV2TicketFileViaRealGit.test_ordinary_land_with_no_divergence_merges_cleanly_must_stay_quiet  # noqa: E501
    def test_ordinary_land_with_no_divergence_merges_cleanly_must_stay_quiet(
        self, v2_repo: tuple[Path, str]
    ) -> None:
        """MUST-STAY-QUIET fixture (the ticket's own acceptance test): an
        ordinary land where the v2 ticket file did NOT diverge between
        main and the worktree branch -- registering the new merge=
        attribute must not introduce any new conflict, prompt, or content
        change on this common path."""
        repo, tid = v2_repo
        _run(["git", "checkout", "-q", "-b", "feature"], repo)
        (repo / "unrelated.txt").write_text("feature work\n")
        _commit_all(repo, "feature: unrelated change")

        _run(["git", "checkout", "-q", "main"], repo)
        (repo / "other.txt").write_text("main work\n")
        _commit_all(repo, "main: unrelated change")

        merge = subprocess.run(
            ["git", "merge", "-q", "--no-edit", "feature"],
            cwd=str(repo),
            capture_output=True,
            text=True,
        )
        assert merge.returncode == 0, (
            f"expected a clean merge with no divergence on the v2 ticket "
            f"file: stdout={merge.stdout!r} stderr={merge.stderr!r}"
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""
        assert (repo / "tickets" / tid / "ticket.md").exists()

    # frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverV2TicketFileViaRealGit.test_diverged_ticket_state_merges_cleanly_via_registered_driver  # noqa: E501
    def test_diverged_ticket_state_merges_cleanly_via_registered_driver(
        self, v2_repo: tuple[Path, str]
    ) -> None:
        """MUST-FIRE, end-to-end: with the `.gitattributes` registration
        this ticket adds in place, a REAL `git merge` where both branches
        mutated the same v2 ticket file's state resolves cleanly (no
        conflict, no markers) via the driver's new dispatch, keeping the
        terminal state."""
        from frob.tickets._store import _parse_ticket_text

        repo, tid = v2_repo
        ticket_path = repo / "tickets" / tid / "ticket.md"

        _run(["git", "checkout", "-q", "-b", "feature"], repo)
        loaded = load_all(repo)
        assert loaded.is_ok
        in_progress = loaded.danger_ok[tid].model_copy(
            update={"state": TicketState.IN_PROGRESS}
        )
        from frob.tickets._store import _serialize_ticket

        ticket_path.write_text(_serialize_ticket(in_progress))
        _commit_all(repo, "feature: start work")

        _run(["git", "checkout", "-q", "main"], repo)
        done = loaded.danger_ok[tid].model_copy(
            update={
                "state": TicketState.DONE,
                "evidence": ("tests/test_x.py::test_ok",),
                "body": loaded.danger_ok[tid].body
                + "\n## Done report\n\nevidence attached\n",
            }
        )
        ticket_path.write_text(_serialize_ticket(done))
        _commit_all(repo, "main: close it directly")

        merge = subprocess.run(
            ["git", "merge", "-q", "--no-edit", "feature"],
            cwd=str(repo),
            capture_output=True,
            text=True,
        )
        assert merge.returncode == 0, (
            f"expected the registered frob-ledger driver to auto-resolve "
            f"the diverged ticket state, got a real conflict instead: "
            f"stdout={merge.stdout!r} stderr={merge.stderr!r}"
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""

        merged_text = ticket_path.read_text()
        assert "<<<<<<<" not in merged_text and ">>>>>>>" not in merged_text
        resolved = _parse_ticket_text(merged_text, "merged")
        assert resolved.is_ok
        assert resolved.danger_ok.state == TicketState.DONE
